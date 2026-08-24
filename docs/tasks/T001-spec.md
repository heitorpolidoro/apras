</Meridian Spec Generator — Task Spec Author>
<T001 — Cadastro de Lotes (quadra, lote, endereço) e vinculação de usuários>

## Scope

This task covers the foundational Lot Management module ("Cadastro de Lotes e Vinculação de Usuários") for APRAS, establishing physical real-estate unit domain tracking and user-to-lot association logic.

### In Scope
1. **Database Schema & Models**:
   - SQLModel entity `Lot` with unique composite constraint on `(block, lot_number)` and soft-delete support (`is_deleted`).
   - SQLModel link entity `UserLotLink` for binding users to lots with relationship metadata and unique constraint on `(user_id, lot_id)`.
   - Domain enumerations `LotStatus` (`VACANT`, `OCCUPIED`, `UNDER_CONSTRUCTION`) and `LotAssociationType` (`PROPRIETARIO`, `INQUILINO`, `RESPONSAVEL_FINANCEIRO`, `OUTRO`).
   - Alembic DDL migration script creating indexes, foreign keys (`ON DELETE CASCADE`), and constraints.

2. **Backend Logic & API Services**:
   - Service layer `LotService` with full CRUD, validation, unique constraint error handling, pagination, and user link orchestration.
   - RESTful endpoints under `/api/v1/lots`:
     - `GET /api/v1/lots`: List lots with filters (`block`, `status`) and pagination (`skip`, `limit`).
     - `POST /api/v1/lots`: Create lot (ADMINISTRATOR and DIRECTOR).
     - `GET /api/v1/lots/{id}`: Fetch lot details along with linked users summary.
     - `PUT /api/v1/lots/{id}`: Update lot properties (ADMINISTRATOR and DIRECTOR).
     - `DELETE /api/v1/lots/{id}`: Soft delete lot (`is_deleted=True`) (ADMINISTRATOR only).
     - `POST /api/v1/lots/{id}/users`: Bind user to lot (ADMINISTRATOR and DIRECTOR).
     - `DELETE /api/v1/lots/{id}/users/{user_id}`: Unlink user from lot (ADMINISTRATOR and DIRECTOR).
   - Domain exception classes (`LotNotFoundError`, `LotAlreadyExistsError`, `UserLotLinkAlreadyExistsError`, `UserLotLinkNotFoundError`) registered in global exception handlers.

3. **Frontend UI & State Management**:
   - Route `/lots` (`LotsPage.tsx`) protected by `ProtectedRoute`.
   - Navigation entry in `Navbar.tsx` ("Lotes").
   - React components: `LotTable`, `LotFormModal`, `UserLotAssignmentModal`, and `LotDetailsView`.
   - API client module (`src/api/lots.ts`) and custom TanStack Query hooks (`useLots.ts`).
   - i18n translation keys in `pt.json` and `en.json`.

4. **Testing & Quality Assurance**:
   - Pytest suite covering model constraints, service logic, RBAC security, and endpoint response contracts (≥ 90% backend coverage).
   - Vitest suite covering component rendering, form validation, modal state, and API integration hooks (≥ 75% frontend coverage).

---

## Approach

### Data Layer (`backend/app/models/` & `backend/app/schemas/`)

1. **Domain Enums (`backend/app/models/enums.py`)**:
   ```python
   class LotStatus(StrEnum):
       VACANT = "VACANT"
       OCCUPIED = "OCCUPIED"
       UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"

   class LotAssociationType(StrEnum):
       PROPRIETARIO = "PROPRIETARIO"
       INQUILINO = "INQUILINO"
       RESPONSAVEL_FINANCEIRO = "RESPONSAVEL_FINANCEIRO"
       OUTRO = "OUTRO"
   ```

