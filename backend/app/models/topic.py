"""
Topic model — 4th level of the study hierarchy.

Hierarchy: Workspace → Course → Subject → Topic → Documents

Topics allow fine-grained organization within a subject.
Example:
    Subject: "Bloque 1: Legislación"
    Topics:  "Tema 1: Constitución Española"
             "Tema 2: Estatutos de Autonomía"
             "Tema 3: Ley de Bases del Régimen Local"
"""

from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Topic(Base):
    """
    4th-level organizational unit within a Subject.

    Allows granular topic-by-topic material organization.
    Documents, exams, and RAG queries can be scoped to a Topic.

    Attributes:
        id: Unique identifier (UUID v4)
        subject_id: Parent subject reference
        name: Topic display name (e.g. "Tema 1: Constitución Española")
        color: Hex color for visual differentiation
        position: Display order (0-indexed, user-draggable)
        created_at: Creation timestamp
    """
    __tablename__ = "topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    color = Column(String(7), default="#6366F1")
    position = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subject = relationship("Subject", back_populates="topics")
    documents = relationship(
        "Document",
        back_populates="topic",
        foreign_keys="Document.topic_id",
    )

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, name={self.name})>"
