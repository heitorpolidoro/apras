</Meridian Spec Generator — Task Spec Author>
<T009 — Central de Documentos e Arquivos da Associação>

## Scope

This task implements the Document Repository module ("Central de Documentos e Arquivos da Associação") for APRAS, providing a structured, role-gated, hierarchical digital repository for legal, financial, administrative, and operational HOA files with PDF inline preview, version history tracking, metadata search, and download logging.

### In Scope
1. **Database Schema & SQLModels**:
   - SQLModel entity `DocumentFolder`: Hierarchical folder tree with `id` (UUID PK), `name` (str), `description` (str | None), `parent_id` (UUID | None FK -> `document_folder.id` ON DELETE CASCADE), `allowed_roles_json` (str, JSON array of allowed role strings e.g. `["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]`), `created_at`, and `updated_at`.
   - SQLModel entity `AssociationDocument`: Document item record with `id` (UUID PK), `folder_id` (UUID FK -> `document_folder.id` ON DELETE CASCADE), `title` (str), `description` (str | None), `file_url` (str), `file_size_bytes` (int), `mime_type` (str e.g. `"application/pdf"`), `version_number` (int, default 1), `previous_version_id` (UUID | None FK -> `association_document.id` ON DELETE SET NULL), `publication_year` (int | None), `publication_month` (int | None), `tags_json` (str | None, JSON array of tags e.g. `["balancete", "2026"]`), `uploaded_by_id` (UUID FK -> `user.id`), `created_at`, and `updated_at`.
   - SQLModel entity `DocumentDownloadLog`: Download audit trail recording `id` (UUID PK), `document_id` (UUID FK -> `association_document.id` ON DELETE CASCADE), `user_id` (UUID FK -> `user.id` ON DELETE CASCADE), and `downloaded_at` (datetime).
   - Alembic DDL migration script creating `document_folder`, `association_document`, and `document_download_log` tables with foreign keys, indexes on `(folder_id, created_at)`, `(publication_year, publication_month)`, and unique constraints.

2. **RBAC & Security Rules**:
   - Folder visibility filtering: Folders (and their contained documents) are accessible only if the user's role is included in `allowed_roles_json` (or if caller is `ADMINISTRATOR` or `DIRECTOR`).
   - Standard roles (`RESIDENT`, `MANAGER`) can list accessible folders, query/filter documents, preview PDFs inline, and download files.
   - Management roles (`ADMINISTRATOR`, `DIRECTOR`) have full CRUD access to create/update/delete folders, upload new documents, create document versions, and delete documents.

3. **Document Versioning**:
   - Endpoint `POST /api/v1/documents/{id}/versions` enables uploading a new version of an existing document.
   - Automatically increments `version_number` (`previous.version_number + 1`), links `previous_version_id = previous.id`, inherits or updates metadata, and preserves full document version ancestry chain.

4. **Backend REST API Endpoints under `/api/v1/documents`**:
   - `GET /api/v1/documents/folders`: Retrieve nested folder hierarchy tree filtered by current user's role.
   - `POST /api/v1/documents/folders`: Create folder (Admin / Director only).
   - `PUT /api/v1/documents/folders/{id}`: Update folder name, description, or allowed roles (Admin / Director only).
   - `DELETE /api/v1/documents/folders/{id}`: Delete folder and recursively cascade contained subfolders & documents (Admin / Director only).
   - `GET /api/v1/documents`: Search and list documents across accessible folders (filter by `folder_id`, `tag`, `publication_year`, `publication_month`, or text query).
   - `POST /api/v1/documents`: Upload new document into a folder (Admin / Director only).
   - `POST /api/v1/documents/{id}/versions`: Upload new version linked to existing document (Admin / Director only).
   - `POST /api/v1/documents/{id}/download`: Record download event in `DocumentDownloadLog` and return stream/download target URL.
   - `DELETE /api/v1/documents/{id}`: Delete document record (Admin / Director only).
   - Custom domain exceptions (`DocumentFolderNotFoundError`, `DocumentNotFoundError`, `FolderAccessDeniedError`, `InvalidFolderHierarchyError`) registered in FastAPI global exception handlers.

