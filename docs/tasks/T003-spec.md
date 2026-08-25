</Meridian Spec Generator — Task Spec Author>
<T003 — Cadastro e Autorização de Visitantes e Prestadores de Serviço>

## Scope

This task covers the Visitor and Service Provider Management module ("Cadastro e Autorização de Visitantes e Prestadores de Serviço") for APRAS, establishing master visitor registrations, resident pre-authorizations with day/shift constraints, and real-time gatekeeper (*Portaria*) check-in and check-out tracking.

### In Scope
1. **Database Schema & Models**:
   - SQLModel entity `Visitor`: Master registry of visitors and service providers (`full_name`, `cpf`, `rg`, `phone`, `company_name`, `vehicle_plate`, `vehicle_model`, `notes`, timestamps).
   - SQLModel entity `VisitorAuthorization`: Resident/Admin pre-authorizations tied to a `Visitor` and `Lot` with authorization type (`SINGLE`, `PERMANENT`), JSON-encoded allowed days and allowed shifts, validity datetime range (max 1 year for permanent authorizations), status (`ACTIVE`, `EXPIRED`, `REVOKED`), authorizer ID, and timestamps.
   - SQLModel entity `AccessLog`: Entry/exit access history capturing `authorization_id` (nullable, `ON DELETE SET NULL`), `visitor_id`, `lot_id`, `entry_time`, `exit_time`, `gatekeeper_user_id`, `entry_notes`, and `exit_notes`.
   - Domain enumerations `AuthorizationType` (`SINGLE`, `PERMANENT`), `AuthorizationStatus` (`ACTIVE`, `EXPIRED`, `REVOKED`), `DayOfWeek` (`MON`, `TUE`, `WED`, `THU`, `FRI`, `SAT`, `SUN`), and `ShiftType` (`MORNING`, `AFTERNOON`, `NIGHT`, `FULL_DAY`).
   - Alembic DDL migration script generating tables, indexes, and foreign keys (`ON DELETE CASCADE` / `ON DELETE SET NULL`).

2. **Backend Logic & API Services**:
   - Service layer `VisitorService`, `AuthorizationService`, and `AccessLogService` implementing search, pre-authorization, revocation, check-in validation (checking authorization status, date window, day of week, allowed shift, and preventing duplicate open check-ins), and check-out.
   - Real-time in-app notification/log trigger on visitor check-in targeting lot owner and linked residents.
   - RESTful API endpoints under `/api/v1/visitors`, `/api/v1/authorizations`, `/api/v1/access-logs`, and `/api/v1/lots/{lot_id}/authorizations`:
     - `GET /api/v1/visitors`: Search visitors by name, CPF, or vehicle plate.
     - `POST /api/v1/visitors`: Create new visitor master profile with CPF check-digit validation.
     - `GET /api/v1/lots/{lot_id}/authorizations`: List visitor pre-authorizations for a specific lot.
     - `POST /api/v1/lots/{lot_id}/authorizations`: Create pre-authorization for a lot (enforcing max 1-year limit for permanent type).
     - `PUT /api/v1/authorizations/{id}/revoke`: Revoke authorization immediately.
     - `POST /api/v1/access-logs/check-in`: Register visitor entry at gate.
     - `POST /api/v1/access-logs/check-out`: Register visitor exit at gate.
     - `GET /api/v1/access-logs`: Query access log timeline history with lot, visitor, status, and date filters.
   - Domain exceptions (`VisitorNotFoundError`, `AuthorizationNotFoundError`, `AuthorizationExpiredError`, `AuthorizationRevokedError`, `AccessDeniedDayError`, `AccessDeniedShiftError`, `VisitorAlreadyCheckedInError`, `NoActiveCheckInError`) registered in global exception handlers.

3. **Visibility & Role-Based Access Control (RBAC)**:
   - **Administration (ADMINISTRATOR / DIRECTOR)**: Full CRUD on visitors, authorizations across all lots, and access logs.
   - **Manager / Gatekeeper (MANAGER)**: Search visitors, create visitors, execute check-in / check-out, view all active authorizations and access logs.
   - **Lot Residents / Standard Users**: Can list, create, and revoke authorizations for their own associated lot(s). Accessing or modifying authorizations for unassociated lots returns `403 Forbidden`. Can view access log history for their own lot(s).

