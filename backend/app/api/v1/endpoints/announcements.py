"""API Endpoints for the Announcement Feed module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models.enums import UserRole
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
    MarkReadResponse,
    PaginatedAnnouncementRead,
)
from app.services import announcement_service

router = APIRouter()


def _assert_not_porteiro(current_user: User) -> None:
    """Raise 403 if the caller is PORTEIRO (gate-only role, no access here)."""
    if current_user.role == UserRole.PORTEIRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )


@router.get("", response_model=PaginatedAnnouncementRead)
def list_announcements(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> PaginatedAnnouncementRead:
    """Lists the announcement feed, newest first."""
    _assert_not_porteiro(current_user)
    return announcement_service.list_announcements(session=db, user=current_user, skip=skip, limit=limit)


@router.post("", response_model=AnnouncementRead, status_code=status.HTTP_201_CREATED)
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnnouncementRead:
    """Creates a new announcement (publishers only)."""
    _assert_not_porteiro(current_user)
    return announcement_service.create_announcement(session=db, user=current_user, data=data)


@router.get("/{id}", response_model=AnnouncementDetailRead)
def get_announcement(
    id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnnouncementDetailRead:
    """Retrieves a single announcement with its media and comments."""
    _assert_not_porteiro(current_user)
    return announcement_service.get_announcement(session=db, user=current_user, announcement_id=id)


@router.put("/{id}", response_model=AnnouncementRead)
def update_announcement(
    id: UUID,
    data: AnnouncementUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnnouncementRead:
    """Updates an announcement's title/content (publishers only)."""
    _assert_not_porteiro(current_user)
    return announcement_service.update_announcement(
        session=db, user=current_user, announcement_id=id, data=data
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-deletes an announcement (publishers only)."""
    _assert_not_porteiro(current_user)
    announcement_service.delete_announcement(session=db, user=current_user, announcement_id=id)


@router.post("/{id}/media", response_model=AnnouncementMediaRead, status_code=status.HTTP_201_CREATED)
async def upload_announcement_media(
    id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnnouncementMediaRead:
    """Uploads an image or PDF attachment to an announcement (publishers only)."""
    _assert_not_porteiro(current_user)
    file_bytes = await file.read()
    filename = file.filename or "attachment"
    mime_type = file.content_type or "application/octet-stream"

    return announcement_service.upload_media(
        session=db,
        user=current_user,
        announcement_id=id,
        file_bytes=file_bytes,
        filename=filename,
        mime_type=mime_type,
    )


@router.delete("/{id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement_media(
    id: UUID,
    media_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Deletes an announcement media attachment (publishers only)."""
    _assert_not_porteiro(current_user)
    announcement_service.delete_media(
        session=db, user=current_user, announcement_id=id, media_id=media_id
    )


@router.get("/{id}/comments", response_model=list[AnnouncementCommentRead])
def list_comments(
    id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AnnouncementCommentRead]:
    """Lists comments for an announcement, oldest first."""
    _assert_not_porteiro(current_user)
    return announcement_service.list_comments(session=db, announcement_id=id)


@router.post(
    "/{id}/comments", response_model=AnnouncementCommentRead, status_code=status.HTTP_201_CREATED
)
def add_comment(
    id: UUID,
    data: AnnouncementCommentCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnnouncementCommentRead:
    """Adds a comment to an announcement (not allowed for GUEST role)."""
    _assert_not_porteiro(current_user)
    return announcement_service.add_comment(session=db, user=current_user, announcement_id=id, data=data)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Deletes a comment (author or publisher only)."""
    _assert_not_porteiro(current_user)
    announcement_service.delete_comment(session=db, user=current_user, comment_id=comment_id)


@router.post("/{id}/read", response_model=MarkReadResponse)
def mark_read(
    id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MarkReadResponse:
    """Idempotently marks an announcement as read by the current user."""
    _assert_not_porteiro(current_user)
    read_at = announcement_service.mark_read(session=db, user=current_user, announcement_id=id)
    return MarkReadResponse(read_at=read_at)


@router.get("/{id}/read-receipts", response_model=list[AnnouncementReadReceiptRead])
def list_read_receipts(
    id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AnnouncementReadReceiptRead]:
    """Lists users who have read the announcement (publishers only)."""
    _assert_not_porteiro(current_user)
    return announcement_service.list_read_receipts(session=db, user=current_user, announcement_id=id)
