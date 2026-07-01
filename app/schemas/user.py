from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserRole


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    role: UserRole
    block_id: int | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = None
    password: str | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None
    role: UserRole | None = None


class FamilyLoginSchema(BaseModel):
    national_id: int
    date_of_birth: date
