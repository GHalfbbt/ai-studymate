"""
Subject model for organizing documents and study materials.

Subjects are the primary organizational level where documents are uploaded
and from which exams and flashcards are generated.
"""

from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Subject(Base):
    """
    Subject within a course.

    The primary level for document organization and study material management.
    RAG queries, exam generation, and flashcard creation operate at this level.

    Examples:
        - "Data Structures" under "Computer Science 2024"
        - "Constitutional Law" under "Legal Fundamentals"

    Attributes:
        id: Unique identifier (UUID v4)
        course_id: Parent course reference
        name: Subject display name
        color: Hex color code for UI differentiation (default blue)
        created_at: Creation timestamp
    """
    __tablename__ = "subjects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    color = Column(String(7), default="#3B82F6")  # Hex color for UI
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="subjects")
    documents = relationship(
        "Document",
        back_populates="subject",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, name={self.name})>"