4. **Frontend UI & State Management**:
   - Route `/authorizations` (`VisitorAuthPage.tsx`): Pre-authorization list, filter, creation modal, and revocation UI for residents and administration.
   - Route `/gate` (`GatekeeperDashboard.tsx`): Portaria check-in/check-out search terminal, active visitor counter, entry/exit modal, and recent access log feed.
   - Navbar entries for "Autorizações" and "Portaria".
   - Components: `VisitorTable`, `AuthorizationFormModal`, `GatekeeperEntryModal`, `AccessLogTimeline`.
   - API client module (`src/api/visitorManagement.ts`) and custom TanStack Query hooks (`useVisitors.ts`, `useAuthorizations.ts`, `useAccessLogs.ts`).
   - i18n translation keys in `pt.json` and `en.json`.

5. **Testing & Quality Assurance**:
   - Pytest test suite (`backend/tests/test_visitor_management.py`) covering database schemas, validation rules (CPF, 1-year max limit, day/shift check-in verification, single-entry auto-expiration, duplicate check-in prevention), and RBAC security gates (≥ 90% backend coverage).
   - Vitest test suite (`frontend/src/features/visitor-management/__tests__/`) covering component rendering, form state, entry/exit workflows, and API hooks (≥ 75% frontend coverage).

---

## Approach

### Data Layer (`backend/app/models/` & `backend/app/schemas/`)

1. **Domain Enums (`backend/app/models/enums.py`)**:
   ```python
   class AuthorizationType(StrEnum):
       SINGLE = "SINGLE"
       PERMANENT = "PERMANENT"

   class AuthorizationStatus(StrEnum):
       ACTIVE = "ACTIVE"
       EXPIRED = "EXPIRED"
       REVOKED = "REVOKED"

   class DayOfWeek(StrEnum):
       MON = "MON"
       TUE = "TUE"
       WED = "WED"
       THU = "THU"
       FRI = "FRI"
       SAT = "SAT"
       SUN = "SUN"

   class ShiftType(StrEnum):
       MORNING = "MORNING"
       AFTERNOON = "AFTERNOON"
       NIGHT = "NIGHT"
       FULL_DAY = "FULL_DAY"
   ```

2. **SQLModel Entities (`backend/app/models/visitor.py`, `backend/app/models/visitor_authorization.py`, `backend/app/models/access_log.py`)**:
   - `Visitor`:
     - `id`: UUID = Field(default_factory=uuid4, primary_key=True)
     - `full_name`: str = Field(nullable=False, index=True)
     - `cpf`: str | None = Field(default=None, index=True)
     - `rg`: str | None = Field(default=None)
     - `phone`: str | None = Field(default=None)
     - `company_name`: str | None = Field(default=None, index=True)
     - `vehicle_plate`: str | None = Field(default=None, index=True)
     - `vehicle_model`: str | None = Field(default=None)
     - `notes`: str | None = Field(default=None)
     - `created_at`: datetime = Field(default_factory=datetime.utcnow, nullable=False)
     - `updated_at`: datetime = Field(default_factory=datetime.utcnow, nullable=False)
   - `VisitorAuthorization`:
     - `id`: UUID = Field(default_factory=uuid4, primary_key=True)
     - `visitor_id`: UUID = Field(foreign_key="visitor.id", ondelete="CASCADE", nullable=False, index=True)
     - `lot_id`: UUID = Field(foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True)
     - `authorizer_user_id`: UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
     - `auth_type`: AuthorizationType = Field(default=AuthorizationType.SINGLE, nullable=False)
     - `allowed_days_json`: str = Field(default='["MON","TUE","WED","THU","FRI","SAT","SUN"]', nullable=False)
     - `allowed_shifts_json`: str = Field(default='["MORNING","AFTERNOON","NIGHT","FULL_DAY"]', nullable=False)
     - `valid_from`: datetime | None = Field(default=None)
     - `valid_until`: datetime | None = Field(default=None)
     - `status`: AuthorizationStatus = Field(default=AuthorizationStatus.ACTIVE, nullable=False, index=True)
     - `notes`: str | None = Field(default=None)
     - `created_at`: datetime = Field(default_factory=datetime.utcnow, nullable=False)
     - `updated_at`: datetime = Field(default_factory=datetime.utcnow, nullable=False)
   - `AccessLog`:
     - `id`: UUID = Field(default_factory=uuid4, primary_key=True)
     - `authorization_id`: UUID | None = Field(default=None, foreign_key="visitor_authorization.id", ondelete="SET NULL", nullable=True, index=True)
     - `visitor_id`: UUID = Field(foreign_key="visitor.id", ondelete="CASCADE", nullable=False, index=True)
     - `lot_id`: UUID = Field(foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True)
     - `entry_time`: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
     - `exit_time`: datetime | None = Field(default=None, index=True)
     - `gatekeeper_user_id`: UUID | None = Field(default=None, foreign_key="user.id", nullable=True, index=True)
     - `entry_notes`: str | None = Field(default=None)
     - `exit_notes`: str | None = Field(default=None)

