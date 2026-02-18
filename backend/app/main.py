"""
FastAPI application entry point.

Configures the main FastAPI instance with CORS middleware,
API routers, and startup/shutdown event handlers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import router as api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for resource initialization
    and cleanup (database connections, vector store, etc.).
    """
    # === Startup ===
    # Mensaje en español para el desarrollador
    print("🚀 Iniciando AI StudyMate Backend...")
    print(f"📦 Entorno: {settings.ENVIRONMENT}")
    print(f"🔗 Base de datos: {settings.DATABASE_URL[:30]}...")
    print(f"🤖 Proveedor LLM: {settings.LLM_PROVIDER}")
    print(f"🌐 CORS orígenes: {settings.cors_origins_list}")

    yield

    # === Shutdown ===
    print("🛑 Cerrando AI StudyMate Backend...")


# Create FastAPI application instance
app = FastAPI(
    title="AI StudyMate API",
    description=(
        "AI-powered study assistant API. "
        "Provides document ingestion, RAG queries, exam generation, "
        "flashcard creation, and voice practice features."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS middleware
# Allows the frontend to make requests to the backend API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router with all endpoints
app.include_router(api_v1_router)


# Root endpoint (convenience for checking if API is running)
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint providing basic API information.

    Returns:
        dict: API name, version, and documentation URL
    """
    return {
        "message": "Welcome to AI StudyMate API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
