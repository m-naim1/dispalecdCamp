from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import ConflictError, NotFoundError
from app.models.family import Family, Member
from app.repositories.base import IMemberRepository
from app.schemas.family import MemberCreate, MemberUpdate
from app.schemas.filters import MemberFilterParams


class MemberRepository(IMemberRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_many(
        self, family_id: int, members: list[MemberCreate]
    ) -> list[Member]:
        """
        Bulk-inserts all members for a family in a single flush.
        Checks the whole batch for ID conflicts up front instead of one query per member.
        """
        ids = [m.id for m in members]

        # Catch duplicate IDs within the submitted payload itself
        if len(set(ids)) != len(ids):
            dupes = {i for i in ids if ids.count(i) > 1}
            raise ConflictError(
                code="duplicate_member_id",
                message=f"Duplicate member id(s) in request: {sorted(dupes)}",
            )

        # One query to check for conflicts against existing members, instead of N
        existing = await self.db.execute(select(Member.id).where(Member.id.in_(ids)))
        conflicting_ids = {row[0] for row in existing.all()}
        if conflicting_ids:
            raise ConflictError(
                code="member_already_exists",
                message=f"Member id(s) {sorted(conflicting_ids)} already exist in another family.",
            )

        new_members = [Member(**m.model_dump(), family_id=family_id) for m in members]
        self.db.add_all(new_members)
        await self.db.flush()
        return new_members

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

    async def get_all(
        self, filters: MemberFilterParams, skip: int = 0, limit: int = 100
    ) -> list[Member]:
        query = select(Member)

        if filters.current_shelter_center_id or filters.shelter_block_id:
            query = query.options(joinedload(Member.family))
            if filters.current_shelter_center_id:
                query = query.where(
                    Family.current_shelter_center_id.in_(
                        filters.current_shelter_center_id
                    )
                )
            if filters.shelter_block_id:
                query = query.where(
                    Family.shelter_block_id.in_(filters.shelter_block_id)
                )

        if filters.family_id:
            query = query.where(Member.family_id == filters.family_id)
        if filters.gender:
            query = query.where(Member.gender == filters.gender)

        # --- MULTI-VALUE FILTERS (.in_) ---
        if filters.marital_status:
            query = query.where(Member.marital_status.in_(filters.marital_status))
        if filters.relationship_to_head_id:
            query = query.where(
                Member.relationship_to_head_id.in_(filters.relationship_to_head_id)
            )

        if filters.has_chronic_disease is not None:
            query = query.where(
                Member.has_chronic_disease == filters.has_chronic_disease
            )
        if filters.injured is not None:
            query = query.where(Member.injured == filters.injured)
        if filters.disabled is not None:
            query = query.where(Member.disabled == filters.disabled)
        if filters.pregnant is not None:
            query = query.where(Member.pregnant == filters.pregnant)
        if filters.breastfeeding is not None:
            query = query.where(Member.breastfeeding == filters.breastfeeding)

        # Date range filtering
        if filters.dob_from:
            query = query.where(Member.date_of_birth >= filters.dob_from)
        if filters.dob_to:
            query = query.where(Member.date_of_birth <= filters.dob_to)

        if filters.full_name:
            query = query.where(
                Member.full_name.ilike(f"%{filters.full_name}%")
            ).order_by(func.similarity(Member.full_name, filters.full_name).desc())

        # Dynamic Sorting
        sort_by_field = filters.sort_by or "full_name"
        sort_column = getattr(Member, sort_by_field, Member.id)
        if filters.sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
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
