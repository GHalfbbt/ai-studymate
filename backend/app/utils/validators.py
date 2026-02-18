"""
File validation helper utilities.

Provides validation functions for uploaded files
including type checking, size validation, and sanitization.
"""

import os
from typing import Set

from app.core.config import settings


# Allowed MIME types mapped to file extensions
ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "image/png": "image",
    "image/jpeg": "image",
}

# Allowed file extensions
ALLOWED_EXTENSIONS: Set[str] = {"pdf", "docx", "txt", "png", "jpg", "jpeg"}


def validate_file_extension(filename: str) -> str:
    """
    Validate and return the file extension.

    Args:
        filename: Original filename

    Returns:
        str: Validated file extension (lowercase)

    Raises:
        ValueError: If the file extension is not allowed
    """
    if "." not in filename:
        raise ValueError("File must have an extension")

    extension = filename.rsplit(".", 1)[-1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File extension '.{extension}' is not allowed. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    return extension


def validate_file_size(file_size: int) -> None:
    """
    Validate that a file is within the allowed size limit.

    Args:
        file_size: File size in bytes

    Raises:
        ValueError: If the file exceeds the maximum allowed size
    """
    max_size = settings.MAX_UPLOAD_SIZE

    if file_size <= 0:
        raise ValueError("File is empty")

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"File size ({file_mb:.1f} MB) exceeds maximum "
            f"allowed size ({max_mb:.1f} MB)"
        )


def get_file_type(filename: str) -> str:
    """
    Determine the file type category from filename.

    Maps file extensions to type categories used by the system.

    Args:
        filename: Original filename

    Returns:
        str: File type category (pdf, docx, txt, image)
    """
    extension = filename.rsplit(".", 1)[-1].lower()

    if extension in {"png", "jpg", "jpeg"}:
        return "image"

    return extension


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe storage.

    Removes potentially dangerous characters while preserving
    the file extension.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename safe for filesystem storage
    """
    # Keep only alphanumeric, dash, underscore, and dot
    import re

    # Get the extension
    name, ext = os.path.splitext(filename)

    # Clean the name part
    name = re.sub(r"[^\w\-.]", "_", name)
    name = re.sub(r"_{2,}", "_", name)  # Remove consecutive underscores
    name = name.strip("_")

    # Limit length
    if len(name) > 100:
        name = name[:100]

    return f"{name}{ext}"
