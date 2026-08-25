</Meridian Spec Generator — Task Spec Author>
<T004 — Gestão e Armazenamento de Fotos nos Cadastros>

## Scope

This task implements the Media & Photo Management module ("Gestão e Armazenamento de Fotos nos Cadastros") for APRAS. It provides a secure media asset storage backend service, file upload validation, client-side webcam capture & crop capabilities, auto-thumbnail generation, and an administrative photo approval workflow required before biometrics or profile photos are active in access control and registers.

### In Scope

1. **Database Schema & SQLModels**:
   - SQLModel entity `MediaAsset`: Master entity for uploaded photo assets.
     - `id`: UUID (PK, default `uuid4`)
     - `entity_type`: Enum `EntityType` (`RESIDENT`, `VISITOR`, `EMPLOYEE`, `LOT`, `ANNOUNCEMENT`, `OCCURRENCE`)
     - `entity_id`: UUID | None (nullable FK/reference to target entity)
     - `storage_provider`: Enum `StorageProvider` (`LOCAL_DISK`, `VERCEL_BLOB`, `AWS_S3`, `CLOUDINARY`), default `LOCAL_DISK`
     - `file_path`: str (internal storage path / object key)
     - `url`: str (public/signed HTTP access URL)
     - `thumbnail_url`: str | None (HTTP URL for 150x150 square thumbnail)
     - `file_size_bytes`: int
     - `mime_type`: str (`image/jpeg`, `image/png`, `image/webp`)
     - `width`: int | None (image pixel width)
     - `height`: int | None (image pixel height)
     - `status`: Enum `PhotoApprovalStatus` (`PENDING_APPROVAL`, `APPROVED`, `REJECTED`)
     - `rejection_reason`: str | None (mandatory explanation when status is `REJECTED`)
     - `uploaded_by_id`: UUID (FK -> `user.id` ON DELETE CASCADE)
     - `approved_by_id`: UUID | None (FK -> `user.id` ON DELETE SET NULL)
     - `created_at`: datetime (default `datetime.utcnow`)
     - `updated_at`: datetime (default `datetime.utcnow`)
     - `approved_at`: datetime | None
   - Domain Enums in `backend/app/models/enums.py`:
     - `EntityType`: `RESIDENT`, `VISITOR`, `EMPLOYEE`, `LOT`, `ANNOUNCEMENT`, `OCCURRENCE`
     - `StorageProvider`: `LOCAL_DISK`, `VERCEL_BLOB`, `AWS_S3`, `CLOUDINARY`
     - `PhotoApprovalStatus`: `PENDING_APPROVAL`, `APPROVED`, `REJECTED`
   - Alembic migration `0011_add_media_asset_table.py` generating `media_asset` table, FK constraints, and indexes on `(entity_type, entity_id)`, `status`, and `uploaded_by_id`.

2. **Storage Abstraction & Image Processing**:
   - Abstract `BaseStorageProvider` class with concrete implementations:
     - `LocalStorageProvider`: Saves files locally under `backend/static/uploads/` and serves via FastAPI static mounts.
     - Extensible interface signatures for `VercelBlobStorageProvider`, `S3StorageProvider`, and `CloudinaryStorageProvider`.
   - Image validation:
     - Maximum file size limit: 5MB (5,242,880 bytes).
     - Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`.
     - Inspection using Pillow (`PIL.Image`) to extract dimensions (`width`, `height`) and prevent corrupted or malicious payload uploads.
   - Thumbnail generation:
     - Automatically resizes/crops uploaded images to a 150x150 pixel square JPEG/WebP thumbnail (`_thumb` suffix) saved alongside original asset.

3. **Approval & RBAC Workflow**:
   - **Approval Policy**:
     - Uploads by `RESIDENT` users enter `PENDING_APPROVAL` status.
     - Uploads directly executed by administrative users (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`) auto-approve instantly (`status = APPROVED`, `approved_by_id = uploaded_by_id`, `approved_at = datetime.utcnow()`).
   - **Approval Queue API & UI**:
     - Route `/admin/photo-approvals` accessible only to `ADMINISTRATOR` and `DIRECTOR`.
     - Endpoints to approve (`PUT /api/v1/uploads/photos/{id}/approve`) or reject with reason (`PUT /api/v1/uploads/photos/{id}/reject`).
   - **Active Biometrics Constraint**:
     - Only photos with status `APPROVED` can be retrieved or linked for facial recognition sync (T005) or active avatar display in resident/visitor rosters.

