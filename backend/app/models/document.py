"""
Document and DocumentChunk models for study material storage.

Documents represent uploaded files (PDF, DOCX, TXT, images).
DocumentChunks are processed text segments stored alongside their
vector embeddings for similarity search.
"""

from uuid import uuid4

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """
    Uploaded study material document.

    A document can be attached to any level of the hierarchy:
      - workspace_id only → general workspace document (e.g. exam bases)
      - course_id → associated with a specific course
      - subject_id → specific subject material
      - topic_id → specific topic within a subject (most granular)

    Processing pipeline: pending → processing → completed/failed

    Attributes:
        id: Unique identifier (UUID v4)
        user_id: Owner (for quota tracking and search)
        workspace_id / course_id / subject_id / topic_id: Hierarchy attachment
        filename: Original file name
        file_type: File extension (pdf, docx, txt, image)
        file_path: Server-side storage path
        file_size: File size in bytes
        processing_status: Current pipeline status
        processing_error: Error message if processing failed
        language: Detected content language
        chunk_count: Number of text chunks generated
        created_at: Upload timestamp
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Owner — required for quota tracking
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # nullable for existing rows; new uploads always set this
        index=True,
    )

    # Hierarchy attachment (at least one must be set)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=True,  # Now nullable — can live at higher levels
        index=True,
    )
    topic_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, docx, txt, image
    file_path = Column(String(1000), nullable=False)  # Storage path
    file_size = Column(Integer)  # Bytes

    # Processing status tracking
    processing_status = Column(
        String(20), default="pending"
    )  # pending, processing, completed, failed
    processing_error = Column(Text)

    # Metadata
    language = Column(String(10), default="en")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subject = relationship("Subject", back_populates="documents", foreign_keys=[subject_id])
    topic = relationship("Topic", back_populates="documents", foreign_keys=[topic_id])
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def attachment_level(self) -> str:
        """Returns where in the hierarchy this document is attached."""
        if self.topic_id:
            return "topic"
        if self.subject_id:
            return "subject"
        if self.course_id:
            return "course"
        return "workspace"

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.processing_status})>"


class DocumentChunk(Base):
    """
    Text chunk extracted from a processed document.

    Each chunk is embedded using sentence-transformers and stored
    in ChromaDB for vector similarity search. The PostgreSQL record
    keeps the text content and a reference to the ChromaDB vector ID.

    Attributes:
        id: Unique identifier (UUID v4)
        document_id: Parent document reference
        chunk_index: Position within the document (0-indexed)
        content: Text content of the chunk
        token_count: Approximate token count for the chunk
        vector_id: Reference ID in ChromaDB vector store
    """
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)  # Order within document
    content = Column(Text, nullable=False)
    token_count = Column(Integer)

    # Vector DB reference
    vector_id = Column(String(255), unique=True, index=True)  # ChromaDB ID

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, doc={self.document_id}, index={self.chunk_index})>"
