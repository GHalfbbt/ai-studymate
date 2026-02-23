"""
RAG (Retrieval-Augmented Generation) API endpoints.

Provides the study chat functionality: receives a question,
retrieves relevant document chunks via vector search, and
generates an AI-powered answer using the LLM.

Supports:
- Scoped queries (subject / workspace / all)
- No-hallucination guard (empty context → canned message, no LLM call)
- Structured source linking (document_id for clickable downloads)
- Quiz mode (generate questions + evaluate answers via same endpoint)
"""

import json
from typing import Optional, Literal, List
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


def get_llm(provider: str = None):
    """Get LLM client. If provider specified, creates per-request instance."""
    if provider and provider != "auto":
        from app.services.llm_client import LLMClient
        return LLMClient(provider=provider)
    global _llm
    if _llm is None:
        from app.services.llm_client import LLMClient
        _llm = LLMClient()
    return _llm


# ─── Helpers ─────────────────────────────────────────────

def _resolve_subject_ids(
    db: Session,
    user: User,
    scope: str,
    subject_id: Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
) -> List[UUID]:
    """
    Resolve scope parameters to a flat list of subject IDs.
    Reuses the same logic as analytics._resolve_subject_ids.
    """
    from app.models.subject import Subject
    from app.models.course import Course
    from app.models.workspace import Workspace

    if scope == "subject" and subject_id:
        return [subject_id]

    if scope == "workspace" and workspace_id:
        rows = (
            db.query(Subject.id)
            .join(Course, Subject.course_id == Course.id)
            .filter(Course.workspace_id == workspace_id)
            .all()
        )
        return [r[0] for r in rows]

    # scope == "all" or fallback
    rows = (
        db.query(Subject.id)
        .join(Course, Subject.course_id == Course.id)
        .join(Workspace, Course.workspace_id == Workspace.id)
        .filter(Workspace.user_id == user.id)
        .all()
    )
    return [r[0] for r in rows]


# ─── Request/Response Schemas ────────────────────────────

class RAGQuery(BaseModel):
    """Request schema for RAG query."""
    question: str = Field(..., min_length=1, max_length=2000, description="Study question")
    subject_id: Optional[UUID] = Field(None, description="Filter by subject")
    workspace_id: Optional[UUID] = Field(None, description="Filter by workspace")
    scope: Literal["subject", "workspace", "all"] = Field(
        "subject", description="Query scope: subject, workspace, or all documents"
    )
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks to retrieve")
    mode: Literal["chat", "quiz", "quiz_evaluate"] = Field(
        "chat", description="Mode: chat (normal RAG), quiz (generate question), quiz_evaluate (evaluate answer)"
    )
    # Quiz evaluate fields
    quiz_question: Optional[str] = Field(None, description="Original quiz question (for quiz_evaluate)")
    user_answer: Optional[str] = Field(None, description="User's answer to evaluate (for quiz_evaluate)")


class RAGSource(BaseModel):
    """A source document chunk used in the answer."""
    document_id: Optional[str] = None
    document_name: str
    chunk_index: int
    relevance_score: float
    content: str
    page: Optional[int] = None


class RAGResponse(BaseModel):
    """Response schema for RAG query."""
    answer: str
    sources: list[RAGSource]
    question: str
    mode: str = "chat"


# ─── No-hallucination guard message ─────────────────────

NO_CONTEXT_MESSAGE = (
    "I do not have enough context in your uploaded documents to answer this. "
    "Please upload relevant study materials or try a different scope."
)

