from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models.family import Family, Member
from app.repositories.base import IFamilyRepository
from app.schemas.family import FamilyCreate, FamilyUpdate


class FamilyRepository(IFamilyRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create(self, family_data: FamilyCreate) -> Family:
        existing_head = await self.db.execute(
            select(Member).where(Member.id == family_data.head_id)
        )
        if existing_head.scalar_one_or_none():
            raise ConflictError(
                code="family_already_exists",
                message=f"The head member with id {family_data.head_id} already exists.",
            )
        family = Family(
            **family_data.model_dump(exclude={"members", "head_id", "spouse_id"})
        )
        self.db.add(family)
        await self.db.flush()
        await self.db.refresh(family)
        return family

    async def get_all(self, skip=0, limit=20, is_active=True) -> list[Family]:
        result = await self.db.execute(
            select(Family)
            .where(Family.is_active == is_active)
            .order_by(Family.id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_head_id(self, head_id: int) -> Family | None:
        result = await self.db.execute(select(Family).where(Family.head_id == head_id))
        family = result.scalar_one_or_none()
        if not family:
            return None
        return family

    async def get_by_head_name(
        self,
        head_name: str,
        skip: int = 0,
        limit: int = 20,
        active: bool = True,
    ) -> list[Family]:

        query = select(Family).join(Member, Family.head_id == Member.id)
        if active:
            query = query.where(Family.is_active == active)
        query = (
            (
                query.where(Member.full_name.ilike(f"%{head_name}%")).order_by(
                    func.similarity(Member.full_name, head_name).desc()
                )
            ).offset((skip - 1) * limit)
        ).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_family_id(self, family_id: int) -> Family | None:
        result = await self.db.execute(
            select(Family)
            .options(selectinload(Family.members))
            .where(Family.id == family_id)
        )
        return result.scalar_one_or_none()

    async def archive(self, family_id: int) -> Family:
        family = await self.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with id {family_id} not found",
            )
        family.is_active = False
        family.archived_at = datetime.now(UTC)
        await self.db.commit()
        return family

    async def activate(self, family_id: int) -> Family:
        family = await self.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with id {family_id} not found",
            )
        family.is_active = True
        family.archived_at = None
        await self.db.commit()
        return family

    async def update(self, family_id: int, family_data: FamilyUpdate) -> Family:
        family = await self.get_by_family_id(family_id=family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with family id {family_id} not found",
            )
        for key, value in family_data.model_dump(exclude_unset=True).items():
            setattr(family, key, value)
        await self.db.commit()
        return family

    async def commit(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()
