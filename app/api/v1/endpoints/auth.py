from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_role
from app.core.security import create_access_token
from app.models.family import Member, Family
from app.models.enums import UserRole
from app.schemas.user import Token, UserResponse, UserCreate
from app.services import user_service
from app.core.errors import ConflictError

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/family-login", response_model=Token)
def family_login(national_id: str, date_of_birth: date, db: Session = Depends(get_db)):
    head = db.query(Member).filter(Member.id == national_id).first()
    if not head or head.date_of_birth != date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    family = (
        db.query(Family)
        .filter(Family.id == head.family_id, Family.is_active == True)
        .first()
    )
    if not family:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Family not found or inactive",
        )
    if family.head_id != head.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(
        data={"sub": str(national_id), "role": UserRole.FAMILY, "family_id": family.id}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    if isinstance(current_user, dict):
        raise HTTPException(
            status_code=403, detail="Family users do not have a profile endpoint"
        )
    return current_user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    """
    Create a new system user (Manager, Block_hed, etc)
    Only admin can access this endpoint
    """
    try:
        return user_service.create_user(db, user_in)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
