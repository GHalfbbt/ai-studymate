"""
User model for authentication and profile management.

Stores user credentials and profile information.
Serves as the root entity for all user-owned data.
"""

from uuid import uuid4

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """
    User account for the AI StudyMate system.

    Each user has a unique email address and can own multiple workspaces.
    Password is stored as a bcrypt hash for security.

    Attributes:
        id: Unique identifier (UUID v4)
        email: User's email address (unique, indexed)
        hashed_password: Bcrypt hashed password
        full_name: User's display name
        created_at: Account creation timestamp
        updated_at: Last profile update timestamp
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    llm_provider = Column(String(20), nullable=False, server_default="auto")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    workspaces = relationship(
        "Workspace",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
