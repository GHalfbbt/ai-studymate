"""
Document ingestion pipeline service.

Orchestrates the full document processing flow:
Upload → Extract → Clean → Chunk → Embed → Store

Handles PDF, DOCX, TXT, and image files.
"""

from typing import Optional
from uuid import UUID
import os

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.embedder import EmbedderService
from app.services.vector_store import VectorStore
from app.utils.extractors import extract_text
from app.utils.chunkers import chunk_text


class IngestorService:
    """
    Document ingestion pipeline.

    Processes uploaded files through a multi-step pipeline:
    1. Create database record with "processing" status
    2. Extract raw text from file (PDF/DOCX/TXT)
    3. Chunk text into overlapping segments
    4. Generate embeddings for all chunks (batch)
    5. Store chunks in PostgreSQL and vectors in ChromaDB
    6. Update document status to "completed"

    If any step fails, the document status is set to "failed"
    with the error message stored for debugging.

    Usage:
        ingestor = IngestorService(db, embedder, vector_store)
        document = await ingestor.ingest_document(
            file_path="/path/to/file.pdf",
            filename="notes.pdf",
            file_type="pdf",
            subject_id=uuid,
            user_id=uuid,
        )
    """

    def __init__(
        self,
        db: Session,
        embedder: EmbedderService,
        vector_store: VectorStore,
    ):
        """
        Initialize ingestion service with required dependencies.

        Args:
            db: SQLAlchemy database session
            embedder: Embedding service for vector generation
            vector_store: ChromaDB vector store for similarity search
        """
        self.db = db
        self.embedder = embedder
        self.vector_store = vector_store

    async def ingest_document(
        self,
        file_path: str,
        filename: str,
        file_type: str,
        subject_id: UUID,
        user_id: UUID,
        document_id: UUID = None,
    ) -> Document:
        """
        Process and ingest a single document through the full pipeline.

        If document_id is provided, updates the existing record instead of
        creating a duplicate. This is the expected flow when called from
        the upload endpoint which already creates the Document row.

        Args:
            file_path: Absolute path to the uploaded file on disk
            filename: Original filename for display
            file_type: File extension (pdf, docx, txt, image)
            subject_id: Subject this document belongs to
            user_id: Owner user ID for access control metadata
            document_id: Existing document record ID (from upload endpoint)

        Returns:
            Document: Updated document record with final processing status

        Raises:
            ValueError: If the file is invalid or text extraction fails
            Exception: For any unexpected processing errors
        """
        print(f"📄 Processing document: {filename}")

        # Use existing document record if provided, otherwise create new one
        if document_id:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found in database")
            document.processing_status = "processing"
            self.db.commit()
            self.db.refresh(document)
        else:
            document = Document(
                user_id=user_id,
                subject_id=subject_id,
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                processing_status="processing",
            )
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)

        try:
            # Step 2: Extract text from document
            print(f"  📝 Extrayendo texto del archivo {file_type}...")
            text = extract_text(file_path, file_type)

            # Validate extracted text has meaningful content
            if not text or len(text.strip()) < 100:
                raise ValueError(
                    "Extracted text is too short or empty. "
                    "Minimum 100 characters required. "
                    f"Got {len(text.strip()) if text else 0} characters."
                )

            # Step 3: Chunk text into manageable overlapping segments
            print(f"  ✂️ Dividiendo texto en chunks...")
            chunks = chunk_text(
                text,
                chunk_size=600,       # ~600 tokens per chunk
                chunk_overlap=100,    # 100 token overlap for context continuity
                min_chunk_size=200,   # Discard chunks smaller than 200 tokens
            )

            if not chunks:
                raise ValueError(
                    "No valid chunks generated from document. "
                    "The text may be too short or contain only whitespace."
                )

            print(f"  📊 Generados {len(chunks)} chunks")

            # Step 4: Generate embeddings for all chunks in batch
            print(f"  🧠 Generando embeddings...")
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedder.embed_batch(chunk_texts)

            # Step 5: Store chunks in both PostgreSQL and ChromaDB
            print(f"  💾 Almacenando chunks en base de datos y vector store...")
            for idx, (chunk_data, embedding) in enumerate(zip(chunks, embeddings)):
                # Create chunk record in PostgreSQL
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=idx,
                    content=chunk_data["text"],
                    token_count=chunk_data["token_count"],
                )
                self.db.add(db_chunk)
                self.db.flush()  # Flush to get the auto-generated UUID

                # Store embedding in ChromaDB with metadata for filtering
                vector_id = self.vector_store.add_document(
                    chunk_id=str(db_chunk.id),
                    text=chunk_data["text"],
                    embedding=embedding,
                    metadata={
                        "document_id": str(document.id),
                        "subject_id": str(subject_id),
                        "user_id": str(user_id),
                        "chunk_index": idx,
                        "filename": filename,
                        "file_type": file_type,
                    },
                )

                # Link the vector store ID back to the PostgreSQL record
                db_chunk.vector_id = vector_id

            # Step 6: Update document status to completed
            document.processing_status = "completed"
            document.chunk_count = len(chunks)
            document.language = "en"  # TODO: Auto-detect with langdetect
            self.db.commit()

            print(f"  ✅ Documento procesado exitosamente: {len(chunks)} chunks almacenados")
            return document

        except Exception as e:
            # Mark document as failed and store the error message
            print(f"  ❌ Error procesando documento: {str(e)}")
            document.processing_status = "failed"
            document.processing_error = str(e)
            self.db.commit()
            raise