NO_CONTEXT_MESSAGE_QUIZ = (
    "I do not have enough context in your uploaded documents to generate a quiz question. "
    "Please upload relevant study materials first."
)


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

    Modes:
    - chat: Normal RAG (embed question → search → LLM answer)
    - quiz: Generate a quiz question from context
    - quiz_evaluate: Evaluate user's answer to a quiz question

    Scopes:
    - subject: Filter by subject_id
    - workspace: Filter by all subjects in workspace_id
    - all: All user's documents
    """
    embedder = get_embedder()
    vector_store = get_vector_store()
    # Use user's preferred LLM provider
    user_provider = getattr(current_user, "llm_provider", None) or "auto"
    llm = get_llm(provider=user_provider)

    # ── Quiz Evaluate mode (no vector search needed) ─────
    if query.mode == "quiz_evaluate":
        return _handle_quiz_evaluate(query, llm)

    # ── Build metadata filter based on scope ─────────────
    where_filter = {"user_id": str(current_user.id)}

    if query.scope == "subject" and query.subject_id:
        where_filter["subject_id"] = str(query.subject_id)
    elif query.scope == "workspace" and query.workspace_id:
        subject_ids = _resolve_subject_ids(
            db, current_user, "workspace", workspace_id=query.workspace_id
        )
        if subject_ids:
            where_filter["subject_id"] = {"$in": [str(sid) for sid in subject_ids]}
        else:
            # No subjects in workspace → no context
            return RAGResponse(
                answer=NO_CONTEXT_MESSAGE if query.mode == "chat" else NO_CONTEXT_MESSAGE_QUIZ,
                sources=[],
                question=query.question,
                mode=query.mode,
            )
    # scope == "all" → only user_id filter (already set)

    # 1. Embed the question
    query_embedding = embedder.embed_query(query.question)

    # 2. Search vector store for relevant chunks
    results = vector_store.query(
        query_embedding=query_embedding,
        n_results=query.top_k,
        filter_dict=where_filter,
    )

    # ── No-hallucination guard ───────────────────────────
    if not results or not results.get("documents") or not results["documents"][0]:
        guard_msg = NO_CONTEXT_MESSAGE if query.mode == "chat" else NO_CONTEXT_MESSAGE_QUIZ
        return RAGResponse(
            answer=guard_msg,
            sources=[],
            question=query.question,
            mode=query.mode,
        )

    # 3. Extract chunks and metadata
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(chunks)
    distances = results["distances"][0] if results.get("distances") else [0.0] * len(chunks)

    # 4. Build source references (with document_id for clickable links)
    sources = []
    for i, (chunk, metadata, distance) in enumerate(zip(chunks, metadatas, distances)):
        sources.append(RAGSource(
            document_id=metadata.get("document_id"),
            document_name=metadata.get("filename", "Unknown"),
            chunk_index=metadata.get("chunk_index", i),
            relevance_score=round(1 - distance, 4),
            content=chunk[:300] + "..." if len(chunk) > 300 else chunk,
            page=metadata.get("page"),
        ))

    # 5. Route to appropriate handler
    if query.mode == "quiz":
        return _handle_quiz_generate(query, chunks, sources, llm)
    else:
        return _handle_chat(query, chunks, sources, llm)


def _handle_chat(
    query: RAGQuery,
    chunks: list,
    sources: list,
    llm,
) -> RAGResponse:
    """Normal RAG chat: generate answer from context."""
    answer = llm.generate_with_context(
        question=query.question,
        context_chunks=chunks,
    )

    return RAGResponse(
        answer=answer,
        sources=sources,
        question=query.question,
        mode="chat",
    )


def _handle_quiz_generate(
    query: RAGQuery,
    chunks: list,
    sources: list,
    llm,
) -> RAGResponse:
    """Quiz mode: generate a single question from context."""
    context = "\n\n---\n\n".join(chunks)

    quiz_system = (
        "You are a study quiz generator. Based ONLY on the provided context, "
        "generate exactly ONE clear, specific question that tests understanding "
        "of the material. The question should be answerable from the context.\n\n"
        "Output ONLY the question text, nothing else. No numbering, no prefix, "
        "no 'Question:' label. Just the question."
    )

    quiz_prompt = (
        f"## Context from study materials:\n\n{context}\n\n"
        f"## Generate one quiz question based on this context:"
    )

    question_text = llm.generate(
        prompt=quiz_prompt,
        system_prompt=quiz_system,
        temperature=0.5,
        max_tokens=500,
    )

    return RAGResponse(
        answer=question_text.strip(),
        sources=sources,
        question=query.question,
        mode="quiz",
    )


def _handle_quiz_evaluate(
    query: RAGQuery,
    llm,
) -> RAGResponse:
    """Quiz evaluate mode: evaluate user's answer using LLM."""
    if not query.quiz_question or not query.user_answer:
        return RAGResponse(
            answer="Missing quiz_question or user_answer for evaluation.",
            sources=[],
            question=query.question,
            mode="quiz_evaluate",
        )

    eval_system = (
        "You are a fair study quiz evaluator. Evaluate the student's answer "
        "to the given question.\n\n"
        "Respond with ONLY valid JSON in this exact format:\n"
        '{"is_correct": true, "score": 8, "feedback": "Your explanation here"}\n\n'
        "Rules:\n"
        "- score: 0-10 scale (0=completely wrong, 10=perfect)\n"
        "- is_correct: true if score >= 5\n"
        "- feedback: Be constructive and educational, explain what was good and what could improve\n"
        "- Consider partial credit for partially correct answers\n"
        "- Focus on conceptual understanding, not exact wording"
    )

    eval_prompt = (
        f"## Question:\n{query.quiz_question}\n\n"
        f"## Student's Answer:\n{query.user_answer}\n\n"
        f"## Evaluate and respond with JSON:"
    )

    raw = llm.generate_json(
        prompt=eval_prompt,
        system_prompt=eval_system,
        temperature=0.2,
    )

    # Parse evaluation result
    try:
        result = json.loads(raw)
        is_correct = result.get("is_correct", False)
        score = min(10, max(0, float(result.get("score", 0))))
        feedback = result.get("feedback", "No feedback available.")
    except (json.JSONDecodeError, ValueError):
        is_correct = False
        score = 0
        feedback = "Could not evaluate your answer. Please try again."

    # Format as readable answer
    emoji = "✅" if is_correct else "❌"
    answer = (
        f"{emoji} **Score: {score:.0f}/10**\n\n"
        f"{feedback}"
    )

    return RAGResponse(
        answer=answer,
        sources=[],
        question=query.quiz_question,
        mode="quiz_evaluate",
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
        status_info["llm"] = llm.client is not None if hasattr(llm, 'client') else bool(llm.clients)
    except Exception:
        pass

    return {
        "service": "RAG Pipeline",
        "status": "ready" if all(status_info.values()) else "partial",
        "components": status_info,
    }
