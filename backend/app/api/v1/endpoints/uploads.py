import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlmodel import Session

from app.api.deps import get_current_active_user, get_db, require_permission
from app.models.enums import EntityType
from app.models.user import User
from app.schemas.media_asset import (
    MediaAssetListResponse,
    MediaAssetRead,
    PhotoRejectRequest,
)
from app.services.media_service import media_service

router = APIRouter(prefix="/uploads", tags=["Uploads"])

#: The three APRAS-51 guards, bound once at import. Same reason as
#: `endpoints/feedback.py`: this module uses the older
#: `current_user: User = Depends(...)` spelling, and a call in an argument
#: default is `B008`. `get_current_active_user` stays imported -- the three
#: photo-moderation routes still use it.
_require_photo_create = require_permission("uploads:photo_create")
_require_photo_read = require_permission("uploads:photo_read")
_require_photo_delete = require_permission("uploads:delete")


@router.post("/photo", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: Annotated[UploadFile, File()],
    entity_type: Annotated[EntityType, Form()],
    # Ahead of `entity_id` because `Annotated[..., Depends(...)]` has no
    # default and cannot follow a parameter that has one. Dependencies are not
    # OpenAPI parameters, so the multipart body's fields do not move.
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(_require_photo_create)],
    entity_id: Annotated[uuid.UUID | None, Form()] = None,
) -> MediaAssetRead:
    file_bytes = await file.read()
    filename = file.filename or "upload.jpg"
    mime_type = file.content_type or "image/jpeg"

    return media_service.upload_photo(
        session=db,
        current_user=current_user,
        file_bytes=file_bytes,
        filename=filename,
        mime_type=mime_type,
        entity_type=entity_type,
        entity_id=entity_id,
    )


@router.get("/photos/pending")
def get_pending_photos(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MediaAssetListResponse:
    return media_service.list_pending_photos(
        session=db, current_user=current_user, page=page, limit=limit
    )


@router.put("/photos/{photo_id}/approve")
def approve_photo(
    photo_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> MediaAssetRead:
    return media_service.approve_photo(
        session=db, photo_id=photo_id, admin_user=current_user
    )


@router.put("/photos/{photo_id}/reject")
def reject_photo(
    photo_id: uuid.UUID,
    body: PhotoRejectRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> MediaAssetRead:
    return media_service.reject_photo(
        session=db,
        photo_id=photo_id,
        admin_user=current_user,
        rejection_reason=body.rejection_reason,
    )


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(_require_photo_delete)],
) -> None:
    media_service.delete_photo(session=db, photo_id=photo_id, current_user=current_user)


@router.get("/photos/{photo_id}")
def get_photo_metadata(
    photo_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(_require_photo_read)],
) -> MediaAssetRead:
    return media_service.get_photo_metadata(session=db, photo_id=photo_id)
