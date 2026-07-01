import asyncio
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

# from passlib.context import CryptContext
from app.core.config import settings

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return bcrypt.checkpw(
#         plain_password.encode("utf-8"), hashed_password.encode("utf-8")
#     )
async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(
        bcrypt.checkpw, plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


async def get_password_hash(password: str) -> str:
    hash_pass_bytes = await asyncio.to_thread(
        bcrypt.hashpw, password.encode("utf-8"), bcrypt.gensalt()
    )
    return hash_pass_bytes.decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
