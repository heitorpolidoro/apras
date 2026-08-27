# T006 — Blog/Feed de Comunicados e Notícias

## Scope

This task implements the Announcement Feed module ("Blog/Feed de Comunicados e Notícias") for APRAS: an Instagram-style news feed where Administrators and Directors publish HOA announcements with image/PDF carousels, and all authenticated users can browse the feed, comment, and have their reads tracked via read receipts.

### In Scope

1. **Database Schema & SQLModels** (`backend/app/models/announcement.py`):
   - `Announcement`: `id` (UUID PK), `title` (str, indexed), `content` (str, long text body), `author_id` (UUID FK -> `user.id`, not nullable), `is_deleted` (bool, default `False`, indexed, soft-delete flag), `created_at`, `updated_at`.
   - `AnnouncementMedia`: `id` (UUID PK), `announcement_id` (UUID FK -> `announcement.id` ON DELETE CASCADE, indexed), `media_type` (str enum `IMAGE`/`PDF`), `file_path` (str, on-disk relative path for deletion), `url` (str, public URL), `mime_type` (str), `file_size_bytes` (int), `order_index` (int, default 0), `created_at`.
   - `AnnouncementComment`: `id` (UUID PK), `announcement_id` (UUID FK -> `announcement.id` ON DELETE CASCADE, indexed), `user_id` (UUID FK -> `user.id` ON DELETE CASCADE, indexed), `content` (str), `created_at`. No soft-delete — `DELETE` removes the row permanently.
   - `AnnouncementReadReceipt`: `id` (UUID PK), `announcement_id` (UUID FK -> `announcement.id` ON DELETE CASCADE, indexed), `user_id` (UUID FK -> `user.id` ON DELETE CASCADE, indexed), `read_at` (datetime). Unique constraint on `(announcement_id, user_id)`.
   - New enum `AnnouncementMediaType(StrEnum)`: `IMAGE`, `PDF` — added to `backend/app/models/enums.py`.
   - Alembic migration `0013_add_announcement_tables.py` (`down_revision = "0012_add_access_control_tables"`) creating all four tables with FKs, indexes on `(announcement_id, created_at)` for media/comments, and the unique constraint on `announcement_read_receipt(announcement_id, user_id)`.

2. **RBAC & Security Rules** ("publisher role guards"):
   - Only `ADMINISTRATOR` or `DIRECTOR` ("publishers") may create, update, delete announcements, and upload/delete announcement media. Other roles attempting these actions receive `403 Forbidden`.
   - All authenticated users (including `RESIDENT`, `MANAGER`) may view the feed, view a single announcement, list comments, add comments, and mark an announcement as read.
   - `GUEST` may view the feed, view a single announcement, list comments, and mark as read, but **cannot** post comments (read-only role per project convention) — `403 Forbidden` on `POST .../comments`.
   - A comment may be deleted by its own author or by any `ADMINISTRATOR`/`DIRECTOR`; anyone else gets `403 Forbidden`.
   - `GET /api/v1/announcements/{id}/read-receipts` is restricted to `ADMINISTRATOR`/`DIRECTOR`.