2. **SQLModel Entities (`backend/app/models/lot.py`)**:
   - `Lot`:
     - `id`: UUID = Field(default_factory=uuid4, primary_key=True)
     - `block`: str = Field(index=True, nullable=False)
     - `lot_number`: str = Field(index=True, nullable=False)
     - `address`: str | None = Field(default=None)
     - `postal_code`: str | None = Field(default=None)
     - `area_sqm`: float | None = Field(default=None)
     - `fraction_ideal`: float | None = Field(default=None)
     - `status`: LotStatus = Field(default=LotStatus.VACANT, nullable=False)
     - `notes`: str | None = Field(default=None)
     - `is_deleted`: bool = Field(default=False, nullable=False)
     - `created_at`: datetime = Field(default_factory=datetime.utcnow, nullable=False)
     - `updated_at`: datetime = Field(default_factory=datetime.utcnow, nullable=False)
     - Table args: `UniqueConstraint("block", "lot_number", name="uq_lot_block_lot_number")`
   - `UserLotLink`:
     - `id`: UUID = Field(default_factory=uuid4, primary_key=True)
     - `user_id`: UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
     - `lot_id`: UUID = Field(foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True)
     - `association_type`: LotAssociationType = Field(default=LotAssociationType.PROPRIETARIO, nullable=False)
     - `is_primary`: bool = Field(default=False, nullable=False)
     - `start_date`: datetime | None = Field(default=None)
     - `end_date`: datetime | None = Field(default=None)
     - `created_at`: datetime = Field(default_factory=datetime.utcnow, nullable=False)
     - Table args: `UniqueConstraint("user_id", "lot_id", name="uq_user_lot_link_user_lot")`

3. **Pydantic Schemas (`backend/app/schemas/lot.py`)**:
   - `LotCreate`: Validation for `block`, `lot_number`, optional `address`, `postal_code`, `area_sqm`, `fraction_ideal`, `status`, `notes`.
   - `LotUpdate`: Optional update payload.
   - `LotRead`: Base lot fields.
   - `UserLotLinkCreate`: `user_id`, `association_type`, `is_primary`, `start_date`, `end_date`.
   - `UserLotLinkRead`: Link details with nested `user` summary (`id`, `full_name`, `email`, `role`).
   - `LotDetailRead`: `LotRead` combined with `users: list[UserLotLinkRead]`.
   - `PaginatedLotRead`: `items: list[LotRead]`, `total: int`, `skip: int`, `limit: int`.

### Service Layer (`backend/app/services/lot_service.py`)

- `get_lots(session, block, status, skip, limit)`: Paginated query filtering by active `is_deleted = False` and optional block/status filters. Returns `(items, total_count)`.
- `create_lot(session, lot_in)`: Checks for existing lot with same `(block, lot_number)` (excluding soft-deleted). Raises `LotAlreadyExistsError` on conflict.
- `get_lot_by_id(session, lot_id)`: Raises `LotNotFoundError` if not found or soft-deleted.
- `get_lot_detail(session, lot_id)`: Retrieves lot and joins `UserLotLink` entries with user profiles.
- `update_lot(session, db_lot, lot_in)`: Updates lot attributes and updates `updated_at`.
- `delete_lot(session, db_lot)`: Performs soft deletion (`is_deleted = True`).
- `link_user(session, lot_id, link_in)`: Verifies user existence, checks for duplicate link (raises `UserLotLinkAlreadyExistsError`), inserts `UserLotLink`, and updates lot status to `OCCUPIED` if status was `VACANT`.
- `unlink_user(session, lot_id, user_id)`: Deletes `UserLotLink` record. If no remaining users are linked, updates lot status back to `VACANT`.

### Endpoint & Security Layer (`backend/app/api/v1/endpoints/lots.py`)

- Permission checks:
  - `GET /api/v1/lots`, `GET /api/v1/lots/{id}`: `get_current_user` (ADMINISTRATOR, DIRECTOR, MANAGER allowed).
  - `POST /`, `PUT /{id}`, `POST /{id}/users`, `DELETE /{id}/users/{user_id}`: `_require_lot_write_permission` (ADMINISTRATOR and DIRECTOR only).
  - `DELETE /{id}`: `get_current_active_admin` (ADMINISTRATOR only).

### Database Migration

- Alembic revision script creating `lot` and `user_lot_link` tables with appropriate indexes and composite unique constraints.

### Frontend Layer (`frontend/src/features/lot-management/`)

1. **Types & API Client**:
   - `frontend/src/types/lot.ts`: TypeScript interfaces for `Lot`, `UserLotLink`, `LotStatus`, `LotAssociationType`, `LotCreate`, `LotUpdate`, `UserLotLinkCreate`.
   - `frontend/src/api/lots.ts`: Axios client calls for all `/api/v1/lots` endpoints.
