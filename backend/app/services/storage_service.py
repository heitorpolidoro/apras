import abc
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Tuple

from app.core.config import settings


class BaseStorageProvider(abc.ABC):
    """Abstract interface for media asset storage providers."""

    @abc.abstractmethod
    def save_file(self, file_bytes: bytes, filename: str, content_type: str) -> Tuple[str, str]:
        """
        Save file bytes to storage backend.

        Returns:
            Tuple[str, str]: (internal_file_path, public_or_relative_url)
        """
        pass

    @abc.abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a stored file by its internal file path.

        Returns:
            bool: True if deleted successfully or missing, False otherwise.
        """
        pass


class LocalStorageProvider(BaseStorageProvider):
    """Local disk storage provider saving to static/uploads/{year}/{month}/."""

    def __init__(self, base_dir: str | Path = "static/uploads") -> None:
        self.base_dir = Path(base_dir)

    def save_file(self, file_bytes: bytes, filename: str, content_type: str) -> Tuple[str, str]:
        now = datetime.utcnow()
        year_month_subfolder = f"{now.year}/{now.month:02d}"
        target_dir = self.base_dir / year_month_subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(filename).suffix.lower()
        if not ext:
            ext = ".jpg" if content_type == "image/jpeg" else ".png" if content_type == "image/png" else ".webp"

        unique_name = f"{uuid.uuid4()}{ext}"
        relative_path = os.path.join(year_month_subfolder, unique_name)
        full_path = target_dir / unique_name

        with open(full_path, "wb") as f:
            f.write(file_bytes)

        url = f"/static/uploads/{relative_path}"
        return str(full_path), url

    def delete_file(self, file_path: str) -> bool:
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
            return True
        except Exception:
            return False


class VercelBlobStorageProvider(BaseStorageProvider):
    """Stub implementation for Vercel Blob storage provider."""

    def save_file(self, file_bytes: bytes, filename: str, content_type: str) -> Tuple[str, str]:
        raise NotImplementedError("Vercel Blob storage provider is not configured.")

    def delete_file(self, file_path: str) -> bool:
        raise NotImplementedError("Vercel Blob storage provider is not configured.")


class S3StorageProvider(BaseStorageProvider):
    """Stub implementation for AWS S3 storage provider."""

    def save_file(self, file_bytes: bytes, filename: str, content_type: str) -> Tuple[str, str]:
        raise NotImplementedError("S3 storage provider is not configured.")

    def delete_file(self, file_path: str) -> bool:
        raise NotImplementedError("S3 storage provider is not configured.")


class CloudinaryStorageProvider(BaseStorageProvider):
    """Stub implementation for Cloudinary storage provider."""

    def save_file(self, file_bytes: bytes, filename: str, content_type: str) -> Tuple[str, str]:
        raise NotImplementedError("Cloudinary storage provider is not configured.")

    def delete_file(self, file_path: str) -> bool:
        raise NotImplementedError("Cloudinary storage provider is not configured.")
