from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ConflictError
from app.models.family import Member
from app.schemas.family import MemberCreate, MemberResponse, MemberUpdate
from app.repositories.base import IMemberRepository


class MemberRepository(IMemberRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def _get_member(self, id: int) -> Member | None:
        result = await self.db.execute(select(Member).where(Member.id == id))
        return result.scalar_one_or_none()

    async def create(self, family_id: int, member: MemberCreate) -> MemberResponse:
        mem = await self._get_member(member.id)
        if mem:
            raise ConflictError(
                code="member_already_exists",
                message=f"Member with the {member.id} already exists in another family.",
            )

        new_member = Member(**member.model_dump(), family_id=family_id)
        self.db.add(new_member)
        await self.db.flush()
        await self.db.refresh(new_member)
        return MemberResponse.model_validate(new_member)

    async def delete(self, memberId: int) -> MemberResponse:
        member = await self._get_member(memberId)
        if member:
            await self.db.delete(member)
            await self.db.commit()
            return MemberResponse.model_validate(member)
        raise NotFoundError(
            code="Member_not_Found", message=f"Member with id {memberId} not found"
        )

    async def get_by_id(self, memberId: int) -> MemberResponse | None:
        member = member = await self._get_member(memberId)
        if member:
            return MemberResponse.model_validate(member)
        return None
    async def get_all(self) -> list[MemberResponse]:
        result = await self.db.execute(select(Member))
        return [MemberResponse.model_validate(member) for member in  result.all()]
    
    async def get_by_name(self, memberName: str) -> list[MemberResponse] | None:
        result = await self.db.execute(
            select(Member).where(Member.full_name.like(f"%{memberName}%"))
        )
        members = result.all()
        if members:
            return [MemberResponse.model_validate(member) for member in members]
        return None

    async def update_member(
        self, memberId: int, member_data: MemberUpdate
    ) -> MemberResponse:
        member = await self._get_member(memberId)
        if not member:
            raise NotFoundError(
                code="Member_not_Found", message=f"Member with id {memberId} not found"
            )
        # for key, value in member_data.model_dump(exclude_unset=True).items():
        #     setattr(member,key,value)
        await self.db.execute(
            update(Member)
            .where(Member.id == memberId)
            .values(member_data.model_dump(exclude_unset=True))
        )
        await self.db.flush()
        await self.db.refresh(member)
        return MemberResponse.model_validate(member)

    async def commit(self):
        await self.db.commit()
