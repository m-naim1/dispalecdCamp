import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.core.scoping import (
    require_block_head_scope,
    require_manager_shelter_id,
    verify_family_scope,
)
from app.models.enums import Gender
from app.models.family import Family, Member
from app.models.lookups import ShelterBlock, ShelterCenter
from app.models.user import User, UserRole
from app.repositories.base import (
    IFamilyRepository,
    IMemberRepository,
)
from app.schemas.family import (
    FamilyCreate,
    FamilyUpdate,
    MemberCreate,
    MemberUpdate,
)
from app.schemas.filters import FamilyFilterParams, MemberFilterParams

logger = structlog.getLogger()


async def get_dashboard_stats(db: AsyncSession) -> dict:
    """
    Aggregates all statistics needed for the admin dashboard in a single service call.
    """

    async def _count(query) -> int:
        result = await db.execute(query)
        return result.scalar() or 0

    total_families = await _count(select(func.count(Family.id)))
    active_families = await _count(
        select(func.count(Family.id)).where(Family.is_active == True)
    )
    total_members = await _count(select(func.count(Member.id)))

    block_result = await db.execute(
        select(ShelterBlock.name_en, func.count(Family.id).label("cnt"))
        .outerjoin(Family, Family.shelter_block_id == ShelterBlock.id)
        .group_by(ShelterBlock.id)
        .order_by(func.count(Family.id).desc())
    )
    block_counts = block_result.all()

    center_result = await db.execute(
        select(ShelterCenter.name_en, func.count(Family.id).label("cnt"))
        .outerjoin(Family, Family.current_shelter_center_id == ShelterCenter.id)
        .group_by(ShelterCenter.id)
        .order_by(func.count(Family.id).desc())
    )
    center_counts = center_result.all()

    return {
        "total_families": total_families,
        "active_families": active_families,
        "archived_families": total_families - active_families,
        "total_members": total_members,
        "avg_per_family": round(total_members / total_families, 1)
        if total_families
        else 0,
        "disabled": await _count(
            select(func.count(Member.id)).where(Member.disabled == True)
        ),
        "injured": await _count(
            select(func.count(Member.id)).where(Member.injured == True)
        ),
        "pregnant": await _count(
            select(func.count(Member.id)).where(Member.pregnant == True)
        ),
        "chronic": await _count(
            select(func.count(Member.id)).where(Member.has_chronic_disease == True)
        ),
        "block_counts": block_counts,
        "center_counts": center_counts,
        "max_block": max((c for _, c in block_counts), default=1) or 1,
    }


