"""
Exam-related models for test generation and evaluation.

Includes Exam (container), ExamQuestion (individual questions),
ExamAttempt (user test sessions), and ExamAnswer (user responses).
"""

from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Exam(Base):
    """
    Generated exam from study materials.

    Contains multiple questions (multiple choice and short answer).
    Tracks which documents were used to generate the questions.

    Attributes:
        id: Unique identifier (UUID v4)
        subject_id: Subject this exam covers
        title: Exam display title
        description: Optional exam description
        question_count: Total number of questions
        mc_count: Number of multiple choice questions
        short_answer_count: Number of short answer questions
        generated_from_document_ids: JSON list of source document IDs
        created_at: Generation timestamp
    """
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Exam configuration
    question_count = Column(Integer, nullable=False)
    mc_count = Column(Integer, default=0)
    short_answer_count = Column(Integer, default=0)

    # Generation metadata
    generated_from_document_ids = Column(JSON)  # List of source document IDs
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subject = relationship("Subject")
    questions = relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    attempts = relationship("ExamAttempt", back_populates="exam")

    def __repr__(self) -> str:
        return f"<Exam(id={self.id}, title={self.title})>"


class ExamQuestion(Base):
    """
    Individual question within an exam.

    Supports two question types:
    - 'mc': Multiple choice with 4 options (A, B, C, D)
    - 'short_answer': Open-ended with model answer and keywords

    Attributes:
        id: Unique identifier (UUID v4)
        exam_id: Parent exam reference
        question_order: Display order within the exam (1-indexed)
        question_type: 'mc' or 'short_answer'
        question_text: The question prompt
        options: JSON list of answer options (MC only)
        correct_answer: Correct option letter (MC only, e.g., "B")
        model_answer: Expected answer text (short answer only)
        keywords: JSON list of key concepts to check (short answer only)
        explanation: Why the correct answer is right
        difficulty: easy/medium/hard
        topic: Specific topic or subtopic covered
    """
    __tablename__ = "exam_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    exam_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_order = Column(Integer, nullable=False)
    question_type = Column(String(20), nullable=False)  # mc, short_answer

    # Question content
    question_text = Column(Text, nullable=False)

    # Multiple choice specific fields
    options = Column(JSON)  # ["Option A", "Option B", "Option C", "Option D"]
    correct_answer = Column(String(10))  # "B" for MC, null for short answer

    # Short answer specific fields
    model_answer = Column(Text)  # Expected answer
    keywords = Column(JSON)  # Key concepts to check

    # Metadata
    explanation = Column(Text)  # Why this answer is correct
    difficulty = Column(String(10), default="medium")  # easy, medium, hard
    topic = Column(String(255))  # Topic/subtopic covered

    # Relationships
    exam = relationship("Exam", back_populates="questions")

    def __repr__(self) -> str:
        return f"<ExamQuestion(id={self.id}, type={self.question_type}, order={self.question_order})>"


class ExamAttempt(Base):
    """
    User's attempt at taking an exam.

    Tracks the session from start to completion, including
    final score and individual answers.

    Attributes:
        id: Unique identifier (UUID v4)
        exam_id: Exam being attempted
        user_id: User taking the exam
        started_at: When the attempt began
        completed_at: When the attempt was finished
        status: in_progress/completed/abandoned
        score: Final percentage score (0-100)
        total_questions: Total questions in exam
        correct_answers: Number answered correctly
    """
    __tablename__ = "exam_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    exam_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Attempt metadata
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    status = Column(
        String(20), default="in_progress"
    )  # in_progress, completed, abandoned

    # Results
    score = Column(Float)  # Percentage (0-100)
    total_questions = Column(Integer)
    correct_answers = Column(Integer)

    # Relationships
    exam = relationship("Exam", back_populates="attempts")
    user = relationship("User")
    answers = relationship(
        "ExamAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ExamAttempt(id={self.id}, status={self.status}, score={self.score})>"


class ExamAnswer(Base):
    """
    User's answer to a specific exam question.

    Stores the submitted answer, whether it's correct, and
    detailed LLM-generated feedback for short answer questions.

    Attributes:
        id: Unique identifier (UUID v4)
        attempt_id: Parent attempt reference
        question_id: Question being answered
        user_answer: User's submitted answer text
        is_correct: Boolean correctness flag
        score: Numeric score for short answers (0-10)
        llm_feedback: Detailed feedback text
        answered_at: Submission timestamp
    """
    __tablename__ = "exam_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User's answer
    user_answer = Column(Text, nullable=False)

    # Evaluation
    is_correct = Column(Boolean)
    score = Column(Float)  # For short answers (0-10)
    llm_feedback = Column(Text)  # Detailed feedback

    # Timestamps
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    attempt = relationship("ExamAttempt", back_populates="answers")
    question = relationship("ExamQuestion")

    def __repr__(self) -> str:
        return f"<ExamAnswer(id={self.id}, correct={self.is_correct})>"