5. **Frontend UI & State Management**:
   - Route `/documents` (`DocumentCenterPage.tsx`) protected by `ProtectedRoute`.
   - Navigation link added to `Navbar.tsx` ("Documentos").
   - React components: `FolderTreeSidebar`, `DocumentGridTable`, `PDFViewerModal`, `DocumentUploadModal`, `FolderFormModal`.
   - TypeScript definitions (`src/types/document.ts`), API client module (`src/api/documents.ts`), and custom TanStack Query hooks (`src/hooks/useDocuments.ts`).
   - Internationalization translation keys in `pt.json` and `en.json`.

6. **Testing & Quality Assurance**:
   - Pytest test suite (`backend/tests/test_documents.py`) verifying database schemas, folder nesting recursion, RBAC role filtering, versioning increment logic, download logging, and endpoint contracts (≥ 90% backend coverage).
   - Vitest test suite (`frontend/src/features/document-management/__tests__/`) verifying folder tree rendering, document filtering by tag/year, PDF preview modal, upload modal forms, and RBAC button gating (≥ 75% frontend coverage).

---

## Approach

### Data Layer (`backend/app/models/` & `backend/app/schemas/`)

1. **SQLModel Entities (`backend/app/models/document.py`)**:
   ```python
   import uuid
   from datetime import datetime
   from sqlmodel import Field, Relationship, SQLModel

   class DocumentFolder(SQLModel, table=True):
       __tablename__ = "document_folder"

       id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
       name: str = Field(nullable=False, index=True)
       description: str | None = Field(default=None, nullable=True)
       parent_id: uuid.UUID | None = Field(
           default=None,
           foreign_key="document_folder.id",
           ondelete="CASCADE",
           nullable=True,
           index=True,
       )
       allowed_roles_json: str = Field(
           default='["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]',
           nullable=False,
       )
       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

       # Relationships
       parent_folder: "DocumentFolder | None" = Relationship(
           sa_relationship_kwargs={"remote_side": "DocumentFolder.id"}
       )
       subfolders: list["DocumentFolder"] = Relationship(
           back_populates="parent_folder",
           sa_relationship_kwargs={"cascade": "all, delete-orphan"},
       )
       documents: list["AssociationDocument"] = Relationship(
           back_populates="folder",
           sa_relationship_kwargs={"cascade": "all, delete-orphan"},
       )

   class AssociationDocument(SQLModel, table=True):
       __tablename__ = "association_document"

       id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
       folder_id: uuid.UUID = Field(
           foreign_key="document_folder.id",
           ondelete="CASCADE",
           nullable=False,
           index=True,
       )
       title: str = Field(nullable=False, index=True)
       description: str | None = Field(default=None, nullable=True)
       file_url: str = Field(nullable=False)
       file_size_bytes: int = Field(nullable=False)
       mime_type: str = Field(default="application/pdf", nullable=False)
       version_number: int = Field(default=1, nullable=False)
       previous_version_id: uuid.UUID | None = Field(
           default=None,
           foreign_key="association_document.id",
           ondelete="SET NULL",
           nullable=True,
           index=True,
       )
       publication_year: int | None = Field(default=None, nullable=True, index=True)
       publication_month: int | None = Field(default=None, nullable=True, index=True)
       tags_json: str | None = Field(default=None, nullable=True)
       uploaded_by_id: uuid.UUID = Field(
           foreign_key="user.id",
           nullable=False,
           index=True,
       )
       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

       # Relationships
       folder: DocumentFolder = Relationship(back_populates="documents")
       uploaded_by: "User" = Relationship()
       previous_version: "AssociationDocument | None" = Relationship(
           sa_relationship_kwargs={"remote_side": "AssociationDocument.id"}
       )
       download_logs: list["DocumentDownloadLog"] = Relationship(
           back_populates="document",
           sa_relationship_kwargs={"cascade": "all, delete-orphan"},
       )

   class DocumentDownloadLog(SQLModel, table=True):
       __tablename__ = "document_download_log"

       id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
       document_id: uuid.UUID = Field(
           foreign_key="association_document.id",
           ondelete="CASCADE",
           nullable=False,
           index=True,
       )
       user_id: uuid.UUID = Field(
           foreign_key="user.id",
           ondelete="CASCADE",
           nullable=False,
           index=True,
       )
       downloaded_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

       # Relationships
       document: AssociationDocument = Relationship(back_populates="download_logs")
       user: "User" = Relationship()
   ```

