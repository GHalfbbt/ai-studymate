"""
API dependency injection utilities.

Provides reusable dependencies for FastAPI routes including
database sessions, current user authentication, and service instances.
"""

from typing import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# OAuth2 scheme for JWT token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that extracts and validates the current user from JWT token.

    Used in protected routes to ensure the request is authenticated.
    Raises 401 if the token is invalid or the user doesn't exist.

    Args:
        token: JWT token from Authorization header (auto-extracted)
        db: Database session (auto-injected)

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode the JWT token to get user ID
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    # Look up user in the database
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None:
        raise credentials_exception

    return user
