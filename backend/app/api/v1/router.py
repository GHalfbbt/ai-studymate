"""
Main API v1 router.

Combines all endpoint routers under the /api/v1 prefix.
Each router handles a specific domain (auth, documents, RAG, etc.).
"""

from fastapi import APIRouter

# Import individual routers
from app.api.v1.auth import router as auth_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.documents import router as documents_router
from app.api.v1.rag import router as rag_router
from app.api.v1.exams import router as exams_router
from app.api.v1.flashcards import router as flashcards_router

# Main API v1 router
router = APIRouter(prefix="/api/v1")

# Health check endpoint (always available, no auth required)
@router.get("/health", tags=["health"])
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        dict: Status message confirming the API is running
    """
    return {
        "status": "healthy",
        "service": "AI StudyMate API",
        "version": "1.0.0",
    }


# Include active routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
router.include_router(documents_router, prefix="/documents", tags=["documents"])
router.include_router(rag_router, prefix="/rag", tags=["rag"])
router.include_router(exams_router, prefix="/exams", tags=["exams"])
router.include_router(flashcards_router, prefix="/flashcards", tags=["flashcards"])

# TODO: Include remaining routers (Day 4-5)
# from app.api.v1.voice import router as voice_router
# router.include_router(voice_router, prefix="/voice", tags=["voice"])
