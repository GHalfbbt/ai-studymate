"""
Document management API endpoints.

Provides file upload, listing, and deletion for study materials.
Documents can be attached at any hierarchy level:
  workspace → course → subject → topic
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.document import Document
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
    workspace_id: Optional[UUID] = Form(None, description="Workspace to attach to"),
    course_id: Optional[UUID] = Form(None, description="Course to attach to"),
    subject_id: Optional[UUID] = Form(None, description="Subject to attach to"),
    topic_id: Optional[UUID] = Form(None, description="Topic to attach to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a study document for processing.

    Attach to ANY hierarchy level. At least one ID must be provided.
    The most specific level wins for organization purposes.

    Processing pipeline (async):
    1. Text extraction (PDF with OCR / DOCX / TXT)
    2. Text chunking with overlap
    3. Embedding generation (sentence-transformers)
    4. Vector store indexing (ChromaDB)
    """
    # Validate: at least one hierarchy ID must be provided
    if not any([workspace_id, course_id, subject_id, topic_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of workspace_id, course_id, subject_id, or topic_id must be provided",
        )

    # Verify ownership through the hierarchy
    from app.models.workspace import Workspace
    from app.models.course import Course
    from app.models.subject import Subject
    from app.models.topic import Topic

    # Determine the target and verify ownership
    owner_workspace_id = None

    if topic_id:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        subject = db.query(Subject).filter(Subject.id == topic.subject_id).first()
        course = db.query(Course).filter(Course.id == subject.course_id).first()
        owner_workspace_id = course.workspace_id
        # Auto-fill parent IDs
        subject_id = subject_id or topic.subject_id
        course_id = course_id or subject.course_id
        workspace_id = workspace_id or course.workspace_id

    elif subject_id:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        course = db.query(Course).filter(Course.id == subject.course_id).first()
        owner_workspace_id = course.workspace_id
        course_id = course_id or subject.course_id
        workspace_id = workspace_id or course.workspace_id

    elif course_id:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        owner_workspace_id = course.workspace_id
        workspace_id = workspace_id or course.workspace_id

    elif workspace_id:
        owner_workspace_id = workspace_id

    # Verify workspace belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == owner_workspace_id, Workspace.user_id == current_user.id
    ).first()
    if not workspace:
        raise HTTPException(status_code=403, detail="You don't have permission to upload here")

    # Save file to storage
    storage_key = subject_id or course_id or workspace_id
    try:
        file_info = await storage_service.save_file(file, storage_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create document record
    document = Document(
        user_id=current_user.id,
        workspace_id=workspace_id,
        course_id=course_id,
        subject_id=subject_id,
        topic_id=topic_id,
        filename=file_info["filename"],
        file_type=file_info["file_type"],
        file_path=file_info["file_path"],
        file_size=file_info["file_size"],
        processing_status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Schedule async processing
    background_tasks.add_task(
        _process_document_sync,
        document_id=document.id,
        file_path=file_info["file_path"],
        filename=file_info["filename"],
        file_type=file_info["file_type"],
        subject_id=subject_id,
        user_id=current_user.id,
    )

    return document


def _process_document_sync(
    document_id: UUID,
    file_path: str,
    filename: str,
    file_type: str,
    subject_id: Optional[UUID],
    user_id: UUID,
):
    """
    Background task for document processing (synchronous wrapper).

    BackgroundTasks runs this in a thread pool. The actual ingestion
    pipeline extracts text, chunks it, generates embeddings, and
    stores vectors in ChromaDB.
    """
    import asyncio
    from app.core.database import SessionLocal

    print(f"🔄 Iniciando procesamiento en background: {filename}")

    db = SessionLocal()
    try:
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

        # Run the async ingestion pipeline in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                ingestor.ingest_document(
                    file_path=file_path,
                    filename=filename,
                    file_type=file_type,
                    subject_id=subject_id,
                    user_id=user_id,
                )
            )
        finally:
            loop.close()

        print(f"✅ Documento procesado exitosamente: {filename}")

    except Exception as e:
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
    workspace_id: Optional[UUID] = None,
    course_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
    topic_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List documents owned by the current user.
    Can filter by any hierarchy level.
    """
    # Use user_id directly (no complex JOINs)
    query = db.query(Document).filter(Document.user_id == current_user.id)

    if workspace_id:
        query = query.filter(Document.workspace_id == workspace_id)
    if course_id:
        query = query.filter(Document.course_id == course_id)
    if subject_id:
        query = query.filter(Document.subject_id == subject_id)
    if topic_id:
        query = query.filter(Document.topic_id == topic_id)

    documents = query.order_by(Document.created_at.desc()).all()

    return DocumentListResponse(documents=documents, total=len(documents))


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
    """Get details for a specific document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
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
    """Delete a document, its chunks, and its vectors."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete vectors from ChromaDB
    try:
        from app.services.vector_store import VectorStore
        vector_store = VectorStore()
        vector_store.delete_by_document(str(document_id))
    except Exception as e:
        print(f"⚠️ Error eliminando vectores: {str(e)}")

    # Delete file from storage
    storage_service.delete_file(document.file_path)

    # Delete from database (cascades to chunks)
    db.delete(document)
    db.commit()
