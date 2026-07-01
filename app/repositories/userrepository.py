from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.user import User
from app.repositories.base import IUserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(IUserRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create(self, user_in: UserCreate, hashed_password: str) -> User:
        new_user = User(
            **user_in.model_dump(exclude={"password"}), hashed_password=hashed_password
        )
        self.db.add(new_user)
        await self.db.commit()
        return new_user

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, is_active: bool = True) -> User | None:
        query = select(User).where(User.email == email)
        if is_active:
            query = query.where(User.is_active == True)  # noqa: E712
        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_by_username(
        self, username: str, is_active: bool = True
    ) -> User | None:
        query = select(User).where(User.username == username)
        if is_active:
            query = query.where(User.is_active == True)  # noqa: E712
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self, is_active: bool = True, skip: int = 0, limit: int = 100
    ) -> list[User]:
        query = select(User)
        if is_active:
            query = query.where(User.is_active == True)  # noqa: E712
        query = query.offset(skip).limit(limit).order_by(User.id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, user_id: int, user_data: UserUpdate, hashed_password: str | None = None
    ) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                code="User_not_Found", message=f"User with id {user_id} not found"
            )
        for key, value in user_data.model_dump(
            exclude_unset=True, exclude={"password"}
        ).items():
            setattr(user, key, value)
        if hashed_password:
            user.hashed_password = hashed_password
        await self.db.commit()
        return user

    async def archive(self, user_id: int) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.is_active = False
        await self.db.commit()
        return user

    async def check_username_and_email(self, username: str, email: str) -> bool:
        """Check if a user with the given username or email already exists in the database."""
        result = await self.db.execute(
            select(User).where(or_(User.username == username, User.email == email))
        )
        if result.scalar_one_or_none():
            return True
        else:
            return False
