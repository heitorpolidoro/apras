</Meridian Spec Generator — Task Spec Author>
<T010 — Livro de Ocorrências e Atendimento de Reclamações>

## Scope

This task implements the digital Occurrence Book and Complaints Management module ("Livro de Ocorrências e Atendimento de Reclamações") for APRAS, providing residents and administrators with a structured protocol-driven ticket system to report, track, assign, and resolve community complaints, maintenance incidents, rule infractions, and operational issues.

### In Scope
1. **Database Schema & Models**:
   - SQLModel entity `Occurrence` with protocol auto-generation, lot reference, reporter identity, anonymity toggle, public visibility toggle, category, status, priority, photo attachment links, assignee, resolution notes, and timestamps.
   - SQLModel entity `OccurrenceTimeline` with status change audit logs, note content, internal-only visibility toggle, actor reference, and timestamp.
   - Domain enumerations `OccurrenceCategory` (`NOISE`, `MAINTENANCE`, `SECURITY`, `PARKING`, `RULES_VIOLATION`, `OTHER`), `OccurrenceStatus` (`OPEN`, `UNDER_REVIEW`, `IN_PROGRESS`, `RESOLVED`, `REJECTED`), and `OccurrencePriority` (`LOW`, `MEDIUM`, `HIGH`, `URGENT`).
   - Alembic DDL migration script generating `occurrence` and `occurrence_timeline` tables with appropriate foreign keys (`ON DELETE SET NULL` for references, `ON DELETE CASCADE` for timeline notes), composite indices, and constraints.

2. **Protocol Generation Service**:
   - Sequential sequence generator producing formatted protocol strings `OCO-YYYY-XXXXXX` (e.g. `OCO-2026-000001`), resetting sequence counters per calendar year with atomic database transaction safety.

3. **Visibility & Role-Based Access Control (RBAC)**:
   - **Private Occurrences (`is_public = False`)**: Visible exclusively to the ticket reporter, assigned staff (`assigned_to_id`), and system administrators (`ADMINISTRATOR` / `DIRECTOR`).
   - **Public Occurrences (`is_public = True`)**: Visible to all authenticated residents and management staff.
   - **Anonymous Occurrences (`is_anonymous = True`)**: Reporter identity (`reporter_user_id` and name) is stripped and replaced with `"Anônimo"` in API responses for non-admin users. Administrators and Directors retain full access to reporter identity for audit purposes.
   - **Internal Timeline Notes (`is_internal_only = True`)**: Visible exclusively to `ADMINISTRATOR` and `DIRECTOR` roles; filtered out from resident API responses.

4. **Backend API & Service Endpoints**:
   - `GET /api/v1/occurrences`: List occurrences with category, status, public visibility filters, and protocol/text search (enforcing RBAC rules).
   - `POST /api/v1/occurrences`: Create a new occurrence ticket with auto-generated protocol number and initial timeline log entry.
   - `GET /api/v1/occurrences/{id}`: Retrieve occurrence details along with timeline history logs.
   - `PUT /api/v1/occurrences/{id}/status`: Update occurrence status, priority, assigned user, and resolution notes (Admin, Director, or Assigned Manager).
   - `POST /api/v1/occurrences/{id}/timeline`: Append a timeline note or status transition log to an occurrence.
   - Domain exception classes (`OccurrenceNotFoundError`, `OccurrencePermissionError`, `InvalidStatusTransitionError`) registered in global FastAPI exception handlers.

5. **Frontend UI & State Management**:
   - Route `/occurrences` (`OccurrenceBookPage.tsx`) protected by `ProtectedRoute`.
   - Navigation link added in `Navbar.tsx` ("Livro de Ocorrências").
   - React components: `OccurrenceTable`, `NewOccurrenceModal`, `OccurrenceDetailsView`, `OccurrenceTimelineLog`.
   - TypeScript interfaces (`src/types/occurrence.ts`), API client module (`src/api/occurrences.ts`), and custom TanStack Query hooks (`src/hooks/useOccurrences.ts`).
   - i18n translation keys in `pt.json` and `en.json`.

6. **Testing & Quality Assurance**:
   - Pytest test suite (`backend/tests/test_occurrences.py`) testing schema validation, protocol sequence generation, visibility/RBAC rules, anonymity masking, timeline logging, and endpoint response contracts (≥ 90% backend coverage).
   - Vitest test suite (`frontend/src/features/occurrence-management/__tests__/`) testing page rendering, ticket creation modal, status updates, timeline rendering, and RBAC visibility (≥ 75% frontend coverage).

---

## Approach

### Data Layer (`backend/app/models/` & `backend/app/schemas/`)

