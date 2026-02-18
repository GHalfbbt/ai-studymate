"""
Alembic environment configuration.

Configures the Alembic migration environment to use the
application's database URL and model metadata. This ensures
that auto-generated migrations reflect the actual SQLAlchemy models.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys

# Add the backend directory to the Python path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import all models to ensure they are registered with Base.metadata
from app.core.database import Base
from app.models import *  # noqa: F401, F403 - Import all models for metadata

# Alembic Config object which provides access to the .ini file values
config = context.config

# Override sqlalchemy.url with our application's DATABASE_URL
# This allows us to use environment variables instead of hardcoding
from app.core.config import settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging (if present)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This generates SQL scripts without connecting to the database.
    Useful for generating migration SQL for review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Connects to the database and applies migrations directly.
    This is the default mode for development workflows.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
