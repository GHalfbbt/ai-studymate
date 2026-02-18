"""
Document management API endpoints.

Provides file upload, listing, and deletion for study materials.
Documents are processed through the ingestion pipeline after upload.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.subject import Subject
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.storage import StorageService

router = APIRouter()

# Initialize storage service
storage_service = StorageService()


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT, or image)"),
    subject_id: UUID = Form(..., description="Subject to associate the document with"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a study document for processing.

    The file is saved to storage and then processed asynchronously:
    1. Text extraction (PDF/DOCX/TXT)
    2. Text chunking with overlap
    3. Embedding generation
    4. Vector store indexing

    The document starts with status 'pending' and transitions to
    'processing' → 'completed' or 'failed'.

    Args:
        file: The uploaded file
        subject_id: Subject UUID to associate the document with
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        DocumentResponse: Created document record with processing status
    """
    # Verify the subject exists and belongs to the current user
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found",
        )

    # Verify ownership through the hierarchy:
    # Subject → Course → Workspace → User
    from app.models.course import Course
    from app.models.workspace import Workspace

    course = db.query(Course).filter(Course.id == subject.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    workspace = db.query(Workspace).filter(Workspace.id == course.workspace_id).first()
    if not workspace or workspace.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to upload to this subject",
        )

    # Save file to storage
    try:
        file_info = await storage_service.save_file(file, subject_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Create document record with 'pending' status
    document = Document(
        subject_id=subject_id,
        filename=file_info["filename"],
        file_type=file_info["file_type"],
        file_path=file_info["file_path"],
        file_size=file_info["file_size"],
        processing_status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Schedule async ingestion in background
    # The actual ingestion will be triggered when the IngestorService
    # is fully integrated (requires embedder + vector store initialization)
    background_tasks.add_task(
        _process_document,
        document_id=document.id,
        file_path=file_info["file_path"],
        filename=file_info["filename"],
        file_type=file_info["file_type"],
        subject_id=subject_id,
        user_id=current_user.id,
    )

    return document


async def _process_document(
    document_id: UUID,
    file_path: str,
    filename: str,
    file_type: str,
    subject_id: UUID,
    user_id: UUID,
):
    """
    Background task for document processing.

    Runs the full ingestion pipeline asynchronously after the
    upload HTTP response has been sent.

    Args:
        document_id: Document record ID
        file_path: Path to saved file
        filename: Original filename
        file_type: File type category
        subject_id: Target subject
        user_id: Owner user
    """
    from app.core.database import SessionLocal

    # Mensaje en español para el desarrollador
    print(f"🔄 Iniciando procesamiento en background: {filename}")

    db = SessionLocal()
    try:
        # Import services here to avoid circular imports
        from app.services.embedder import EmbedderService
        from app.services.vector_store import VectorStore
        from app.services.ingestor import IngestorService

        embedder = EmbedderService()
        vector_store = VectorStore()
        ingestor = IngestorService(db, embedder, vector_store)

        # Update status to processing
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = "processing"
            db.commit()

        # Run the ingestion pipeline
        await ingestor.ingest_document(
            file_path=file_path,
            filename=filename,
            file_type=file_type,
            subject_id=subject_id,
            user_id=user_id,
        )

        print(f"✅ Documento procesado exitosamente: {filename}")

    except Exception as e:
        # Mark as failed if anything goes wrong
        print(f"❌ Error procesando documento {filename}: {str(e)}")
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = "failed"
            document.processing_error = str(e)
            db.commit()
    finally:
        db.close()


@router.get(
    "/list",
    response_model=DocumentListResponse,
    summary="List documents",
)
async def list_documents(
    subject_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List documents owned by the current user.

    Can be filtered by subject_id to show only documents
    belonging to a specific subject.

    Args:
        subject_id: Optional filter by subject
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        DocumentListResponse: List of documents with total count
    """
    from app.models.workspace import Workspace
    from app.models.course import Course

    # Build query for user's documents through the hierarchy
    query = (
        db.query(Document)
        .join(Subject)
        .join(Course)
        .join(Workspace)
        .filter(Workspace.user_id == current_user.id)
    )

    if subject_id:
        query = query.filter(Document.subject_id == subject_id)

    documents = query.order_by(Document.created_at.desc()).all()

    return DocumentListResponse(
        documents=documents,
        total=len(documents),
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details for a specific document.

    Args:
        document_id: Document UUID
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        DocumentResponse: Document details including processing status
    """
    from app.models.workspace import Workspace
    from app.models.course import Course

    document = (
        db.query(Document)
        .join(Subject)
        .join(Course)
        .join(Workspace)
        .filter(
            Document.id == document_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a document and its associated chunks and vectors.

    Args:
        document_id: Document UUID to delete
        db: Database session (injected)
        current_user: Authenticated user (injected)
    """
    from app.models.workspace import Workspace
    from app.models.course import Course

    document = (
        db.query(Document)
        .join(Subject)
        .join(Course)
        .join(Workspace)
        .filter(
            Document.id == document_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete vectors from ChromaDB
    try:
        from app.services.vector_store import VectorStore

        vector_store = VectorStore()
        vector_store.delete_by_document(str(document_id))
    except Exception as e:
        # Log but don't fail the deletion
        print(f"⚠️ Error eliminando vectores: {str(e)}")

    # Delete file from storage
    storage_service.delete_file(document.file_path)

    # Delete from database (cascades to chunks)
    db.delete(document)
    db.commit()
