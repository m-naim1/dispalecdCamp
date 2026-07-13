from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_family_service,
    get_member_service,
    get_update_request_service,
    require_role,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.family import (
    FamilyCreate,
    FamilyListResponse,
    FamilyResponse,
    FamilyUpdate,
    MemberCreate,
    MemberResponse,
    MemberUpdate,
    UpdateRequestCreate,
)
from app.schemas.filters import FamilyFilterParams, MemberFilterParams
from app.services.family_service import FamilyService, MemberService
from app.services.update_request_service import UpdateRequestService

router = APIRouter()


@router.post("/", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_family(
    family_in: FamilyCreate,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Create a new family with all its members.
    - Validates IDs using Luhn algorithm.
    - Prevents duplicate members.
    """
    return await family_service.create_family(
        family_in=family_in, current_user=current_user
    )


@router.get("/{family_id}", response_model=FamilyResponse)
async def read_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(
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
    return await family_service.get_family(
        family_id=family_id, current_user=current_user
    )


@router.get("/", response_model=list[FamilyListResponse])
async def read_families(
    page: int = 1,
    limit: int = 100,
    filters: FamilyFilterParams = Depends(),
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
):
    """
    Get Sequence of families with advanced filtering and sorting.
    """
    skip = (page - 1) * limit
    return await family_service.get_families(
        filters=filters, current_user=current_user, skip=skip, limit=limit
    )


@router.put("/{family_id}", response_model=FamilyResponse)
async def update_family_details(
    family_id: int,
    family_update: FamilyUpdate,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Update family-level details (Housing, Phone, Status).
    """
    return await family_service.update_family(
        family_id=family_id, family_data=family_update, current_user=current_user
    )


@router.patch("/{family_id}/archive", response_model=FamilyResponse)
async def archive_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Soft delete (archive) a family.
    Sets is_active = False and records the archived_at timestamp.
    """
    return await family_service.deactivate_family(
        family_id=family_id, current_user=current_user
    )


@router.patch("/{family_id}/restore", response_model=FamilyResponse)
async def restore_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Restore an archived family back to active status.
    """
    return await family_service.activate_family(
        family_id=family_id, current_user=current_user
    )


@router.post("/{family_id}/members", response_model=MemberResponse)
async def add_member_to_family(
    family_id: int,
    member_in: MemberCreate,
    member_service: MemberService = Depends(get_member_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Add a new member to an existing family.
    Automatically recalculates family statistics.
    """
    return await member_service.add_member(
        family_id=family_id, member_in=member_in, current_user=current_user
    )


@router.get("/members", response_model=list[MemberResponse])
async def read_members(
    page: int = 1,
    limit: int = 100,
    filters: MemberFilterParams = Depends(),
    member_service: MemberService = Depends(get_member_service),
    current_user: User = Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
):
    """
    Get Sequence of members with advanced filtering and sorting.
    """
    skip = (page - 1) * limit
    return await member_service.get_members(
        filters=filters, current_user=current_user, skip=skip, limit=limit
    )


@router.put("/members/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: int,
    member_update: MemberUpdate,
    member_service: MemberService = Depends(get_member_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Update a specific member's details (e.g., pregnancy status, injury).
    Automatically recalculates family statistics.
    """
    return await member_service.update_member(
        member_id=member_id, member_in=member_update, current_user=current_user
    )


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: int,
    member_service: MemberService = Depends(get_member_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Permanently remove a member from the family.
    Automatically recalculates family statistics.
    """
    await member_service.delete_member(member_id=member_id, current_user=current_user)


@router.get("/me", response_model=FamilyResponse)
async def get_my_family(
    family_service: FamilyService = Depends(get_family_service),
    current_user=Depends(require_role(UserRole.FAMILY)),
):
    """Families can only view their own data."""
    if isinstance(current_user, dict) and current_user.get("role") == UserRole.FAMILY:
        family_id = current_user.get("family_id", -1)
        return await family_service.get_family(family_id=family_id, current_user=None)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only family users can access this endpoint",
    )


@router.post(
    "/me/update-requests", status_code=status.HTTP_201_CREATED, tags=["update-request"]
)
async def request_family_update(
    req_in: UpdateRequestCreate,
    current_user=Depends(require_role(UserRole.FAMILY)),
    update_req_service: UpdateRequestService = Depends(get_update_request_service),
):
    """Family proposes a change (e.g., new baby, changed phone number)."""
    if (
        not isinstance(current_user, dict)
        or current_user.get("role") != UserRole.FAMILY
    ):
        raise HTTPException(status_code=403, detail="Only families can request updates")
    new_req = await update_req_service.create_request(
        current_user.get("family_id", -1), req_in
    )

    return {"message": "Update request submitted for manager review", "id": new_req.id}


@router.get(
    "/update-requests",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    tags=["update-request"],
)
async def get_families_update_requests(
    current_user=Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
    update_req_service: UpdateRequestService = Depends(get_update_request_service),
):
    """get families update requests (e.g., new baby, changed phone number)."""
    return await update_req_service.get_scoped_pending_requests(current_user)


@router.patch("/{request_id}/approve", tags=["update-request"])
async def approve_request(
    request_id: int,
    current_user=Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
    service: UpdateRequestService = Depends(get_update_request_service),
):
    return await service.approve_request(request_id, current_user)


@router.patch("/{request_id}/reject", tags=["update-request"])
async def reject_request(
    request_id: int,
    current_user=Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
    service: UpdateRequestService = Depends(get_update_request_service),
):
    return await service.reject_request(request_id, current_user)
