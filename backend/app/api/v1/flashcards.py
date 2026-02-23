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

    user_provider = getattr(current_user, "llm_provider", None) or "auto"
    llm = LLMClient(provider=None if user_provider == "auto" else user_provider)
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

    user_provider = getattr(current_user, "llm_provider", None) or "auto"
    llm = LLMClient(provider=None if user_provider == "auto" else user_provider)
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

    user_provider = getattr(current_user, "llm_provider", None) or "auto"
    llm = LLMClient(provider=None if user_provider == "auto" else user_provider)
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
    from app.models.subject import Subject
    from app.models.course import Course
    from app.models.workspace import Workspace

    flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard not found",
        )

    # Verify ownership
    user_workspace_ids = [w.id for w in db.query(Workspace).filter(Workspace.user_id == current_user.id).all()]
    user_course_ids = [c.id for c in db.query(Course).filter(Course.workspace_id.in_(user_workspace_ids)).all()]
    user_subject_ids = [s.id for s in db.query(Subject).filter(Subject.course_id.in_(user_course_ids)).all()]
    if flashcard.subject_id not in user_subject_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this flashcard",
        )

    db.delete(flashcard)
    db.commit()


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_flashcards(
    subject_id: Optional[UUID] = None,
    course_id: Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete all flashcards at a given scope level.

    Supports deleting by subject_id, course_id, or workspace_id.
    At least one must be provided.

    Args:
        subject_id: Delete flashcards for this subject
        course_id: Delete flashcards for all subjects in this course
        workspace_id: Delete flashcards for all subjects in this workspace
    """
    from app.models.subject import Subject
    from app.models.course import Course
    from app.models.workspace import Workspace

    if not any([subject_id, course_id, workspace_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of subject_id, course_id, or workspace_id must be provided",
        )

    # Verify ownership and resolve target subject_ids
    user_workspace_ids = [w.id for w in db.query(Workspace).filter(Workspace.user_id == current_user.id).all()]
    user_course_ids = [c.id for c in db.query(Course).filter(Course.workspace_id.in_(user_workspace_ids)).all()]
    user_subject_ids = [s.id for s in db.query(Subject).filter(Subject.course_id.in_(user_course_ids)).all()]

    target_subject_ids = []

    if subject_id:
        if subject_id not in user_subject_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete flashcards for this subject",
            )
        target_subject_ids = [subject_id]
    elif course_id:
        if course_id not in user_course_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete flashcards for this course",
            )
        target_subject_ids = [s.id for s in db.query(Subject).filter(Subject.course_id == course_id).all()]
    elif workspace_id:
        if workspace_id not in user_workspace_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete flashcards for this workspace",
            )
        ws_course_ids = [c.id for c in db.query(Course).filter(Course.workspace_id == workspace_id).all()]
        target_subject_ids = [s.id for s in db.query(Subject).filter(Subject.course_id.in_(ws_course_ids)).all()]

    if target_subject_ids:
        db.query(Flashcard).filter(Flashcard.subject_id.in_(target_subject_ids)).delete(synchronize_session=False)
        db.commit()


@router.get("/export/json")
def export_flashcards_json(
    subject_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export flashcards as JSON with full spaced repetition state.

    Includes pool, difficulty, review history, ease factor — everything
    needed to import and restore the exact learning state.

    Args:
        subject_id: Subject to export

    Returns:
        JSON with flashcards and full state
    """
    flashcards = (
        db.query(Flashcard)
        .filter(Flashcard.subject_id == subject_id)
        .order_by(Flashcard.created_at)
        .all()
    )

    if not flashcards:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No flashcards found for this subject",
        )

    export_data = {
        "version": "1.0",
        "subject_id": str(subject_id),
        "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
        "total": len(flashcards),
        "flashcards": [
            {
                "front": fc.front,
                "back": fc.back,
                "difficulty": fc.difficulty,
                "times_reviewed": fc.times_reviewed or 0,
                "ease_factor": fc.ease_factor or 2.5,
                "last_reviewed": fc.last_reviewed.isoformat() if fc.last_reviewed else None,
                "next_review": fc.next_review.isoformat() if fc.next_review else None,
                "created_at": fc.created_at.isoformat() if fc.created_at else None,
            }
            for fc in flashcards
        ],
    }

    return export_data


@router.post("/import/json", response_model=List[FlashcardResponse], status_code=status.HTTP_201_CREATED)
def import_flashcards_json(
    subject_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import flashcards from JSON with full spaced repetition state.

    Restores pool, difficulty, review history, ease factor.

    Args:
        subject_id: Subject to import into
        data: JSON with flashcards array

    Returns:
        List of created flashcards
    """
    from datetime import datetime

    flashcards_data = data.get("flashcards", [])
    if not flashcards_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No flashcards found in import data",
        )

    created = []
    for fc_data in flashcards_data:
        # Parse dates if provided
        last_reviewed = None
        next_review = None
        created_at = None
        if fc_data.get("last_reviewed"):
            try:
                last_reviewed = datetime.fromisoformat(fc_data["last_reviewed"])
            except (ValueError, TypeError):
                pass
        if fc_data.get("next_review"):
            try:
                next_review = datetime.fromisoformat(fc_data["next_review"])
            except (ValueError, TypeError):
                pass

        flashcard = Flashcard(
            subject_id=subject_id,
            front=fc_data.get("front", ""),
            back=fc_data.get("back", ""),
            difficulty=fc_data.get("difficulty", "medium"),
            times_reviewed=fc_data.get("times_reviewed", 0),
            ease_factor=fc_data.get("ease_factor", 2.5),
            last_reviewed=last_reviewed,
            next_review=next_review,
        )
        db.add(flashcard)
        created.append(flashcard)

    db.commit()
    for fc in created:
        db.refresh(fc)

    return created
