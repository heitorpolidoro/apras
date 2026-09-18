import abc
import os
import uuid
from pathlib import Path

from app.core import clock
from app.core.uploads import canonical_extension


class BaseStorageProvider(abc.ABC):
    """Abstract interface for media asset storage providers."""

    @abc.abstractmethod
    def save_file(
        self, file_bytes: bytes, filename: str, content_type: str
    ) -> tuple[str, str]:
        """
        Save file bytes to storage backend.

        Returns:
            Tuple[str, str]: (internal_file_path, public_or_relative_url)
        """

    @abc.abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a stored file by its internal file path.

        Returns:
            bool: True if deleted successfully or missing, False otherwise.
        """


#: Where user-supplied uploads live, and the prefix the mount serving them
#: answers on. That mount forces a download for anything outside
#: ``INLINE_SAFE_EXTENSIONS``.
DEFAULT_UPLOAD_BASE_DIR = "static/uploads"
DEFAULT_UPLOAD_URL_PREFIX = "/static/uploads"

#: Where output **this application renders itself** lives, and its prefix. The
#: mount serving it renders inline, which is only safe because nothing a client
#: supplies is ever written here -- see :func:`generated_storage_provider`.
GENERATED_BASE_DIR = "static/generated"
GENERATED_URL_PREFIX = "/static/generated"


class LocalStorageProvider(BaseStorageProvider):
    """Local disk storage provider saving to {base_dir}/{year}/{month}/."""

    def __init__(
        self,
        base_dir: str | Path = DEFAULT_UPLOAD_BASE_DIR,
        url_prefix: str = DEFAULT_UPLOAD_URL_PREFIX,
    ) -> None:
        """``url_prefix`` is paired with ``base_dir``: it is what the mount
        serving that directory answers on, and both default to the upload
        tree so every existing caller mints exactly the URL it minted before.
        """
        self.base_dir = Path(base_dir)
        self.url_prefix = url_prefix.rstrip("/")

    def save_file(
        self,
        file_bytes: bytes,
        filename: str,  # noqa: ARG002  # part of `BaseStorageProvider.save_file`; deliberately unused here (APRAS-65)
        content_type: str,
    ) -> tuple[str, str]:
        """Write the bytes under a UUID name whose suffix comes from the type.

        ``filename`` is **display metadata and nothing else**: it does not
        reach the disk. The suffix is derived from the already-validated
        ``content_type`` instead, because the static mount guesses what it
        serves from the extension and the client must not get to choose it
        (APRAS-65). An unmapped type yields an inert ``.bin``.
        """
        now = clock.db_now()
        year_month_subfolder = f"{now.year}/{now.month:02d}"
        target_dir = self.base_dir / year_month_subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        unique_name = f"{uuid.uuid4()}{canonical_extension(content_type)}"
        relative_path = os.path.join(year_month_subfolder, unique_name)
        full_path = target_dir / unique_name

        with open(full_path, "wb") as f:
            f.write(file_bytes)

        url = f"{self.url_prefix}/{relative_path}"
        return str(full_path), url

    def delete_file(self, file_path: str) -> bool:
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
            return True
        except Exception:  # noqa: BLE001  # best-effort side effect; a failure here must not fail the request
            return False


def generated_storage_provider() -> LocalStorageProvider:
    """The provider the assembly-minutes and works-report generators use.

    Server-rendered HTML has to be served inline to be of any use, and the
    upload mount refuses to do that for a good reason. So generated output
    gets its own tree and its own mount. This factory is the **only** way any
    service reaches that tree: no call site names the directory itself, so
    "what can land next to inline-rendered HTML" stays answerable by reading
    this one function's callers.
    """
    return LocalStorageProvider(
        base_dir=GENERATED_BASE_DIR, url_prefix=GENERATED_URL_PREFIX
    )


class VercelBlobStorageProvider(BaseStorageProvider):
    """Stub implementation for Vercel Blob storage provider."""

    def save_file(
        self, file_bytes: bytes, filename: str, content_type: str
    ) -> tuple[str, str]:
        raise NotImplementedError("Vercel Blob storage provider is not configured.")

    def delete_file(self, file_path: str) -> bool:
        raise NotImplementedError("Vercel Blob storage provider is not configured.")


class S3StorageProvider(BaseStorageProvider):
    """Stub implementation for AWS S3 storage provider."""

    def save_file(
        self, file_bytes: bytes, filename: str, content_type: str
    ) -> tuple[str, str]:
        raise NotImplementedError("S3 storage provider is not configured.")

    def delete_file(self, file_path: str) -> bool:
        raise NotImplementedError("S3 storage provider is not configured.")


class CloudinaryStorageProvider(BaseStorageProvider):
    """Stub implementation for Cloudinary storage provider."""

    def save_file(
        self, file_bytes: bytes, filename: str, content_type: str
    ) -> tuple[str, str]:
        raise NotImplementedError("Cloudinary storage provider is not configured.")

    def delete_file(self, file_path: str) -> bool:
        raise NotImplementedError("Cloudinary storage provider is not configured.")
