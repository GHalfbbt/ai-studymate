#!/bin/bash
# ===========================================
# Backend Entrypoint Script
# ===========================================
# Runs database migrations before starting the application.
# This ensures the database schema is always up-to-date.

set -e  # Exit immediately if a command fails

echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete. Starting application..."
exec "$@"