class FamilyService:
    def __init__(
        self,
        family_repository: IFamilyRepository,
        member_repository: IMemberRepository,
    ):
        self.family_repo = family_repository
        self.member_repo = member_repository

    async def create_family(
        self, family_in: FamilyCreate, current_user: User
    ) -> Family:
        match current_user:
            case User(role=UserRole.MANAGER):
                family_in.current_shelter_center_id = require_manager_shelter_id(
                    current_user
                )
            case User(role=UserRole.BLOCK_HEAD):
                shelter_center_id, block_id = require_block_head_scope(current_user)
                family_in.current_shelter_center_id = shelter_center_id
                family_in.shelter_block_id = block_id

        family = await self.family_repo.create(family_in)

        try:
            await self.member_repo.create_many(family.id, family_in.members)
        except ConflictError as e:
            await self.member_repo.rollback()
            raise e

        family.head_id = family_in.head_id
        if family_in.spouse_id:
            family.spouse_id = family_in.spouse_id

        family = await self.family_repo.get_by_family_id(family.id)
        if not family:
            await self.family_repo.rollback()
            raise DomainError(
                code="Couldn't_create_family", message="Family did not created."
            )

        logger.info(
            "family_creation_started",
            head_id=family_in.head_id,
            member_count=len(family_in.members),
        )
        await self.family_repo.commit()
        return family

    async def get_family(self, family_id: int, current_user: User | None) -> Family:
        """
        Retrieves a family by its ID, including all members.
        """

        family = await self.family_repo.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found", message=f"Family with id {family_id} not found"
            )
        if current_user:
            verify_family_scope(current_user, family)
        logger.info(
            "family_retrieved",
            family_id=family_id,
            head_id=family.head_id,
            member_count=len(family.members),
        )
        return family

    async def get_families(
        self,
        filters: FamilyFilterParams,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Family]:
        match current_user:
            case User(role=UserRole.MANAGER):
                filters.current_shelter_center_id = [
                    require_manager_shelter_id(current_user)
                ]
            case User(role=UserRole.BLOCK_HEAD):
                shelter_center_id, block_id = require_block_head_scope(current_user)
                filters.current_shelter_center_id = [shelter_center_id]
                filters.shelter_block_id = [block_id]
        return await self.family_repo.get_all(filters, skip, limit)

    async def update_family(
        self, family_id: int, family_data: FamilyUpdate, current_user: User
    ) -> Family:
        """
        Updates family-level details (like phone, housing, etc.) without affecting members.
        """
        await self.get_family(family_id, current_user)
        match current_user:
            case User(role=UserRole.MANAGER):
                family_data.current_shelter_center_id = require_manager_shelter_id(
                    current_user
                )
            case User(role=UserRole.BLOCK_HEAD):
                shelter_center_id, block_id = require_block_head_scope(current_user)
                family_data.current_shelter_center_id = shelter_center_id
                family_data.shelter_block_id = block_id
        family = await self.family_repo.update(family_id, family_data)
        return family

    async def deactivate_family(self, family_id: int, current_user: User) -> Family:
        """
        Archive a family without deleting it.
        """
        family = await self.get_family(family_id, current_user)

        return await self.family_repo.archive(family_id)

    async def activate_family(self, family_id: int, current_user: User) -> Family:
        """
        Restore an archived family back to active status.
        """
        family = await self.get_family(family_id, current_user)
        return await self.family_repo.activate(family_id=family_id)


class MemberService:
    def __init__(
        self, member_repository: IMemberRepository, family_repository: IFamilyRepository
    ):
        self.member_repo = member_repository
        self.family_repo = family_repository

    async def _get_owning_family(self, family_id: int) -> Family:
        family = await self.family_repo.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found", message=f"Family with id {family_id} not found"
            )
        return family

    async def add_member(
        self, family_id: int, member_in: MemberCreate, current_user: User
    ) -> Member:
        """
        Adds a new member to an existing family.
        """
        family = await self._get_owning_family(family_id)
        verify_family_scope(current_user, family)
        member = await self.member_repo.create(family_id, member_in)
        await self.member_repo.commit()
        return member

    async def update_member(
        self, member_id: int, member_in: MemberUpdate, current_user: User
    ):
        """
        Updates an existing member's details.
        """

        member = await self.get_member(member_id, current_user)

        if member_in.pregnant is not None:
            if member_in.pregnant and member.gender != Gender.FEMALE:
                raise ValidationError(
                    code="Invalid_pregnancy_status",
                    message="Only female members can be pregnant.",
                )
        member = await self.member_repo.update(member_id, member_in)
        return member

    async def delete_member(self, member_id: int, current_user: User):
        """
        Deletes a member from the database.
        """
        member = await self.get_member(member_id, current_user)
        await self.member_repo.delete(member_id)

    async def get_member(self, member_id: int, current_user: User | None = None) -> Member:
        """
        Retrieves a member by their ID.
        """
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(
                code="Member_not_Found", message=f"Member with id {member_id} not found"
            )
        family = await self._get_owning_family(member.family_id)
        if current_user:
            verify_family_scope(current_user, family)
        return member

    async def get_members(
        self,
        filters: MemberFilterParams,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Member]:
        match current_user:
            case User(role=UserRole.MANAGER):
                filters.current_shelter_center_id = [
                    require_manager_shelter_id(current_user)
                ]
            case User(role=UserRole.BLOCK_HEAD):
                shelter_center_id, block_id = require_block_head_scope(current_user)
                filters.current_shelter_center_id = [shelter_center_id]
                filters.shelter_block_id = [block_id]
        return await self.member_repo.get_all(filters, skip, limit)
