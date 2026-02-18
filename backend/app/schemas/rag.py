"""
RAG query Pydantic schemas for request/response validation.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class RAGQuery(BaseModel):
    """Schema for RAG query request."""
    question: str = Field(..., min_length=3, description="User's question")
    subject_id: Optional[UUID] = Field(None, description="Filter by subject")
    document_ids: Optional[List[UUID]] = Field(
        None, description="Filter by specific documents"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class RAGSource(BaseModel):
    """Schema for a single RAG source citation."""
    source_number: int
    document_id: Optional[str]
    filename: Optional[str]
    chunk_index: Optional[int]
    relevance_score: float
    excerpt: str


class RAGResponse(BaseModel):
    """Schema for RAG query response."""
    answer: str
    sources: List[RAGSource]
    confidence: float
