from abc import ABC, abstractmethod

from app.schemas.family import (
    FamilyCreate,
    FamilyResponse,
    FamilyUpdate,
    MemberCreate,
    MemberResponse,
    MemberUpdate,
)


class IFamilyRepository(ABC):
    @abstractmethod
    async def create(self, family_data: FamilyCreate) -> FamilyResponse:
        pass

    @abstractmethod
    async def get_all(self) -> list[FamilyResponse]:
        pass

    @abstractmethod
    async def get_by_head_id(self, headId: int) -> FamilyResponse | None:
        pass

    @abstractmethod
    async def get_by_head_name(self, headName: str) -> list[FamilyResponse]:
        pass

    @abstractmethod
    async def get_by_family_id(self, familyId: int) -> FamilyResponse | None:
        pass

    @abstractmethod
    async def archive(self, familyId: int) -> FamilyResponse:
        pass

    @abstractmethod
    async def activate(self, familyId: int) -> FamilyResponse:
        pass

    @abstractmethod
    async def update_family(self, familyId: int, family_data: FamilyUpdate) -> FamilyResponse:
        pass

    @abstractmethod
    async def commit(self):
        pass


class IMemberRepository(ABC):
    @abstractmethod
    async def create(self, family_id: int, member: MemberCreate) -> MemberResponse:
        pass

    @abstractmethod
    async def get_all(self) -> list[MemberResponse]:
        pass

    @abstractmethod
    async def delete(self, memberId: int) -> MemberResponse:
        pass

    @abstractmethod
    async def get_by_id(self, memberId: int) -> MemberResponse | None:
        pass

    @abstractmethod
    async def get_by_name(self, memberName: str) -> list[MemberResponse] | None:
        pass

    @abstractmethod
    async def update_member(self, memberId: int, member_data: MemberUpdate) -> MemberResponse:
        pass

    @abstractmethod
    async def commit(self):
        pass
