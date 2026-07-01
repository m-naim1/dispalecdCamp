from fastapi import APIRouter, Depends, status

from app.api.deps import get_family_service, get_member_service, require_role
from app.models.enums import UserRole
from app.schemas.family import (
    FamilyCreate,
    FamilyListResponse,
    FamilyResponse,
    FamilyUpdate,
    MemberCreate,
    MemberResponse,
    MemberUpdate,
)
from app.services.family_service import FamilyService, MemberService

router = APIRouter()


@router.post("/", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_family(
    family_in: FamilyCreate,
    family_service: FamilyService = Depends(get_family_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Create a new family with all its members.
    - Validates IDs using Luhn algorithm.
    - Prevents duplicate members.
    """
    return await family_service.create_family(family_in=family_in)


@router.get("/{family_id}", response_model=FamilyResponse)
async def read_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    _=Depends(
        require_role(
            UserRole.SUPERADMIN,
            UserRole.MANAGER,
            UserRole.BLOCK_HEAD,
        )
    ),
):
    """
    Get a specific family by ID to see the calculated stats and members.
    """
    return await family_service.get_family(family_id=family_id)


@router.get("/", response_model=list[FamilyListResponse])
async def read_families(
    page: int = 1,
    limit: int = 100,
    active_only: bool = True,
    head_name:str = "",
    
    family_service: FamilyService = Depends(get_family_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)),
):
    """
    Get Sequence of families.
    By default, only returns active families.
    Set active_only=False to see everyone (including archived).
    """
    return await family_service.get_families(
        skip=(page - 1) * limit, limit=limit, active=active_only, head_name=head_name
    )


@router.put("/{family_id}", response_model=FamilyResponse)
async def update_family_details(
    family_id: int,
    family_update: FamilyUpdate,
    family_service: FamilyService = Depends(get_family_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Update family-level details (Housing, Phone, Status).
    """
    return await family_service.update_family(
        family_id=family_id, family_data=family_update
    )


@router.patch("/{family_id}/archive", response_model=FamilyResponse)
async def archive_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Soft delete (archive) a family.
    Sets is_active = False and records the archived_at timestamp.
    """
    return await family_service.deactivate_family(family_id=family_id)


@router.patch("/{family_id}/restore", response_model=FamilyResponse)
async def restore_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Restore an archived family back to active status.
    """
    return await family_service.activate_family(family_id=family_id)


@router.post("/{family_id}/members", response_model=MemberResponse)
async def add_member_to_family(
    family_id: int,
    member_in: MemberCreate,
    member_service: MemberService = Depends(get_member_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Add a new member to an existing family.
    Automatically recalculates family statistics.
    """
    return await member_service.add_member(family_id=family_id, member_in=member_in)


@router.put("/members/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: int,
    member_update: MemberUpdate,
    member_service: MemberService = Depends(get_member_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Update a specific member's details (e.g., pregnancy status, injury).
    Automatically recalculates family statistics.
    """
    return await member_service.update_member(
        member_id=member_id, member_in=member_update
    )


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: int,
    member_service: MemberService = Depends(get_member_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Permanently remove a member from the family.
    Automatically recalculates family statistics.
    """
    await member_service.delete_member(member_id=member_id)
