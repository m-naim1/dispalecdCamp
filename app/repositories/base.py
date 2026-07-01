from abc import ABC, abstractmethod

from app.models.family import Family, Member
from app.models.user import User
from app.schemas.family import (
    FamilyCreate,
    FamilyUpdate,
    MemberCreate,
    MemberUpdate,
)
from app.schemas.user import UserCreate, UserUpdate


class IFamilyRepository(ABC):
    @abstractmethod
    async def create(self, family_data: FamilyCreate) -> Family:
        pass

    @abstractmethod
    async def get_all(self, skip: int, limit: int, is_active: bool) -> list[Family]:
        pass

    @abstractmethod
    async def get_by_head_id(self, head_id: int) -> Family | None:
        pass

    @abstractmethod
    async def get_by_head_name(self, head_name: str,skip: int = 0, limit: int = 100, active: bool = True) -> list[Family]:
        pass

    @abstractmethod
    async def get_by_family_id(self, family_id: int) -> Family | None:
        pass

    @abstractmethod
    async def archive(self, family_id: int) -> Family:
        pass

    @abstractmethod
    async def activate(self, family_id: int) -> Family:
        pass

    @abstractmethod
    async def update(self, family_id: int, family_data: FamilyUpdate) -> Family:
        pass

    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass


class IMemberRepository(ABC):
    @abstractmethod
    async def create(self, family_id: int, member: MemberCreate) -> Member:
        pass

    @abstractmethod
    async def get_all(self) -> list[Member]:
        pass

    @abstractmethod
    async def delete(self, member_id: int) -> Member:
        pass

    @abstractmethod
    async def get_by_id(self, member_id: int) -> Member | None:
        pass

    @abstractmethod
    async def get_by_name(self, member_name: str) -> list[Member] | None:
        pass

    @abstractmethod
    async def update(self, member_id: int, member_data: MemberUpdate) -> Member:
        pass

    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        pass

    @abstractmethod
    async def get_all(self) -> list[User]:
        pass

    @abstractmethod
    async def create(self, user_in: UserCreate, hashed_password: str) -> User:
        pass

    @abstractmethod
    async def update(
        self, user_id: int, user_data: UserUpdate, hashed_password: str
    ) -> User:
        pass

    @abstractmethod
    async def archive(self, user_id: int) -> User | None:
        pass

    @abstractmethod
    async def check_username_and_email(self, username: str, email: str):
        pass