4. **Backend REST API Endpoints under `/api/v1/uploads`**:
   - `POST /api/v1/uploads/photo`: Multipart file upload (accepting file binary, `entity_type`, optional `entity_id`).
   - `GET /api/v1/uploads/photos/pending`: List pending photo approval queue with filtering and pagination.
   - `PUT /api/v1/uploads/photos/{id}/approve`: Approve a pending photo asset (Admin / Director only).
   - `PUT /api/v1/uploads/photos/{id}/reject`: Reject a pending photo asset with reason (Admin / Director only).
   - `DELETE /api/v1/uploads/photos/{id}`: Delete a photo asset and its physical stored files (Uploader or Admin/Director).
   - `GET /api/v1/uploads/photos/{id}`: Retrieve photo asset metadata and URLs.

5. **Frontend UI & Components**:
   - Route `/admin/photo-approvals` (`PhotoApprovalQueuePage.tsx`) with status filtering (`PENDING_APPROVAL`, `APPROVED`, `REJECTED`), side-by-side photo comparison modal, reject reason dialog, and batch/single action buttons.
   - Reusable frontend components in `frontend/src/components/`:
     - `PhotoUploadModal.tsx`: File upload dialog supporting drag-and-drop, file input, and webcam toggle.
     - `WebcamCaptureDialog.tsx`: Modal for live camera feed capture using HTML5 MediaDevices / `react-webcam`.
     - `AvatarCropEditor.tsx`: Interactive square cropper for photo alignment prior to submission.
     - `AvatarWithFallback.tsx`: Reusable profile photo component displaying approved photo avatar or fallback initials.
   - API client (`src/api/photoUpload.ts`) and custom TanStack Query hook (`src/hooks/usePhotoUpload.ts`).
   - Navbar indicator badge for pending photo approval count for Admin/Director roles.

6. **Testing & Quality Assurance**:
   - Pytest suite (`backend/tests/test_photo_uploads.py`) covering file validations (size/MIME), storage providers, auto-approval vs pending rules, thumbnail generation, approval queue actions, deletion, and RBAC guards (≥ 90% backend coverage).
   - Vitest suite (`frontend/src/features/photo-management/__tests__/`) covering file selection, webcam snapshot capture, cropping editor state, photo approval queue filtering, and approval/rejection actions (≥ 75% frontend coverage).

---

## Approach

### Data Layer (`backend/app/models/` & `backend/app/schemas/`)

1. **Domain Enums (`backend/app/models/enums.py`)**:
   ```python
   class EntityType(StrEnum):
       RESIDENT = "RESIDENT"
       VISITOR = "VISITOR"
       EMPLOYEE = "EMPLOYEE"
       LOT = "LOT"
       ANNOUNCEMENT = "ANNOUNCEMENT"
       OCCURRENCE = "OCCURRENCE"

   class StorageProvider(StrEnum):
       LOCAL_DISK = "LOCAL_DISK"
       VERCEL_BLOB = "VERCEL_BLOB"
       AWS_S3 = "AWS_S3"
       CLOUDINARY = "CLOUDINARY"

   class PhotoApprovalStatus(StrEnum):
       PENDING_APPROVAL = "PENDING_APPROVAL"
       APPROVED = "APPROVED"
       REJECTED = "REJECTED"
   ```

2. **SQLModel Entity (`backend/app/models/media_asset.py`)**:
   ```python
   import uuid
   from datetime import datetime
   from sqlmodel import Field, Relationship, SQLModel
   from app.models.enums import EntityType, StorageProvider, PhotoApprovalStatus

   class MediaAsset(SQLModel, table=True):
       __tablename__ = "media_asset"

       id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
       entity_type: EntityType = Field(index=True, nullable=False)
       entity_id: uuid.UUID | None = Field(default=None, index=True, nullable=True)
       storage_provider: StorageProvider = Field(default=StorageProvider.LOCAL_DISK, nullable=False)
       file_path: str = Field(nullable=False)
       url: str = Field(nullable=False)
       thumbnail_url: str | None = Field(default=None, nullable=True)
       file_size_bytes: int = Field(nullable=False)
       mime_type: str = Field(nullable=False)
       width: int | None = Field(default=None, nullable=True)
       height: int | None = Field(default=None, nullable=True)
       status: PhotoApprovalStatus = Field(default=PhotoApprovalStatus.PENDING_APPROVAL, index=True, nullable=False)
       rejection_reason: str | None = Field(default=None, nullable=True)

       uploaded_by_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
       approved_by_id: uuid.UUID | None = Field(foreign_key="user.id", ondelete="SET NULL", nullable=True)

       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       approved_at: datetime | None = Field(default=None, nullable=True)

       uploaded_by: "User" = Relationship(sa_relationship_kwargs={"foreign_keys": "[MediaAsset.uploaded_by_id]"})
       approved_by: "User" | None = Relationship(sa_relationship_kwargs={"foreign_keys": "[MediaAsset.approved_by_id]"})
   ```

