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
    description: Optional[str] = Field(None, description="Course description")


class CourseResponse(BaseModel):
    """Schema for course response."""
    id: UUID
    workspace_id: UUID
    name: str
    created_at: datetime
    subject_count: int = 0

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    """Schema for creating a new subject within a course."""
    name: str = Field(..., min_length=1, max_length=255, description="Subject name")
    description: Optional[str] = Field(None, description="Subject description")
    color: Optional[str] = Field(
        "#3B82F6",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code for UI",
    )


class SubjectResponse(BaseModel):
    """Schema for subject response."""
    id: UUID
    course_id: UUID
    name: str
    color: str
    created_at: datetime
    document_count: int = 0

    class Config:
        from_attributes = True
