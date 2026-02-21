"""
File storage service for managing uploaded documents.

Supports two backends:
1. **Supabase Storage** (production) — when SUPABASE_URL, SUPABASE_SERVICE_KEY,
   and SUPABASE_BUCKET are configured. Files are uploaded to a private bucket
   and served via signed URLs.
2. **Local disk** (development fallback) — files stored in UPLOAD_DIR.

The ingestion pipeline always needs a local file for text extraction,
so Supabase uploads also keep a temporary local copy that is cleaned up
after processing completes.
"""

import os
import re
import shutil
import unicodedata
from typing import Optional
from uuid import UUID, uuid4

import httpx
from fastapi import UploadFile

from app.core.config import settings


def _sanitize_filename_for_cloud(filename: str) -> str:
    """
    Sanitize a filename for Supabase Storage (which rejects non-ASCII keys).

    Removes accents/diacritics, replaces spaces with underscores,
    and strips any characters that aren't alphanumeric, hyphens,
    underscores, or dots.

    Examples:
        "Presentación Tema 2. Principales amenazas.pdf"
        → "Presentacion_Tema_2._Principales_amenazas.pdf"
    """
    # Decompose unicode characters and remove combining marks (accents)
    nfkd = unicodedata.normalize("NFKD", filename)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    # Replace spaces with underscores
    ascii_only = ascii_only.replace(" ", "_")
    # Remove any remaining unsafe characters (keep alphanumeric, -, _, .)
    safe = re.sub(r"[^a-zA-Z0-9_.\-]", "", ascii_only)
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    return safe or "unnamed_file"