1. **Domain Enums (`backend/app/models/enums.py`)**:
   ```python
   class OccurrenceCategory(StrEnum):
       NOISE = "NOISE"
       MAINTENANCE = "MAINTENANCE"
       SECURITY = "SECURITY"
       PARKING = "PARKING"
       RULES_VIOLATION = "RULES_VIOLATION"
       OTHER = "OTHER"

   class OccurrenceStatus(StrEnum):
       OPEN = "OPEN"
       UNDER_REVIEW = "UNDER_REVIEW"
       IN_PROGRESS = "IN_PROGRESS"
       RESOLVED = "RESOLVED"
       REJECTED = "REJECTED"

   class OccurrencePriority(StrEnum):
       LOW = "LOW"
       MEDIUM = "MEDIUM"
       HIGH = "HIGH"
       URGENT = "URGENT"
   ```

2. **SQLModel Entities (`backend/app/models/occurrence.py`)**:
   ```python
   class Occurrence(SQLModel, table=True):
       __tablename__ = "occurrence"

       id: UUID = Field(default_factory=uuid4, primary_key=True)
       protocol_number: str = Field(index=True, unique=True, nullable=False)
       lot_id: UUID | None = Field(default=None, foreign_key="lot.id", ondelete="SET NULL", nullable=True, index=True)
       reporter_user_id: UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True)
       is_anonymous: bool = Field(default=False, nullable=False)
       is_public: bool = Field(default=False, nullable=False)
       category: OccurrenceCategory = Field(nullable=False, index=True)
       title: str = Field(nullable=False)
       description: str = Field(nullable=False)
       photo_urls_json: str | None = Field(default=None, nullable=True)
       status: OccurrenceStatus = Field(default=OccurrenceStatus.OPEN, nullable=False, index=True)
       priority: OccurrencePriority = Field(default=OccurrencePriority.MEDIUM, nullable=False, index=True)
       assigned_to_id: UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True)
       resolution_notes: str | None = Field(default=None, nullable=True)
       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       resolved_at: datetime | None = Field(default=None, nullable=True)

       # Relationships
       lot: "Lot | None" = Relationship()
       reporter: "User | None" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Occurrence.reporter_user_id]"})
       assigned_to: "User | None" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Occurrence.assigned_to_id]"})
       timeline_entries: list["OccurrenceTimeline"] = Relationship(back_populates="occurrence", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

   class OccurrenceTimeline(SQLModel, table=True):
       __tablename__ = "occurrence_timeline"

       id: UUID = Field(default_factory=uuid4, primary_key=True)
       occurrence_id: UUID = Field(foreign_key="occurrence.id", ondelete="CASCADE", nullable=False, index=True)
       actor_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
       status_from: OccurrenceStatus | None = Field(default=None, nullable=True)
       status_to: OccurrenceStatus | None = Field(default=None, nullable=True)
       note: str = Field(nullable=False)
       is_internal_only: bool = Field(default=False, nullable=False)
       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

       # Relationships
       occurrence: "Occurrence" = Relationship(back_populates="timeline_entries")
       actor: "User" = Relationship()
   ```

3. **Pydantic Schemas (`backend/app/schemas/occurrence.py`)**:
   - `OccurrenceCreate`: `lot_id: UUID | None = None`, `is_anonymous: bool = False`, `is_public: bool = False`, `category: OccurrenceCategory`, `title: str`, `description: str`, `photo_urls: list[str] | None = None`.
   - `OccurrenceStatusUpdate`: `status: OccurrenceStatus | None = None`, `priority: OccurrencePriority | None = None`, `assigned_to_id: UUID | None = None`, `resolution_notes: str | None = None`.
   - `TimelineNoteCreate`: `note: str`, `is_internal_only: bool = False`, `status_to: OccurrenceStatus | None = None`.
   - `OccurrenceTimelineRead`: `id: UUID`, `occurrence_id: UUID`, `actor_id: UUID`, `actor_name: str | None`, `status_from: OccurrenceStatus | None`, `status_to: OccurrenceStatus | None`, `note: str`, `is_internal_only: bool`, `created_at: datetime`.
   - `OccurrenceRead`: `id`, `protocol_number`, `lot_id`, `lot_summary: str | None`, `reporter_user_id: UUID | None`, `reporter_name: str | None`, `is_anonymous`, `is_public`, `category`, `title`, `description`, `photo_urls: list[str]`, `status`, `priority`, `assigned_to_id`, `assigned_to_name: str | None`, `resolution_notes`, `created_at`, `updated_at`, `resolved_at`.
   - `OccurrenceDetailRead`: Inherits `OccurrenceRead` and appends `timeline: list[OccurrenceTimelineRead]`.
   - `PaginatedOccurrenceRead`: `items: list[OccurrenceRead]`, `total: int`, `skip: int`, `limit: int`.