3. **Pydantic Schemas (`backend/app/schemas/media_asset.py`)**:
   ```python
   from datetime import datetime
   import uuid
   from pydantic import BaseModel
   from app.models.enums import EntityType, StorageProvider, PhotoApprovalStatus

   class MediaAssetRead(BaseModel):
       id: uuid.UUID
       entity_type: EntityType
       entity_id: uuid.UUID | None
       storage_provider: StorageProvider
       file_path: str
       url: str
       thumbnail_url: str | None
       file_size_bytes: int
       mime_type: str
       width: int | None
       height: int | None
       status: PhotoApprovalStatus
       rejection_reason: str | None
       uploaded_by_id: uuid.UUID
       uploaded_by_name: str | None = None
       approved_by_id: uuid.UUID | None = None
       approved_by_name: str | None = None
       created_at: datetime
       updated_at: datetime
       approved_at: datetime | None = None

       class Config:
           from_attributes = True

   class PhotoRejectRequest(BaseModel):
       rejection_reason: str

   class MediaAssetListResponse(BaseModel):
       items: list[MediaAssetRead]
       total: int
       pending_count: int
   ```

4. **Domain Exceptions (`backend/app/core/exceptions.py`)**:
   - `MediaAssetNotFoundError`: HTTP 404 ("Foto não encontrada.")
   - `PhotoFileTooLargeError`: HTTP 400 ("Arquivo excede o limite máximo permitido de 5MB.")
   - `InvalidPhotoFormatError`: HTTP 400 ("Formato de imagem inválido. Formatos aceitos: JPEG, PNG, WebP.")
   - `PhotoApprovalPermissionError`: HTTP 403 ("Apenas Administradores e Diretores podem aprovar ou rejeitar fotos.")
   - `PhotoRejectionReasonRequiredError`: HTTP 400 ("Motivo de rejeição é obrigatório.")

---

### Backend Service Layer (`backend/app/services/`)

1. **Storage Provider Interface (`backend/app/services/storage_service.py`)**:
   - Class `BaseStorageProvider`:
     - `async save_file(file_bytes: bytes, filename: str, content_type: str) -> tuple[str, str]` (returns `(file_path, url)`)
     - `async delete_file(file_path: str) -> bool`
   - Class `LocalStorageProvider(BaseStorageProvider)`:
     - Saves files into `backend/static/uploads/{year}/{month}/`.
     - Generates static URL pointing to `/static/uploads/{year}/{month}/{unique_filename}`.

2. **Media Service (`backend/app/services/media_service.py`)**:
   - Class `MediaService`:
     - `upload_photo(session, current_user, file_bytes, filename, mime_type, entity_type, entity_id) -> MediaAsset`:
       1. Enforces max size `5 * 1024 * 1024` bytes.
       2. Validates MIME type in `["image/jpeg", "image/png", "image/webp"]`.
       3. Uses Pillow (`PIL.Image.open`) to extract width and height.
       4. Generates a square 150x150 thumbnail image and saves both original and thumbnail via `StorageProvider`.
       5. Determines status: if `current_user.role` in `[UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER]`, sets `status = PhotoApprovalStatus.APPROVED`, `approved_by_id = current_user.id`, `approved_at = datetime.utcnow()`. Otherwise sets `status = PhotoApprovalStatus.PENDING_APPROVAL`.
       6. Creates and commits `MediaAsset` record.
     - `list_pending_photos(session, page, limit) -> tuple[list[MediaAsset], int, int]`:
       - Returns pending approval items with total count and pending queue size.
     - `approve_photo(session, photo_id, admin_user) -> MediaAsset`:
       - Updates status to `APPROVED`, sets `approved_by_id = admin_user.id`, `approved_at = datetime.utcnow()`.
     - `reject_photo(session, photo_id, admin_user, rejection_reason) -> MediaAsset`:
       - Enforces non-empty rejection reason string. Updates status to `REJECTED`, sets `approved_by_id = admin_user.id`, `rejection_reason = rejection_reason`.
     - `delete_photo(session, photo_id, current_user)`:
       - Deletes physical files (original + thumbnail) via `StorageProvider` and removes `MediaAsset` record from database.

---

### Backend Router & Endpoints (`backend/app/api/v1/endpoints/uploads.py`)

```python
router = APIRouter(prefix="/uploads", tags=["Uploads"])

@router.post("/photo", response_model=MediaAssetRead, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    entity_type: EntityType = Form(...),
    entity_id: uuid.UUID | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
)

@router.get("/photos/pending", response_model=MediaAssetListResponse)
def get_pending_photos(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user) # Guard: Admin or Director
)

@router.put("/photos/{photo_id}/approve", response_model=MediaAssetRead)
def approve_photo(
    photo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user) # Guard: Admin or Director
)

@router.put("/photos/{photo_id}/reject", response_model=MediaAssetRead)
def reject_photo(
    photo_id: uuid.UUID,
    body: PhotoRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user) # Guard: Admin or Director
)

@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
)

@router.get("/photos/{photo_id}", response_model=MediaAssetRead)
def get_photo_metadata(
    photo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
)
```

