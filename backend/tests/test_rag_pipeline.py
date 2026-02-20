"""
Phase 3 & 4 — RAG pipeline and Vector DB validation tests.

Tests cover:
- Full ingestion pipeline (extract → chunk → embed → store)
- Vector store operations (add, query, delete)
- RAG query endpoint with mocked LLM
- Source attribution in RAG responses
- Negative query (no relevant context)
- Embedding count matches chunk count
- Metadata validation in vector store
"""

import os
import uuid
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk


class TestVectorStore:
    """Phase 4 — Vector database validation."""

    def test_add_and_query_document(self, mock_embedder):
        """Add a document to vector store and query it back."""
        from app.services.vector_store import VectorStore

        # Use a temporary directory for ChromaDB
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(persist_directory=tmpdir)

            # Add a test document chunk
            chunk_id = str(uuid.uuid4())
            text = "The capital of Mars is Olympus Mons."
            embedding = mock_embedder.embed_query(text)
            metadata = {
                "document_id": str(uuid.uuid4()),
                "subject_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "chunk_index": 0,
                "filename": "test.txt",
                "file_type": "txt",
            }

            result_id = store.add_document(
                chunk_id=chunk_id,
                text=text,
                embedding=embedding,
                metadata=metadata,
            )
            assert result_id == chunk_id

            # Verify collection count increased
            assert store.get_collection_count() >= 1

    def test_query_returns_relevant_results(self, mock_embedder):
        """Query should return the most relevant chunks."""
        from app.services.vector_store import VectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(persist_directory=tmpdir)
            user_id = str(uuid.uuid4())
            doc_id = str(uuid.uuid4())
            subject_id = str(uuid.uuid4())

            # Add multiple chunks
            texts = [
                "The capital of Mars is Olympus Mons, founded in 2157.",
                "Python is a programming language created by Guido van Rossum.",
                "The governor of Olympus Mons is Dr. Elena Vasquez.",
            ]

            for i, text in enumerate(texts):
                embedding = mock_embedder.embed_query(text)
                store.add_document(
                    chunk_id=str(uuid.uuid4()),
                    text=text,
                    embedding=embedding,
                    metadata={
                        "document_id": doc_id,
                        "subject_id": subject_id,
                        "user_id": user_id,
                        "chunk_index": i,
                        "filename": "test.txt",
                        "file_type": "txt",
                    },
                )

            # Query for Mars-related content
            query_embedding = mock_embedder.embed_query("What is the capital of Mars?")
            results = store.query(
                query_embedding=query_embedding,
                filter_dict={"user_id": user_id},
                n_results=3,
            )

            assert results is not None
            assert len(results["documents"][0]) == 3
            assert len(results["metadatas"][0]) == 3
            assert len(results["distances"][0]) == 3

    def test_delete_by_document(self, mock_embedder):
        """Deleting by document_id should remove all related chunks."""
        from app.services.vector_store import VectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(persist_directory=tmpdir)
            doc_id = str(uuid.uuid4())

            # Add 3 chunks for the same document
            for i in range(3):
                embedding = mock_embedder.embed_query(f"Chunk {i} content")
                store.add_document(
                    chunk_id=str(uuid.uuid4()),
                    text=f"Chunk {i} content",
                    embedding=embedding,
                    metadata={
                        "document_id": doc_id,
                        "subject_id": str(uuid.uuid4()),
                        "user_id": str(uuid.uuid4()),
                        "chunk_index": i,
                        "filename": "test.txt",
                        "file_type": "txt",
                    },
                )

            initial_count = store.get_collection_count()
            assert initial_count == 3

            # Delete all chunks for this document
            store.delete_by_document(doc_id)

            final_count = store.get_collection_count()
            assert final_count == 0

    def test_metadata_contains_required_fields(self, mock_embedder):
        """Stored metadata must contain user_id, document_id, subject_id, chunk_index."""
        from app.services.vector_store import VectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(persist_directory=tmpdir)

            chunk_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            doc_id = str(uuid.uuid4())
            subject_id = str(uuid.uuid4())

            embedding = mock_embedder.embed_query("Test metadata content")
            store.add_document(
                chunk_id=chunk_id,
                text="Test metadata content",
                embedding=embedding,
                metadata={
                    "document_id": doc_id,
                    "subject_id": subject_id,
                    "user_id": user_id,
                    "chunk_index": 0,
                    "filename": "meta_test.txt",
                    "file_type": "txt",
                },
            )

            # Retrieve and verify metadata
            results = store.query(
                query_embedding=embedding,
                n_results=1,
            )

            meta = results["metadatas"][0][0]
            assert meta["user_id"] == user_id
            assert meta["document_id"] == doc_id
            assert meta["subject_id"] == subject_id
            assert meta["chunk_index"] == 0
            assert meta["filename"] == "meta_test.txt"

    def test_filtered_query_by_user(self, mock_embedder):
        """Query with user_id filter should only return that user's chunks."""
        from app.services.vector_store import VectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(persist_directory=tmpdir)

            user_a = str(uuid.uuid4())
            user_b = str(uuid.uuid4())

            # Add chunk for user A
            emb_a = mock_embedder.embed_query("User A's study notes about Mars")
            store.add_document(
                chunk_id=str(uuid.uuid4()),
                text="User A's study notes about Mars",
                embedding=emb_a,
                metadata={
                    "document_id": str(uuid.uuid4()),
                    "subject_id": str(uuid.uuid4()),
                    "user_id": user_a,
                    "chunk_index": 0,
                    "filename": "a.txt",
                    "file_type": "txt",
                },
            )

            # Add chunk for user B
            emb_b = mock_embedder.embed_query("User B's notes about Python")
            store.add_document(
                chunk_id=str(uuid.uuid4()),
                text="User B's notes about Python",
                embedding=emb_b,
                metadata={
                    "document_id": str(uuid.uuid4()),
                    "subject_id": str(uuid.uuid4()),
                    "user_id": user_b,
                    "chunk_index": 0,
                    "filename": "b.txt",
                    "file_type": "txt",
                },
            )

            # Query filtered by user A
            results = store.query(
                query_embedding=emb_a,
                filter_dict={"user_id": user_a},
                n_results=5,
            )

            # Should only get user A's chunk
            assert len(results["documents"][0]) == 1
            assert results["metadatas"][0][0]["user_id"] == user_a


