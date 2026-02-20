"""
Pytest fixtures for integration and validation testing.

Provides database sessions, test clients, authenticated helpers,
and mock services for testing the full backend pipeline.

Uses SQLite in-memory for fast, isolated tests that don't require
a running PostgreSQL instance.
"""

import os
import uuid
import shutil
import tempfile
from typing import Generator, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.workspace import Workspace
from app.models.course import Course
from app.models.subject import Subject
from app.models.document import Document, DocumentChunk


# ---------------------------------------------------------------------------
# Database setup — SQLite in-memory for speed and isolation
# ---------------------------------------------------------------------------

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Enable foreign key enforcement in SQLite (off by default)
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test function.
    Creates all tables before the test and drops them after.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test HTTP client with database override.
    Uses the test database instead of the production database.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

TEST_USER_EMAIL = "testuser@studymate.ai"
TEST_USER_PASSWORD = "TestPassword123!"
TEST_USER_NAME = "Test User"


@pytest.fixture(scope="function")
def test_user(db: Session) -> User:
    """Create a test user in the database."""
    user = User(
        email=TEST_USER_EMAIL,
        hashed_password=hash_password(TEST_USER_PASSWORD),
        full_name=TEST_USER_NAME,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(test_user: User) -> str:
    """Generate a valid JWT token for the test user."""
    return create_access_token(subject=str(test_user.id))


@pytest.fixture(scope="function")
def auth_headers(auth_token: str) -> Dict[str, str]:
    """Return Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


# ---------------------------------------------------------------------------
# Workspace hierarchy fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_workspace(db: Session, test_user: User) -> Workspace:
    """Create a test workspace."""
    ws = Workspace(
        name="Test Workspace",
        description="Workspace for testing",
        user_id=test_user.id,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


@pytest.fixture(scope="function")
def test_course(db: Session, test_workspace: Workspace) -> Course:
    """Create a test course inside the test workspace."""
    course = Course(
        name="Test Course",
        workspace_id=test_workspace.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture(scope="function")
def test_subject(db: Session, test_course: Course) -> Subject:
    """Create a test subject inside the test course."""
    subject = Subject(
        name="Test Subject",
        course_id=test_course.id,
        color="#6366F1",
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


# ---------------------------------------------------------------------------
# File / upload fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def upload_dir(tmp_path) -> str:
    """Create a temporary upload directory for tests."""
    upload_path = str(tmp_path / "uploads")
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


@pytest.fixture(scope="function")
def test_pdf_content() -> str:
    """
    Return specific test content for RAG validation.
    This content is intentionally fictional so we can verify
    the RAG pipeline returns it and doesn't hallucinate.
    """
    return (
        "The capital of Mars is Olympus Mons. This statement is intentionally fictional "
        "and is used for testing purposes only. The city of Olympus Mons was founded in "
        "the year 2157 by the first Martian colonists. It has a population of approximately "
        "50,000 inhabitants and is known for its advanced terraforming technology. "
        "The main industries include helium-3 mining, atmospheric processing, and "
        "interplanetary trade. The governor of Olympus Mons is Dr. Elena Vasquez, "
        "who was elected in 2180. The city features the largest dome structure in the "
        "solar system, spanning 12 kilometers in diameter. Education in Olympus Mons "
        "is provided by the Mars Colonial University, which offers degrees in "
        "astrobiology, terraforming engineering, and space law. The currency used "
        "is the Martian Credit (MC), which is pegged to the Earth Dollar at a rate "
        "of 1 MC = 2.5 USD. Transportation within the city relies on magnetic "
        "levitation trains and personal hover vehicles. The average temperature "
        "inside the dome is maintained at 22 degrees Celsius year-round."
    )


@pytest.fixture(scope="function")
def test_txt_file(tmp_path, test_pdf_content) -> str:
    """Create a test .txt file with specific content for RAG testing."""
    file_path = str(tmp_path / "test_document.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(test_pdf_content)
    return file_path


# ---------------------------------------------------------------------------
# Mock service fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def mock_embedder():
    """
    Mock EmbedderService that returns deterministic embeddings.
    Returns 384-dimensional vectors (same as all-MiniLM-L6-v2).
    """
    mock = MagicMock()
    mock.get_dimension.return_value = 384

    def fake_embed_query(text: str):
        """Generate a deterministic embedding based on text hash."""
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        # Create a 384-dim vector from the hash
        base = [int(h[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
        return (base * 24)[:384]  # Repeat to fill 384 dims

    def fake_embed_batch(texts, batch_size=32):
        return [fake_embed_query(t) for t in texts]

    mock.embed_query = fake_embed_query
    mock.embed_batch = fake_embed_batch
    return mock


@pytest.fixture(scope="function")
def mock_llm():
    """
    Mock LLMClient that returns predictable responses.
    Avoids calling real Groq API during tests.
    """
    mock = MagicMock()
    mock.client = True  # Simulate configured client

    def fake_generate(prompt, system_prompt="", model=None, temperature=0.7, max_tokens=2000):
        return "This is a mock LLM response for testing purposes."

    def fake_generate_with_context(question, context_chunks, system_prompt=None):
        # Return an answer that references the context
        if context_chunks:
            return f"Based on the provided context: {context_chunks[0][:200]}"
        return "I don't have enough context to answer this question."

    def fake_generate_json(prompt, system_prompt, temperature=0.3):
        return '{"questions": []}'

    mock.generate = fake_generate
    mock.generate_with_context = fake_generate_with_context
    mock.generate_json = fake_generate_json
    return mock
