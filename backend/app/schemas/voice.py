"""
Voice-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Schema for STT transcription response."""
    text: str = Field(..., description="Transcribed text")
    language: str = Field(..., description="Detected language")
    duration_seconds: Optional[int] = Field(None, description="Audio duration")
    provider: str = Field(..., description="STT provider used")


class SynthesizeRequest(BaseModel):
    """Schema for TTS synthesis request."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    language: str = Field(default="en", description="Target language")
    voice: Optional[str] = Field(None, description="Specific voice to use")


class SpeakingEvaluation(BaseModel):
    """Schema for speaking practice evaluation response."""
    transcription: str
    grammar_score: float = Field(..., ge=0, le=10)
    fluency_score: float = Field(..., ge=0, le=10)
    vocabulary_score: float = Field(..., ge=0, le=10)
    pronunciation_score: float = Field(..., ge=0, le=10)
    overall_score: float = Field(..., ge=0, le=10)
    feedback: Dict[str, Any]
    corrections: List[Dict[str, str]]


class VoiceSessionResponse(BaseModel):
    """Schema for voice session response."""
    id: UUID
    session_type: str
    transcription: Optional[str]
    grammar_score: Optional[float]
    fluency_score: Optional[float]
    vocabulary_score: Optional[float]
    pronunciation_score: Optional[float]
    feedback: Optional[Dict[str, Any]]
    duration_seconds: Optional[int]
    language: str
    created_at: datetime

    class Config:
        from_attributes = True
