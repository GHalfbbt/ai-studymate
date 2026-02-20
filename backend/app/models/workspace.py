"""
Workspace model for top-level content organization.

Workspaces are the highest-level organizational unit, allowing users
to separate different study contexts (e.g., "University", "Certification Exam").
"""

from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Workspace(Base):
    """
    Top-level organization unit for study materials.

    Examples:
        - "University Studies" for a college student
        - "Bar Exam 2025" for an exam candidate
        - "AWS Certification" for a professional

    Attributes:
        id: Unique identifier (UUID v4)
        user_id: Owner user reference
        name: Workspace display name
        description: Optional description of the workspace purpose
        created_at: Creation timestamp
    """
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    icon = Column(String(10), default="🗂️")
    position = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="workspaces")
    courses = relationship(
        "Course",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name={self.name})>"
