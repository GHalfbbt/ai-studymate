"""
Flashcard model for spaced repetition learning.

Flashcards are generated from document content and support
basic spaced repetition tracking (ease factor, review schedule).
"""

from uuid import uuid4

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Flashcard(Base):
    """
    Study flashcard for spaced repetition review.

    Generated from document content via LLM. Each flashcard
    has a front side (question) and back side (answer).

    Spaced repetition fields follow a simplified SM-2 algorithm:
    - ease_factor: Multiplier for review intervals (default 2.5)
    - next_review: When the card should be reviewed next
    - times_reviewed: Total review count for analytics

    Attributes:
        id: Unique identifier (UUID v4)
        subject_id: Subject this flashcard belongs to
        document_id: Source document (nullable if deleted)
        front: Question/prompt text
        back: Answer/explanation text
        difficulty: easy/medium/hard classification
        created_at: Creation timestamp
        times_reviewed: Number of times reviewed
        last_reviewed: Last review timestamp
        next_review: Next scheduled review timestamp
        ease_factor: SM-2 ease factor (default 2.5)
    """
    __tablename__ = "flashcards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )

    # Card content
    front = Column(Text, nullable=False)  # Question
    back = Column(Text, nullable=False)  # Answer

    # Metadata
    difficulty = Column(String(10), default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Spaced repetition fields
    times_reviewed = Column(Integer, default=0)
    last_reviewed = Column(DateTime(timezone=True))
    next_review = Column(DateTime(timezone=True))
    ease_factor = Column(Float, default=2.5)

    # Relationships
    subject = relationship("Subject")
    document = relationship("Document")

    def __repr__(self) -> str:
        return f"<Flashcard(id={self.id}, subject={self.subject_id})>"
