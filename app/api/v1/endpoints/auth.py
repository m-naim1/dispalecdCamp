from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, require_role
from app.core.security import create_access_token
from app.models.enums import UserRole
from app.schemas.user import Token, UserResponse, UserCreate
from app.services import user_service, family_service
from app.core.errors import ConflictError

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    user = await user_service.authenticate_user(
        db, form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/family-login", response_model=Token)
async def family_login(
    national_id: int, date_of_birth: date, db: AsyncSession = Depends(get_db)
):
    head = await family_service.get_member(db, national_id)
    if not head or head.date_of_birth != date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    family = await family_service.get_family(db, head.family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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
async def get_me(current_user=Depends(get_current_user)):
    if isinstance(current_user, dict):
        raise HTTPException(
            status_code=403, detail="Family users do not have a profile endpoint"
        )
    return current_user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    """
    Create a new system user (Manager, Block_hed, etc)
    Only admin can access this endpoint
    """
    try:
        return await user_service.create_user(db, user_in)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
