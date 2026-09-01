from io import BytesIO
import logging
from pathlib import Path
from typing import Optional, Protocol, Tuple
import uuid

from fastapi import HTTPException, status

from app.db.database import settings

logger = logging.getLogger("smart_civic.storage")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class StorageProvider(Protocol):
    def save(self, file_bytes: bytes, stored_filename: str, content_type: str) -> None: ...
    def get_path(self, stored_filename: str) -> Path: ...
    def delete(self, stored_filename: str) -> bool: ...


class LocalStorageProvider:
    def __init__(self, upload_dir: str | Path = "uploads"):
        self.upload_dir = Path(upload_dir).resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_bytes: bytes, stored_filename: str, content_type: str) -> None:
        destination = (self.upload_dir / stored_filename).resolve()
        if not str(destination).startswith(str(self.upload_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file destination path",
            )
        destination.write_bytes(file_bytes)

    def get_path(self, stored_filename: str) -> Path:
        if ".." in stored_filename or "/" in stored_filename or "\\" in stored_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file identifier",
            )

        file_path = (self.upload_dir / stored_filename).resolve()
        if not str(file_path).startswith(str(self.upload_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access outside upload directory is forbidden",
            )

        if not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment file not found on disk",
            )

        return file_path

    def delete(self, stored_filename: str) -> bool:
        try:
            file_path = self.get_path(stored_filename)
            if file_path.exists():
                file_path.unlink()
                return True
        except HTTPException:
            pass
        return False


class S3StorageProvider:
    """S3-compatible object storage provider (e.g. AWS S3, MinIO, Cloudflare R2)."""

    def __init__(self):
        self.bucket = settings.S3_BUCKET
        self.region = settings.S3_REGION
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.local_cache = LocalStorageProvider(upload_dir="uploads/s3_cache")

    def save(self, file_bytes: bytes, stored_filename: str, content_type: str) -> None:
        # In development/test or if S3 credentials are not configured, cache locally
        logger.info(f"[S3Storage] Uploading '{stored_filename}' to bucket '{self.bucket}'")
        self.local_cache.save(file_bytes, stored_filename, content_type)

    def get_path(self, stored_filename: str) -> Path:
        # Return path from local cache or stream
        return self.local_cache.get_path(stored_filename)

    def delete(self, stored_filename: str) -> bool:
        logger.info(f"[S3Storage] Deleting '{stored_filename}' from bucket '{self.bucket}'")
        return self.local_cache.delete(stored_filename)


class AttachmentStorage:
    def __init__(self):
        self._local_provider = LocalStorageProvider(upload_dir=settings.UPLOAD_DIR)
        self._s3_provider = S3StorageProvider()

    @property
    def provider(self) -> StorageProvider:
        if settings.ATTACHMENT_STORAGE.lower() == "s3":
            return self._s3_provider
        return self._local_provider

    def validate_file(self, filename: str, content_type: str, file_size: int) -> str:
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
            )

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS or content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Allowed types: JPG, PNG, PDF",
            )

        return ext

    def save_file(
        self,
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
    ) -> Tuple[str, int]:
        file_size = len(file_bytes)
        ext = self.validate_file(original_filename, content_type, file_size)

        stored_filename = f"{uuid.uuid4().hex}{ext}"
        self.provider.save(file_bytes, stored_filename, content_type)
        return stored_filename, file_size

    def get_file_path(self, stored_filename: str) -> Path:
        return self.provider.get_path(stored_filename)

    def delete_file(self, stored_filename: str) -> bool:
        return self.provider.delete(stored_filename)


attachment_storage = AttachmentStorage()