2. **State Management & Hooks**:
   - `frontend/src/hooks/useLots.ts`: Custom React Query hooks (`useLots`, `useLotDetail`, `useCreateLot`, `useUpdateLot`, `useDeleteLot`, `useLinkUserLot`, `useUnlinkUserLot`).
3. **Components**:
   - `LotsPage.tsx`: Container page featuring search bar, block/status filter selects, action button to create lot, and toggle between `LotTable` and `LotDetailsView`.
   - `LotTable.tsx`: Displays list of lots, columns for Quadra, Lote, Endereço, CEP, Área (m²), Fração Ideal, Status badge, number of linked users, and context actions (View, Edit, Link User, Delete).
   - `LotFormModal.tsx`: Modal dialog for creating and updating lot metadata.
   - `UserLotAssignmentModal.tsx`: Modal dialog to select a system user, select association type, toggle `is_primary`, and select validity dates (`start_date`, `end_date`).
   - `LotDetailsView.tsx`: Displays detailed card of the lot along with a table of linked users, association badges, primary tag, and unlink action.
4. **Navigation & Routing**:
   - Register `/lots` route in `frontend/src/App.tsx`.
   - Update `frontend/src/features/user-administration/components/Navbar.tsx` to include the "Lotes" link visible to authenticated users (ADMINISTRATOR, DIRECTOR, MANAGER).
5. **Internationalization (i18n)**:
   - Add translation dictionaries in `pt.json` and `en.json` under `nav.lots` and `lots.*` namespace (labels, titles, buttons, status tags, association types, and error toasts).

---

## Expected Results

- [ ] Database migration executes cleanly creating `lot` and `user_lot_link` tables with correct composite unique keys and indexes.
- [ ] SQLModel models `Lot` and `UserLotLink` strictly adhere to required schema, defaults, FK cascades, and `StrEnum` types.
- [ ] `POST /api/v1/lots` creates a new lot, enforces uniqueness of `(block, lot_number)`, and returns status `201 Created` for Admin/Director roles.
- [ ] `GET /api/v1/lots` returns paginated lots with support for `block` and `status` query filters.
- [ ] `GET /api/v1/lots/{id}` returns complete lot details along with list of linked users and association metadata.
- [ ] `PUT /api/v1/lots/{id}` updates lot attributes successfully for Admin/Director roles.
- [ ] `DELETE /api/v1/lots/{id}` performs soft deletion (`is_deleted=True`) and is restricted strictly to Administrator role (Director receives `403 Forbidden`).
- [ ] `POST /api/v1/lots/{id}/users` links a user to a lot, prevents duplicate user-lot links (`400 Bad Request`), and auto-updates vacant lot status to `OCCUPIED`.
- [ ] `DELETE /api/v1/lots/{id}/users/{user_id}` unlinks user from lot and auto-reverts lot status to `VACANT` when no active users remain.
- [ ] A single user can be linked to multiple lots concurrently without constraint errors.
- [ ] Vacant lots can be created and managed without requiring any linked user.
- [ ] Frontend `/lots` route renders `LotsPage` with `LotTable`, search, and status/block filtering under `ProtectedRoute`.
- [ ] `LotFormModal` correctly validates inputs and creates/updates lots.
- [ ] `UserLotAssignmentModal` enables binding users to lots with association types (`PROPRIETARIO`, `INQUILINO`, etc.) and primary flag.
- [ ] `LotDetailsView` displays linked users with association badges and allows unlinking user with modal confirmation.
- [ ] Internationalization strings for lot management are fully populated in both `pt.json` and `en.json`.
- [ ] Backend test suite in `backend/tests/test_lots.py` passes with ≥ 90% code coverage.
- [ ] Frontend test suite in `frontend/src/features/lot-management/__tests__/` passes with ≥ 75% code coverage.

---

## Out of Scope

- Tracking individual resident census profiles without user accounts (handled in task T002).
- Pre-authorized visitor management or gatekeeper access logs per lot (handled in task T003).
- Photo attachments or media uploads for lots (handled in task T004).
- CSV/Excel batch import of lots.
- Automatic automated user role alteration/revocation upon tenancy end date expiration.
