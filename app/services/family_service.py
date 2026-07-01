import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.models.enums import Gender
from app.models.family import Family, Member
from app.models.lookups import ShelterBlock, ShelterCenter
from app.repositories.base import IFamilyRepository, IMemberRepository
from app.schemas.family import (
    FamilyCreate,
    FamilyUpdate,
    MemberCreate,
    MemberUpdate,
)

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
        self, family_repository: IFamilyRepository, member_repository: IMemberRepository
    ):
        self.family_repo = family_repository
        self.member_repo = member_repository

    async def create_family(self, family_in: FamilyCreate) -> Family:
        """
        Creates a new family and its members
        """

        family = await self.family_repo.create(family_in)

        members: list[Member] = []
        for member_data in family_in.members:
            try:
                member = await self.member_repo.create(family.id, member_data)
            except ConflictError as e:
                await self.member_repo.rollback()
                raise e
            members.append(member)

        family.head_id = family_in.head_id
        if family_in.spouse_id:
            family.spouse_id = family_in.spouse_id
        family = await self.family_repo.get_by_family_id(family.id)
        if not family:
            await self.family_repo.rollback()
            raise DomainError(
                code="Couldn't_create_family",
                message="Family did not created.",
            )
        logger.info(
            "family_creation_started",
            head_id=family_in.head_id,
            member_count=len(family_in.members),
        )
        await self.family_repo.commit()
        return family

    async def get_family(self, family_id: int) -> Family:
        """
        Retrieves a family by its ID, including all members.
        """
        family = await self.family_repo.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found", message=f"Family with id {family_id} not found"
            )
        logger.info(
            "family_retrived",
            family_id=family_id,
            head_id=family.head_id,
            member_count=len(family.members),
        )
        return family

    async def get_families(
        self, skip: int = 0, limit: int = 100, active: bool = True, head_name= ""
    ) -> list[Family]:
        """
        Retrieves a list of families, with optional pagination and active-only filtering.
        """
        if head_name:
            return await self.family_repo.get_by_head_name(head_name)
        return await self.family_repo.get_all(skip, limit, active)


    async def update_family(self, family_id: int, family_data: FamilyUpdate) -> Family:
        """
        Updates family-level details (like phone, housing, etc.) without affecting members.
        """
        family = await self.family_repo.update(family_id, family_data)

        return family

    async def deactivate_family(self, family_id: int) -> Family:
        """
        Archive a family without deleting it.
        """
        return await self.family_repo.archive(family_id)

    async def activate_family(self, family_id: int) -> Family:
        """
        Restore an archived family back to active status.
        """
        return await self.family_repo.activate(family_id=family_id)


class MemberService:
    def __init__(self, member_repository: IMemberRepository):
        self.member_repo = member_repository

    async def add_member(self, family_id: int, member_in: MemberCreate) -> Member:
        """
        Adds a new member to an existing family.
        """
        member = await self.member_repo.create(family_id, member_in)
        await self.member_repo.commit()
        return member

    async def update_member(self, member_id: int, member_in: MemberUpdate):
        """
        Updates an existing member's details.
        """
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(
                code="Member_not_Found", message=f"Member with id {member_id} not found"
            )

        if member_in.pregnant is not None:
            if member_in.pregnant and member.gender != Gender.FEMALE:
                raise ValidationError(
                    code="Invalid_pregnancy_status",
                    message="Only female members can be pregnant.",
                )
        member = await self.member_repo.update(member_id, member_in)
        return member

    async def delete_member(self, member_id: int):
        """
        Deletes a member from the database.
        """
        await self.member_repo.delete(member_id)

    async def get_member(self, member_id: int) -> Member:
        """
        Retrieves a member by their ID.
        """
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(
                code="Member_not_Found", message=f"Member with id {member_id} not found"
            )
        return member
