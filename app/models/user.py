from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import UserRole
from app.models.family import Block
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.FAMILY, nullable=False)
    # Scope Fields
    # Which block does this user manage? (Only for blockHead)
    block_id = Column(Integer,ForeignKey("blocks.id"), nullable=True, index=True)

    # Which family does this user belong to? (Only for family role)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to the family if this is a family-type user
    family_profile = relationship("Family", backref="user_account", uselist=False)
