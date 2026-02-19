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
    print("🚀 Iniciando AI StudyMate Backend...")
    print(f"📦 Entorno: {settings.ENVIRONMENT}")
    print(f"🔗 Base de datos: {settings.DATABASE_URL[:30]}...")
    print(f"🤖 Proveedor LLM: {settings.LLM_PROVIDER}")
    print(f"🌐 CORS orígenes: {settings.cors_origins_list}")

    # Seed demo user for Try Demo functionality (avoids LOPD issues)
    _seed_demo_user()

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


# ─── Demo User Seeding ──────────────────────────────────

DEMO_EMAIL = "demo@studymate.ai"
DEMO_PASSWORD = "demo1234"


def _seed_demo_user():
    """
    Create a demo user with pre-configured workspace/course/subject
    if it doesn't already exist. Used for the 'Try Demo' feature.
    """
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.models.course import Course
    from app.models.subject import Subject

    db = SessionLocal()
    try:
        # Check if demo user already exists with full hierarchy
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing:
            # Check if the full hierarchy exists (user + workspace + courses)
            ws = db.query(Workspace).filter(Workspace.user_id == existing.id).first()
            if ws:
                course_count = db.query(Course).filter(Course.workspace_id == ws.id).count()
                if course_count > 0:
                    print(f"👤 Usuario demo ya existe: {DEMO_EMAIL}")
                    return
                # Workspace exists but no courses — delete and recreate
                db.delete(ws)
                db.flush()
            demo_user = existing
            print("🔧 Completando setup del usuario demo...")
        else:
            # Create demo user
            demo_user = User(
                email=DEMO_EMAIL,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name="Demo User",
            )
            db.add(demo_user)
            db.flush()

        # Create demo workspace
        workspace = Workspace(
            name="📚 My Study Space",
            description="Demo workspace with sample courses",
            user_id=demo_user.id,
        )
        db.add(workspace)
        db.flush()

        # Create demo courses
        course_ai = Course(
            name="Artificial Intelligence",
            workspace_id=workspace.id,
        )
        course_web = Course(
            name="Web Development",
            workspace_id=workspace.id,
        )
        db.add_all([course_ai, course_web])
        db.flush()

        # Create demo subjects
        subjects = [
            Subject(name="Machine Learning Basics", course_id=course_ai.id, color="#6366F1"),
            Subject(name="Neural Networks", course_id=course_ai.id, color="#8B5CF6"),
            Subject(name="React & TypeScript", course_id=course_web.id, color="#06B6D4"),
            Subject(name="FastAPI & Python", course_id=course_web.id, color="#10B981"),
        ]
        db.add_all(subjects)

        db.commit()
        print(f"✅ Usuario demo creado: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"   📁 Workspace: {workspace.name}")
        print(f"   📖 Cursos: {course_ai.name}, {course_web.name}")
        print(f"   📝 Asignaturas: {len(subjects)} creadas")

    except Exception as e:
        db.rollback()
        print(f"⚠️ Error creando usuario demo: {e}")
    finally:
        db.close()
