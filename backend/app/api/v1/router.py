"""
Main API v1 router.

Combines all endpoint routers under the /api/v1 prefix.
Each router handles a specific domain (auth, documents, RAG, etc.).
"""

from fastapi import APIRouter

# Import individual routers
# These will be activated as features are implemented (Day 1-5)
# from app.api.v1.auth import router as auth_router
# from app.api.v1.workspaces import router as workspaces_router
# from app.api.v1.courses import router as courses_router
# from app.api.v1.subjects import router as subjects_router
from app.api.v1.documents import router as documents_router
# from app.api.v1.rag import router as rag_router
# from app.api.v1.exams import router as exams_router
# from app.api.v1.flashcards import router as flashcards_router
# from app.api.v1.voice import router as voice_router
# from app.api.v1.analytics import router as analytics_router

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


# TODO: Include routers as they are implemented (Day 1-5)
# router.include_router(auth_router, prefix="/auth", tags=["auth"])
# router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
# router.include_router(courses_router, prefix="/courses", tags=["courses"])
# router.include_router(subjects_router, prefix="/subjects", tags=["subjects"])
router.include_router(documents_router, prefix="/documents", tags=["documents"])
# router.include_router(rag_router, prefix="/rag", tags=["rag"])
# router.include_router(exams_router, prefix="/exams", tags=["exams"])
# router.include_router(flashcards_router, prefix="/flashcards", tags=["flashcards"])
# router.include_router(voice_router, prefix="/voice", tags=["voice"])
# router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
