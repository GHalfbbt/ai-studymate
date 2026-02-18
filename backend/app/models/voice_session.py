"""
VoiceSession model for speech practice tracking.

Stores audio recordings, transcriptions, and evaluation results
for speaking and listening practice sessions.
"""

from uuid import uuid4

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class VoiceSession(Base):
    """
    Voice practice session record.

    Tracks both speaking practice (user records audio → evaluated)
    and listening practice (system generates audio → comprehension test).

    Evaluation scores range from 0.0 to 10.0 for each dimension.

    Attributes:
        id: Unique identifier (UUID v4)
        user_id: User who created the session
        session_type: 'speaking_practice' or 'listening_practice'
        audio_path: Path to stored audio file
        transcription: Speech-to-text output
        grammar_score: Grammar evaluation (0-10)
        fluency_score: Fluency evaluation (0-10)
        vocabulary_score: Vocabulary usage evaluation (0-10)
        pronunciation_score: Pronunciation evaluation (0-10)
        feedback: Structured JSON feedback with corrections
        duration_seconds: Audio duration in seconds
        language: Language of the session
        created_at: Session creation timestamp
    """
    __tablename__ = "voice_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_type = Column(
        String(30), nullable=False
    )  # speaking_practice, listening_practice

    # Session data
    audio_path = Column(String(1000))  # Path to stored audio file
    transcription = Column(Text)  # STT output

    # Evaluation scores (0-10 scale)
    grammar_score = Column(Float)
    fluency_score = Column(Float)
    vocabulary_score = Column(Float)
    pronunciation_score = Column(Float)
    feedback = Column(JSON)  # Structured feedback with corrections

    # Metadata
    duration_seconds = Column(Integer)
    language = Column(String(10), default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<VoiceSession(id={self.id}, type={self.session_type})>"
