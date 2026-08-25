import io
import uuid
from datetime import datetime
from typing import Tuple, List, Optional
from PIL import Image
from sqlmodel import Session, select, func

from app.core.exceptions import (
    MediaAssetNotFoundError,
    PhotoFileTooLargeError,
    InvalidPhotoFormatError,
    PhotoApprovalPermissionError,
    PhotoRejectionReasonRequiredError,
    ForbiddenError,
)
from app.models.enums import EntityType, StorageProvider, PhotoApprovalStatus, UserRole
from app.models.media_asset import MediaAsset
from app.models.user import User
from app.schemas.media_asset import MediaAssetRead, MediaAssetListResponse
from app.services.storage_service import LocalStorageProvider, BaseStorageProvider

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class MediaService:
    """Service handling photo upload, thumbnail generation, approval workflow, and storage."""

    def __init__(self, storage_provider: Optional[BaseStorageProvider] = None) -> None:
        self.storage_provider = storage_provider or LocalStorageProvider()

    def _to_read_schema(self, session: Session, asset: MediaAsset) -> MediaAssetRead:
        uploader = session.get(User, asset.uploaded_by_id)
        approver = session.get(User, asset.approved_by_id) if asset.approved_by_id else None

        return MediaAssetRead(
            id=asset.id,
            entity_type=asset.entity_type,
            entity_id=asset.entity_id,
            storage_provider=asset.storage_provider,
            file_path=asset.file_path,
            url=asset.url,
            thumbnail_url=asset.thumbnail_url,
            file_size_bytes=asset.file_size_bytes,
            mime_type=asset.mime_type,
            width=asset.width,
            height=asset.height,
            status=asset.status,
            rejection_reason=asset.rejection_reason,
            uploaded_by_id=asset.uploaded_by_id,
            uploaded_by_name=uploader.full_name if uploader else None,
            approved_by_id=asset.approved_by_id,
            approved_by_name=approver.full_name if approver else None,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            approved_at=asset.approved_at,
        )

    def upload_photo(
        self,
        session: Session,
        current_user: User,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        entity_type: EntityType,
        entity_id: Optional[uuid.UUID] = None,
    ) -> MediaAssetRead:
        # 1. Size validation
        if len(file_bytes) > MAX_FILE_SIZE:
            raise PhotoFileTooLargeError()

        # 2. MIME type validation
        if mime_type not in ALLOWED_MIME_TYPES:
            raise InvalidPhotoFormatError()

        # 3. Pillow validation & dimensions extraction
        try:
            img = Image.open(io.BytesIO(file_bytes))
            width, height = img.size
            img_format = img.format
        except Exception:
            raise InvalidPhotoFormatError()

        # 4. Generate 150x150 square thumbnail
        try:
            # Crop to square before resizing for thumbnail
            min_dim = min(width, height)
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            cropped = img.crop((left, top, left + min_dim, top + min_dim))
            thumb_img = cropped.resize((150, 150), Image.Resampling.LANCZOS)
            
            thumb_io = io.BytesIO()
            save_format = img_format if img_format in ("JPEG", "PNG", "WEBP") else "JPEG"
            thumb_img.save(thumb_io, format=save_format)
            thumb_bytes = thumb_io.getvalue()
        except Exception:
            thumb_bytes = file_bytes

        # 5. Save files via StorageProvider
        file_path, url = self.storage_provider.save_file(file_bytes, filename, mime_type)
        thumb_filename = f"thumb_{filename}"
        _, thumbnail_url = self.storage_provider.save_file(thumb_bytes, thumb_filename, mime_type)

        # 6. Auto-approval policy
        admin_roles = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER}
        if current_user.role in admin_roles:
            status = PhotoApprovalStatus.APPROVED
            approved_by_id = current_user.id
            approved_at = datetime.utcnow()
        else:
            status = PhotoApprovalStatus.PENDING_APPROVAL
            approved_by_id = None
            approved_at = None

        # 7. Create DB record
        asset = MediaAsset(
            entity_type=entity_type,
            entity_id=entity_id,
            storage_provider=StorageProvider.LOCAL_DISK,
            file_path=file_path,
            url=url,
            thumbnail_url=thumbnail_url,
            file_size_bytes=len(file_bytes),
            mime_type=mime_type,
            width=width,
            height=height,
            status=status,
            uploaded_by_id=current_user.id,
            approved_by_id=approved_by_id,
            approved_at=approved_at,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        session.add(asset)
        session.commit()
        session.refresh(asset)

        return self._to_read_schema(session, asset)

    def list_pending_photos(
        self, session: Session, current_user: User, page: int = 1, limit: int = 20
    ) -> MediaAssetListResponse:
        if current_user.role not in {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}:
            raise PhotoApprovalPermissionError()

        pending_stmt = select(MediaAsset).where(MediaAsset.status == PhotoApprovalStatus.PENDING_APPROVAL)
        total_pending = len(session.exec(pending_stmt).all())

        total_stmt = select(MediaAsset)
        total_all = len(session.exec(total_stmt).all())

        offset = (page - 1) * limit
        items_stmt = (
            select(MediaAsset)
            .where(MediaAsset.status == PhotoApprovalStatus.PENDING_APPROVAL)
            .order_by(MediaAsset.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        assets = session.exec(items_stmt).all()

        items = [self._to_read_schema(session, a) for a in assets]

        return MediaAssetListResponse(
            items=items,
            total=total_all,
            pending_count=total_pending,
        )

    def approve_photo(self, session: Session, photo_id: uuid.UUID, admin_user: User) -> MediaAssetRead:
        if admin_user.role not in {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}:
            raise PhotoApprovalPermissionError()

        asset = session.get(MediaAsset, photo_id)
        if not asset:
            raise MediaAssetNotFoundError(photo_id)

        asset.status = PhotoApprovalStatus.APPROVED
        asset.approved_by_id = admin_user.id
        asset.approved_at = datetime.utcnow()
        asset.rejection_reason = None
        asset.updated_at = datetime.utcnow()

        session.add(asset)
        session.commit()
        session.refresh(asset)

        return self._to_read_schema(session, asset)

    def reject_photo(
        self, session: Session, photo_id: uuid.UUID, admin_user: User, rejection_reason: str
    ) -> MediaAssetRead:
        if admin_user.role not in {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}:
            raise PhotoApprovalPermissionError()

        if not rejection_reason or not rejection_reason.strip():
            raise PhotoRejectionReasonRequiredError()

        asset = session.get(MediaAsset, photo_id)
        if not asset:
            raise MediaAssetNotFoundError(photo_id)

        asset.status = PhotoApprovalStatus.REJECTED
        asset.approved_by_id = admin_user.id
        asset.rejection_reason = rejection_reason.strip()
        asset.updated_at = datetime.utcnow()

        session.add(asset)
        session.commit()
        session.refresh(asset)

        return self._to_read_schema(session, asset)

    def delete_photo(self, session: Session, photo_id: uuid.UUID, current_user: User) -> None:
        asset = session.get(MediaAsset, photo_id)
        if not asset:
            raise MediaAssetNotFoundError(photo_id)

        is_owner = asset.uploaded_by_id == current_user.id
        is_admin = current_user.role in {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}

        if not (is_owner or is_admin):
            raise ForbiddenError("Você não tem permissão para excluir esta foto.")

        # Delete files from disk
        if asset.file_path:
            self.storage_provider.delete_file(asset.file_path)

        session.delete(asset)
        session.commit()

    def get_photo_metadata(self, session: Session, photo_id: uuid.UUID) -> MediaAssetRead:
        asset = session.get(MediaAsset, photo_id)
        if not asset:
            raise MediaAssetNotFoundError(photo_id)

        return self._to_read_schema(session, asset)


media_service = MediaService()