2. **Pydantic Schemas (`backend/app/schemas/document.py`)**:
   - `DocumentFolderCreate`: `name: str`, `description: str | None = None`, `parent_id: UUID | None = None`, `allowed_roles: list[str] = ["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]`.
   - `DocumentFolderUpdate`: `name: str | None = None`, `description: str | None = None`, `parent_id: UUID | None = None`, `allowed_roles: list[str] | None = None`.
   - `DocumentFolderRead`: `id: UUID`, `name: str`, `description: str | None`, `parent_id: UUID | None`, `allowed_roles: list[str]`, `document_count: int = 0`, `created_at: datetime`, `updated_at: datetime`.
   - `DocumentFolderTreeRead`: Inherits `DocumentFolderRead` and adds `children: list["DocumentFolderTreeRead"] = []`.
   - `AssociationDocumentCreate`: `folder_id: UUID`, `title: str`, `description: str | None = None`, `file_url: str`, `file_size_bytes: int`, `mime_type: str = "application/pdf"`, `publication_year: int | None = None`, `publication_month: int | None = None`, `tags: list[str] | None = None`.
   - `AssociationDocumentVersionCreate`: `title: str | None = None`, `description: str | None = None`, `file_url: str`, `file_size_bytes: int`, `mime_type: str = "application/pdf"`, `tags: list[str] | None = None`.
   - `AssociationDocumentRead`: `id: UUID`, `folder_id: UUID`, `folder_name: str | None`, `title: str`, `description: str | None`, `file_url: str`, `file_size_bytes: int`, `mime_type: str`, `version_number: int`, `previous_version_id: UUID | None`, `publication_year: int | None`, `publication_month: int | None`, `tags: list[str]`, `uploaded_by_id: UUID`, `uploader_name: str | None`, `created_at: datetime`, `updated_at: datetime`.
   - `DocumentDownloadLogRead`: `id: UUID`, `document_id: UUID`, `user_id: UUID`, `user_name: str | None`, `downloaded_at: datetime`.
   - `PaginatedDocumentRead`: `items: list[AssociationDocumentRead]`, `total: int`, `skip: int`, `limit: int`.

---

### Service Layer (`backend/app/services/document_service.py`)

