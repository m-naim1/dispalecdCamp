# from typing import List
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.errors import ConflictError, NotFoundError, DomainError, ValidationError
from app.models import family
from app.models.family import Family as FamilyModel
from app.models.family import Member as MemberModel
from app.schemas.family import (
    FamilyCreate,
    FamilyResponse,
    FamilyUpdate,
    MemberCreate,
    MemberResponse,
    MemberUpdate,
)
from app.services import family_service

router = APIRouter()


@router.post("/", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
def create_new_family(family_in: FamilyCreate, db: Session = Depends(get_db)):
    """
    Create a new family with all its members.
    - Validates IDs using Luhn algorithm.
    - Prevents duplicate members.
    """
    try:
        family = family_service.create_family(db=db, family_in=family_in)
    except ConflictError as e:
        raise HTTPException(
            status_code=400,
            detail=e.message,
        )
    return family


@router.get("/{family_id}", response_model=FamilyResponse)
def read_family(family_id: int, db: Session = Depends(get_db)):
    """
    Get a specific family by ID to see the calculated stats and members.
    """
    family = db.query(FamilyModel).filter(FamilyModel.id == family_id).first()
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")
    return family


@router.get("/", response_model=List[FamilyResponse])
def read_families(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    Get list of families.
    By default, only returns active families.
    Set active_only=False to see everyone (including archived).
    """
    return family_service.get_families(
        db=db, skip=skip, limit=limit, active=active_only
    )


@router.put("/{family_id}", response_model=FamilyResponse)
def update_family_details(
    family_id: int, family_update: FamilyUpdate, db: Session = Depends(get_db)
):
    """
    Update family-level details (Housing, Phone, Status).
    """
    try:
        family = family_service.update_family(
            db=db, family_id=family_id, family_data=family_update
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

    return family


@router.patch("/{family_id}/archive", response_model=FamilyResponse)
def archive_family(family_id: int, db: Session = Depends(get_db)):
    """
    Soft delete (archive) a family.
    Sets is_active = False and records the archived_at timestamp.
    """
    try:
        family = family_service.deactivate_family(db=db, family_id=family_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DomainError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return family


@router.patch("/{family_id}/restore", response_model=FamilyResponse)
def restore_family(family_id: int, db: Session = Depends(get_db)):
    """
    Restore an archived family back to active status.
    """
    try:
        family = family_service.activate_family(db=db, family_id=family_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DomainError as e:
        raise HTTPException(status_code=400, detail=e.message)
    return family


@router.post("/{family_id}/members", response_model=MemberResponse)
def add_member_to_family(
    family_id: int, member_in: MemberCreate, db: Session = Depends(get_db)
):
    """
    Add a new member to an existing family.
    Automatically recalculates family statistics.
    """
    try:
        new_member = family_service.add_member(db=db, family_id=family_id, member_in=member_in)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return new_member


@router.put("/members/{member_id}", response_model=MemberResponse)
def update_member(
    member_id: int, member_update: MemberUpdate, db: Session = Depends(get_db)
):
    """
    Update a specific member's details (e.g., pregnancy status, injury).
    Automatically recalculates family statistics.
    """
    try:
        updated_member = family_service.update_member(db=db, member_id=member_id, member_in=member_update)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    return updated_member

@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(member_id: int, db: Session = Depends(get_db)):
    """
    Permanently remove a member from the family.
    Automatically recalculates family statistics.
    """
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(db_member)
    db.commit()
    return None
