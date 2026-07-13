from abc import ABC, abstractmethod

from app.models.enums import UpdateRequestStatus, UpdateRequestType
from app.models.family import Family, FamilyUpdateRequest, Member
from app.models.user import User
from app.schemas.family import (
    FamilyCreate,
    FamilyUpdate,
    MemberCreate,
    MemberUpdate,
    UpdateRequestCreate,
)
from app.schemas.filters import FamilyFilterParams, MemberFilterParams
from app.schemas.user import UserCreate, UserUpdate


class IFamilyRepository(ABC):
    @abstractmethod
    async def create(self, family_data: FamilyCreate) -> Family:
        pass

    @abstractmethod
    async def get_all(
        self, filters: FamilyFilterParams, skip: int = 0, limit: int = 100
    ) -> list[Family]:
        pass

    @abstractmethod
    async def get_by_head_id(self, head_id: int) -> Family | None:
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
    async def create_many(
        self, family_id: int, members: list[MemberCreate]
    ) -> list[Member]:
        pass

    @abstractmethod
    async def create(self, family_id: int, member: MemberCreate) -> Member:
        pass

    @abstractmethod
    async def get_all(
        self, filters: MemberFilterParams, skip: int = 0, limit: int = 100
    ) -> list[Member]:
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


class IFamilyUpdateRequestRepository(ABC):
    @abstractmethod
    async def create(
        self, family_id: int, update_request: UpdateRequestCreate
    ) -> FamilyUpdateRequest:
        pass

    @abstractmethod
    async def get_all(
        self,
        shelter_center_id: int | None = None,
        block_id: int | None = None,
        family_id: int | None = None,
        request_status: UpdateRequestStatus = UpdateRequestStatus.PENDING,
        request_type: UpdateRequestType | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[FamilyUpdateRequest]:
        pass

    @abstractmethod
    async def get_by_id(self, update_request_id: int) -> FamilyUpdateRequest | None:
        pass

    @abstractmethod
    async def update(
        self, update_request_id: int, status: UpdateRequestStatus, user_reviewer_id: int
    ) -> FamilyUpdateRequest:
        pass
