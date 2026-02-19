"""
Exam API endpoints.

Handles exam generation, retrieval, submission, and evaluation.
"""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.exam import Exam, ExamQuestion, ExamAttempt, ExamAnswer
from app.schemas.exam import (
    ExamGenerate,
    ExamResponse,
    ExamQuestionResponse,
    SubmitExam,
    ExamResultResponse,
    ExamAnswerFeedback,
)

router = APIRouter()


@router.post("/generate", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def generate_exam(
    data: ExamGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an exam from study materials using AI.

    The LLM creates questions based on document chunks stored
    for the specified subject. Supports multiple choice and
    short answer question types.

    Args:
        data: Exam generation configuration

    Returns:
        ExamResponse: Generated exam with questions (answers hidden)
    """
    from app.services.llm_client import LLMClient
    from app.services.exam_generator import ExamGeneratorService

    llm = LLMClient()
    generator = ExamGeneratorService(db=db, llm=llm)

    try:
        exam = generator.generate_exam(
            subject_id=data.subject_id,
            user_id=current_user.id,
            mc_count=data.mc_count,
            short_answer_count=data.short_answer_count,
            difficulty=data.difficulty,
            title=data.title,
            document_ids=data.document_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return exam


@router.get("/", response_model=List[ExamResponse])
def list_exams(
    subject_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List exams, optionally filtered by subject.

    Args:
        subject_id: Optional filter by subject

    Returns:
        List of exams with their questions
    """
    query = db.query(Exam)

    if subject_id:
        query = query.filter(Exam.subject_id == subject_id)

    # Order by most recent first
    exams = query.order_by(Exam.created_at.desc()).limit(50).all()
    return exams


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific exam by ID.

    Args:
        exam_id: Exam UUID

    Returns:
        ExamResponse with questions (answers hidden for taking)
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    return exam


@router.post("/{exam_id}/start")
def start_exam_attempt(
    exam_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a new exam attempt.

    Creates an ExamAttempt record to track the session.

    Args:
        exam_id: Exam to start

    Returns:
        Dict with attempt_id and exam details
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    attempt = ExamAttempt(
        exam_id=exam_id,
        user_id=current_user.id,
        total_questions=exam.question_count,
        status="in_progress",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": str(attempt.id),
        "exam_id": str(exam_id),
        "exam_title": exam.title,
        "total_questions": exam.question_count,
        "started_at": attempt.started_at.isoformat(),
    }


@router.post("/{exam_id}/submit", response_model=ExamResultResponse)
def submit_exam(
    exam_id: UUID,
    data: SubmitExam,
    attempt_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit exam answers for evaluation.

    Automatically grades MC questions and uses LLM for short answers.

    Args:
        exam_id: Exam being submitted
        data: All answers
        attempt_id: Optional attempt ID (creates one if not provided)

    Returns:
        ExamResultResponse with scores and feedback for each question
    """
    from app.services.llm_client import LLMClient
    from app.services.exam_generator import ExamGeneratorService

    # Get exam with questions
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    # Get or create attempt
    if attempt_id:
        attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    else:
        attempt = ExamAttempt(
            exam_id=exam_id,
            user_id=current_user.id,
            total_questions=exam.question_count,
            status="in_progress",
        )
        db.add(attempt)
        db.flush()

    # Build question lookup
    questions_map = {str(q.id): q for q in exam.questions}

    llm = LLMClient()
    generator = ExamGeneratorService(db=db, llm=llm)

    correct_count = 0
    total_score = 0
    feedbacks = []

    for answer_data in data.answers:
        question = questions_map.get(str(answer_data.question_id))
        if not question:
            continue

        is_correct = False
        score = 0.0
        feedback_text = ""

        if question.question_type == "mc":
            # Automatic grading for multiple choice
            is_correct = (
                answer_data.user_answer.strip().upper()
                == (question.correct_answer or "").strip().upper()
            )
            score = 10.0 if is_correct else 0.0
            if is_correct:
                feedback_text = "Correct!"
                correct_count += 1
            else:
                feedback_text = (
                    f"Incorrect. The correct answer is {question.correct_answer}."
                )
        else:
            # LLM evaluation for short answer
            eval_result = generator.evaluate_short_answer(
                question_text=question.question_text,
                model_answer=question.model_answer or "",
                keywords=question.keywords or [],
                user_answer=answer_data.user_answer,
            )
            is_correct = eval_result["is_correct"]
            score = eval_result["score"]
            feedback_text = eval_result["feedback"]
            if is_correct:
                correct_count += 1

        total_score += score

        # Save answer record
        exam_answer = ExamAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            user_answer=answer_data.user_answer,
            is_correct=is_correct,
            score=score,
            llm_feedback=feedback_text,
        )
        db.add(exam_answer)

        feedbacks.append(
            ExamAnswerFeedback(
                question_id=question.id,
                question_text=question.question_text,
                question_type=question.question_type,
                user_answer=answer_data.user_answer,
                correct_answer=question.correct_answer or question.model_answer,
                is_correct=is_correct,
                score=score,
                feedback=feedback_text,
                explanation=question.explanation,
            )
        )

    # Calculate final score as percentage
    total_questions = len(data.answers) or 1
    final_score = (total_score / (total_questions * 10)) * 100

    # Update attempt
    attempt.completed_at = datetime.utcnow()
    attempt.status = "completed"
    attempt.score = round(final_score, 1)
    attempt.correct_answers = correct_count

    db.commit()
    db.refresh(attempt)

    return ExamResultResponse(
        attempt_id=attempt.id,
        exam_id=exam.id,
        exam_title=exam.title,
        score=attempt.score,
        total_questions=total_questions,
        correct_answers=correct_count,
        answers=feedbacks,
        completed_at=attempt.completed_at,
    )


@router.get("/{exam_id}/attempts")
def list_attempts(
    exam_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all attempts for a specific exam by the current user.

    Args:
        exam_id: Exam to get attempts for

    Returns:
        List of attempt summaries
    """
    attempts = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.user_id == current_user.id,
        )
        .order_by(ExamAttempt.started_at.desc())
        .all()
    )

    return [
        {
            "attempt_id": str(a.id),
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "status": a.status,
            "score": a.score,
            "correct_answers": a.correct_answers,
            "total_questions": a.total_questions,
        }
        for a in attempts
    ]


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an exam and all associated questions/attempts.

    Args:
        exam_id: Exam to delete
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    db.delete(exam)
    db.commit()
