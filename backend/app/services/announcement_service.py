"""Service layer for the Announcement Feed module."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.exceptions import (
    AnnouncementCommentNotFoundError,
    AnnouncementMediaNotFoundError,
    AnnouncementMediaTooLargeError,
    AnnouncementNotFoundError,
    AnnouncementPermissionError,
    InvalidAnnouncementMediaFormatError,
)
from app.models.announcement import (
    Announcement,
    AnnouncementComment,
    AnnouncementMedia,
    AnnouncementReadReceipt,
)
from app.models.enums import AnnouncementMediaType, UserRole
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementCommentCreate,
    AnnouncementCommentRead,
    AnnouncementCreate,
    AnnouncementDetailRead,
    AnnouncementMediaRead,
    AnnouncementRead,
    AnnouncementReadReceiptRead,
    AnnouncementUpdate,
    PaginatedAnnouncementRead,
)
from app.services.storage_service import BaseStorageProvider, LocalStorageProvider

MAX_MEDIA_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MEDIA_MIME_TYPES: dict[str, AnnouncementMediaType] = {
    "image/jpeg": AnnouncementMediaType.IMAGE,
    "image/png": AnnouncementMediaType.IMAGE,
    "image/webp": AnnouncementMediaType.IMAGE,
    "application/pdf": AnnouncementMediaType.PDF,
}

_storage_provider: BaseStorageProvider = LocalStorageProvider()


def _check_publisher(user: User) -> None:
    if user.role not in (UserRole.ADMINISTRATOR, UserRole.DIRECTOR):
        raise AnnouncementPermissionError()


def _format_media_read(media: AnnouncementMedia) -> AnnouncementMediaRead:
    return AnnouncementMediaRead(
        id=media.id,
        announcement_id=media.announcement_id,
        media_type=media.media_type,
        url=media.url,
        mime_type=media.mime_type,
        file_size_bytes=media.file_size_bytes,
        order_index=media.order_index,
        created_at=media.created_at,
    )


def _format_comment_read(session: Session, comment: AnnouncementComment) -> AnnouncementCommentRead:
    author = session.get(User, comment.user_id)
    return AnnouncementCommentRead(
        id=comment.id,
        announcement_id=comment.announcement_id,
        user_id=comment.user_id,
        author_name=author.full_name if author else None,
        content=comment.content,
        created_at=comment.created_at,
    )


def _format_announcement_read(
    session: Session, announcement: Announcement, current_user: User
) -> AnnouncementRead:
    author = session.get(User, announcement.author_id)

    media_items = session.exec(
        select(AnnouncementMedia)
        .where(AnnouncementMedia.announcement_id == announcement.id)
        .order_by(AnnouncementMedia.order_index.asc())
    ).all()

    comment_count = session.exec(
        select(func.count(AnnouncementComment.id)).where(
            AnnouncementComment.announcement_id == announcement.id
        )
    ).one()

    read_receipt = session.exec(
        select(AnnouncementReadReceipt).where(
            AnnouncementReadReceipt.announcement_id == announcement.id,
            AnnouncementReadReceipt.user_id == current_user.id,
        )
    ).first()

    return AnnouncementRead(
        id=announcement.id,
        title=announcement.title,
        content=announcement.content,
        author_id=announcement.author_id,
        author_name=author.full_name if author else None,
        media=[_format_media_read(m) for m in media_items],
        comment_count=comment_count,
        is_read=read_receipt is not None,
        created_at=announcement.created_at,
        updated_at=announcement.updated_at,
    )


def list_announcements(
    session: Session, user: User, skip: int = 0, limit: int = 20
) -> PaginatedAnnouncementRead:
    query = select(Announcement).where(Announcement.is_deleted == False)  # noqa: E712

    total = session.exec(select(func.count()).select_from(query.subquery())).one()

    announcements = session.exec(
        query.order_by(Announcement.created_at.desc()).offset(skip).limit(limit)
    ).all()

    items = [_format_announcement_read(session, a, user) for a in announcements]
    return PaginatedAnnouncementRead(items=items, total=total, skip=skip, limit=limit)


def get_announcement(session: Session, user: User, announcement_id: UUID) -> AnnouncementDetailRead:
    announcement = session.get(Announcement, announcement_id)
    if not announcement or announcement.is_deleted:
        raise AnnouncementNotFoundError(announcement_id)

    base = _format_announcement_read(session, announcement, user)
    comments = session.exec(
        select(AnnouncementComment)
        .where(AnnouncementComment.announcement_id == announcement_id)
        .order_by(AnnouncementComment.created_at.asc())
    ).all()

    return AnnouncementDetailRead(
        **base.model_dump(),
        comments=[_format_comment_read(session, c) for c in comments],
    )


def create_announcement(session: Session, user: User, data: AnnouncementCreate) -> AnnouncementRead:
    _check_publisher(user)

    announcement = Announcement(
        title=data.title,
        content=data.content,
        author_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(announcement)
    session.commit()
    session.refresh(announcement)

    return _format_announcement_read(session, announcement, user)


def update_announcement(
    session: Session, user: User, announcement_id: UUID, data: AnnouncementUpdate
) -> AnnouncementRead:
    _check_publisher(user)

    announcement = session.get(Announcement, announcement_id)
    if not announcement or announcement.is_deleted:
        raise AnnouncementNotFoundError(announcement_id)

    if data.title is not None:
        announcement.title = data.title
    if data.content is not None:
        announcement.content = data.content

    announcement.updated_at = datetime.utcnow()
    session.add(announcement)
    session.commit()
    session.refresh(announcement)

    return _format_announcement_read(session, announcement, user)


def delete_announcement(session: Session, user: User, announcement_id: UUID) -> None:
    _check_publisher(user)

    announcement = session.get(Announcement, announcement_id)
    if not announcement or announcement.is_deleted:
        raise AnnouncementNotFoundError(announcement_id)

    announcement.is_deleted = True
    announcement.updated_at = datetime.utcnow()
    session.add(announcement)
    session.commit()


def upload_media(
    session: Session,
    user: User,
    announcement_id: UUID,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> AnnouncementMediaRead:
    _check_publisher(user)

    announcement = session.get(Announcement, announcement_id)
    if not announcement or announcement.is_deleted:
        raise AnnouncementNotFoundError(announcement_id)

    if len(file_bytes) > MAX_MEDIA_FILE_SIZE:
        raise AnnouncementMediaTooLargeError()

    media_type = ALLOWED_MEDIA_MIME_TYPES.get(mime_type)
    if media_type is None:
        raise InvalidAnnouncementMediaFormatError()

    file_path, url = _storage_provider.save_file(file_bytes, filename, mime_type)

    max_order = session.exec(
        select(func.max(AnnouncementMedia.order_index)).where(
            AnnouncementMedia.announcement_id == announcement_id
        )
    ).one()
    next_order = (max_order + 1) if max_order is not None else 0

    media = AnnouncementMedia(
        announcement_id=announcement_id,
        media_type=media_type,
        file_path=file_path,
        url=url,
        mime_type=mime_type,
        file_size_bytes=len(file_bytes),
        order_index=next_order,
        created_at=datetime.utcnow(),
    )
    session.add(media)
    session.commit()
    session.refresh(media)

    return _format_media_read(media)


def delete_media(session: Session, user: User, announcement_id: UUID, media_id: UUID) -> None:
    _check_publisher(user)

    media = session.get(AnnouncementMedia, media_id)
    if not media or media.announcement_id != announcement_id:
        raise AnnouncementMediaNotFoundError(media_id)

    if media.file_path:
        _storage_provider.delete_file(media.file_path)

    session.delete(media)
    session.commit()


def list_comments(session: Session, announcement_id: UUID) -> list[AnnouncementCommentRead]:
    announcement = session.get(Announcement, announcement_id)
    if not announcement or announcement.is_deleted:
        raise AnnouncementNotFoundError(announcement_id)

    comments = session.exec(
        select(AnnouncementComment)
        .where(AnnouncementComment.announcement_id == announcement_id)
        .order_by(AnnouncementComment.created_at.asc())
    ).all()

    return [_format_comment_read(session, c) for c in comments]


def add_comment(
    session: Session, user: User, announcement_id: UUID, data: AnnouncementCommentCreate
) -> AnnouncementCommentRead:
    if user.role == UserRole.GUEST:
        raise AnnouncementPermissionError("Convidados não podem comentar em comunicados.")

    announcement = session.get(Announcement, announcement_id)
    if not announcement or announcement.is_deleted:
        raise AnnouncementNotFoundError(announcement_id)

    comment = AnnouncementComment(
        announcement_id=announcement_id,
        user_id=user.id,
        content=data.content,
        created_at=datetime.utcnow(),
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)

    return _format_comment_read(session, comment)


def delete_comment(session: Session, user: User, comment_id: UUID) -> None:
    comment = session.get(AnnouncementComment, comment_id)
    if not comment:
        raise AnnouncementCommentNotFoundError(comment_id)

    is_author = comment.user_id == user.id
    is_publisher = user.role in (UserRole.ADMINISTRATOR, UserRole.DIRECTOR)
    if not (is_author or is_publisher):
        raise AnnouncementPermissionError(
            "Apenas o autor do comentário ou um Administrador/Diretor pode excluí-lo."
        )

    session.delete(comment)
    session.commit()


def mark_read(session: Session, user: User, announcement_id: UUID) -> datetime:
    announcement = session.get(Announcement, announcement_id)
    if not announcement or announcement.is_deleted:
        raise AnnouncementNotFoundError(announcement_id)

    existing = session.exec(
        select(AnnouncementReadReceipt).where(
            AnnouncementReadReceipt.announcement_id == announcement_id,
            AnnouncementReadReceipt.user_id == user.id,
        )
    ).first()
    if existing:
        return existing.read_at

    receipt = AnnouncementReadReceipt(
        announcement_id=announcement_id,
        user_id=user.id,
        read_at=datetime.utcnow(),
    )
    session.add(receipt)
    session.commit()
    session.refresh(receipt)

    return receipt.read_at


def list_read_receipts(
    session: Session, user: User, announcement_id: UUID
) -> list[AnnouncementReadReceiptRead]:
    _check_publisher(user)

    announcement = session.get(Announcement, announcement_id)
    if not announcement or announcement.is_deleted:
        raise AnnouncementNotFoundError(announcement_id)

    receipts = session.exec(
        select(AnnouncementReadReceipt).where(
            AnnouncementReadReceipt.announcement_id == announcement_id
        )
    ).all()

    results = []
    for r in receipts:
        reader = session.get(User, r.user_id)
        results.append(
            AnnouncementReadReceiptRead(
                user_id=r.user_id,
                user_name=reader.full_name if reader else None,
                read_at=r.read_at,
            )
        )
    return results
