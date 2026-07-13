from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload, selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models.family import Family, Member
from app.models.lookups import City
from app.repositories.base import IFamilyRepository
from app.schemas.family import FamilyCreate, FamilyUpdate
from app.schemas.filters import FamilyFilterParams


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

    async def get_all(
        self, filters: FamilyFilterParams, skip: int = 0, limit: int = 100
    ) -> list[Family]:
        query = select(Family)

        # Single-value filters (Equality)
        if filters.is_active is not None:
            query = query.where(Family.is_active == filters.is_active)
        if filters.residency_status:
            query = query.where(Family.residency_status == filters.residency_status)
        if filters.female_headed is not None:
            query = query.where(Family.female_headed == filters.female_headed)
        if filters.child_headed is not None:
            query = query.where(Family.child_headed == filters.child_headed)

        # --- MULTI-VALUE FILTERS (.in_) ---
        if filters.housing_type:
            query = query.where(Family.housing_type.in_(filters.housing_type))
        if filters.current_shelter_center_id:
            query = query.where(
                Family.current_shelter_center_id.in_(filters.current_shelter_center_id)
            )
        if filters.shelter_block_id:
            query = query.where(Family.shelter_block_id.in_(filters.shelter_block_id))
        if filters.current_city_id:
            query = query.where(Family.current_city_id.in_(filters.current_city_id))
        if filters.original_city_id:
            query = query.where(Family.original_city_id.in_(filters.original_city_id))
        if filters.shelter_quality_id:
            query = query.where(
                Family.shelter_quality_id.in_(filters.shelter_quality_id)
            )

        # --- GOVERNOR FILTERS (Requires joining City table) ---
        if filters.current_governor_id or filters.original_governor_id:
            CurrentCity = aliased(City)
            OriginalCity = aliased(City)

            if filters.current_governor_id:
                query = query.join(
                    CurrentCity, Family.current_city_id == CurrentCity.id
                ).where(CurrentCity.governor_id.in_(filters.current_governor_id))
            if filters.original_governor_id:
                query = query.join(
                    OriginalCity, Family.original_city_id == OriginalCity.id
                ).where(OriginalCity.governor_id.in_(filters.original_governor_id))

        # Text search filters
        if filters.phone_number:
            query = query.where(
                Family.primary_phone_number.ilike(f"%{filters.phone_number}%")
            )

        if filters.head_name:
            query = (
                query.join(Member, Family.head_id == Member.id)
                .where(Member.full_name.ilike(f"%{filters.head_name}%"))
                .order_by(func.similarity(Member.full_name, filters.head_name).desc())
            )

        # Dynamic Sorting
        sort_by_field = filters.sort_by or "id"
        sort_column = getattr(Family, sort_by_field, Family.id)

        if filters.sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_head_id(self, head_id: int) -> Family | None:
        result = await self.db.execute(select(Family).where(Family.head_id == head_id))
        family = result.scalar_one_or_none()
        if not family:
            return None
        return family

    async def get_by_family_id(self, family_id: int) -> Family | None:
        result = await self.db.execute(
            select(Family)
            .options(selectinload(Family.members))
            .options(joinedload(Family.head))
            .options(joinedload(Family.spouse))
            .where(Family.id == family_id)
        )
        return result.unique().scalar_one_or_none()

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
