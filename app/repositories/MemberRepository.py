from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.family import Member
from app.repositories.base import IMemberRepository
from app.schemas.family import MemberCreate, MemberUpdate


class MemberRepository(IMemberRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create(self, family_id: int, member: MemberCreate) -> Member:
        mem = await self.get_by_id(member.id)
        if mem:
            raise ConflictError(
                code="member_already_exists",
                message=f"Member with the {member.id} already exists in another family.",
            )

        new_member = Member(**member.model_dump(), family_id=family_id)
        self.db.add(new_member)
        await self.db.flush()
        await self.db.refresh(new_member)
        return new_member

    async def delete(self, member_id: int) -> Member:
        member = await self.get_by_id(member_id)
        if member:
            await self.db.delete(member)
            await self.db.commit()
            return member
        raise NotFoundError(
            code="Member_not_Found", message=f"Member with id {member_id} not found"
        )

    async def get_by_id(self, member_id: int) -> Member | None:
        result = await self.db.execute(select(Member).where(Member.id == member_id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 25) -> list[Member]:
        result = await self.db.execute(
            select(Member).order_by(Member.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, member_name: str, limit: int = 10
    ) -> list[Member] | None:
        result = await self.db.execute(
            select(Member).where(
                Member.full_name.ilike(f"%{member_name}%")
                .order_by(func.similarity(Member.full_name, member_name).desc())
                .limit(limit)
            )
        )
        members = result.scalars().all()
        if members:
            return list(members)
        return None

    async def update(self, member_id: int, member_data: MemberUpdate) -> Member:
        member = await self.get_by_id(member_id)
        if not member:
            raise NotFoundError(
                code="Member_not_Found", message=f"Member with id {member_id} not found"
            )
        for key, value in member_data.model_dump(exclude_unset=True).items():
            setattr(member, key, value)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def commit(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()
