"""Add position ordering, quota tracking and topics table

Revision ID: 002_add_topics_position_quota
Revises: 001_initial_schema
Create Date: 2026-02-19

Changes:
- workspaces: add `position` (ordering), `icon` (emoji)
- courses: add `position`, `color`
- subjects: add `position`
- users: add `storage_used_bytes`, `storage_quota_bytes`
- documents: make `subject_id` nullable (docs can live at any level),
             add `course_id`, `workspace_id` (direct attachment)
- NEW TABLE: topics  (4th level: Subject -> Topic -> Documents)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_add_topics_position_quota"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None

# Default quota: 200 MB per user
DEFAULT_QUOTA_BYTES = 200 * 1024 * 1024


def upgrade() -> None:

    # ── users: storage quota tracking ───────────────
    op.add_column("users", sa.Column(
        "storage_used_bytes", sa.BigInteger, server_default="0", nullable=False
    ))
    op.add_column("users", sa.Column(
        "storage_quota_bytes", sa.BigInteger,
        server_default=str(DEFAULT_QUOTA_BYTES), nullable=False
    ))

    # ── workspaces: ordering + icon ──────────────────
    op.add_column("workspaces", sa.Column(
        "position", sa.Integer, server_default="0", nullable=False
    ))
    op.add_column("workspaces", sa.Column(
        "icon", sa.String(10), server_default="🗂️", nullable=True
    ))

    # ── courses: ordering + color ────────────────────
    op.add_column("courses", sa.Column(
        "position", sa.Integer, server_default="0", nullable=False
    ))
    op.add_column("courses", sa.Column(
        "color", sa.String(7), server_default="#3B82F6", nullable=True
    ))

    # ── subjects: ordering ───────────────────────────
    op.add_column("subjects", sa.Column(
        "position", sa.Integer, server_default="0", nullable=False
    ))

    # ── topics table (4th level) ─────────────────────
    op.create_table(
        "topics",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("color", sa.String(7), server_default="#6366F1", nullable=True),
        sa.Column("position", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_topics_subject_id", "topics", ["subject_id"])

    # ── documents: allow upload at any level ─────────
    # Add optional FK to workspace, course, topic
    # subject_id stays but becomes nullable so docs can live at higher levels
    op.add_column("documents", sa.Column(
        "workspace_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    ))
    op.add_column("documents", sa.Column(
        "course_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
    ))
    op.add_column("documents", sa.Column(
        "topic_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=True,
    ))
    # Also track user_id directly for quota + search performance
    op.add_column("documents", sa.Column(
        "user_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # nullable for existing rows
    ))
    # Make subject_id nullable (docs can now live at other levels)
    op.alter_column("documents", "subject_id", nullable=True)

    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_index("ix_documents_course_id", "documents", ["course_id"])
    op.create_index("ix_documents_topic_id", "documents", ["topic_id"])


def downgrade() -> None:
    # documents
    op.drop_index("ix_documents_topic_id", table_name="documents")
    op.drop_index("ix_documents_course_id", table_name="documents")
    op.drop_index("ix_documents_workspace_id", table_name="documents")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.alter_column("documents", "subject_id", nullable=False)
    op.drop_column("documents", "topic_id")
    op.drop_column("documents", "course_id")
    op.drop_column("documents", "workspace_id")
    op.drop_column("documents", "user_id")

    # topics
    op.drop_table("topics")

    # subjects / courses / workspaces
    op.drop_column("subjects", "position")
    op.drop_column("courses", "color")
    op.drop_column("courses", "position")
    op.drop_column("workspaces", "icon")
    op.drop_column("workspaces", "position")

    # users
    op.drop_column("users", "storage_quota_bytes")
    op.drop_column("users", "storage_used_bytes")
