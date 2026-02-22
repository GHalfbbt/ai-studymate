"""Add llm_provider to users table

Revision ID: 003
Revises: 002
Create Date: 2026-02-22
"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_user_llm_provider"
down_revision = "002_add_topics_position_quota"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("llm_provider", sa.String(20), nullable=False, server_default="auto"),
    )


def downgrade() -> None:
    op.drop_column("users", "llm_provider")
