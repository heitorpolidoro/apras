# T005 — Controle de Acesso e Integração de Reconhecimento Facial

## Scope

This task implements the Access Control & Facial Recognition Integration module ("Controle de Acesso e Integração de Reconhecimento Facial") for APRAS. It provides a device registry for physical facial-recognition access-control hardware (turnstiles/gates), a facial template sync mechanism built on top of the approved photo pipeline (T004), a device-authenticated webhook that ingests verification events from the hardware, and a live gate-monitor UI for gatekeepers/administration.

### In Scope

1. **Database Schema & SQLModels** (`backend/app/models/access_control.py`):
   - `AccessDevice`: registry of physical facial-recognition devices/turnstiles.
     - `id`: UUID (PK)
     - `name`: str (unique, e.g. "Portaria Principal")
     - `location`: str | None
     - `device_key`: str (unique, opaque bearer secret used by the physical device to authenticate webhook calls; generated server-side, never derived from user input)
     - `status`: enum `AccessDeviceStatus` (`ONLINE`, `OFFLINE`, `MAINTENANCE`), default `OFFLINE`
     - `last_seen_at`: datetime | None
     - `created_by_id`: UUID (FK -> `user.id`, `ON DELETE CASCADE`)
     - `created_at` / `updated_at`: datetime
   - `FacialTemplate`: sync record linking a `Resident` to an **approved** `MediaAsset` photo as their active biometric enrollment reference.
     - `id`: UUID (PK)
     - `resident_id`: UUID (FK -> `resident.id`, `ON DELETE CASCADE`, unique — one active template per resident)
     - `media_asset_id`: UUID (FK -> `media_asset.id`, `ON DELETE CASCADE`)
     - `sync_status`: enum `FacialTemplateSyncStatus` (`PENDING`, `SYNCED`, `FAILED`), default `PENDING`
     - `synced_at`: datetime | None
     - `failure_reason`: str | None
     - `created_at` / `updated_at`: datetime
   - `FacialAccessEvent`: immutable log of verification attempts reported by a device.
     - `id`: UUID (PK)
     - `device_id`: UUID (FK -> `access_device.id`, `ON DELETE CASCADE`, indexed)
     - `resident_id`: UUID | None (FK -> `resident.id`, `ON DELETE SET NULL`, indexed — null when the device reports no match)
     - `matched`: bool (whether the device recognized an enrolled template)
     - `confidence_score`: float | None (0.0–1.0, as reported by the device)
     - `access_granted`: bool (final decision — `True` only when `matched` is `True` and the resident's lot association is active)
     - `event_time`: datetime (default `datetime.utcnow`, indexed)
     - `raw_payload`: str | None (JSON string of the original webhook body, for audit)
   - Domain enums in `backend/app/models/enums.py`:
     - `AccessDeviceStatus`: `ONLINE`, `OFFLINE`, `MAINTENANCE`
     - `FacialTemplateSyncStatus`: `PENDING`, `SYNCED`, `FAILED`
   - Alembic migration `0012_add_access_control_tables.py` creating `access_device`, `facial_template`, and `facial_access_event` tables with FKs, unique constraints (`access_device.name`, `access_device.device_key`, `facial_template.resident_id`), and indexes (`facial_access_event.device_id`, `facial_access_event.resident_id`, `facial_access_event.event_time`).

2. **Backend Logic & API Services** (`backend/app/services/access_control_service.py`):
   - `AccessControlService.create_device(session, device_in, current_user)`: Admin/Director only. Generates a unique `device_key` via `secrets.token_urlsafe(32)`, persists `AccessDevice`.
   - `AccessControlService.list_devices(session)`: Returns all devices.
   - `AccessControlService.update_device_status(session, device_id, status_in, current_user)`: Admin/Director only. Updates `status` and `last_seen_at`.
   - `AccessControlService.regenerate_device_key(session, device_id, current_user)`: Admin/Director only. Rotates `device_key`.
   - `AccessControlService.sync_facial_template(session, resident_id, current_user)`: Admin/Director only.
     1. Looks up the resident's most recent `MediaAsset` with `entity_type == RESIDENT`, `entity_id == resident_id`, `status == APPROVED` (ordered by `created_at desc`). Raises `NoApprovedPhotoError` if none exists.
     2. Creates or updates (upsert on `resident_id`) the `FacialTemplate` row, sets `sync_status = SYNCED`, `synced_at = datetime.utcnow()`, `media_asset_id` to the resolved photo (simulated sync — no external hardware call is made in this task).
   - `AccessControlService.get_facial_template(session, resident_id)`: Returns the resident's `FacialTemplate` or `None`.
   - `AccessControlService.process_verification_webhook(session, device_key, payload)`:
     1. Resolves `AccessDevice` by `device_key`; raises `InvalidDeviceKeyError` (→ `401`) if not found.
     2. Updates device `status = ONLINE`, `last_seen_at = datetime.utcnow()`.
     3. If `payload.resident_id` is provided, verifies a `FacialTemplate` exists for that resident with `sync_status == SYNCED`; sets `matched = True` if found, else `matched = False`.
     4. If `matched` and the resident has at least one active `Lot` association (reuses existing `Resident.is_active` and lot link), `access_granted = True`; otherwise `False`.
     5. Persists a `FacialAccessEvent` capturing the decision and raw payload.
     6. Returns the created event.
   - `AccessControlService.list_events(session, current_user, device_id=None, resident_id=None, skip=0, limit=100)`: Admin/Director/Manager only — paginated, filterable event feed for the live monitor, most recent first.

3. **Domain Exceptions** (`backend/app/core/exceptions.py`):
   - `AccessDeviceNotFoundError` (404)
   - `DuplicateDeviceNameError` (400)
   - `InvalidDeviceKeyError` (401 — raised for webhook calls with an unknown/missing device key)
   - `NoApprovedPhotoError` (400 — raised when attempting to sync a facial template without an approved `RESIDENT` photo)
   - `ResidentNotFoundError` is reused (already defined) for facial-template endpoints referencing an unknown resident.

4. **REST API Endpoints** (`backend/app/api/v1/endpoints/access_control.py`, mounted under `/api/v1/access-control`):
   - `POST /api/v1/access-control/devices`: Register a device (Admin/Director only).
   - `GET /api/v1/access-control/devices`: List all devices (Admin/Director/Manager).
   - `PUT /api/v1/access-control/devices/{device_id}/status`: Update device status (Admin/Director only).
   - `POST /api/v1/access-control/devices/{device_id}/regenerate-key`: Rotate the device's secret key, returned once in the response body (Admin/Director only).
   - `POST /api/v1/access-control/residents/{resident_id}/facial-template/sync`: Trigger (simulated) facial template sync from the resident's approved avatar (Admin/Director only).
   - `GET /api/v1/access-control/residents/{resident_id}/facial-template`: Get sync status for a resident (Admin/Director/Manager).
   - `POST /api/v1/access-control/webhook/verification`: **Unauthenticated via JWT** — authenticated instead via `X-Device-Key` header matched against `AccessDevice.device_key`. Body: `{resident_id: UUID | null, confidence_score: float | null}`. Returns the created `FacialAccessEvent`.
   - `GET /api/v1/access-control/events`: Paginated live event feed with optional `device_id` / `resident_id` filters (Admin/Director/Manager only).

5. **Frontend UI & State Management** (`frontend/src/features/access-control/`):
   - Route `/admin/access-control` (`AccessControlPage.tsx`, gated to `ADMINISTRATOR`/`DIRECTOR`): Device registry table (name, location, status badge, last seen, regenerate-key action, register-device modal), and a per-resident facial template sync panel (resident search, sync button, status badge).
   - Route `/gate-monitor` (`GateMonitorPage.tsx`, gated to `ADMINISTRATOR`/`DIRECTOR`/`MANAGER`): Live-polling feed (TanStack Query `refetchInterval`) of the most recent `FacialAccessEvent` records, showing device name, resident name (or "Não reconhecido"), granted/denied badge, confidence score, and timestamp; device status strip at the top.
   - Components: `DeviceTable.tsx`, `RegisterDeviceModal.tsx`, `FacialTemplateSyncPanel.tsx`, `AccessEventFeed.tsx`.
   - `frontend/src/types/accessControl.ts`: TS interfaces for `AccessDevice`, `FacialTemplate`, `FacialAccessEvent`, `AccessDeviceStatus`, `FacialTemplateSyncStatus`.
   - `frontend/src/api/accessControl.ts`: Axios client functions.
   - `frontend/src/hooks/useAccessControl.ts`: TanStack Query hooks (`useDevices`, `useCreateDevice`, `useUpdateDeviceStatus`, `useRegenerateDeviceKey`, `useFacialTemplate`, `useSyncFacialTemplate`, `useAccessEvents`).
   - Navbar entries "Controle de Acesso" and "Monitor da Portaria" for Admin/Director (Manager sees only "Monitor da Portaria").
   - i18n keys under `accessControl.*` in `pt.json` and `en.json`.

6. **Testing & Quality Assurance**:
   - Pytest suite `backend/tests/test_access_control.py` covering: device CRUD + RBAC, device-key uniqueness/regeneration, facial template sync (success + `NoApprovedPhotoError`), webhook auth (valid key → 201, invalid/missing key → 401), matched vs unmatched verification decisions, `access_granted` logic, and event listing/RBAC (≥ 90% backend coverage).
   - Vitest suite `frontend/src/features/access-control/__tests__/` covering `AccessControlPage`, `GateMonitorPage`, device table rendering/actions, sync panel, and the event feed (≥ 75% frontend coverage).

## Approach

### Data Layer

Enums added to `backend/app/models/enums.py`:
```python
class AccessDeviceStatus(StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"

class FacialTemplateSyncStatus(StrEnum):
    PENDING = "PENDING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"
```

`backend/app/models/access_control.py` defines `AccessDevice`, `FacialTemplate`, `FacialAccessEvent` as SQLModel `table=True` classes following the field/FK conventions shown in Scope §1 (mirroring the style of `backend/app/models/visitor.py` and `backend/app/models/media_asset.py`: `Field(default_factory=uuid4, primary_key=True)`, `Field(foreign_key=..., ondelete=..., nullable=..., index=True)`, `Relationship(...)` where useful for read schemas).

`backend/app/schemas/access_control.py` defines: `AccessDeviceCreate`, `AccessDeviceRead` (excludes `device_key` except on create/regenerate responses via a separate `AccessDeviceKeyRead` that includes it once), `AccessDeviceStatusUpdate`, `FacialTemplateRead`, `FacialVerificationWebhookIn`, `FacialAccessEventRead`, and `Paginated*` wrappers matching the pattern in `backend/app/schemas/visitor.py`.

### Service Layer

`backend/app/services/access_control_service.py` implements the methods listed in Scope §2 as a class with `@staticmethod` methods (matching `VisitorService` conventions in `backend/app/services/visitor_service.py`). Device-key generation uses `secrets.token_urlsafe(32)`. The webhook auth path (`process_verification_webhook`) does **not** depend on `get_current_user` — it takes the raw `device_key` string and looks up the device directly, since physical devices cannot obtain a user JWT.

### Endpoint Layer

`backend/app/api/v1/endpoints/access_control.py` registers a new `APIRouter`, wired into `backend/app/api/v1/api.py` with `prefix="/access-control"`. All endpoints except the webhook use `Depends(deps.get_current_user)` plus an inline RBAC guard function (`_assert_admin_or_director`, `_assert_admin_director_or_manager`), matching the guard style already used in `backend/app/api/v1/endpoints/access_logs.py`. The webhook endpoint reads `X-Device-Key` via `Header(...)` and does not use `get_current_user`.

### Database Migration

`backend/alembic/versions/0012_add_access_control_tables.py`, chained after `0011_add_media_asset_table.py` (matches existing revision numbering), creating the three new tables, their FKs/uniques/indexes as specified in Scope §1.

### Frontend Architecture

Follows the structure of `frontend/src/features/visitor-management/` (see `VisitorAuthPage.tsx` / `GatekeeperDashboard.tsx` for reference) and `frontend/src/features/media-management/` for photo-status badge conventions. Routes are registered in `frontend/src/App.tsx` using `ProtectedRoute` with `requiredRole` matching the existing pattern (e.g. `requiredRole={UserRole.DIRECTOR}` used for `/admin/photo-approvals`); `/gate-monitor` additionally must render for `MANAGER`, so its route guard checks role membership in `[ADMINISTRATOR, DIRECTOR, MANAGER]` the same way `/gate` does today for `GatekeeperDashboard`.

## Expected Results

- [ ] SQLModel entities `AccessDevice`, `FacialTemplate`, `FacialAccessEvent` defined in `backend/app/models/access_control.py` with FKs, unique constraints, and indexes as specified.
- [ ] Alembic migration `0012_add_access_control_tables.py` created and executes cleanly (`alembic upgrade head` succeeds against the test/dev database).
- [ ] `POST /api/v1/access-control/devices` creates a device with a unique, server-generated `device_key`; duplicate `name` returns `400` (`DuplicateDeviceNameError`); non-Admin/Director callers receive `403`.
- [ ] `POST /api/v1/access-control/devices/{device_id}/regenerate-key` rotates the device's `device_key` and returns the new key exactly once in the response body.
- [ ] `POST /api/v1/access-control/residents/{resident_id}/facial-template/sync` creates/updates a `FacialTemplate` with `sync_status = SYNCED` when the resident has an `APPROVED` `MediaAsset` of `entity_type = RESIDENT`; returns `400` (`NoApprovedPhotoError`) when no approved photo exists.
- [ ] `GET /api/v1/access-control/residents/{resident_id}/facial-template` returns the current sync status for a resident.
- [ ] `POST /api/v1/access-control/webhook/verification` authenticates via `X-Device-Key` header (not JWT): a valid key creates a `FacialAccessEvent` and returns `201`; a missing or unknown key returns `401` (`InvalidDeviceKeyError`).
- [ ] Verification webhook correctly computes `matched` (`True` only if the referenced resident has a `SYNCED` `FacialTemplate`) and `access_granted` (`True` only if `matched` and the resident is active), persisting both flags plus `confidence_score` and `raw_payload` on the event.
- [ ] `GET /api/v1/access-control/events` returns a paginated, most-recent-first event feed filterable by `device_id` and `resident_id`, restricted to Admin/Director/Manager (`403` otherwise).
- [ ] Frontend route `/admin/access-control` renders `AccessControlPage` with device table, register-device modal, regenerate-key action, and facial template sync panel; gated to Administrator/Director.
- [ ] Frontend route `/gate-monitor` renders `GateMonitorPage` with a live-polling access event feed and device status strip; accessible to Administrator, Director, and Manager.
- [ ] Navbar exposes "Controle de Acesso" (Admin/Director) and "Monitor da Portaria" (Admin/Director/Manager) entries.
- [ ] Internationalization strings for access control (device management, sync panel, event feed) are fully defined in `pt.json` and `en.json`.
- [ ] Backend test suite `backend/tests/test_access_control.py` passes with ≥ 90% code coverage.
- [ ] Frontend test suite `frontend/src/features/access-control/__tests__/` passes with 100% pass rate and ≥ 75% code coverage.

## Out of Scope

- Actual biometric vector extraction/matching algorithms or third-party facial-recognition SDK/vendor integration — `process_verification_webhook` trusts the device's own `resident_id` claim and confidence score as reported; this task only builds the sync bookkeeping and event pipeline.
- Physical turnstile/barrier relay actuation (opening a gate) — out of scope; only the access decision (`access_granted`) is recorded.
- Automatic device health polling/heartbeat jobs — device `status`/`last_seen_at` are updated only as a side effect of a verification webhook call or manual admin update, not via a background scheduler.
- WhatsApp/SMS alerting on access events (handled in task `whatsapp-integration`).
- QR-code-based access as an alternative credential (handled in task `qr-code-visitor-passes`).