class TestIngestionPipeline:
    """Phase 2/3 — Full ingestion pipeline with mocked embedder."""

    def test_ingest_txt_document(
        self, db: Session, mock_embedder, test_pdf_content,
    ):
        """Full ingestion pipeline should create chunks and embeddings."""
        from app.services.vector_store import VectorStore
        from app.services.ingestor import IngestorService
        from app.models.user import User
        from app.models.workspace import Workspace
        from app.models.course import Course
        from app.models.subject import Subject
        from app.core.security import hash_password

        # Create test hierarchy
        user = User(email="ingest@test.com", hashed_password=hash_password("Pass1234!"), full_name="Ingest User")
        db.add(user)
        db.flush()

        ws = Workspace(name="Ingest WS", user_id=user.id)
        db.add(ws)
        db.flush()

        course = Course(name="Ingest Course", workspace_id=ws.id)
        db.add(course)
        db.flush()

        subject = Subject(name="Ingest Subject", course_id=course.id)
        db.add(subject)
        db.commit()

        # Create test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(test_pdf_content)
            file_path = f.name

        try:
            with tempfile.TemporaryDirectory() as chroma_dir:
                vector_store = VectorStore(persist_directory=chroma_dir)
                ingestor = IngestorService(db, mock_embedder, vector_store)

                import asyncio
                loop = asyncio.new_event_loop()
                document = loop.run_until_complete(
                    ingestor.ingest_document(
                        file_path=file_path,
                        filename="mars_capital.txt",
                        file_type="txt",
                        subject_id=subject.id,
                        user_id=user.id,
                    )
                )
                loop.close()

                # Verify document record
                assert document.processing_status == "completed"
                assert document.chunk_count > 0
                assert document.filename == "mars_capital.txt"

                # Verify chunks in database
                chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document.id
                ).all()
                assert len(chunks) > 0
                assert len(chunks) == document.chunk_count

                # Verify each chunk has content and vector_id
                for chunk in chunks:
                    assert chunk.content is not None
                    assert len(chunk.content) > 0
                    assert chunk.vector_id is not None
                    assert chunk.chunk_index >= 0

                # Verify embeddings in vector store match chunk count
                vector_count = vector_store.get_collection_count()
                assert vector_count == len(chunks)

        finally:
            os.unlink(file_path)

    def test_ingest_with_existing_document_id(
        self, db: Session, mock_embedder, test_pdf_content,
    ):
        """Ingestion with document_id should update existing record (not create duplicate)."""
        from app.services.vector_store import VectorStore
        from app.services.ingestor import IngestorService
        from app.models.user import User
        from app.models.workspace import Workspace
        from app.models.course import Course
        from app.models.subject import Subject
        from app.core.security import hash_password

        # Create test hierarchy
        user = User(email="nodedup@test.com", hashed_password=hash_password("Pass1234!"), full_name="No Dup")
        db.add(user)
        db.flush()

        ws = Workspace(name="NoDup WS", user_id=user.id)
        db.add(ws)
        db.flush()

        course = Course(name="NoDup Course", workspace_id=ws.id)
        db.add(course)
        db.flush()

        subject = Subject(name="NoDup Subject", course_id=course.id)
        db.add(subject)
        db.flush()

        # Pre-create the document record (like upload endpoint does)
        existing_doc = Document(
            user_id=user.id,
            workspace_id=ws.id,
            subject_id=subject.id,
            filename="existing.txt",
            file_type="txt",
            file_path="/fake/path.txt",
            file_size=100,
            processing_status="pending",
        )
        db.add(existing_doc)
        db.commit()
        db.refresh(existing_doc)

        # Create test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(test_pdf_content)
            file_path = f.name

        try:
            with tempfile.TemporaryDirectory() as chroma_dir:
                vector_store = VectorStore(persist_directory=chroma_dir)
                ingestor = IngestorService(db, mock_embedder, vector_store)

                import asyncio
                loop = asyncio.new_event_loop()
                document = loop.run_until_complete(
                    ingestor.ingest_document(
                        file_path=file_path,
                        filename="existing.txt",
                        file_type="txt",
                        subject_id=subject.id,
                        user_id=user.id,
                        document_id=existing_doc.id,  # Pass existing ID
                    )
                )
                loop.close()

                # Should have updated the existing document, not created a new one
                assert document.id == existing_doc.id
                assert document.processing_status == "completed"

                # Count total documents — should be exactly 1
                total_docs = db.query(Document).filter(
                    Document.user_id == user.id
                ).count()
                assert total_docs == 1

        finally:
            os.unlink(file_path)

    def test_ingest_short_text_fails(self, db: Session, mock_embedder):
        """Ingestion of very short text should fail with meaningful error."""
        from app.services.vector_store import VectorStore
        from app.services.ingestor import IngestorService
        from app.models.user import User
        from app.models.workspace import Workspace
        from app.models.course import Course
        from app.models.subject import Subject
        from app.core.security import hash_password

        user = User(email="short@test.com", hashed_password=hash_password("Pass1234!"), full_name="Short")
        db.add(user)
        db.flush()

        ws = Workspace(name="Short WS", user_id=user.id)
        db.add(ws)
        db.flush()

        course = Course(name="Short Course", workspace_id=ws.id)
        db.add(course)
        db.flush()

        subject = Subject(name="Short Subject", course_id=course.id)
        db.add(subject)
        db.commit()

        # Create a file with very short content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Too short.")
            file_path = f.name

        try:
            with tempfile.TemporaryDirectory() as chroma_dir:
                vector_store = VectorStore(persist_directory=chroma_dir)
                ingestor = IngestorService(db, mock_embedder, vector_store)

                import asyncio
                loop = asyncio.new_event_loop()
                with pytest.raises(ValueError, match="too short"):
                    loop.run_until_complete(
                        ingestor.ingest_document(
                            file_path=file_path,
                            filename="short.txt",
                            file_type="txt",
                            subject_id=subject.id,
                            user_id=user.id,
                        )
                    )
                loop.close()
        finally:
            os.unlink(file_path)