- `get_accessible_folder_ids(session: Session, user: User) -> set[UUID]`:
  - Queries all `DocumentFolder` records.
  - Determines user role string (e.g. `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, or `"RESIDENT"` for users linked to lot/resident profiles).
  - Admins and Directors automatically access all folders. For other roles, parses `allowed_roles_json` and includes folder IDs where the user's role is present.
- `get_folder_tree(session: Session, user: User) -> list[DocumentFolderTreeRead]`:
  - Fetches accessible folders and constructs hierarchical tree array with top-level root folders (`parent_id is None`) containing nested `children`.
- `create_folder(session: Session, user: User, folder_in: DocumentFolderCreate) -> DocumentFolderRead`:
  - Checks if user role is `ADMINISTRATOR` or `DIRECTOR` (raises `ForbiddenError` otherwise).
  - Validates `parent_id` if provided (raises `DocumentFolderNotFoundError` if parent doesn't exist). Prevents self-referential or cyclic folder hierarchies.
  - Serializes `allowed_roles` to `allowed_roles_json` string and saves entity.
- `update_folder(session: Session, user: User, folder_id: UUID, folder_in: DocumentFolderUpdate) -> DocumentFolderRead`:
  - Enforces `ADMINISTRATOR` or `DIRECTOR` role guard. Updates fields and `updated_at`.
- `delete_folder(session: Session, user: User, folder_id: UUID) -> None`:
  - Enforces `ADMINISTRATOR` or `DIRECTOR` role guard. Deletes folder entity (cascade handles subfolders and documents).
- `get_documents(session: Session, user: User, folder_id: UUID | None, tag: str | None, year: int | None, month: int | None, search: str | None, skip: int, limit: int)`:
  - Fetches set of accessible folder IDs. If `folder_id` is passed, verifies it is in accessible set (raises `FolderAccessDeniedError` / `403 Forbidden` if disallowed).
  - Queries `AssociationDocument` filtering by accessible folder IDs, optional `tag` matching in `tags_json`, `publication_year`, `publication_month`, and text ILIKE query against `title` / `description`.
  - Deserializes `tags_json` into `tags: list[str]`.
- `create_document(session: Session, user: User, doc_in: AssociationDocumentCreate) -> AssociationDocumentRead`:
  - Enforces `ADMINISTRATOR` or `DIRECTOR` role guard.
  - Verifies target `folder_id` exists. Sets `uploaded_by_id = user.id`, `version_number = 1`, serializes `tags` to `tags_json`.
- `create_document_version(session: Session, user: User, doc_id: UUID, version_in: AssociationDocumentVersionCreate) -> AssociationDocumentRead`:
  - Enforces `ADMINISTRATOR` or `DIRECTOR` role guard.
  - Fetches previous `AssociationDocument` by `doc_id`.
  - Creates new `AssociationDocument` with `folder_id = previous.folder_id`, `version_number = previous.version_number + 1`, `previous_version_id = previous.id`, and updated file URL / metadata.
- `log_download(session: Session, user: User, doc_id: UUID) -> str`:
  - Verifies document exists and belongs to an accessible folder for the user.
  - Inserts `DocumentDownloadLog(document_id=doc_id, user_id=user.id, downloaded_at=utcnow())`.
  - Returns `file_url` for immediate client streaming/downloading.
- `delete_document(session: Session, user: User, doc_id: UUID) -> None`:
  - Enforces `ADMINISTRATOR` or `DIRECTOR` role guard. Deletes document record.

---

### Endpoint & Security Layer (`backend/app/api/v1/endpoints/documents.py`)

- `GET /api/v1/documents/folders`: Returns `list[DocumentFolderTreeRead]` accessible to caller.
- `POST /api/v1/documents/folders`: Returns `201 Created` with `DocumentFolderRead`.
- `PUT /api/v1/documents/folders/{id}`: Returns updated `DocumentFolderRead`.
- `DELETE /api/v1/documents/folders/{id}`: Returns `204 No Content`.
- `GET /api/v1/documents`: Returns `PaginatedDocumentRead`.
- `POST /api/v1/documents`: Returns `201 Created` with `AssociationDocumentRead`.
- `POST /api/v1/documents/{id}/versions`: Returns `201 Created` with `AssociationDocumentRead`.
- `POST /api/v1/documents/{id}/download`: Returns `{"file_url": doc.file_url}` after creating download log.
- `DELETE /api/v1/documents/{id}`: Returns `204 No Content`.

---

### Database Migration

- Alembic revision script creating `document_folder`, `association_document`, and `document_download_log` tables with composite indexes on `(folder_id, created_at)` and `(publication_year, publication_month)` and foreign keys (`ON DELETE CASCADE` / `ON DELETE SET NULL`).

---

### Frontend Layer (`frontend/src/features/document-management/`)

1. **Types & API Client**:
   - `frontend/src/types/document.ts`: Interfaces (`DocumentFolder`, `DocumentFolderTree`, `AssociationDocument`, `DocumentDownloadLog`, `DocumentFolderCreate`, `DocumentFolderUpdate`, `AssociationDocumentCreate`, `AssociationDocumentVersionCreate`).
   - `frontend/src/api/documents.ts`: Axios client functions for `/api/v1/documents` endpoints.
   - `frontend/src/hooks/useDocuments.ts`: TanStack Query hooks (`useDocumentFolders`, `useDocuments`, `useCreateFolder`, `useUpdateFolder`, `useDeleteFolder`, `useUploadDocument`, `useCreateDocumentVersion`, `useDownloadDocument`, `useDeleteDocument`).

2. **Components**:
   - `DocumentCenterPage.tsx`: Container layout featuring title header, global document search bar, filter dropdowns (year, month, tag), "Nova Pasta" / "Novo Documento" action buttons (gated for Admin/Director), sidebar folder tree, document table grid, and modal preview handlers.
   - `FolderTreeSidebar.tsx`: Tree view of nested folders with collapsible nodes, active folder selection indicator, folder creation/edit trigger icons for managers, and item counter badges.
   - `DocumentGridTable.tsx`: Table listing documents within selected folder/search scope with columns for Title, Folder, Version badge, Size, Date/Year, Tags, and Action buttons (Inline PDF Preview, Version History, Download, Delete).
   - `PDFViewerModal.tsx`: Dialog rendering PDF document inline using `<iframe>` or HTML canvas previewer with full-screen toggle and download trigger button.
   - `DocumentUploadModal.tsx`: Dialog form for uploading new documents or new versions with file URL input, title, description, folder selector, publication year/month, and tag pills.
   - `FolderFormModal.tsx`: Dialog form to create or edit folder name, description, parent folder selection, and role permissions checkboxes (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `RESIDENT`).

3. **Navigation & Routing**:
   - Register route `/documents` (`DocumentCenterPage.tsx`) in `frontend/src/App.tsx`.
   - Add navigation link in `frontend/src/features/user-administration/components/Navbar.tsx` ("Documentos").

4. **Internationalization (i18n)**:
   - Add translation key dictionaries under `documents.*` namespace in `pt.json` and `en.json`.

---

## Expected Results

- [ ] Alembic migration cleanly creates `document_folder`, `association_document`, and `document_download_log` tables with foreign keys and indexes.
- [ ] SQLModel entities `DocumentFolder`, `AssociationDocument`, and `DocumentDownloadLog` accurately implement fields, FK constraints, and relationships.
- [ ] `GET /api/v1/documents/folders` returns a nested folder tree structure filtered by caller's effective role.
- [ ] `POST /api/v1/documents/folders` allows Administrators and Directors to create root or nested folders with custom `allowed_roles_json`.
- [ ] Non-admin/director users attempting folder CRUD or document deletion receive `403 Forbidden`.
- [ ] `GET /api/v1/documents` lists documents matching folder, tag, year/month, or text search criteria while strictly filtering out disallowed folders.
- [ ] `POST /api/v1/documents` uploads document metadata and file URL into specified folder.
- [ ] `POST /api/v1/documents/{id}/versions` creates a new document version linked to `previous_version_id` with incremented `version_number`.
- [ ] `POST /api/v1/documents/{id}/download` logs user download event in `DocumentDownloadLog` table and returns file download target URL.
- [ ] Frontend route `/documents` renders `DocumentCenterPage` with `FolderTreeSidebar` and `DocumentGridTable` under `ProtectedRoute`.
- [ ] `PDFViewerModal` previews PDF files inline inside modal dialog with download trigger.
- [ ] `DocumentUploadModal` and `FolderFormModal` enable full CRUD workflows for administrative roles.
- [ ] i18n key dictionaries for document management are fully populated in `pt.json` and `en.json`.
- [ ] Pytest test suite in `backend/tests/test_documents.py` passes with ≥ 90% code coverage.
- [ ] Vitest test suite in `frontend/src/features/document-management/__tests__/` passes with ≥ 75% code coverage.

---

## Out of Scope

- Direct cloud storage binary chunk uploading to S3 or Azure Blob (uses file URL reference string; file storage provider abstraction handled in T004).
- OCR text extraction from PDF content for full-text search (uses title/description/tags metadata search).
- Electronic signatures and digital signing workflows (future module).
