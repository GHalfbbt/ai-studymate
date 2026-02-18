"""
Document-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    """Schema for document upload metadata (sent alongside the file)."""
    subject_id: UUID = Field(..., description="Subject to associate the document with")


class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: UUID
    subject_id: UUID
    filename: str
    file_type: str
    file_size: Optional[int]
    processing_status: str
    processing_error: Optional[str]
    language: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for paginated document list."""
    documents: list[DocumentResponse]
    total: int