class TestRAGEndpoint:
    """Phase 3 — RAG query endpoint validation."""

    def test_rag_query_with_context(
        self, client: TestClient, auth_headers: dict,
        test_user, test_subject, db: Session,
        mock_embedder, mock_llm,
    ):
        """RAG query should return answer with sources when context exists."""
        from app.services.vector_store import VectorStore

        with tempfile.TemporaryDirectory() as chroma_dir:
            vector_store = VectorStore(persist_directory=chroma_dir)

            # Add test chunks to vector store
            text = "The capital of Mars is Olympus Mons, founded in 2157."
            embedding = mock_embedder.embed_query(text)
            vector_store.add_document(
                chunk_id=str(uuid.uuid4()),
                text=text,
                embedding=embedding,
                metadata={
                    "document_id": str(uuid.uuid4()),
                    "subject_id": str(test_subject.id),
                    "user_id": str(test_user.id),
                    "chunk_index": 0,
                    "filename": "mars.txt",
                    "file_type": "txt",
                },
            )

            # Mock the RAG service singletons
            with patch("app.api.v1.rag.get_embedder", return_value=mock_embedder), \
                 patch("app.api.v1.rag.get_vector_store", return_value=vector_store), \
                 patch("app.api.v1.rag.get_llm", return_value=mock_llm):

                response = client.post(
                    "/api/v1/rag/query",
                    headers=auth_headers,
                    json={
                        "question": "What is the capital of Mars?",
                        "subject_id": str(test_subject.id),
                        "top_k": 5,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "answer" in data
                assert "sources" in data
                assert "question" in data
                assert data["question"] == "What is the capital of Mars?"
                assert len(data["sources"]) > 0

                # Verify source structure
                source = data["sources"][0]
                assert "content" in source
                assert "document_name" in source
                assert "relevance_score" in source
                assert source["document_name"] == "mars.txt"

    def test_rag_query_no_context(
        self, client: TestClient, auth_headers: dict,
        mock_embedder, mock_llm,
    ):
        """RAG query with no matching documents should return safe fallback."""
        from app.services.vector_store import VectorStore

        with tempfile.TemporaryDirectory() as chroma_dir:
            vector_store = VectorStore(persist_directory=chroma_dir)
            # Empty vector store — no documents

            with patch("app.api.v1.rag.get_embedder", return_value=mock_embedder), \
                 patch("app.api.v1.rag.get_vector_store", return_value=vector_store), \
                 patch("app.api.v1.rag.get_llm", return_value=mock_llm):

                response = client.post(
                    "/api/v1/rag/query",
                    headers=auth_headers,
                    json={
                        "question": "What is the capital of France?",
                        "top_k": 5,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "answer" in data
                assert data["sources"] == []
                # Should indicate no relevant info found
                assert "no" in data["answer"].lower() or "encontrado" in data["answer"].lower()

    def test_rag_query_requires_auth(self, client: TestClient):
        """RAG query without authentication should return 401."""
        response = client.post(
            "/api/v1/rag/query",
            json={"question": "Test question"},
        )
        assert response.status_code == 401

    def test_rag_query_empty_question(
        self, client: TestClient, auth_headers: dict,
    ):
        """RAG query with empty question should return 422."""
        response = client.post(
            "/api/v1/rag/query",
            headers=auth_headers,
            json={"question": ""},
        )
        assert response.status_code == 422

    def test_rag_status_endpoint(self, client: TestClient):
        """RAG status endpoint should return component status."""
        response = client.get("/api/v1/rag/status")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert "components" in data
        assert "embedder" in data["components"]
        assert "vector_store" in data["components"]
        assert "llm" in data["components"]


class TestEmbeddingChunkConsistency:
    """Phase 4 — Verify embedding count matches chunk count."""

    def test_embedding_count_equals_chunk_count(
        self, db: Session, mock_embedder, test_pdf_content,
    ):
        """After ingestion, vector store count must equal DB chunk count."""
        from app.services.vector_store import VectorStore
        from app.services.ingestor import IngestorService
        from app.models.user import User
        from app.models.workspace import Workspace
        from app.models.course import Course
        from app.models.subject import Subject
        from app.core.security import hash_password

        user = User(email="count@test.com", hashed_password=hash_password("Pass1234!"), full_name="Count")
        db.add(user)
        db.flush()

        ws = Workspace(name="Count WS", user_id=user.id)
        db.add(ws)
        db.flush()

        course = Course(name="Count Course", workspace_id=ws.id)
        db.add(course)
        db.flush()

        subject = Subject(name="Count Subject", course_id=course.id)
        db.add(subject)
        db.commit()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(test_pdf_content)
            file_path = f.name

        try:
            with tempfile.TemporaryDirectory() as chroma_dir:
                vector_store = VectorStore(persist_directory=chroma_dir)
                ingestor = IngestorService(db, mock_embedder, vector_store)

                import asyncio
                loop = asyncio.new_event_loop()
                document = loop.run_until_complete(
                    ingestor.ingest_document(
                        file_path=file_path,
                        filename="count_test.txt",
                        file_type="txt",
                        subject_id=subject.id,
                        user_id=user.id,
                    )
                )
                loop.close()

                # Count chunks in DB
                db_chunk_count = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document.id
                ).count()

                # Count embeddings in vector store
                vector_count = vector_store.get_collection_count()

                # They must match
                assert db_chunk_count == vector_count
                assert db_chunk_count == document.chunk_count
                assert db_chunk_count > 0

        finally:
            os.unlink(file_path)
