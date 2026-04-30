from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from sqlalchemy import select
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.db.session import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models.user import User
from app.models.enums import UserRole

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db


async def get_current_user(
    token: str = Depends(oauth2_schema), db: AsyncSession = Depends(get_db)
) -> User | dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    role = payload.get("role")

    # Family token — no User row exists
    if role == UserRole.FAMILY:
        family_id = payload.get("family_id")
        if not family_id:
            raise credentials_exception
        return {"role": UserRole.FAMILY, "family_id": family_id}

    # System user token
    username: str = payload.get("sub")  # type: ignore
    if not username:
        raise credentials_exception
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_role(*allowed_roles: UserRole):
    def checker(current_user=Depends(get_current_user)) -> User | dict:
        user_role = (
            current_user.role
            if isinstance(current_user, User)
            else current_user.get("role")
        )
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return checker