---

### Protocol Sequence Generator (`backend/app/services/protocol_generator.py`)

- Method `generate_occurrence_protocol(session: Session) -> str`:
  1. Determines current UTC year `YYYY` (e.g. `2026`).
  2. Queries the database for maximum existing `protocol_number` matching `OCO-YYYY-%`.
  3. Extracts the trailing integer sequence `XXXXXX`, increments by `1` (or starts at `1` if none exist for the year), and formats as 6-digit zero-padded string (`OCO-2026-000001`).
  4. Wraps in atomic execution/retry block to prevent race conditions during concurrent creation calls.

---

### Service Layer (`backend/app/services/occurrence_service.py`)

- `get_occurrences(session, current_user, category, status, is_public, search, skip, limit)`:
  - Queries active occurrences based on RBAC & visibility rules:
    - If `current_user.role` in `[ADMINISTRATOR, DIRECTOR]`: returns all matching tickets.
    - If `current_user.role == MANAGER`: returns tickets assigned to `current_user.id`, created by `current_user.id`, or marked `is_public=True`.
    - Otherwise (standard resident): returns tickets where `reporter_user_id == current_user.id` OR `is_public=True`.
  - Applies filters (`category`, `status`, `is_public`) and protocol/title text search.
  - Sanitizes returned `OccurrenceRead` records: if `is_anonymous=True` and user is not Admin/Director, strips `reporter_user_id` and sets `reporter_name = "Anônimo"`.
- `create_occurrence(session, current_user, occurrence_in)`:
  - Generates protocol number using `generate_occurrence_protocol`.
  - Sets `reporter_user_id = current_user.id`. Converts `photo_urls` list to `photo_urls_json` string.
  - Inserts `Occurrence` record with default status `OPEN` and priority `MEDIUM` (or specified priority).
  - Automatically appends initial `OccurrenceTimeline` entry (`note="Ocorrência registrada no sistema"`, `actor_id=current_user.id`, `status_to=OPEN`).
- `get_occurrence_by_id(session, current_user, occurrence_id)`:
  - Fetches occurrence by ID. Enforces visibility check; raises `OccurrenceNotFoundError` (or `OccurrencePermissionError` / `403 Forbidden`) if caller lacks access.
  - Constructs `OccurrenceDetailRead`. Filters out timeline items with `is_internal_only=True` if caller is not Admin/Director.
- `update_occurrence_status(session, current_user, occurrence_id, update_in)`:
  - Restricted to Admin/Director or assigned user (`assigned_to_id == current_user.id`).
  - Updates fields (`status`, `priority`, `assigned_to_id`, `resolution_notes`).
  - If status transitions to `RESOLVED` or `REJECTED`, sets `resolved_at = datetime.utcnow()`.
  - Appends `OccurrenceTimeline` entry capturing `status_from`, `status_to`, optional resolution note, and `actor_id=current_user.id`.
- `add_timeline_note(session, current_user, occurrence_id, note_in)`:
  - Verifies caller has permission to access the ticket.
  - If caller is not Admin/Director, forces `is_internal_only = False`.
  - Inserts `OccurrenceTimeline` entry and updates `Occurrence.updated_at`.

---

### Endpoint & Security Layer (`backend/app/api/v1/endpoints/occurrences.py`)

- `GET /api/v1/occurrences`: Auth required (`get_current_user`). Returns `PaginatedOccurrenceRead`.
- `POST /api/v1/occurrences`: Auth required (`get_current_user`). Returns `201 Created` with `OccurrenceRead`.
- `GET /api/v1/occurrences/{id}`: Auth required (`get_current_user`). Returns `OccurrenceDetailRead`.
- `PUT /api/v1/occurrences/{id}/status`: Auth required (`get_current_user`). Enforces update permission check. Returns updated `OccurrenceRead`.
- `POST /api/v1/occurrences/{id}/timeline`: Auth required (`get_current_user`). Enforces access check. Returns `OccurrenceTimelineRead`.

---

### Database Migration

- Alembic revision script creating `occurrence` and `occurrence_timeline` tables with foreign keys, composite indexes on `(status, category, is_public)`, and unique constraint on `protocol_number`.

---

### Frontend Layer (`frontend/src/features/occurrence-management/`)

1. **Types & API Client**:
   - `frontend/src/types/occurrence.ts`: TypeScript interfaces (`Occurrence`, `OccurrenceTimeline`, `OccurrenceCategory`, `OccurrenceStatus`, `OccurrencePriority`, `OccurrenceCreate`, `OccurrenceStatusUpdate`, `TimelineNoteCreate`).
   - `frontend/src/api/occurrences.ts`: Axios client functions for `/api/v1/occurrences` endpoints.
   - `frontend/src/hooks/useOccurrences.ts`: TanStack Query hooks (`useOccurrences`, `useOccurrenceDetail`, `useCreateOccurrence`, `useUpdateOccurrenceStatus`, `useAddTimelineNote`).

