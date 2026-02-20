"""
Course model for grouping related subjects.

Courses belong to a workspace and contain multiple subjects.
Example: "Computer Science 2024" containing "Data Structures", "Algorithms", etc.
"""

from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Course(Base):
    """
    Course within a workspace.

    Groups related subjects together for organizational purposes.

    Examples:
        - "Computer Science 2024" under "University Studies"
        - "General Knowledge" under "Civil Service Exam"

    Attributes:
        id: Unique identifier (UUID v4)
        workspace_id: Parent workspace reference
        name: Course display name
        created_at: Creation timestamp
    """
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    color = Column(String(7), default="#3B82F6")
    position = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="courses")
    subjects = relationship(
        "Subject",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, name={self.name})>"
