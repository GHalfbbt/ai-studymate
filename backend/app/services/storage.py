"""
File storage service for managing uploaded documents.

Handles file saving, path generation, and cleanup.
Files are organized by subject_id for easy management.
"""

import os
import shutil
from typing import Optional
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    """
    Local file storage service for uploaded documents.

    Files are stored in a hierarchical directory structure:
    uploads/{subject_id}/{document_id}_{filename}

    This allows easy cleanup when subjects or documents are deleted.

    Usage:
        storage = StorageService()
        path = await storage.save_file(file, subject_id)
        storage.delete_file(path)
    """

    # Allowed file extensions for upload
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "png", "jpg", "jpeg"}

    # Maximum file size (from settings, default 10MB)
    MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE

    def __init__(self, upload_dir: Optional[str] = None):
        """
        Initialize storage service.

        Creates the upload directory if it doesn't exist.

        Args:
            upload_dir: Base directory for file storage.
                       Defaults to UPLOAD_DIR from settings.
        """
        self.upload_dir = upload_dir or settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_file(
        self,
        file: UploadFile,
        subject_id: UUID,
    ) -> dict:
        """
        Save an uploaded file to the storage directory.

        Args:
            file: FastAPI upload file object
            subject_id: Subject ID for directory organization

        Returns:
            dict with keys:
                - file_path: Full path to saved file
                - filename: Original filename
                - file_type: File extension
                - file_size: File size in bytes

        Raises:
            ValueError: If file type is not allowed or file is too large
        """
        # Validate file extension
        filename = file.filename or "unnamed_file"
        file_extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '.{file_extension}' is not allowed. "
                f"Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )

        # Determine file type category
        if file_extension in {"png", "jpg", "jpeg"}:
            file_type = "image"
        else:
            file_type = file_extension

        # Create subject-specific directory
        subject_dir = os.path.join(self.upload_dir, str(subject_id))
        os.makedirs(subject_dir, exist_ok=True)

        # Generate unique filename to prevent collisions
        unique_id = str(uuid4())[:8]
        safe_filename = f"{unique_id}_{filename}"
        file_path = os.path.join(subject_dir, safe_filename)

        # Read and validate file size
        content = await file.read()
        file_size = len(content)

        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum "
                f"allowed size ({self.MAX_FILE_SIZE} bytes)"
            )

        if file_size == 0:
            raise ValueError("File is empty")

        # Write file to disk
        with open(file_path, "wb") as f:
            f.write(content)

        return {
            "file_path": file_path,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
        }

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Full path to the file to delete

        Returns:
            bool: True if file was deleted, False if not found
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except OSError:
            return False

    def delete_subject_directory(self, subject_id: UUID) -> bool:
        """
        Delete all files for a subject.

        Args:
            subject_id: Subject ID whose files should be removed

        Returns:
            bool: True if directory was deleted, False if not found
        """
        subject_dir = os.path.join(self.upload_dir, str(subject_id))
        try:
            if os.path.exists(subject_dir):
                shutil.rmtree(subject_dir)
                return True
            return False
        except OSError:
            return False

    def get_file_path(self, subject_id: UUID, filename: str) -> str:
        """
        Get the full storage path for a file.

        Args:
            subject_id: Subject the file belongs to
            filename: The stored filename

        Returns:
            str: Full file path
        """
        return os.path.join(self.upload_dir, str(subject_id), filename)