3. **Media Upload Rules**:
   - Accepted MIME types: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`. Anything else raises `InvalidAnnouncementMediaFormatError` (`400`).
   - Max file size: 10MB. Larger files raise `AnnouncementMediaTooLargeError` (`400`).
   - This is a dedicated, independent upload path from the T004 `media_service`/`MediaAsset` pipeline (which is image-only and carries an approval workflow that does not apply here — publishers are already trusted). Files are stored via the existing `LocalStorageProvider` (`app/services/storage_service.py`), reused as-is.
   - `order_index` is assigned as `max(existing order_index for the announcement) + 1` (starting at 0) so the carousel renders in upload order.

4. **Backend REST API Endpoints under `/api/v1/announcements`**:
   - `GET /api/v1/announcements?skip=&limit=`: Paginated feed, newest first, excludes `is_deleted=True`. Each item includes `media: list[AnnouncementMediaRead]`, `comment_count: int`, and `is_read: bool` (whether the caller has a read receipt).
   - `GET /api/v1/announcements/{id}`: Single announcement detail, same shape as feed item plus `comments: list[AnnouncementCommentRead]`. `404` via `AnnouncementNotFoundError` if missing or soft-deleted.
   - `POST /api/v1/announcements`: Create (publishers only). Body: `title`, `content`. Sets `author_id = caller.id`. Returns `201`.
   - `PUT /api/v1/announcements/{id}`: Update `title`/`content` (publishers only). Returns updated detail.
   - `DELETE /api/v1/announcements/{id}`: Soft-delete (`is_deleted = True`) (publishers only). Returns `204`.
   - `POST /api/v1/announcements/{id}/media`: Multipart file upload attaching media to an announcement (publishers only). Returns `201` with `AnnouncementMediaRead`.
   - `DELETE /api/v1/announcements/{id}/media/{media_id}`: Deletes a media item + its stored file (publishers only). Returns `204`.
   - `GET /api/v1/announcements/{id}/comments`: Lists comments for an announcement ordered by `created_at` ascending.
   - `POST /api/v1/announcements/{id}/comments`: Adds a comment authored by the caller (`GUEST` forbidden). Returns `201`.
   - `DELETE /api/v1/announcements/comments/{comment_id}`: Deletes a comment (author or publisher only). Returns `204`.
   - `POST /api/v1/announcements/{id}/read`: Idempotently upserts a read receipt for the caller (`INSERT ... ON CONFLICT DO NOTHING` semantics implemented in Python via a pre-check). Returns `200` with `{"read_at": ...}` — calling twice never creates a duplicate row.
   - `GET /api/v1/announcements/{id}/read-receipts`: Lists `AnnouncementReadReceiptRead` (user id/name + `read_at`) for the announcement (publishers only).
   - Custom domain exceptions registered in `app/core/exceptions.py` and wired into `app/core/exception_handlers.py`: `AnnouncementNotFoundError` (404), `AnnouncementCommentNotFoundError` (404), `AnnouncementMediaNotFoundError` (404), `AnnouncementPermissionError` (403), `InvalidAnnouncementMediaFormatError` (400), `AnnouncementMediaTooLargeError` (400).

5. **Frontend UI & State Management** (`frontend/src/features/announcement-feed/`):
   - Route `/announcements` (`AnnouncementFeedPage.tsx`) protected by `ProtectedRoute`, registered in `App.tsx`.
   - Navigation link added to `Navbar.tsx` ("Comunicados" / `nav.announcements`) visible to all authenticated roles.
   - Components: `AnnouncementFeedPage.tsx` (vertical Instagram-style feed, newest first, "Novo Comunicado" button gated to Admin/Director), `AnnouncementCard.tsx` (author, date, title, content, embeds `MediaCarousel`, comment count, read indicator, marks as read on mount/view), `MediaCarousel.tsx` (swipeable/paged carousel rendering images inline and PDFs as a thumbnail/link that opens the file in a new tab), `AnnouncementFormModal.tsx` (create/edit form + media upload input, gated to Admin/Director), `CommentThread.tsx` (list of comments + add-comment form, input hidden for `GUEST`, delete button shown only to comment author or Admin/Director).
   - `frontend/src/types/announcement.ts`: `Announcement`, `AnnouncementDetail`, `AnnouncementMedia`, `AnnouncementComment`, `AnnouncementReadReceipt`, `AnnouncementCreatePayload`, `AnnouncementUpdatePayload`, `CommentCreatePayload`, `PaginatedAnnouncementsResponse`.
   - `frontend/src/api/announcements.ts`: Axios client functions for all endpoints above.
   - `frontend/src/features/announcement-feed/hooks/useAnnouncements.ts`: TanStack Query hooks (`useAnnouncements`, `useAnnouncementDetail`, `useCreateAnnouncement`, `useUpdateAnnouncement`, `useDeleteAnnouncement`, `useUploadAnnouncementMedia`, `useDeleteAnnouncementMedia`, `useAnnouncementComments`, `useAddComment`, `useDeleteComment`, `useMarkAnnouncementRead`).
   - i18n keys under `announcements.*` namespace in `pt.json` and `en.json`, plus `nav.announcements`.

6. **Testing & Quality Assurance**:
   - `backend/tests/test_announcements.py`: model/migration sanity, RBAC on create/update/delete/media (publisher-only), comment RBAC (guest blocked, author/publisher can delete), read-receipt idempotency (no duplicate on second call), feed pagination/ordering/exclusion of soft-deleted items, media MIME/size validation. Target ≥ 90% backend coverage (CI gate).
   - `frontend/src/features/announcement-feed/__tests__/`: feed rendering, carousel rendering for image vs PDF media, form modal gated by role, comment thread hides input for guest, read receipt call on view. Target ≥ 75% frontend coverage (CI gate).

---

## Approach

### Data Layer

`backend/app/models/announcement.py`:
```python
import uuid
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint
from app.models.enums import AnnouncementMediaType


