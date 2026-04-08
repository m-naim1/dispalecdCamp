from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.core.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.models.enums import Gender
from app.models.family import Family, Member
from app.schemas.family import FamilyCreate, FamilyUpdate, MemberCreate, MemberUpdate


def create_family(db: Session, family_in: FamilyCreate) -> Family:
    """
    Creates a new family and its members, automatically calculating statistics.
    """

    # 1. Pre-check: Ensure the Head of Family doesn't already exist
    # (This prevents double registration of the same family)
    existing_head = db.query(Member).filter(Member.id == family_in.head_id).first()
    if existing_head:
        raise ConflictError(
            code="member_already_exists",
            message=f"Member with the {family_in.head_id} already exists in another family.",
        )

    db_members = []

    for member_data in family_in.members:
        # Check for duplicates for every single member in the list
        if db.query(Member).filter(Member.id == member_data.id).first():
            raise ConflictError(
                code="member_already_exists",
                message=f"Member with the {member_data.id} already exists in another family.",
            )
        
        db_member = Member(**member_data.model_dump())
        db_members.append(db_member)

    # 3. Create the Family Object
    db_family = Family(**family_in.model_dump())

    # 4. Save to Database
    db.add(db_family)
    db.flush()  # "Flush" pushes the family to DB to generate the unique 'id', but doesn't commit yet

    # 5. Link Members to the new Family ID
    for db_member in db_members:
        db_member.family_id = db_family.id
        db.add(db_member)

    # Commit everything as a single transaction
    db.commit()
    db.refresh(db_family)

    return db_family


def get_family(db: Session, family_id: int) -> Family:
    """
    Retrieves a family by its ID, including all members.
    """
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise NotFoundError(
            code="Family_not_Found", message=f"Family with id {family_id} not found"
        )
    return family


def get_families(
    db: Session, skip: int = 0, limit: int = 100, active: bool = True
) -> List[Family]:
    """
    Retrieves a list of families, with optional pagination and active-only filtering.
    """
    query = db.query(Family)
    if active:
        query = query.filter(Family.is_active)
    return query.offset(skip).limit(limit).all()


def update_family(db: Session, family_id: int, family_data: FamilyUpdate) -> Family:
    """
    Updates family-level details (like phone, housing, etc.) without affecting members.
    """
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise NotFoundError(
            code="Family_not_Found", message=f"Family with id {family_id} not found"
        )

    update_data = family_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(family, key, value)

    db.add(family)
    db.commit()
    db.refresh(family)

    return family


def deactivate_family(db: Session, family_id: int) -> Family:
    """
    Archive a family without deleteting it.
    """
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise NotFoundError(
            code="Family_not_Found", message=f"Family with id {family_id} not found"
        )
    if not family.is_active:
        raise DomainError(
            code="Family_already_archived",
            message=f"Family with id {family_id} already archived",
        )
    family.is_active = False
    family.archived_at = datetime.now()

    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def activate_family(db: Session, family_id: int) -> Family:
    """
    Archive a family without deleteting it.
    """
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise NotFoundError(
            code="Family_not_Found", message=f"Family with id {family_id} not found"
        )
    if family.is_active:
        raise DomainError(
            code="Family_already_activated",
            message=f"Family with id {family_id} already activated",
        )
    family.is_active = True
    family.archived_at = None  # type: ignore

    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def add_member(db: Session, family_id: int, member_in: MemberCreate) -> Member:
    """
    Adds a new member to an existing family and updates family statistics.
    """
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise NotFoundError(
            code="Family_not_Found", message=f"Family with id {family_id} not found"
        )

    # Check for duplicate member ID across all families
    if db.query(Member).filter(Member.id == member_in.id).first():
        raise ConflictError(
            code="member_already_exists",
            message=f"Member with the {member_in.id} already exists in another family.",
        )

    # Create and add the new member
    new_member = Member(**member_in.model_dump(), family_id=family_id)
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return new_member


def update_member(db: Session, member_id: int, member_in: MemberUpdate):
    """
    Updates an existing member's details.
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise NotFoundError(
            code="Member_not_Found", message=f"Member with id {member_id} not found"
        )
    # validate updateting Gender and pregnancy status
    if member_in.pregnant is not None:
        if member_in.pregnant and member.gender != Gender.FEMALE:
            raise ValidationError(
                code="Invalid_pregnancy_status",
                message="Only female members can be pregnant."
            )


    update_data = member_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(member, key, value)

    db.add(member)
    db.commit()
    db.refresh(member)

    return member


def delete_member(db: Session, member_id: int):
    """
    Deletes a member from the database and updates family statistics.
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise NotFoundError(
            code="Member_not_Found", message=f"Member with id {member_id} not found"
        )

    db.delete(member)
    db.commit()


# def recalculate_family_stats(db: Session, family_id: int):
#     """
#     Recalculates counts (pregnant, disabled, etc.) for a specific family
#     based on its current members in the database.
#     """
#     family = db.query(Family).filter(Family.id == family_id).first()
#     if not family:
#         raise NotFoundError(
#             code="Family_not_Found", message=f"Family with id {family_id} not found"
#         )

#     # Fetch all members freshly from DB
#     members: List[Member] = db.query(Member).filter(Member.family_id == family_id).all()

#     # Reset counters
#     family.total_members_count = len(members)
#     family.disabled_count = 0
#     family.injured_count = 0
#     family.chronic_disease_count = 0
#     family.pregnant_count = 0

#     # Recount
#     for member in members:
#         if member.is_disabled:
#             family.disabled_count += 1
#         if member.is_injured:
#             family.injured_count += 1
#         if member.has_chronic_disease:
#             family.chronic_disease_count += 1
#         if member.is_pregnant:
#             family.pregnant_count += 1
#     # Update Records
#     db.add(family)
#     db.commit()
#     db.refresh(family)
