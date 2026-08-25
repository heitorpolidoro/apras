import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlmodel import Session

from app.api.deps import get_current_active_user, get_db
from app.models.enums import EntityType
from app.models.user import User
from app.schemas.media_asset import MediaAssetRead, MediaAssetListResponse, PhotoRejectRequest
from app.services.media_service import media_service

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/photo", response_model=MediaAssetRead, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    entity_type: EntityType = Form(...),
    entity_id: Optional[uuid.UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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


@router.get("/photos/pending", response_model=MediaAssetListResponse)
def get_pending_photos(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MediaAssetListResponse:
    return media_service.list_pending_photos(session=db, current_user=current_user, page=page, limit=limit)


@router.put("/photos/{photo_id}/approve", response_model=MediaAssetRead)
def approve_photo(
    photo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MediaAssetRead:
    return media_service.approve_photo(session=db, photo_id=photo_id, admin_user=current_user)


@router.put("/photos/{photo_id}/reject", response_model=MediaAssetRead)
def reject_photo(
    photo_id: uuid.UUID,
    body: PhotoRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MediaAssetRead:
    return media_service.reject_photo(
        session=db, photo_id=photo_id, admin_user=current_user, rejection_reason=body.rejection_reason
    )


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    media_service.delete_photo(session=db, photo_id=photo_id, current_user=current_user)


@router.get("/photos/{photo_id}", response_model=MediaAssetRead)
def get_photo_metadata(
    photo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MediaAssetRead:
    return media_service.get_photo_metadata(session=db, photo_id=photo_id)
