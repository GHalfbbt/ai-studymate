"""
Exam-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class ExamGenerate(BaseModel):
    """Schema for exam generation request."""
    subject_id: Optional[UUID] = Field(None, description="Subject to generate exam from")
    course_id: Optional[UUID] = Field(None, description="Course to generate exam from (all docs)")
    workspace_id: Optional[UUID] = Field(None, description="Workspace to generate exam from (all docs)")
    title: Optional[str] = Field(None, description="Custom exam title")
    mc_count: int = Field(
        default=5, ge=0, le=30, description="Number of multiple choice questions"
    )
    short_answer_count: int = Field(
        default=3, ge=0, le=15, description="Number of short answer questions"
    )
    difficulty: str = Field(
        default="medium", description="Target difficulty: easy, medium, hard"
    )
    document_ids: Optional[List[UUID]] = Field(
        None, description="Specific documents to generate from"
    )


class ExamQuestionResponse(BaseModel):
    """Schema for a single exam question response."""
    id: UUID
    question_order: int
    question_type: str
    question_text: str
    options: Optional[List[str]]
    difficulty: str
    topic: Optional[str]

    class Config:
        from_attributes = True


class ExamResponse(BaseModel):
    """Schema for exam response (without answers)."""
    id: UUID
    subject_id: Optional[UUID] = None
    title: str
    description: Optional[str]
    question_count: int
    mc_count: int
    short_answer_count: int
    questions: List[ExamQuestionResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class SubmitAnswer(BaseModel):
    """Schema for submitting an answer to a question."""
    question_id: UUID = Field(..., description="Question being answered")
    user_answer: str = Field(..., min_length=1, description="User's answer")


class SubmitExam(BaseModel):
    """Schema for submitting a complete exam."""
    answers: List[SubmitAnswer]


class ExamAnswerFeedback(BaseModel):
    """Schema for feedback on a single answer."""
    question_id: UUID
    question_text: str
    question_type: str
    user_answer: str
    correct_answer: Optional[str]
    is_correct: bool
    score: Optional[float]
    feedback: Optional[str]
    explanation: Optional[str]


class ExamResultResponse(BaseModel):
    """Schema for exam results response."""
    attempt_id: UUID
    exam_id: UUID
    exam_title: str
    score: float
    total_questions: int
    correct_answers: int
    answers: List[ExamAnswerFeedback]
    completed_at: datetime
