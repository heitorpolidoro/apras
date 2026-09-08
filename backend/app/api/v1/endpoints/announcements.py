"""API Endpoints for the Announcement Feed module."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlmodel import Session

from app.api.deps import get_current_user, has_permission
from app.db import get_session
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


def _assert_not_porteiro(current_user: User, session: Session, permission: str) -> None:
    """Raise 403 unless the caller holds this route's own permission.

    Named for the rule it used to spell (PORTEIRO is a gate-only role and
    never reaches this module); each call site now passes the permission of
    *its* route, so a helper shared by a dozen routes does not collapse a
    dozen permissions into one.
    """
    if not has_permission(current_user, session, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )


@router.get("")
def list_announcements(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedAnnouncementRead:
    """Lists the announcement feed, newest first."""
    _assert_not_porteiro(current_user, db, "announcements:read")
    return announcement_service.list_announcements(
        session=db, user=current_user, skip=skip, limit=limit
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_announcement(
    data: AnnouncementCreate,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnnouncementRead:
    """Creates a new announcement (publishers only)."""
    _assert_not_porteiro(current_user, db, "announcements:create")
    return announcement_service.create_announcement(
        session=db, user=current_user, data=data
    )


@router.get("/{id}")
def get_announcement(
    id: UUID,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnnouncementDetailRead:
    """Retrieves a single announcement with its media and comments."""
    _assert_not_porteiro(current_user, db, "announcements:read")
    return announcement_service.get_announcement(
        session=db, user=current_user, announcement_id=id
    )


@router.put("/{id}")
def update_announcement(
    id: UUID,
    data: AnnouncementUpdate,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnnouncementRead:
    """Updates an announcement's title/content (publishers only)."""
    _assert_not_porteiro(current_user, db, "announcements:update")
    return announcement_service.update_announcement(
        session=db, user=current_user, announcement_id=id, data=data
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    id: UUID,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Soft-deletes an announcement (publishers only)."""
    _assert_not_porteiro(current_user, db, "announcements:delete")
    announcement_service.delete_announcement(
        session=db, user=current_user, announcement_id=id
    )


@router.post(
    "/{id}/media",
    status_code=status.HTTP_201_CREATED,
)
async def upload_announcement_media(
    id: UUID,
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnnouncementMediaRead:
    """Uploads an image or PDF attachment to an announcement (publishers only)."""
    _assert_not_porteiro(current_user, db, "announcements:media_upload")
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
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Deletes an announcement media attachment (publishers only)."""
    _assert_not_porteiro(current_user, db, "announcements:media_delete")
    announcement_service.delete_media(
        session=db, user=current_user, announcement_id=id, media_id=media_id
    )


@router.get("/{id}/comments")
def list_comments(
    id: UUID,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AnnouncementCommentRead]:
    """Lists comments for an announcement, oldest first."""
    _assert_not_porteiro(current_user, db, "announcements:read")
    return announcement_service.list_comments(session=db, announcement_id=id)


@router.post(
    "/{id}/comments",
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    id: UUID,
    data: AnnouncementCommentCreate,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnnouncementCommentRead:
    """Adds a comment to an announcement (not allowed for GUEST role)."""
    _assert_not_porteiro(current_user, db, "announcements:comment")
    return announcement_service.add_comment(
        session=db, user=current_user, announcement_id=id, data=data
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Deletes a comment (author or publisher only)."""
    _assert_not_porteiro(current_user, db, "announcements:comment_delete")
    announcement_service.delete_comment(
        session=db, user=current_user, comment_id=comment_id
    )


@router.post("/{id}/read")
def mark_read(
    id: UUID,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MarkReadResponse:
    """Idempotently marks an announcement as read by the current user."""
    _assert_not_porteiro(current_user, db, "announcements:mark_read")
    read_at = announcement_service.mark_read(
        session=db, user=current_user, announcement_id=id
    )
    return MarkReadResponse(read_at=read_at)


@router.get("/{id}/read-receipts")
def list_read_receipts(
    id: UUID,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AnnouncementReadReceiptRead]:
    """Lists users who have read the announcement (publishers only)."""
    _assert_not_porteiro(current_user, db, "announcements:read_receipts_read")
    return announcement_service.list_read_receipts(
        session=db, user=current_user, announcement_id=id
    )
