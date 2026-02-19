"""
RAG (Retrieval-Augmented Generation) API endpoints.

Provides the study chat functionality: receives a question,
retrieves relevant document chunks via vector search, and
generates an AI-powered answer using the LLM.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User

# NOTE: Heavy ML/AI imports (embedder, vector_store, llm_client) are
# done lazily inside the factory functions below to avoid crashing
# the backend at startup if dependencies have issues.

router = APIRouter()

# Initialize services (singleton pattern — loaded lazily on first use)
_embedder = None
_vector_store = None
_llm = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from app.services.embedder import EmbedderService
        _embedder = EmbedderService()
    return _embedder


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        from app.services.vector_store import VectorStore
        _vector_store = VectorStore()
    return _vector_store


def get_llm():
    global _llm
    if _llm is None:
        from app.services.llm_client import LLMClient
        _llm = LLMClient()
    return _llm


# ─── Request/Response Schemas ────────────────────────────

class RAGQuery(BaseModel):
    """Request schema for RAG query."""
    question: str = Field(..., min_length=1, max_length=2000, description="Study question")
    subject_id: Optional[UUID] = Field(None, description="Filter by subject (optional)")
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks to retrieve")


class RAGSource(BaseModel):
    """A source document chunk used in the answer."""
    content: str
    document_name: str
    chunk_index: int
    relevance_score: float


class RAGResponse(BaseModel):
    """Response schema for RAG query."""
    answer: str
    sources: list[RAGSource]
    question: str


# ─── Endpoints ───────────────────────────────────────────

@router.post(
    "/query",
    response_model=RAGResponse,
    summary="Ask a question about your study materials",
)
async def rag_query(
    query: RAGQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieval-Augmented Generation query.

    1. Embeds the question using sentence-transformers
    2. Searches ChromaDB for similar document chunks
    3. Sends relevant chunks + question to Groq LLM
    4. Returns the AI answer with source references
    """
    embedder = get_embedder()
    vector_store = get_vector_store()
    llm = get_llm()

    # Build metadata filter for the user's documents
    where_filter = {"user_id": str(current_user.id)}
    if query.subject_id:
        where_filter["subject_id"] = str(query.subject_id)

    # 1. Embed the question
    query_embedding = embedder.embed_query(query.question)

    # 2. Search vector store for relevant chunks
    results = vector_store.query(
        query_embedding=query_embedding,
        n_results=query.top_k,
        filter_dict=where_filter,
    )

    if not results or not results.get("documents") or not results["documents"][0]:
        # No relevant documents found
        return RAGResponse(
            answer="No he encontrado información relevante en tus materiales de estudio sobre esta pregunta. "
                   "Intenta subir documentos relacionados con el tema o reformula tu pregunta.",
            sources=[],
            question=query.question,
        )

    # 3. Extract chunks and metadata
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(chunks)
    distances = results["distances"][0] if results.get("distances") else [0.0] * len(chunks)

    # 4. Generate AI answer using LLM with context
    answer = llm.generate_with_context(
        question=query.question,
        context_chunks=chunks,
    )

    # 5. Build source references
    sources = []
    for i, (chunk, metadata, distance) in enumerate(zip(chunks, metadatas, distances)):
        sources.append(RAGSource(
            content=chunk[:300] + "..." if len(chunk) > 300 else chunk,
            document_name=metadata.get("filename", "Unknown"),
            chunk_index=metadata.get("chunk_index", i),
            relevance_score=round(1 - distance, 4),  # Convert distance to similarity
        ))

    return RAGResponse(
        answer=answer,
        sources=sources,
        question=query.question,
    )


@router.get("/status", summary="Check RAG service status")
async def rag_status():
    """Check if RAG services (embedder, vector store, LLM) are available."""
    status_info = {
        "embedder": False,
        "vector_store": False,
        "llm": False,
    }

    try:
        get_embedder()
        status_info["embedder"] = True
    except Exception:
        pass

    try:
        get_vector_store()
        status_info["vector_store"] = True
    except Exception:
        pass

    try:
        llm = get_llm()
        status_info["llm"] = llm.client is not None
    except Exception:
        pass

    return {
        "service": "RAG Pipeline",
        "status": "ready" if all(status_info.values()) else "partial",
        "components": status_info,
    }