3. **Pydantic Schemas (`backend/app/schemas/visitor_management.py`)**:
   - `VisitorCreate`, `VisitorUpdate`, `VisitorRead`.
   - `VisitorAuthorizationCreate`, `VisitorAuthorizationRead`, `VisitorAuthorizationRevoke`.
   - `AccessLogCheckIn`, `AccessLogCheckOut`, `AccessLogRead`.
   - Paginated wrappers: `PaginatedVisitorRead`, `PaginatedAuthorizationRead`, `PaginatedAccessLogRead`.

### Service Layer (`backend/app/services/visitor_service.py`, `backend/app/services/authorization_service.py`, `backend/app/services/access_log_service.py`)

- `VisitorService.search_visitors(session, q, skip, limit)`: Filters visitors by `full_name`, `cpf`, or `vehicle_plate`.
- `VisitorService.create_visitor(session, visitor_in)`: Standardizes CPF (if present) with mathematical check-digit validation. Creates `Visitor` record.
- `AuthorizationService.create_authorization(session, lot_id, auth_in, current_user)`: Verifies authorizer permission for target lot. Validates `valid_until - valid_from <= 365 days` for `PERMANENT` type. Validates `allowed_days_json` and `allowed_shifts_json` are valid JSON lists of `DayOfWeek` and `ShiftType`.
- `AuthorizationService.revoke_authorization(session, auth_id, current_user)`: Sets status to `REVOKED`.
- `AccessLogService.check_in(session, check_in_in, current_user)`:
  1. Checks if visitor has active authorization for the lot.
  2. Verifies status is `ACTIVE`. Checks if current time exceeds `valid_until` (if set, auto-updates to `EXPIRED` and raises `AuthorizationExpiredError`).
  3. Checks day of week match (e.g. current UTC/local day mapped to `MON`..`SUN`).
  4. Checks shift match:
     - `MORNING`: 06:00 - 11:59
     - `AFTERNOON`: 12:00 - 17:59
     - `NIGHT`: 18:00 - 23:59
     - `FULL_DAY`: 00:00 - 23:59
  5. Checks visitor has no existing open `AccessLog` (`exit_time IS NULL`).
  6. Creates `AccessLog` entry with `gatekeeper_user_id = current_user.id`.
  7. If `auth_type == SINGLE`, auto-updates authorization status to `EXPIRED`.
  8. Triggers in-app/log notification event to lot owner/linked residents.
- `AccessLogService.check_out(session, check_out_in, current_user)`: Finds active open `AccessLog` record for visitor or log ID, updates `exit_time = now()`, `exit_notes`, and `gatekeeper_user_id`.

### Endpoint & Security Layer (`backend/app/api/v1/endpoints/visitors.py`, `backend/app/api/v1/endpoints/authorizations.py`, `backend/app/api/v1/endpoints/access_logs.py`)

- Endpoints and RBAC guards:
  - `GET /api/v1/visitors`: Authenticated users.
  - `POST /api/v1/visitors`: Authenticated users (Residents, Gatekeeper, Admin, Director, Manager).
  - `GET /api/v1/lots/{lot_id}/authorizations`: Admin/Director/Manager or users linked to `lot_id`.
  - `POST /api/v1/lots/{lot_id}/authorizations`: Admin/Director/Manager or users linked to `lot_id`.
  - `PUT /api/v1/authorizations/{id}/revoke`: Admin/Director or creator/authorizer or user linked to the lot.
  - `POST /api/v1/access-logs/check-in`: Gatekeeper / Admin / Director / Manager.
  - `POST /api/v1/access-logs/check-out`: Gatekeeper / Admin / Director / Manager.
  - `GET /api/v1/access-logs`: Gatekeeper / Admin / Director / Manager for all lots; Residents restricted to their own lot history.

### Database Migration

- Alembic script `0008_add_visitor_authorization_access_log.py` creating `visitor`, `visitor_authorization`, and `access_log` tables with foreign keys, indexes, and cascades.

### Frontend Layer (`frontend/src/features/visitor-management/`)

1. **Types & API Client**:
   - `frontend/src/types/visitor.ts`: TypeScript interfaces for `Visitor`, `VisitorAuthorization`, `AccessLog`, `AuthorizationType`, `AuthorizationStatus`, `ShiftType`, `DayOfWeek`.
   - `frontend/src/api/visitorManagement.ts`: Axios client API calls.
   - `frontend/src/hooks/useVisitorManagement.ts`: TanStack Query hooks (`useVisitors`, `useCreateVisitor`, `useLotAuthorizations`, `useCreateAuthorization`, `useRevokeAuthorization`, `useCheckIn`, `useCheckOut`, `useAccessLogs`).