class Announcement(SQLModel, table=True):
    __tablename__ = "announcement"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(nullable=False, index=True)
    content: str = Field(nullable=False)
    author_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    is_deleted: bool = Field(default=False, nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class AnnouncementMedia(SQLModel, table=True):
    __tablename__ = "announcement_media"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    announcement_id: uuid.UUID = Field(
        foreign_key="announcement.id", ondelete="CASCADE", nullable=False, index=True
    )
    media_type: AnnouncementMediaType = Field(nullable=False)
    file_path: str = Field(nullable=False)
    url: str = Field(nullable=False)
    mime_type: str = Field(nullable=False)
    file_size_bytes: int = Field(nullable=False)
    order_index: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class AnnouncementComment(SQLModel, table=True):
    __tablename__ = "announcement_comment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    announcement_id: uuid.UUID = Field(
        foreign_key="announcement.id", ondelete="CASCADE", nullable=False, index=True
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
    content: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class AnnouncementReadReceipt(SQLModel, table=True):
    __tablename__ = "announcement_read_receipt"
    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_read_receipt_user"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    announcement_id: uuid.UUID = Field(
        foreign_key="announcement.id", ondelete="CASCADE", nullable=False, index=True
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
    read_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
```

`backend/app/schemas/announcement.py`:
- `AnnouncementCreate`: `title: str`, `content: str`.
- `AnnouncementUpdate`: `title: str | None = None`, `content: str | None = None`.
- `AnnouncementMediaRead`: `id`, `announcement_id`, `media_type`, `url`, `mime_type`, `file_size_bytes`, `order_index`, `created_at`.
- `AnnouncementCommentRead`: `id`, `announcement_id`, `user_id`, `author_name`, `content`, `created_at`.
- `AnnouncementCommentCreate`: `content: str`.
- `AnnouncementReadReceiptRead`: `user_id`, `user_name`, `read_at`.
- `AnnouncementRead`: `id`, `title`, `content`, `author_id`, `author_name`, `media: list[AnnouncementMediaRead]`, `comment_count: int`, `is_read: bool`, `created_at`, `updated_at`.
- `AnnouncementDetailRead`: extends `AnnouncementRead` with `comments: list[AnnouncementCommentRead]`.
- `PaginatedAnnouncementRead`: `items: list[AnnouncementRead]`, `total: int`, `skip: int`, `limit: int`.

### Service Layer (`backend/app/services/announcement_service.py`)

- `_assert_publisher(user)`: raises `AnnouncementPermissionError` unless role in `{ADMINISTRATOR, DIRECTOR}`.
- `list_announcements(session, user, skip, limit) -> PaginatedAnnouncementRead`: query non-deleted announcements ordered by `created_at desc`, attach media/comment_count/is_read per item.
- `get_announcement(session, user, id) -> AnnouncementDetailRead`: fetch or raise `AnnouncementNotFoundError`; include comments.
- `create_announcement(session, user, data) -> AnnouncementRead`: `_assert_publisher`; persist with `author_id=user.id`.
- `update_announcement(session, user, id, data) -> AnnouncementRead`: `_assert_publisher`; patch fields + `updated_at`.
- `delete_announcement(session, user, id) -> None`: `_assert_publisher`; set `is_deleted=True`.
- `upload_media(session, user, id, file_bytes, filename, mime_type) -> AnnouncementMediaRead`: `_assert_publisher`; validate mime/size; save via `LocalStorageProvider`; compute next `order_index`; persist.
- `delete_media(session, user, announcement_id, media_id) -> None`: `_assert_publisher`; delete file via storage provider; delete row.
- `list_comments(session, id) -> list[AnnouncementCommentRead]`: ordered `created_at asc`.
- `add_comment(session, user, id, data) -> AnnouncementCommentRead`: raise `AnnouncementPermissionError` if `user.role == GUEST`; persist.
- `delete_comment(session, user, comment_id) -> None`: fetch comment or raise `AnnouncementCommentNotFoundError`; allow if `comment.user_id == user.id` or publisher, else `AnnouncementPermissionError`.
- `mark_read(session, user, id) -> datetime`: fetch existing receipt for `(id, user.id)`; if present return existing `read_at`; else insert new receipt and return its `read_at`. No duplicate insert on repeat calls.
- `list_read_receipts(session, user, id) -> list[AnnouncementReadReceiptRead]`: `_assert_publisher`.

### Endpoint Layer (`backend/app/api/v1/endpoints/announcements.py`)

Mirrors the method signatures/status codes described in "Backend REST API Endpoints" above, following the same `Depends(get_db)` / `Depends(get_current_active_user)` pattern used in `occurrences.py`/`documents.py`. Register router in `app/api/v1/api.py` with `prefix="/announcements"`.

### Database Migration

`backend/alembic/versions/0013_add_announcement_tables.py`, `down_revision = "0012_add_access_control_tables"`, creating `announcement`, `announcement_media`, `announcement_comment`, `announcement_read_receipt` with FKs, indexes, and the read-receipt unique constraint; downgrade drops all four tables in reverse FK order.

### Frontend Layer

As described in "Frontend UI & State Management" above. `MediaCarousel` renders `<img>` for `media_type === "IMAGE"` and a PDF icon/thumbnail link (`target="_blank"`) for `media_type === "PDF"`. `AnnouncementCard` calls `useMarkAnnouncementRead` once per mount via `useEffect`.

---

## Expected Results

- [ ] Alembic migration `0013_add_announcement_tables` cleanly creates `announcement`, `announcement_media`, `announcement_comment`, `announcement_read_receipt` tables with FKs, indexes, and a unique constraint on `(announcement_id, user_id)`.
- [ ] SQLModel entities `Announcement`, `AnnouncementMedia`, `AnnouncementComment`, `AnnouncementReadReceipt` implement the fields/constraints specified above.
- [ ] `POST /api/v1/announcements` succeeds (`201`) for `ADMINISTRATOR`/`DIRECTOR` and returns `403` for `RESIDENT`/`MANAGER`/`GUEST`.
- [ ] `PUT /api/v1/announcements/{id}` and `DELETE /api/v1/announcements/{id}` are restricted to `ADMINISTRATOR`/`DIRECTOR` (`403` otherwise); `DELETE` sets `is_deleted=True` rather than removing the row.
- [ ] `GET /api/v1/announcements` returns a paginated, newest-first feed that excludes soft-deleted announcements and includes `media`, `comment_count`, and `is_read` per item.
- [ ] `POST /api/v1/announcements/{id}/media` accepts `image/jpeg`, `image/png`, `image/webp`, and `application/pdf`, rejects other MIME types with `400`, and rejects files over 10MB with `400`; restricted to publishers (`403` otherwise).
- [ ] `DELETE /api/v1/announcements/{id}/media/{media_id}` removes the media row and its stored file; restricted to publishers.
- [ ] `POST /api/v1/announcements/{id}/comments` succeeds for `RESIDENT`/`MANAGER`/`ADMINISTRATOR`/`DIRECTOR` and returns `403` for `GUEST`.
- [ ] `DELETE /api/v1/announcements/comments/{comment_id}` succeeds for the comment's author or a publisher, and returns `403` for any other user.
- [ ] `POST /api/v1/announcements/{id}/read` creates exactly one `AnnouncementReadReceipt` row per `(announcement, user)` pair even when called multiple times.
- [ ] `GET /api/v1/announcements/{id}/read-receipts` is restricted to publishers and lists all users who read the announcement.
- [ ] Frontend route `/announcements` renders `AnnouncementFeedPage` under `ProtectedRoute`; a "Comunicados" link is visible in `Navbar` for all authenticated roles.
- [ ] `AnnouncementCard`/`MediaCarousel` render image media inline and PDF media as a distinct openable element.
- [ ] `AnnouncementFormModal` create/edit controls render only for `ADMINISTRATOR`/`DIRECTOR`.
- [ ] `CommentThread` hides the comment-input form for the `GUEST` role and shows a delete control only to the comment's author or a publisher.
- [ ] i18n key dictionaries under `announcements.*` (and `nav.announcements`) are fully populated in `pt.json` and `en.json`.
- [ ] `backend/tests/test_announcements.py` passes with ≥ 90% backend code coverage.
- [ ] Vitest suite under `frontend/src/features/announcement-feed/__tests__/` passes with ≥ 75% frontend code coverage.

---

## Out of Scope

- Push notifications, email digests, or any external notification channel for new announcements (see the separate `whatsapp-integration` backlog item for a related but distinct channel).
- Rich text/WYSIWYG editing of announcement content (plain text body only).
- Scheduled/future-dated publishing and draft states (announcements are published immediately on creation).
- Likes/reactions or comment threading/replies (flat comment list only).
- Reusing or modifying the T004 `MediaAsset`/photo-approval pipeline — announcement media uses its own dedicated, unmoderated upload path since publishers are already trusted.
