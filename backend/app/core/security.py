"""
Security utilities for authentication and authorization.

Provides JWT token creation/verification and password hashing
using bcrypt for secure credential storage.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt as _bcrypt

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Uses bcrypt directly (instead of passlib) for compatibility
    with bcrypt >= 4.1 which enforces the 72-byte limit strictly.

    Args:
        password: Plaintext password to hash

    Returns:
        Hashed password string safe for database storage
    """
    # bcrypt requires bytes; truncate to 72 bytes (bcrypt limit)
    pwd_bytes = password.encode("utf-8")[:72]
    salt = _bcrypt.gensalt()
    hashed = _bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.

    Args:
        plain_password: Plaintext password to check
        hashed_password: Bcrypt hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return _bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Token subject (typically user ID as string)
        expires_delta: Custom expiration time (defaults to settings value)

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode and verify a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Subject (user ID) from the token, or None if invalid/expired

    Raises:
        JWTError: If token is malformed (caught internally)
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        subject: str = payload.get("sub")
        if subject is None:
            return None
        return subject
    except JWTError:
        return None