2. **Components**:
   - `OccurrenceBookPage.tsx`: Container view with header title, protocol search bar, category/status/public filter controls, "Nova Ocorrência" button, and rendering of `OccurrenceTable` or detail modal.
   - `OccurrenceTable.tsx`: Data table listing protocol number, category badge, title, status badge, priority badge, reporter name (or "Anônimo"), creation date, and view/manage actions.
   - `NewOccurrenceModal.tsx`: Dialog form allowing residents/admins to select category, enter title & description, optionally select a lot, toggle `is_anonymous` and `is_public`, and upload/attach photo URLs.
   - `OccurrenceDetailsView.tsx`: Detailed card showing protocol header, badges, description, photo gallery, reporter details (if visible), assigned user, resolution notes, and embedded timeline view.
   - `OccurrenceTimelineLog.tsx`: Vertical timeline rendering history of status updates and notes. Includes internal note indicator badges for management and a text form to submit new notes or update ticket status.

3. **Navigation & Routing**:
   - Register route `/occurrences` (`OccurrenceBookPage.tsx`) in `frontend/src/App.tsx`.
   - Add navigation link in `frontend/src/features/user-administration/components/Navbar.tsx` ("Livro de Ocorrências").

4. **Internationalization (i18n)**:
   - Add translation key dictionaries under `occurrences.*` namespace in `pt.json` and `en.json` (covering categories, statuses, priorities, table headers, form labels, tooltips, and toast messages).

---

## Expected Results

- [ ] Alembic migration cleanly creates `occurrence` and `occurrence_timeline` tables with correct foreign keys, indices, and unique constraints.
- [ ] SQLModel entities `Occurrence` and `OccurrenceTimeline` strictly reflect required schema, default values, and `StrEnum` enumerations.
- [ ] Protocol sequence generator reliably creates sequential numbers matching `OCO-YYYY-XXXXXX` (e.g. `OCO-2026-000001`) resetting per year without duplicate key conflicts.
- [ ] `POST /api/v1/occurrences` creates an occurrence ticket, auto-generates protocol number, sets reporter ID, creates initial timeline log entry, and returns `201 Created`.
- [ ] `GET /api/v1/occurrences` lists occurrences with filtering by category, status, public flag, and protocol search.
- [ ] Private occurrences (`is_public = False`) are hidden from standard residents who are not the ticket reporter or assigned staff.
- [ ] Public occurrences (`is_public = True`) are visible to all authenticated residents.
- [ ] Anonymous occurrences (`is_anonymous = True`) hide `reporter_user_id` and return `"Anônimo"` as reporter name for non-admin API calls, while displaying true reporter identity to Admin/Director roles.
- [ ] `GET /api/v1/occurrences/{id}` returns complete ticket details and timeline log history.
- [ ] `PUT /api/v1/occurrences/{id}/status` updates ticket status, priority, assignee, resolution notes, sets `resolved_at` when resolved/rejected, and appends a timeline entry.
- [ ] `POST /api/v1/occurrences/{id}/timeline` adds public or internal timeline notes. Internal notes (`is_internal_only = True`) are stripped from responses for non-admin users.
- [ ] Frontend `/occurrences` route renders `OccurrenceBookPage` with `OccurrenceTable`, search, and status/category filters under `ProtectedRoute`.
- [ ] `NewOccurrenceModal` allows creating tickets with category selection, anonymity toggle, public toggle, and photo attachments.
- [ ] `OccurrenceDetailsView` displays ticket details, photo gallery, status badges, and embedded `OccurrenceTimelineLog`.
- [ ] `OccurrenceTimelineLog` displays audit history, highlights internal notes for management staff, and allows posting timeline notes.
- [ ] Internationalization strings for occurrence management are fully defined in `pt.json` and `en.json`.
- [ ] Pytest test suite in `backend/tests/test_occurrences.py` passes with ≥ 90% code coverage.
- [ ] Vitest test suite in `frontend/src/features/occurrence-management/__tests__/` passes with ≥ 75% code coverage.

---

## Out of Scope

- Direct integration with real-time push notifications or WhatsApp alerts for occurrence updates (handled in T012).
- Automatic SLA escalation timer background jobs (handled in future maintenance task).
- Conversion of feedback messages into occurrences (handled in task T011).
- Physical photo file upload processing and S3 storage handling (uses photo URL strings; file upload service handled in task T004).
