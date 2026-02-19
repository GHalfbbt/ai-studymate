"""
Workspace-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    """Schema for creating a new workspace."""
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    description: Optional[str] = Field(None, description="Workspace description")


class WorkspaceUpdate(BaseModel):
    """Schema for updating an existing workspace."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Schema for workspace response."""
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    course_count: int = 0

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    """Schema for creating a new course within a workspace."""
    name: str = Field(..., min_length=1, max_length=255, description="Course name")
    position: Optional[int] = Field(None, description="Display order position")


class CourseUpdate(BaseModel):
    """Schema for updating a course."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    position: Optional[int] = None


class CourseResponse(BaseModel):
    """Schema for course response."""
    id: UUID
    workspace_id: UUID
    name: str
    position: int
    created_at: datetime
    subject_count: int = 0

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    """Schema for creating a new subject within a course."""
    name: str = Field(..., min_length=1, max_length=255, description="Subject name")
    color: Optional[str] = Field(
        "#3B82F6",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code for UI",
    )
    position: Optional[int] = Field(None, description="Display order position")


class SubjectUpdate(BaseModel):
    """Schema for updating a subject."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    position: Optional[int] = None


class SubjectResponse(BaseModel):
    """Schema for subject response."""
    id: UUID
    course_id: UUID
    name: str
    color: str
    position: int
    created_at: datetime
    document_count: int = 0
    topic_count: int = 0

    class Config:
        from_attributes = True


class TopicCreate(BaseModel):
    """Schema for creating a new topic within a subject."""
    name: str = Field(..., min_length=1, max_length=255, description="Topic name")
    position: Optional[int] = Field(None, description="Display order position")


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    position: Optional[int] = None


class TopicResponse(BaseModel):
    """Schema for topic response."""
    id: UUID
    subject_id: UUID
    name: str
    position: int
    created_at: datetime
    document_count: int = 0

    class Config:
        from_attributes = True
