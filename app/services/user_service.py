from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.errors import NotFoundError, ConflictError


def get_user_by_username(db: Session, username: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError(
            code="User_Not_Found", message=f"User with id {user_id} not found"
        )
    return user


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user_in: UserCreate) -> User:
    if db.query(User).filter(User.username == user_in.username).first():
        raise ConflictError(
            code="User_Already_Exists",
            message=f"User with username {user_in.username} already exists",
        )
    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        block_id=user_in.block_id,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, user_in: UserUpdate) -> User:
    user = get_user_by_id(db, user_id)
    if user_in.username and user_in.username != user.username:
        if db.query(User).filter(User.username == user_in.username).first():
            raise ConflictError(
                code="User_Already_Exists",
                message=f"User with username {user_in.username} already exists",
            )
    for field, value in user_in.model_dump(
        exclude_unset=True, exclude={"password"}
    ).items():
        setattr(user, field, value)
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if (
        not user
        or not user.is_active
        or not verify_password(password, user.hashed_password)
    ):
        return None
    return user


def deactivate_user(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(
            code="User_Not_Found", message=f"User with id {user_id} not found"
        )
    if not user.is_active:
        return
    user.is_active = False
    db.commit()


def activate_user(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(
            code="User_Not_Found", message=f"User with id {user_id} not found"
        )
    if user.is_active:
        return
    user.is_active = True
    db.commit()
