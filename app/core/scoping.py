from fastapi import HTTPException, status

from app.core.errors import DomainError
from app.models.enums import UserRole
from app.models.family import Family
from app.models.user import User


def require_manager_shelter_id(user: User) -> int:
    """A MANAGER must always have a shelter assigned; this is a data-integrity guard."""
    if user.shelter_id is None:
        raise DomainError(
            code="Manager_Missing_Shelter",
            message="This manager account has no shelter assigned.",
        )
    return user.shelter_id


def require_block_head_scope(user: User) -> tuple[int, int]:
    """Returns (shelter_center_id, block_id) for a BLOCK_HEAD; guards missing block data."""
    if user.block_id is None or user.block is None:
        raise DomainError(
            code="BlockHead_Missing_Block",
            message="This block head account has no block assigned.",
        )
    return user.block.shelter_center_id, user.block_id


def verify_family_scope(user: User | dict, family: Family):
    """Enforces actor boundaries on Family objects."""
    match user:
        case {"role": UserRole.FAMILY}:
            if family.id != user.get("family_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this family",
                )
            return
        case User(role=UserRole.SUPERADMIN):
            return
        case User(role=UserRole.MANAGER):
            if family.current_shelter_center_id != user.shelter_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Manager scope violation: Family belongs to a different shelter",
                )
            return
        case User(role=UserRole.BLOCK_HEAD):
            if family.shelter_block_id != user.block_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Block Head scope violation: Family belongs to a different block",
                )
            return
        case _:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session"
            )
