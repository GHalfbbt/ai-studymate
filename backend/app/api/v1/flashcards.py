"""
Flashcard API endpoints.

Handles flashcard generation, listing, review, and CSV export.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.flashcard import Flashcard
from app.schemas.flashcard import (
    FlashcardGenerate,
    FlashcardResponse,
    FlashcardListResponse,
    FlashcardReview,
)

router = APIRouter()


@router.post("/generate", response_model=List[FlashcardResponse], status_code=status.HTTP_201_CREATED)
def generate_flashcards(
    data: FlashcardGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate flashcards from study materials using AI.

    Creates Q&A pairs from document chunks for spaced repetition learning.

    Args:
        data: Flashcard generation configuration

    Returns:
        List of created flashcards
    """
    from app.services.llm_client import LLMClient
    from app.services.flashcard_generator import FlashcardGeneratorService

    llm = LLMClient()
    generator = FlashcardGeneratorService(db=db, llm=llm)

    # Validate at least one scope is provided
    if not any([data.subject_id, data.course_id, data.workspace_id, data.document_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of subject_id, course_id, workspace_id, or document_id must be provided",
        )

    try:
        flashcards = generator.generate_flashcards(
            subject_id=data.subject_id,
            user_id=current_user.id,
            count=data.count,
            document_id=data.document_id,
            course_id=data.course_id,
            workspace_id=data.workspace_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return flashcards


@router.get("/", response_model=FlashcardListResponse)
def list_flashcards(
    subject_id: Optional[UUID] = None,
    due_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List flashcards for a subject.

    Args:
        subject_id: Subject to get flashcards for
        due_only: If true, only return cards due for review

    Returns:
        FlashcardListResponse with flashcards and total count
    """
    from datetime import datetime
    from app.models.subject import Subject
    from app.models.course import Course
    from app.models.workspace import Workspace

    query = db.query(Flashcard)

    if subject_id:
        query = query.filter(Flashcard.subject_id == subject_id)

    # Filter by user ownership: only flashcards whose subject belongs to user's workspace
    user_workspace_ids = [w.id for w in db.query(Workspace).filter(Workspace.user_id == current_user.id).all()]
    user_course_ids = [c.id for c in db.query(Course).filter(Course.workspace_id.in_(user_workspace_ids)).all()]
    user_subject_ids = [s.id for s in db.query(Subject).filter(Subject.course_id.in_(user_course_ids)).all()]
    query = query.filter(Flashcard.subject_id.in_(user_subject_ids))

    if due_only:
        now = datetime.utcnow()
        query = query.filter(
            (Flashcard.next_review == None) | (Flashcard.next_review <= now)
        )

    flashcards = query.order_by(Flashcard.created_at.desc()).all()

    return FlashcardListResponse(
        flashcards=flashcards,
        total=len(flashcards),
    )


@router.post("/{flashcard_id}/review", response_model=FlashcardResponse)
def review_flashcard(
    flashcard_id: UUID,
    data: FlashcardReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a flashcard review result.

    Updates the spaced repetition schedule using SM-2 algorithm.

    Args:
        flashcard_id: Flashcard being reviewed
        data: Review quality (0-5)

    Returns:
        Updated flashcard with new review schedule
    """
    from app.services.llm_client import LLMClient
    from app.services.flashcard_generator import FlashcardGeneratorService

    llm = LLMClient()
    generator = FlashcardGeneratorService(db=db, llm=llm)

    try:
        flashcard = generator.update_review(
            flashcard_id=flashcard_id,
            quality=data.quality,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return flashcard


@router.get("/export/csv")
def export_flashcards_csv(
    subject_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export flashcards as tab-separated CSV for Anki import.

    Format: front<TAB>back (one card per line)

    Args:
        subject_id: Subject to export

    Returns:
        Plain text CSV content
    """
    from app.services.llm_client import LLMClient
    from app.services.flashcard_generator import FlashcardGeneratorService

    llm = LLMClient()
    generator = FlashcardGeneratorService(db=db, llm=llm)
    csv_content = generator.export_csv(subject_id)

    if not csv_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No flashcards found for this subject",
        )

    return PlainTextResponse(
        content=csv_content,
        media_type="text/tab-separated-values",
        headers={
            "Content-Disposition": f"attachment; filename=flashcards_{subject_id}.csv"
        },
    )


@router.delete("/{flashcard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flashcard(
    flashcard_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a specific flashcard.

    Args:
        flashcard_id: Flashcard to delete
    """
    flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard not found",
        )

    db.delete(flashcard)
    db.commit()


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_flashcards(
    subject_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete all flashcards for a subject.

    Args:
        subject_id: Subject to clear flashcards for
    """
    db.query(Flashcard).filter(Flashcard.subject_id == subject_id).delete()
    db.commit()
