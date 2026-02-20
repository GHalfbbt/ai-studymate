"""
SQLAlchemy models package.

Imports all models to ensure they are registered with the Base metadata
before Alembic or any other tool inspects the schema.
"""

from app.models.user import User
from app.models.workspace import Workspace
from app.models.course import Course
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.document import Document, DocumentChunk
from app.models.exam import Exam, ExamQuestion, ExamAttempt, ExamAnswer
from app.models.flashcard import Flashcard
from app.models.voice_session import VoiceSession

__all__ = [
    "User",
    "Workspace",
    "Course",
    "Subject",
    "Topic",
    "Document",
    "DocumentChunk",
    "Exam",
    "ExamQuestion",
    "ExamAttempt",
    "ExamAnswer",
    "Flashcard",
    "VoiceSession",
]
