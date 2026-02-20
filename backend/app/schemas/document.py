"""
Document-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    """Schema for document upload metadata."""
    workspace_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None


class DocumentResponse(BaseModel):
    """Schema for document response — supports multi-level attachment."""
    id: UUID
    user_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None
    filename: str
    file_type: str
    file_size: Optional[int] = None
    processing_status: str
    processing_error: Optional[str] = None
    language: str = "en"
    chunk_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for paginated document list."""
    documents: list[DocumentResponse]
    total: int
