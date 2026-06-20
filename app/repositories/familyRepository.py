from datetime import UTC, datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.family import Family, Member
from app.schemas.family import FamilyCreate, FamilyResponse, FamilyUpdate
from app.repositories.base import IFamilyRepository


class FamilyRepository(IFamilyRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def _get_family(self, familyId) -> Family | None:
        result = await self.db.execute(select(Family).where(Family.id == familyId))
        return result.scalar_one_or_none()

    async def create(self, family_data: FamilyCreate) -> FamilyResponse:
        existing_head = await self.db.execute(
            select(Member).where(Member.id == family_data.head_id)
        )
        if existing_head.scalar_one_or_none():
            raise ConflictError(
                code="family_already_exists",
                message=f"The head member with id {family_data.head_id} already exists.",
            )
        family = Family(family_data.model_dump(exclude={"members"}))
        self.db.add(family)
        await self.db.flush()
        await self.db.refresh(family)
        return FamilyResponse.model_validate(family)

    async def get_all(self) -> list[FamilyResponse]:
        result = await self.db.execute(select(Family))
        return [FamilyResponse.model_validate(family) for family in result.all()]

    async def get_by_head_id(self, headId: int) -> FamilyResponse | None:
        result = await self.db.execute(select(Family).where(Family.head_id == headId))
        family = result.scalar_one_or_none()
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with head id {headId} not found",
            )

    async def get_by_head_name(self, headName: str) -> list[FamilyResponse]:
        result = await self.db.execute(
            select(Family)
            .join(Member, Family.head_id == Member.id)
            .where(Member.full_name.like(f"%{headName}%"))
        )
        families = result.all()
        return [FamilyResponse.model_validate(family) for family in families]

    async def get_by_family_id(self, familyId: int) -> FamilyResponse | None:
        return await self._get_family(familyId=familyId)

    async def archive(self, familyId: int) -> FamilyResponse:
        family = await self._get_family(familyId)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with id {familyId} not found",
            )
        await self.db.execute(
            update(Family)
            .where(Family.id == familyId)
            .values(is_active=False, archived_at=datetime.now(UTC))
        )
        await self.db.flush()
        await self.db.refresh(family)
        return FamilyResponse.model_validate(family)

    async def activate(self, familyId: int) -> FamilyResponse:
        family = await self._get_family(familyId)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with id {familyId} not found",
            )
        await self.db.execute(
            update(Family)
            .where(Family.id == familyId)
            .values(is_active=True, archived_at=datetime.now(UTC))
        )
        await self.db.flush()
        await self.db.refresh(family)
        return FamilyResponse.model_validate(family)

    async def update_family(
        self, familyId: int, family_data: FamilyUpdate
    ) -> FamilyResponse:
        family = await self._get_family(familyId=familyId)
        if not family:
            raise NotFoundError(
                code="Family_not_Found",
                message=f"Family with family id {familyId} not found",
            )
        await self.db.execute(
            update(Family)
            .where(Family.id == familyId)
            .values(**family_data.model_dump(exclude_unset=True))
        )
        await self.db.flush()
        await self.db.refresh(family)
        return FamilyResponse.model_validate(family)

    async def commit(self):
        await self.db.commit()
