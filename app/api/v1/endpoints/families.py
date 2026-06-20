from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import require_role, get_family_service, get_member_service
from app.core.errors import ConflictError, NotFoundError, DomainError, ValidationError
from app.models.enums import UserRole
from app.schemas.family import (
    FamilyCreate,
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
    try:
        family = await family_service.create_family(family_in=family_in)
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    return family


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
    try:
        family = await family_service.get_family(family_id=family_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    return family


@router.get("/", response_model=list[FamilyResponse])
async def read_families(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    family_service: FamilyService = Depends(get_family_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)),
):
    """
    Get Sequence of families.
    By default, only returns active families.
    Set active_only=False to see everyone (including archived).
    """
    return await family_service.get_families(
        skip=skip, limit=limit, active=active_only
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
    try:
        family = await family_service.update_family(
             family_id=family_id, family_data=family_update
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

    return family


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
    try:
        family = await family_service.deactivate_family(
            family_id=family_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DomainError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return family


@router.patch("/{family_id}/restore", response_model=FamilyResponse)
async def restore_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    _=Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Restore an archived family back to active status.
    """
    try:
        family = await family_service.activate_family(
            family_id=family_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DomainError as e:
        raise HTTPException(status_code=400, detail=e.message)
    return family


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
    try:
        new_member = await member_service.add_member( family_id=family_id, member_in=member_in
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return new_member


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
    try:
        updated_member = await member_service.update_member(
             member_id=member_id, member_in=member_update
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    return updated_member


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
    try:
        await member_service.delete_member( member_id=member_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

    return None
