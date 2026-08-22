from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import (
    get_current_user,
    get_family_service,
    get_member_service,
    get_user_service,
    require_role,
)
from app.core.security import create_access_token
from app.models.enums import UserRole
from app.schemas.user import FamilyLoginSchema, Token, UserCreate, UserResponse
from app.services.family_service import FamilyService, MemberService
from app.services.user_service import UserService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.authenticate_user(
        credentials.username, credentials.password
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
    credentials: FamilyLoginSchema,
    family_service: FamilyService = Depends(get_family_service),
    member_service: MemberService = Depends(get_member_service),
):

    head = await member_service.get_member(credentials.national_id)
    if not head or head.date_of_birth != credentials.date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    family = await family_service.get_family(head.family_id, current_user=None)
    if family.head_id != head.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(
        data={
            "sub": str(credentials.national_id),
            "role": UserRole.FAMILY,
            "family_id": family.id,
        }
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
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    """
    Create a new system user (Manager, Block_hed, etc)
    Only admin can access this endpoint
    """

    return await user_service.create_user(user_in)