class StorageService:
    """
    Hybrid file storage service.

    When Supabase Storage is configured, files are persisted in the cloud
    bucket and a local copy is kept for the ingestion pipeline.
    When not configured, falls back to local-only storage.

    Supabase object path layout:
        {user_id}/{document_uuid}_{filename}

    Local path layout (fallback):
        uploads/{subject_id}/{uuid8}_{filename}
    """

    # Allowed file extensions for upload
    ALLOWED_EXTENSIONS = {"pdf", "docx", "odt", "txt", "png", "jpg", "jpeg"}

    # Maximum file size (from settings, default 10MB)
    MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE

    def __init__(self, upload_dir: Optional[str] = None):
        """
        Initialize storage service.

        Args:
            upload_dir: Base directory for local file storage.
                       Defaults to UPLOAD_DIR from settings.
        """
        self.upload_dir = upload_dir or settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

        # Supabase configuration
        self._supabase_enabled = settings.supabase_storage_enabled
        if self._supabase_enabled:
            self._supabase_url = settings.SUPABASE_URL.rstrip("/")
            self._supabase_key = settings.SUPABASE_SERVICE_KEY
            self._bucket = settings.SUPABASE_BUCKET
            self._storage_api = f"{self._supabase_url}/storage/v1"
            self._headers = {
                "apikey": self._supabase_key,
                "Authorization": f"Bearer {self._supabase_key}",
            }
            print(f"☁️  Supabase Storage enabled — bucket: {self._bucket}")
        else:
            print("📁 Using local file storage (Supabase not configured)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save_file(
        self,
        file: UploadFile,
        subject_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> dict:
        """
        Save an uploaded file.

        If Supabase is configured, uploads to the cloud bucket AND saves
        a local copy (needed by the ingestion pipeline for text extraction).
        Otherwise, saves to local disk only.

        Args:
            file: FastAPI upload file object
            subject_id: Subject ID for local directory organization
            user_id: Owner user ID for Supabase path organization

        Returns:
            dict with keys:
                - file_path: Local path to the file (for ingestion)
                - filename: Original filename
                - file_type: File extension category
                - file_size: File size in bytes
                - storage_key: Supabase object path (if cloud) or local path

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

        # Read and validate file content
        content = await file.read()
        file_size = len(content)

        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum "
                f"allowed size ({self.MAX_FILE_SIZE} bytes)"
            )

        if file_size == 0:
            raise ValueError("File is empty")

        # Generate unique filename
        unique_id = str(uuid4())[:8]
        safe_filename = f"{unique_id}_{filename}"

        # Always save a local copy (needed for text extraction pipeline)
        subject_dir = os.path.join(self.upload_dir, str(subject_id))
        os.makedirs(subject_dir, exist_ok=True)
        local_path = os.path.join(subject_dir, safe_filename)

        with open(local_path, "wb") as f:
            f.write(content)

        # Upload to Supabase Storage if configured
        storage_key = local_path  # default: local path
        if self._supabase_enabled and user_id:
            # Sanitize filename for Supabase (no accents, no spaces, ASCII only)
            cloud_safe_name = f"{unique_id}_{_sanitize_filename_for_cloud(filename)}"
            object_path = f"{user_id}/{cloud_safe_name}"
            try:
                await self._upload_to_supabase(object_path, content, file_extension)
                storage_key = f"supabase://{self._bucket}/{object_path}"
                print(f"  ☁️  Uploaded to Supabase: {object_path}")
            except Exception as e:
                print(f"  ⚠️  Supabase upload failed, keeping local only: {e}")
                # Fall back to local storage — file_path stays as local_path

        return {
            "file_path": local_path,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "storage_key": storage_key,
        }

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage (both local and Supabase if applicable).

        Args:
            file_path: The file_path stored in the Document record.
                      Can be a local path or a supabase:// URI.

        Returns:
            bool: True if deletion succeeded
        """
        deleted_local = False
        deleted_cloud = False

        # If it's a Supabase URI, extract the object path and delete from cloud
        if file_path.startswith("supabase://"):
            object_path = file_path.split("/", 3)[-1]  # bucket/user_id/filename → user_id/filename
            # The URI is supabase://bucket/user_id/filename
            parts = file_path.replace("supabase://", "").split("/", 1)
            if len(parts) == 2:
                object_path = parts[1]
                try:
                    self._delete_from_supabase_sync(object_path)
                    deleted_cloud = True
                    print(f"  ☁️  Deleted from Supabase: {object_path}")
                except Exception as e:
                    print(f"  ⚠️  Supabase delete failed: {e}")
        else:
            # Local file path
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_local = True
            except OSError:
                pass

        return deleted_local or deleted_cloud

    async def get_download_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a signed download URL for a file.

        For Supabase files, generates a time-limited signed URL.
        For local files, returns None (caller should use FileResponse).

        Args:
            file_path: The file_path stored in the Document record
            expires_in: URL expiration time in seconds (default 1 hour)

        Returns:
            Signed URL string, or None if local file
        """
        if not file_path.startswith("supabase://"):
            return None

        parts = file_path.replace("supabase://", "").split("/", 1)
        if len(parts) != 2:
            return None

        bucket_name, object_path = parts
        return await self._create_signed_url(object_path, expires_in)

    async def download_file(self, file_path: str) -> Optional[bytes]:
        """
        Download file content from Supabase Storage.

        For local files, reads from disk. For Supabase files, downloads
        from the cloud.

        Args:
            file_path: The file_path stored in the Document record

        Returns:
            File content as bytes, or None on failure
        """
        if file_path.startswith("supabase://"):
            parts = file_path.replace("supabase://", "").split("/", 1)
            if len(parts) != 2:
                return None
            _, object_path = parts
            return await self._download_from_supabase(object_path)
        else:
            # Local file
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    return f.read()
            return None

    def delete_subject_directory(self, subject_id: UUID) -> bool:
        """
        Delete all local files for a subject.

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
        Get the full local storage path for a file.

        Args:
            subject_id: Subject the file belongs to
            filename: The stored filename

        Returns:
            str: Full file path
        """
        return os.path.join(self.upload_dir, str(subject_id), filename)

    @property
    def is_cloud_enabled(self) -> bool:
        """Whether Supabase Storage is active."""
        return self._supabase_enabled

    # ------------------------------------------------------------------
    # Supabase Storage internals (using httpx REST API)
    # ------------------------------------------------------------------

    async def _upload_to_supabase(
        self, object_path: str, content: bytes, file_extension: str
    ) -> None:
        """Upload file bytes to Supabase Storage bucket."""
        content_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "odt": "application/vnd.oasis.opendocument.text",
            "txt": "text/plain",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        content_type = content_types.get(file_extension, "application/octet-stream")

        url = f"{self._storage_api}/object/{self._bucket}/{object_path}"
        headers = {
            **self._headers,
            "Content-Type": content_type,
            "x-upsert": "true",  # Overwrite if exists
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, content=content)
            if response.status_code not in (200, 201):
                raise RuntimeError(
                    f"Supabase upload failed ({response.status_code}): {response.text}"
                )

    async def _create_signed_url(self, object_path: str, expires_in: int) -> Optional[str]:
        """Create a signed URL for private bucket access."""
        url = f"{self._storage_api}/object/sign/{self._bucket}/{object_path}"
        headers = {**self._headers, "Content-Type": "application/json"}
        body = {"expiresIn": expires_in}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=body)
            if response.status_code == 200:
                data = response.json()
                signed_url = data.get("signedURL", "")
                if signed_url:
                    # signedURL is relative — prepend the Supabase URL
                    if signed_url.startswith("/"):
                        return f"{self._supabase_url}/storage/v1{signed_url}"
                    return signed_url
            return None

    async def _download_from_supabase(self, object_path: str) -> Optional[bytes]:
        """Download file content from Supabase Storage."""
        url = f"{self._storage_api}/object/{self._bucket}/{object_path}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=self._headers)
            if response.status_code == 200:
                return response.content
            print(f"  ⚠️  Supabase download failed ({response.status_code}): {response.text}")
            return None

    def _delete_from_supabase_sync(self, object_path: str) -> None:
        """Delete a file from Supabase Storage (synchronous for use in delete_file)."""
        url = f"{self._storage_api}/object/{self._bucket}"
        headers = {**self._headers, "Content-Type": "application/json"}
        body = {"prefixes": [object_path]}

        response = httpx.request(
            "DELETE", url, headers=headers, json=body, timeout=15.0
        )
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(
                f"Supabase delete failed ({response.status_code}): {response.text}"
            )