2. **Pages & Components**:
   - `VisitorAuthPage.tsx` (`/authorizations`): Resident & Admin interface to view, filter, create, and revoke visitor pre-authorizations for lots.
   - `GatekeeperDashboard.tsx` (`/gate`): Portaria interface featuring visitor search bar (name, CPF, plate), active checked-in counter, 1-click check-in modal, active visitors list with 1-click check-out button, and live entry/exit feed.
   - `VisitorTable.tsx`: Displays visitor master list and authorizations.
   - `AuthorizationFormModal.tsx`: Form modal with visitor selector/creator, lot selector, single vs permanent toggle, day of week checkbox grid, shift selector, and validity date pickers.
   - `GatekeeperEntryModal.tsx`: Confirmation modal showing visitor photo/details, target lot info, validation status, and entry notes input.
   - `AccessLogTimeline.tsx`: History component displaying entry/exit logs with status indicators, gatekeeper user tags, and duration calculation.
3. **i18n Translation**:
   - Keys added under `authorizations.*`, `visitors.*`, `gatekeeper.*`, `accessLogs.*` in `pt.json` and `en.json`.

---

## Expected Results

- [ ] Database migration executes cleanly creating `visitor`, `visitor_authorization`, and `access_log` tables with proper foreign keys (`ON DELETE CASCADE` / `ON DELETE SET NULL`) and single-column indices on `cpf`, `vehicle_plate`, `lot_id`, `visitor_id`, `authorization_id`, and `entry_time`.
- [ ] SQLModel models `Visitor`, `VisitorAuthorization`, and `AccessLog` strictly adhere to the defined schema attributes and enum types.
- [ ] CPF validator on `Visitor` creation enforces Brazilian check-digits when provided and normalizes the stored string.
- [ ] `POST /api/v1/lots/{lot_id}/authorizations` enforces maximum 1-year validity period for `PERMANENT` authorization types (`valid_until` cannot exceed 366 days from `valid_from` or current time).
- [ ] Lot permission check enforces that standard users/residents can only create or list authorizations for lots they are linked to (`403 Forbidden` for unlinked lots).
- [ ] `PUT /api/v1/authorizations/{id}/revoke` revokes an active authorization setting status to `REVOKED`.
- [ ] Gatekeeper check-in (`POST /api/v1/access-logs/check-in`) validates active status, validity datetime window, day of week, and allowed shift window, raising appropriate domain error codes on mismatch.
- [ ] Single-entry authorizations (`SINGLE`) are automatically updated to `EXPIRED` status upon successful check-in validation.
- [ ] Gatekeeper check-in rejects visitors who already have an active open `AccessLog` (`exit_time IS NULL`), returning `400 Bad Request` (`VisitorAlreadyCheckedInError`).
- [ ] Real-time in-app notification / log entry is generated upon visitor check-in to inform lot owners/residents.
- [ ] Gatekeeper check-out (`POST /api/v1/access-logs/check-out`) updates open `AccessLog` record with `exit_time` and exit notes.
- [ ] Frontend route `/authorizations` renders `VisitorAuthPage` with authorization filters, creation modal, and revocation actions.
- [ ] Frontend route `/gate` renders `GatekeeperDashboard` with fast visitor search by name/CPF/plate, active visitor count, entry modal, and 1-click check-out button.
- [ ] `AuthorizationFormModal` allows configuring single/permanent authorization, allowed days of week, allowed shifts, and validity date range.
- [ ] `GatekeeperEntryModal` displays authorization validation status and accepts entry notes prior to confirming check-in.
- [ ] `AccessLogTimeline` displays searchable entry/exit history with timestamps, lot info, visitor name, and gatekeeper user tags.
- [ ] Internationalization strings for visitor management, authorizations, gatekeeper, and access logs are fully defined in `pt.json` and `en.json`.
- [ ] Backend test suite in `backend/tests/test_visitor_management.py` (or individual test modules) passes with ≥ 90% code coverage.
- [ ] Frontend test suite in `frontend/src/features/visitor-management/__tests__/` passes with ≥ 75% code coverage.

---

## Out of Scope

- Dynamic QR code generation for turnstile hardware integration (handled in task T086 / T005).
- WhatsApp / SMS automated notification dispatch to visitors (handled in task `whatsapp-integration`).
- Photo capturing or image storage uploads for visitors (handled in task T004).
- Automatic barrier gate hardware relay opening via IoT webhooks (handled in task T005).
- Offline gatekeeper desktop caching mechanism.
