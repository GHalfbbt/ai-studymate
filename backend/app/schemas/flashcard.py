"""
Flashcard-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class FlashcardGenerate(BaseModel):
    """Schema for flashcard generation request."""
    subject_id: UUID = Field(..., description="Subject to generate flashcards from")
    document_id: Optional[UUID] = Field(
        None, description="Specific document to generate from"
    )
    count: int = Field(
        default=10, ge=1, le=50, description="Number of flashcards to generate"
    )


class FlashcardResponse(BaseModel):
    """Schema for flashcard response."""
    id: UUID
    subject_id: UUID
    document_id: Optional[UUID]
    front: str
    back: str
    difficulty: str
    times_reviewed: int
    ease_factor: float
    created_at: datetime

    class Config:
        from_attributes = True


class FlashcardReview(BaseModel):
    """Schema for flashcard review submission."""
    quality: int = Field(
        ...,
        ge=0,
        le=5,
        description="Review quality: 0=total blackout, 5=perfect recall",
    )


class FlashcardListResponse(BaseModel):
    """Schema for flashcard list response."""
    flashcards: List[FlashcardResponse]
    total: int
