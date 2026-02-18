"""Initial database schema - all tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-02-18

Creates all 12 tables for the AI StudyMate application:
- users, workspaces, courses, subjects
- documents, document_chunks
- exams, exam_questions, exam_attempts, exam_answers
- flashcards, voice_sessions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers used by Alembic
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all application tables."""

    # ─────────────────────────────────────────────
    # Enable PostgreSQL extensions
    # ─────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # ─────────────────────────────────────────────
    # users table
    # Root entity - all data belongs to a user
    # ─────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ─────────────────────────────────────────────
    # workspaces table
    # Top-level organization (e.g., "University Studies")
    # ─────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_workspaces_user_id", "workspaces", ["user_id"])

    # ─────────────────────────────────────────────
    # courses table
    # Groups related subjects (e.g., "CS 2024")
    # ─────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_courses_workspace_id", "courses", ["workspace_id"])

    # ─────────────────────────────────────────────
    # subjects table
    # Primary study unit (e.g., "Data Structures")
    # ─────────────────────────────────────────────
    op.create_table(
        "subjects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "course_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("color", sa.String(7), server_default="#3B82F6"),  # Hex color
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_subjects_course_id", "subjects", ["course_id"])

    # ─────────────────────────────────────────────
    # documents table
    # Uploaded study materials
    # ─────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "subject_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("processing_status", sa.String(20), server_default="pending"),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_documents_subject_id", "documents", ["subject_id"])

    # ─────────────────────────────────────────────
    # document_chunks table
    # Text segments from processed documents
    # ─────────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("vector_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_vector_id", "document_chunks", ["vector_id"], unique=True)

    # ─────────────────────────────────────────────
    # exams table
    # Generated exam containers
    # ─────────────────────────────────────────────
    op.create_table(
        "exams",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "subject_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("question_count", sa.Integer, nullable=False),
        sa.Column("mc_count", sa.Integer, server_default="0"),
        sa.Column("short_answer_count", sa.Integer, server_default="0"),
        sa.Column("generated_from_document_ids", postgresql.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_exams_subject_id", "exams", ["subject_id"])

    # ─────────────────────────────────────────────
    # exam_questions table
    # Individual questions within an exam
    # ─────────────────────────────────────────────
    op.create_table(
        "exam_questions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "exam_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_order", sa.Integer, nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False),  # mc, short_answer
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("options", postgresql.JSON, nullable=True),
        sa.Column("correct_answer", sa.String(10), nullable=True),
        sa.Column("model_answer", sa.Text, nullable=True),
        sa.Column("keywords", postgresql.JSON, nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("difficulty", sa.String(10), server_default="medium"),
        sa.Column("topic", sa.String(255), nullable=True),
    )
    op.create_index("ix_exam_questions_exam_id", "exam_questions", ["exam_id"])

    # ─────────────────────────────────────────────
    # exam_attempts table
    # User's exam taking sessions
    # ─────────────────────────────────────────────
    op.create_table(
        "exam_attempts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "exam_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="in_progress"),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("total_questions", sa.Integer, nullable=True),
        sa.Column("correct_answers", sa.Integer, nullable=True),
    )
    op.create_index("ix_exam_attempts_exam_id", "exam_attempts", ["exam_id"])
    op.create_index("ix_exam_attempts_user_id", "exam_attempts", ["user_id"])

    # ─────────────────────────────────────────────
    # exam_answers table
    # User's individual question responses
    # ─────────────────────────────────────────────
    op.create_table(
        "exam_answers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exam_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exam_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_answer", sa.Text, nullable=False),
        sa.Column("is_correct", sa.Boolean, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("llm_feedback", sa.Text, nullable=True),
        sa.Column(
            "answered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_exam_answers_attempt_id", "exam_answers", ["attempt_id"])
    op.create_index("ix_exam_answers_question_id", "exam_answers", ["question_id"])

    # ─────────────────────────────────────────────
    # flashcards table
    # Spaced repetition study cards
    # ─────────────────────────────────────────────
    op.create_table(
        "flashcards",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "subject_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("front", sa.Text, nullable=False),
        sa.Column("back", sa.Text, nullable=False),
        sa.Column("difficulty", sa.String(10), server_default="medium"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("times_reviewed", sa.Integer, server_default="0"),
        sa.Column("last_reviewed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ease_factor", sa.Float, server_default="2.5"),
    )
    op.create_index("ix_flashcards_subject_id", "flashcards", ["subject_id"])

    # ─────────────────────────────────────────────
    # voice_sessions table
    # Voice practice session recordings and evaluations
    # ─────────────────────────────────────────────
    op.create_table(
        "voice_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_type", sa.String(50), nullable=False),
        sa.Column("audio_path", sa.String(1000), nullable=True),
        sa.Column("transcription", sa.Text, nullable=True),
        sa.Column("grammar_score", sa.Float, nullable=True),
        sa.Column("fluency_score", sa.Float, nullable=True),
        sa.Column("vocabulary_score", sa.Float, nullable=True),
        sa.Column("pronunciation_score", sa.Float, nullable=True),
        sa.Column("feedback", postgresql.JSON, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_voice_sessions_user_id", "voice_sessions", ["user_id"])


def downgrade() -> None:
    """Drop all application tables in reverse dependency order."""
    op.drop_table("voice_sessions")
    op.drop_table("flashcards")
    op.drop_table("exam_answers")
    op.drop_table("exam_attempts")
    op.drop_table("exam_questions")
    op.drop_table("exams")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("subjects")
    op.drop_table("courses")
    op.drop_table("workspaces")
    op.drop_table("users")