---

### Frontend Architecture

1. **API Client & Hooks**:
   - `frontend/src/api/photoUpload.ts`: Axios wrapper functions for `/api/v1/uploads/*`.
   - `frontend/src/hooks/usePhotoUpload.ts`: Custom React hook exporting `uploadPhoto`, `usePendingPhotos`, `approvePhoto`, `rejectPhoto`, and `deletePhoto` mutations.

2. **Components (`frontend/src/components/`)**:
   - `PhotoUploadModal.tsx`: Modal overlay providing tabbed selection: File Upload (drag-and-drop zone) and Webcam Snapshot. Displays image preview and integrates `AvatarCropEditor`.
   - `WebcamCaptureDialog.tsx`: HTML5 canvas/MediaDevices webcam stream modal with live camera preview, shutter button, retake option, and video input device selection.
   - `AvatarCropEditor.tsx`: Canvas-based aspect-ratio cropper enabling zoom, pan, and rotation to generate a cropped profile avatar file payload.
   - `AvatarWithFallback.tsx`: Reusable avatar UI displaying thumbnail/url image if `status === "APPROVED"` or fallback initials badge with pending indicator if under review.

3. **Page & Route**:
   - `frontend/src/features/photo-management/pages/PhotoApprovalQueuePage.tsx`:
     - Route `/admin/photo-approvals` registered in `App.tsx` and protected by `ProtectedRoute` (gated to `ADMINISTRATOR` and `DIRECTOR`).
     - Includes summary stats (Pending, Approved, Rejected count), photo grid/table, uploader metadata, entity context (Resident name / Visitor / Lot), side-by-side full resolution viewer, approve button, and reject dialog prompt.
   - `Navbar.tsx`: Display badge count next to "Aprovações de Fotos" for Admin/Director roles.

4. **i18n Locale Keys**:
   - Portuguese (`pt.json`) and English (`en.json`) keys under `photos.*` namespace covering upload labels, webcam controls, crop instructions, status badges (`PENDING_APPROVAL` = "Aguardando Aprovação", `APPROVED` = "Aprovada", `REJECTED` = "Rejeitada"), rejection modal, and notification messages.

---

## Expected Results

- [ ] Data model `MediaAsset` defined in `backend/app/models/media_asset.py` with foreign keys, indexes, and enums (`EntityType`, `StorageProvider`, `PhotoApprovalStatus`).
- [ ] Alembic migration `0011_add_media_asset_table.py` created and successfully executable on PostgreSQL database.
- [ ] Modular storage service `backend/app/services/storage_service.py` implemented with `LocalStorageProvider` and abstract cloud provider signatures.
- [ ] Backend validation enforcing max file size of 5MB and allowed MIME types (`image/jpeg`, `image/png`, `image/webp`), raising typed `PhotoFileTooLargeError` or `InvalidPhotoFormatError`.
- [ ] Automated thumbnail generation producing a 150x150 square thumbnail image alongside the original asset.
- [ ] Approval workflow logic implemented in `MediaService`: uploads by `RESIDENT` enter `PENDING_APPROVAL`, while uploads by Admin/Director/Manager enter `APPROVED` automatically.
- [ ] Backend API endpoints created under `/api/v1/uploads`:
  - `POST /api/v1/uploads/photo`
  - `GET /api/v1/uploads/photos/pending`
  - `PUT /api/v1/uploads/photos/{id}/approve`
  - `PUT /api/v1/uploads/photos/{id}/reject`
  - `DELETE /api/v1/uploads/photos/{id}`
  - `GET /api/v1/uploads/photos/{id}`
- [ ] Frontend reusable components created: `PhotoUploadModal`, `WebcamCaptureDialog`, `AvatarCropEditor`, `AvatarWithFallback`.
- [ ] Admin photo approval queue page built at `/admin/photo-approvals` (`PhotoApprovalQueuePage.tsx`) with filter tabs, image zoom modal, approve action, and rejection reason input modal.
- [ ] Navbar badge indicator added for pending photo approval queue count for `ADMINISTRATOR` and `DIRECTOR` roles.
- [ ] Internationalization translation keys added to `pt.json` and `en.json` under `photos.*`.
- [ ] Pytest test suite `backend/tests/test_photo_uploads.py` passing with ≥ 90% code coverage.
- [ ] Vitest test suite `frontend/src/features/photo-management/__tests__/` passing with 100% pass rate and ≥ 75% code coverage.

## Out of Scope

- Direct facial vector template extraction and access control barrier hardware sync (covered in T005).
- Direct photo gallery carousels for announcement blog feed (covered in T006).
