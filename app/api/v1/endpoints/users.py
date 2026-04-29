from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role
from app.core.errors import NotFoundError, ConflictError
from app.models.enums import UserRole
from app.schemas.user import UserResponse, UserUpdate
from app.services import user_service

router = APIRouter()


@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    return user_service.get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    try:
        return user_service.get_user_by_id(db, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    try:
        return user_service.update_user(db, user_id, user_in)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=e.message)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    try:
        user_service.deactivate_user(db, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
