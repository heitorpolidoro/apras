# APRAS-32 — Package Tracking (Encomendas) for Gatekeeper

**Date:** 2026-08-28
**Status:** Ready for implementation
**Source:** `docs/tasks/APRAS-26-analysis.md`, "Architectural Spec B — Package Tracking (Encomendas)" — treated as a strong draft and verified/adjusted below against the current codebase (post-APRAS-12 merge).

## Problem

The Gatekeeper Dashboard (`GatekeeperDashboard.tsx`, T003/APRAS-17) handles visitor check-in/check-out but has no way to log an incoming package for a lot, track whether it has been picked up, or let a resident check whether they have a package waiting. This is a named parity gap versus COM21's "receipt/pickup/status" feature (APRAS-26).

## Scope

This task adds:
- A `Package` model + migration.
- A `PackageService` service layer (mirrors `occurrence_service.py`'s shape: RBAC-aware create/list/get/update methods, no timeline sub-entity needed here).
- A new `backend/app/api/v1/endpoints/packages.py` router mounted at `/api/v1/packages`.
- An "Encomendas" section in `GatekeeperDashboard.tsx` for logging arrivals and marking pickups.
- A new, minimal resident-facing page (`/packages`) showing the residents of a lot their own lot's packages — see "Why a new page, not an existing one" below.

Out of scope is listed under **Non-Goals**.

### Why a new resident-facing page, not an existing one

The draft in APRAS-26-analysis.md says: "A resident-facing package-status view is a small addition wherever residents already see lot-scoped info (or a new minimal page if none exists — check at implementation time)."

Verified at implementation-spec time: there is **no existing working resident-scoped lot view** to attach to.
- `LotsPage.tsx` (`/lots` route) is reachable by `RESIDENT` and `GUEST` per `App.tsx`'s `ProtectedRoute` role list, but the backend endpoint it calls (`GET /api/v1/lots/`) restricts reads to `_LOT_READ_ROLES = {ADMINISTRATOR, DIRECTOR, MANAGER, PORTEIRO}` (`backend/app/api/v1/endpoints/lots.py`) — `RESIDENT` is **not** in that set, and `backend/tests/test_lots_rbac.py` confirms a non-listed role gets `403`. So today a resident who navigates to `/lots` gets a working page shell but a failed/forbidden data fetch. This is a pre-existing gap in the app, out of scope to fix here (do not add `RESIDENT` to `_LOT_READ_ROLES` as part of this task — that's a separate, broader change with its own implications for lot CRUD visibility).
- `FinanceDashboardPage` and `ConstructionTrackerPage` do let `RESIDENT` read data, but neither is lot-scoped — they show association-wide info, not "my lot's" info. There is no analog to mirror for "resident sees only their own lot's records."

**Decision**: APRAS-32 builds its own minimal resident-facing page (`PackageStatusPage.tsx`) rather than attaching to a page that doesn't actually serve residents lot-scoped data today. The backend resident-scoping logic is new for this feature but follows an existing service-layer *pattern* already used for lot-linkage resolution: `VisitorService.get_user_linked_lot_ids` (`backend/app/services/visitor_service.py`), which resolves a non-privileged user's lot IDs via `UserLotLink` (direct account-to-lot links) union `Resident` (household-member-to-lot links, filtered to `is_active == True`). `PackageService` reuses this exact helper rather than re-implementing lot resolution.

**Scope note**: this resident-facing page plus its supporting `GET /packages/my-lots` endpoint is the most speculative/novel part of this spec (no existing precedent to mirror, unlike the gatekeeper-side work which mirrors `access_logs.py`/`occurrence_service.py` closely). It is kept in this task's scope because Expected Result 3 below depends on it and the total surface is small (one page, one hook, one endpoint), but if implementation time pressure or review feedback favors shipping the gatekeeper-side functionality (Expected Results 1, 2, 5) first, splitting "resident package self-service" (Expected Results 3, 4 as they pertain to `/packages`) into a fast-follow task is a reasonable call — the gatekeeper-side backend (RBAC, model, migration) does not depend on the resident page existing.

## Verified current-codebase facts this spec depends on

- **Gatekeeper-access helper** (post-APRAS-12, merged): `backend/app/api/v1/endpoints/access_logs.py` defines `_assert_gatekeeper_access(current_user: User) -> None`, which raises `ForbiddenError` unless `current_user.role in (UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.PORTEIRO)`. This exact role tuple is mirrored for package create/pickup actions below.
- **Lot read roles**: `backend/app/api/v1/endpoints/lots.py` defines `_LOT_READ_ROLES = {ADMINISTRATOR, DIRECTOR, MANAGER, PORTEIRO}` (RESIDENT excluded, confirmed by test). Not modified by this task.
- **`UserRole` enum** (`backend/app/models/enums.py`) already includes `RESIDENT` (added in migration `0014_add_resident_userrole.py`, pre-dating this task) and `PORTEIRO` (added in `0020_add_porteiro_userrole.py`).
- **Alembic head is a moving target — do not hardcode a revision number.** At spec-review time, `cd backend && uv run alembic heads` reported `0021_add_feedback_table` (landed concurrently by APRAS-25, after this spec's first draft assumed `0020_add_porteiro_userrole` was current). Do **not** use `0021` for this task's migration — it collides with `0021_add_feedback_table`. **Before writing the migration, run `cd backend && uv run alembic heads` yourself** and set `down_revision` to whatever single head it reports, naming the new revision the next free number after that (e.g. if the head is `0021_add_feedback_table`, use `0022_add_package_table`). If `alembic heads` reports more than one head, stop and resolve/merge heads first (follow the precedent in `0015_merge_migration_heads.py`) rather than layering a third head on top.
- **Resident-lot resolution pattern**: `VisitorService.get_user_linked_lot_ids(session, current_user) -> list[UUID]` (in `backend/app/services/visitor_service.py`) already implements "all lots for privileged roles, else union of `UserLotLink` + active `Resident` links" — reused as-is by `PackageService` (see Approach).
- **Migration style for `StrEnum`-backed columns**: confirmed via `0009_add_occurrence_tables.py` — enum columns are created as plain `sa.String()`, never a native Postgres `ENUM` type; validation is Pydantic/application-layer only. `Package.status` follows this convention.

## Data Model

### `backend/app/models/enums.py` — add

```python
class PackageStatus(StrEnum):
    """Enumeration for package pickup status."""

    AWAITING_PICKUP = "AWAITING_PICKUP"
    PICKED_UP = "PICKED_UP"
```

### `backend/app/models/package.py` — new file

```python
"""Database model for Package (encomendas) tracking."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from .enums import PackageStatus

if TYPE_CHECKING:
    from .lot import Lot
    from .user import User


class Package(SQLModel, table=True):
    """A package received at the gatekeeper's desk on behalf of a lot."""

    __tablename__ = "package"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lot_id: UUID = Field(
        foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True
    )
    received_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    description: str | None = Field(default=None)
    carrier: str | None = Field(default=None)
    received_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    status: PackageStatus = Field(
        default=PackageStatus.AWAITING_PICKUP, nullable=False, index=True
    )
    picked_up_at: datetime | None = Field(default=None)
    picked_up_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    picked_up_by_notes: str | None = Field(default=None)

    # Relationships
    lot: "Lot" = Relationship()
    received_by: "User | None" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Package.received_by_id]"}
    )
    picked_up_by: "User | None" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Package.picked_up_by_id]"}
    )
```

**Deviation from the draft**: the draft's `picked_up_by_notes` field alone ("free text: who picked it up, since it may not be a system user") is kept, but a `picked_up_by_id: UUID | None` FK to `User` is *added*. Rationale: the pickup-confirmation UI (see Frontend) needs to record *which authenticated user* (if any) actually confirmed pickup — e.g. the gatekeeper who processed it, or a resident who marks their own pickup (see RBAC decision below) — for audit purposes, exactly as `received_by_id` records who logged the arrival. `picked_up_by_notes` remains for the actual person who physically took the package, who is very often not a system user at all (e.g. "esposa do morador," "porteiro entregou ao filho"). Both fields are optional and independent: `picked_up_by_id` is who *confirmed the action in the app*, `picked_up_by_notes` is free text describing who *physically received it*.

No `Lot` model changes needed — `Package` only adds a reverse FK, no back-reference relationship required on `Lot` for this task (no page renders "all packages" from the `Lot` object graph; `PackageService` queries `Package` directly by `lot_id`).

### Migration — `backend/alembic/versions/<next_free_number>_add_package_table.py`

Follow `0009_add_occurrence_tables.py`'s style exactly (plain `sa.String()` for the `status` enum column, explicit indexes, explicit FKs with `ondelete`). **The exact filename, `revision`, and `down_revision` below are placeholders — do not paste them as-is.** Run `cd backend && uv run alembic heads` immediately before creating this file, confirm there is a single head, set `down_revision` to that head's revision id, and name this revision the next free sequence number after it (e.g. if the head is `0021_add_feedback_table`, this becomes `0022_add_package_table`):

```python
"""add_package_table

Revision ID: <next_free_number>_add_package_table
Revises: <actual current head reported by `alembic heads`>
Create Date: 2026-08-28

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "<next_free_number>_add_package_table"
down_revision: Union[str, Sequence[str], None] = "<actual current head reported by `alembic heads`>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "package",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("received_by_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("carrier", sa.String(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("picked_up_at", sa.DateTime(), nullable=True),
        sa.Column("picked_up_by_id", sa.Uuid(), nullable=True),
        sa.Column("picked_up_by_notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["received_by_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["picked_up_by_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_package_lot_id", "package", ["lot_id"])
    op.create_index("ix_package_status", "package", ["status"])


def downgrade() -> None:
    op.drop_index("ix_package_status", table_name="package")
    op.drop_index("ix_package_lot_id", table_name="package")
    op.drop_table("package")
```

**Before implementing**, run `cd backend && uv run alembic heads` again immediately before opening a PR (heads can move between spec-writing and implementation, and again between implementation and merge) — always chain `down_revision` off whatever single head that command reports at the time, and number this file's revision id as the next free sequence number after it. Do not assume any specific number from this document is still current.

### `backend/app/models/__init__.py`

Add `Package` and `PackageStatus` to the imports and `__all__` list, following the existing pattern (e.g. next to `Occurrence`/`OccurrenceStatus`).

## RBAC

| Action | Allowed roles | Notes |
|---|---|---|
| Create (log arrival) | `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `PORTEIRO` | Mirrors `_assert_gatekeeper_access` exactly. A gatekeeper-desk function; residents cannot log their own package arrival (they didn't receive it at the gate). |
| Mark picked up | `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `PORTEIRO`, **or** the resident linked to the package's `lot_id` (via `UserLotLink` or active `Resident`) | See "Can a resident mark their own pickup?" below. |
| List packages for a lot | `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `PORTEIRO` (any lot) **or** any authenticated user whose linked lots (via `VisitorService.get_user_linked_lot_ids`) include the requested `lot_id` | A resident can only query their own lot(s); passing a `lot_id` they are not linked to returns `403`, not an empty list (avoid silently hiding the access-control decision from the caller). |
| List all `AWAITING_PICKUP` packages (gatekeeper queue) | `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `PORTEIRO` | No `lot_id` filter — this is the Gatekeeper Dashboard's "packages awaiting pickup" queue across all lots. |
| Get single package by id | Same visibility rule as "list packages for a lot," evaluated against that package's `lot_id` | `404` if not found, `403` if found but caller has no lot access (do not leak existence to an unauthorized caller — return `403` after confirming role/lot-link mismatch, consistent with how `OccurrenceService._check_user_access` is used, but note Occurrence returns 404-shaped `OccurrenceAccessForbiddenError`→403 for its own reasons; here just return `403` directly, there's no public/anonymous nuance to preserve). |
| `GUEST` role | No access to any package endpoint, on every route (`create_package`, `get_packages_for_lot`, `get_awaiting_pickup_queue`, `get_package_by_id`, `mark_picked_up`, `get_my_lots`) — matches `GUEST`'s no-access convention elsewhere (e.g. `_LOT_READ_ROLES`, task RBAC). **This must be an explicit role check in `PackageService`, not an implicit side-effect of the linked-lots lookup**: nothing in `backend/app/services/visitor_service.py` (`get_user_linked_lot_ids`, lines 94-117) or `backend/app/services/lot_service.py` (`link_user`, line 173) prevents a `GUEST`-role user from having a `UserLotLink` or active `Resident` row, so a naive "gatekeeper roles bypass, everyone else checked via linked lots" implementation would silently grant a linked `GUEST` account access. `_assert_lot_access` and `get_my_lots` below both reject `UserRole.GUEST` explicitly before ever calling `get_user_linked_lot_ids`. |

### Can a resident mark their own pickup? — resolved (yes, with limits)

The draft leaves this open. Decision: **yes**, a resident linked to the lot (owner, tenant, or active household member via `UserLotLink`/`Resident`) can mark their own lot's `AWAITING_PICKUP` package as `PICKED_UP`, in addition to gatekeeper-desk roles. Rationale:
- The physical reality this models is "the package left the gatekeeper's custody," which most commonly *is* observed by the gatekeeper at time of physical handoff, but residents also legitimately encounter this desk-status being stale (e.g. a night-shift porteiro forgets to mark it) and the least-friction fix is letting the resident self-report once they've physically collected it — consistent with this app's general bias toward giving residents direct self-service actions on their own lot's data (residents create their own `VisitorAuthorization`s and occurrences today without staff mediation).
- This does **not** weaken any access-control property: a resident can only affect their *own* lot's packages (enforced via the same `get_user_linked_lot_ids` check used for reads), and the action only transitions `AWAITING_PICKUP → PICKED_UP` (one-way; see below) — there's no way to abuse self-service pickup-marking to see or affect another lot's data or to fabricate a false "received" event (that still requires gatekeeper-desk role).
- When a resident marks their own pickup, `picked_up_by_id` is set to that resident's own `current_user.id` and `picked_up_by_notes` defaults to `None` unless the resident supplies free text (the UI offers an optional notes field, e.g. "retirado por mim").

A package already `PICKED_UP` cannot be marked picked up again by anyone (idempotency: raise a domain error, `PackageAlreadyPickedUpError`, mapped to `409 Conflict`) — there is no "un-pickup" action in this task (see Non-Goals).

### Old `AWAITING_PICKUP` packages / retention — resolved

No automatic archival, expiry, or deletion job. `Package` rows are never soft- or hard-deleted by this task (no `DELETE` endpoint at all — matches the fact that a package record is an immutable receipt-of-custody event, closer to `AccessLog` than to `Lot`/`Category`, and `AccessLog` likewise has no delete endpoint today). An old `AWAITING_PICKUP` package simply stays visible indefinitely in both the gatekeeper queue and the resident's own-lot view until explicitly marked picked up — this is a deliberate, simple v1 behavior; a future task could add a "flag as lost/returned to sender" terminal status if that need materializes, but it is explicitly out of scope here (see Non-Goals).

## Backend — file/function changes

### `backend/app/core/exceptions.py` — add

```python
class PackageNotFoundError(DomainError):
    """Raised when a package is not found."""

    def __init__(self, package_id: UUID | str = "") -> None:
        msg = f"Encomenda {package_id} não encontrada." if package_id else "Encomenda não encontrada."
        super().__init__(msg)


class PackageAccessForbiddenError(DomainError):
    """Raised when access to a package or lot's packages is forbidden."""

    def __init__(self, message: str = "Acesso negado às encomendas deste lote.") -> None:
        super().__init__(message)


class PackageAlreadyPickedUpError(DomainError):
    """Raised when attempting to mark an already-picked-up package as picked up again."""

    def __init__(self, message: str = "Esta encomenda já foi retirada.") -> None:
        super().__init__(message)
```

### `backend/app/core/exception_handlers.py`

Register the three new exceptions in `domain_exception_handler`:
- `PackageNotFoundError` → join the existing `...NotFoundError` group → `404`.
- `PackageAccessForbiddenError` → join the existing `ForbiddenError`/`...AccessForbiddenError` group → `403`.
- `PackageAlreadyPickedUpError` → new `409` branch (mirror how `InvoiceFileTooLargeError`/`FinanceCategoryTypeMismatchError`-style single-exception `elif` branches are already handled for other one-off status codes in this file — read the current file at implementation time to match its exact `elif` chain shape).

### `backend/app/schemas/package.py` — new file

```python
"""Pydantic schemas for Package (encomendas) tracking."""

from datetime import datetime
from uuid import UUID

from app.models.enums import PackageStatus
from pydantic import BaseModel, ConfigDict


class PackageCreate(BaseModel):
    lot_id: UUID
    description: str | None = None
    carrier: str | None = None


class PackagePickup(BaseModel):
    picked_up_by_notes: str | None = None


class LotSummaryRead(BaseModel):
    id: UUID
    block: str
    lot_number: str


class PackageRead(BaseModel):
    id: UUID
    lot_id: UUID
    lot_summary: LotSummaryRead | None = None
    received_by_id: UUID | None = None
    received_by_name: str | None = None
    description: str | None = None
    carrier: str | None = None
    received_at: datetime
    status: PackageStatus
    picked_up_at: datetime | None = None
    picked_up_by_id: UUID | None = None
    picked_up_by_name: str | None = None
    picked_up_by_notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedPackageRead(BaseModel):
    items: list[PackageRead]
    total: int
    skip: int
    limit: int
```

`received_by_name`/`picked_up_by_name` are resolved server-side in the service layer, matching `OccurrenceService._build_occurrence_read`'s `assigned_to_name` resolution pattern exactly (look up the `User` by id, fall back through `full_name or email`, `None` if the FK is null) — not raw joins exposed to the client.

**Intentional deviation from the `Occurrence` precedent**: `OccurrenceRead.lot_summary` (`backend/app/schemas/occurrence.py`) is a plain `str | None` (a pre-formatted "Quadra X, Lote Y" string). `PackageRead.lot_summary` here is instead the structured `LotSummaryRead` object (`id`/`block`/`lot_number`), not a string. This is a deliberate, explicit divergence, not a copy of the Occurrence shape: the resident-facing `/packages` page (see Frontend) needs to group a resident's packages by lot and needs each lot's `id` to build query keys/links, so a pre-flattened display string alone is insufficient — the frontend needs the structured fields to render its own grouping/heading, with `block`/`lot_number` available for exactly the same "Quadra {block}, Lote {lot_number}" display Occurrence's flattened string would have produced.

### `backend/app/services/package_service.py` — new file

Mirrors `occurrence_service.py`'s shape:

```python
class PackageService:
    _GATEKEEPER_ROLES = (
        UserRole.ADMINISTRATOR,
        UserRole.DIRECTOR,
        UserRole.MANAGER,
        UserRole.PORTEIRO,
    )

    @staticmethod
    def _build_package_read(session: Session, package: Package) -> PackageRead: ...
    # resolves lot_summary via session.get(Lot, package.lot_id) -> LotSummaryRead(id=lot.id, block=lot.block, lot_number=lot.lot_number)
    # resolves received_by_name / picked_up_by_name via session.get(User, ...) -> full_name or email, same null-guard pattern as Occurrence's assigned_to_name

    @staticmethod
    def _assert_gatekeeper_role(current_user: User) -> None:
        if current_user.role not in PackageService._GATEKEEPER_ROLES:
            raise PackageAccessForbiddenError(
                "Apenas administradores, diretores, gerentes e porteiros podem registrar encomendas."
            )

    @staticmethod
    def _assert_lot_access(session: Session, lot_id: UUID, current_user: User) -> None:
        """Gatekeeper roles: unrestricted. GUEST: always denied. Everyone else: must be linked to lot_id."""
        if current_user.role in PackageService._GATEKEEPER_ROLES:
            return
        if current_user.role == UserRole.GUEST:
            # Explicit reject before the linked-lots lookup below: GUEST accounts are not
            # barred from having a UserLotLink/Resident row at the data-model level (see
            # backend/app/services/visitor_service.py:94-117 and
            # backend/app/services/lot_service.py:173 — neither prevents a GUEST-role user
            # from being linked to a lot), so relying on get_user_linked_lot_ids alone would
            # silently grant a linked GUEST access. GUEST must never see or act on package
            # data regardless of any lot linkage it happens to have.
            raise PackageAccessForbiddenError()
        linked_lot_ids = VisitorService.get_user_linked_lot_ids(session, current_user)
        if lot_id not in linked_lot_ids:
            raise PackageAccessForbiddenError()

    @classmethod
    def create_package(cls, session, current_user, package_in: PackageCreate) -> PackageRead:
        cls._assert_gatekeeper_role(current_user)
        lot = session.get(Lot, package_in.lot_id)
        if not lot:
            raise LotNotFoundError(package_in.lot_id)
        package = Package(
            lot_id=package_in.lot_id,
            received_by_id=current_user.id,
            description=package_in.description,
            carrier=package_in.carrier,
            received_at=datetime.utcnow(),
            status=PackageStatus.AWAITING_PICKUP,
        )
        session.add(package)
        session.commit()
        session.refresh(package)
        return cls._build_package_read(session, package)

    @classmethod
    def get_packages_for_lot(cls, session, current_user, lot_id, status=None, skip=0, limit=100) -> tuple[list[PackageRead], int]:
        cls._assert_lot_access(session, lot_id, current_user)
        # query Package where lot_id == lot_id [and status == status], order by received_at desc, paginate
        ...

    @classmethod
    def get_awaiting_pickup_queue(cls, current_user, session, skip=0, limit=100) -> tuple[list[PackageRead], int]:
        cls._assert_gatekeeper_role(current_user)
        # query Package where status == AWAITING_PICKUP across all lots, order by received_at asc (oldest-waiting first), paginate
        ...

    @classmethod
    def get_package_by_id(cls, session, current_user, package_id) -> PackageRead:
        package = session.get(Package, package_id)
        if not package:
            raise PackageNotFoundError(package_id)
        cls._assert_lot_access(session, package.lot_id, current_user)
        return cls._build_package_read(session, package)

    @classmethod
    def mark_picked_up(cls, session, current_user, package_id, pickup_in: PackagePickup) -> PackageRead:
        package = session.get(Package, package_id)
        if not package:
            raise PackageNotFoundError(package_id)
        cls._assert_lot_access(session, package.lot_id, current_user)  # gatekeeper roles OR linked resident
        if package.status == PackageStatus.PICKED_UP:
            raise PackageAlreadyPickedUpError()
        package.status = PackageStatus.PICKED_UP
        package.picked_up_at = datetime.utcnow()
        package.picked_up_by_id = current_user.id
        package.picked_up_by_notes = pickup_in.picked_up_by_notes
        session.commit()
        session.refresh(package)
        return cls._build_package_read(session, package)
```

Import `VisitorService` from `app.services.visitor_service` for `get_user_linked_lot_ids` reuse (no circular-import risk: `visitor_service.py` does not import `package_service.py`).

### `backend/app/api/v1/endpoints/packages.py` — new file

Routes (all `Depends(deps.get_current_user)`-gated; RBAC enforced in the service layer per this codebase's convention, matching `occurrences.py`/`projects.py`):

- `POST /packages` → `PackageCreate` body → `PackageService.create_package` → `201`.
- `GET /packages?lot_id=&status=&skip=&limit=` → if `lot_id` given, `PackageService.get_packages_for_lot`; if omitted, require gatekeeper role and call `PackageService.get_awaiting_pickup_queue` when `status=AWAITING_PICKUP` is also given or defaulted — simplify: `lot_id` is **required** as a query param for non-gatekeeper roles (endpoint itself doesn't need to branch on role; the service methods already do). Concretely: expose two endpoints instead of overloading one, matching this codebase's existing preference for explicit routes over param-driven branching (e.g. `authorizations.py`'s per-lot list vs `access_logs.py`'s cross-lot list are separate routes already):
  - `GET /packages?lot_id={uuid}&status=&skip=&limit=` → `PackageService.get_packages_for_lot` (lot_id required, `422` if missing).
  - `GET /packages/queue?skip=&limit=` → `PackageService.get_awaiting_pickup_queue` (gatekeeper roles only; always `status=AWAITING_PICKUP`, no filter param needed since that's the whole point of "the queue").
- `GET /packages/{package_id}` → `PackageService.get_package_by_id`.
- `POST /packages/{package_id}/pickup` → `PackagePickup` body → `PackageService.mark_picked_up` → `200`.

Response models: `PaginatedPackageRead` for list/queue endpoints, `PackageRead` for create/get/pickup.

### `backend/app/api/v1/api.py`

Add `from app.api.v1.endpoints import ..., packages, ...` and `api_router.include_router(packages.router, prefix="/packages", tags=["packages"])`.

## Frontend

### New types — `frontend/src/types/package.ts`

```typescript
export enum PackageStatus {
  AWAITING_PICKUP = "AWAITING_PICKUP",
  PICKED_UP = "PICKED_UP",
}

export interface LotSummary {
  id: string;
  block: string;
  lot_number: string;
}

export interface Package {
  id: string;
  lot_id: string;
  lot_summary: LotSummary | null;
  received_by_id: string | null;
  received_by_name: string | null;
  description: string | null;
  carrier: string | null;
  received_at: string;
  status: PackageStatus;
  picked_up_at: string | null;
  picked_up_by_id: string | null;
  picked_up_by_name: string | null;
  picked_up_by_notes: string | null;
}

export interface PackageCreate {
  lot_id: string;
  description?: string;
  carrier?: string;
}

export interface PackagePickup {
  picked_up_by_notes?: string;
}

export interface PaginatedPackages {
  items: Package[];
  total: number;
  skip: number;
  limit: number;
}
```

### New API client — `frontend/src/api/packages.ts`

Mirror `frontend/src/api/visitors.ts`'s shape: `createPackage`, `getPackagesForLot(lotId, status?, skip?, limit?)`, `getPackageQueue(skip?, limit?)`, `getPackage(id)`, `markPackagePickedUp(id, data)` — all thin wrappers around the shared `apiClient` from `src/api/client.ts`.

### New hooks — `frontend/src/features/visitor-management/hooks/usePackages.ts`

Mirror `useVisitors.ts`'s shape:
- `usePackageQueue(skip?, limit?)` → `useQuery(["package-queue", skip, limit], ...)`.
- `usePackagesForLot(lotId?, status?, skip?, limit?)` → `useQuery(["packages", lotId, status, skip, limit], ...)`, `enabled: !!lotId`.
- `useCreatePackage()` → `useMutation`, invalidates `["package-queue"]` and `["packages", variables.lot_id]` on success.
- `useMarkPackagePickedUp()` → `useMutation`, invalidates `["package-queue"]` and `["packages"]` (broad invalidate is fine here — package volume per lot is low, no pagination-thrashing concern like `tasks`).

Placed under `visitor-management/hooks/` rather than a new `package-management/` feature directory, since this is a Gatekeeper Dashboard sub-feature reusing that feature's existing lot-selection UI (per the draft's own framing) — not a big enough surface to justify a new top-level feature folder on the backend-adjacent side. The one exception is the resident-facing page (below), which does get its own minimal feature directory since it's a distinct route/audience.

### `GatekeeperDashboard.tsx` — add "Encomendas" section

Add a new collapsible/tabbed section (reuse the existing card styling already used for the Search/Timeline columns) with two parts:

1. **Log arrival form**: lot selector (reuse the dashboard's existing `selectedLotId` state and `<select>` populated from `useLots()` — same lot list already rendered for check-in), plus `description` and `carrier` text inputs, and a "Registrar encomenda" button calling `useCreatePackage().mutateAsync({ lot_id: selectedLotId, description, carrier })`. Disabled while `!selectedLotId`, matching the existing check-in button's disabled pattern.
2. **Awaiting-pickup queue**: a list fed by `usePackageQueue()`, each row showing lot (`Quadra {block}, Lote {lot_number}` from `lot_summary`), `description`/`carrier`, `received_at` (relative or formatted date), and a "Confirmar retirada" button opening a small inline confirm (optional `picked_up_by_notes` text input, e.g. "Retirado por: ___") that calls `useMarkPackagePickedUp().mutateAsync({ id, data: { picked_up_by_notes } })`.

New i18n namespace `packages.*` in `en.json`/`pt.json` (e.g. `packages.title`, `packages.logArrival`, `packages.carrier`, `packages.description`, `packages.awaitingPickup`, `packages.confirmPickup`, `packages.pickedUpBy`, `packages.noPackages`).

### New resident-facing page — `frontend/src/features/package-management/components/PackageStatusPage.tsx`

A new minimal feature directory `frontend/src/features/package-management/` (`components/PackageStatusPage.tsx`, `hooks/usePackages.ts` — this one calling the resident-facing `GET /packages?lot_id=` path for the current user's own linked lot(s), not the gatekeeper queue).

A resident may be linked to more than one lot (e.g. owns two units), and `get_packages_for_lot` takes a single `lot_id` by design (it matches the RBAC table's per-lot scoping). The page therefore needs the caller's own lot ID(s) up front, and no existing endpoint provides that for a `RESIDENT` caller — `GET /api/v1/lots/` is gated by `_LOT_READ_ROLES` (excludes `RESIDENT`, out of scope to change here).

**Decision**: add one small, package-scoped convenience endpoint, `GET /packages/my-lots`, returning `list[LotSummaryRead]` — the lots resolved via `VisitorService.get_user_linked_lot_ids` for the current user. This endpoint is for non-gatekeeper, non-`GUEST` callers only:
- Gatekeeper roles (`ADMINISTRATOR`/`DIRECTOR`/`MANAGER`/`PORTEIRO`) get `403` from it and should use `GET /packages/queue` instead — `get_user_linked_lot_ids` would otherwise return literally every lot in the building for these roles, which isn't a useful "my lots" answer.
- `GUEST` gets `403` from it, explicitly — same reasoning as `_assert_lot_access` above (a `GUEST` account is not prevented at the data-model level from having a `UserLotLink`/`Resident` row, so this must be an explicit role check, not an implicit fall-through of the linked-lots lookup).

Add `PackageService.get_my_lots(session, current_user) -> list[LotSummaryRead]`:

```python
@classmethod
def get_my_lots(cls, session: Session, current_user: User) -> list[LotSummaryRead]:
    if current_user.role in PackageService._GATEKEEPER_ROLES:
        raise PackageAccessForbiddenError(
            "Use /packages/queue para ver encomendas de todos os lotes."
        )
    if current_user.role == UserRole.GUEST:
        raise PackageAccessForbiddenError()
    lot_ids = VisitorService.get_user_linked_lot_ids(session, current_user)
    lots = session.exec(select(Lot).where(Lot.id.in_(lot_ids))).all()
    return [LotSummaryRead(id=lot.id, block=lot.block, lot_number=lot.lot_number) for lot in lots]
```

and route `GET /packages/my-lots` in `packages.py`.

`PackageStatusPage.tsx` then: on mount, calls `useMyLots()` (new hook wrapping `GET /packages/my-lots`); for each returned lot, calls `usePackagesForLot(lot.id)` (or a single new combined hook `useMyPackages()` doing both calls sequentially via `useQueries`); renders a simple list grouped by lot (block/lot_number heading) showing each package's carrier/description/received_at/status, with a "Já retirei" ("I already picked this up") button on `AWAITING_PICKUP` rows calling `useMarkPackagePickedUp()` — this is the resident-self-pickup path described in RBAC above.

### `App.tsx` / `Navbar.tsx`

New route:
```tsx
<Route
  path="/packages"
  element={
    <ProtectedRoute
      requiredRoles={[
        UserRole.ADMINISTRATOR,
        UserRole.DIRECTOR,
        UserRole.MANAGER,
        UserRole.RESIDENT,
      ]}
    >
      <PackageStatusPage />
    </ProtectedRoute>
  }
/>
```
`GUEST` and `PORTEIRO` excluded — `GUEST` is explicitly barred from all package data per the RBAC rule above (regardless of any lot linkage it happens to have) so this route would only ever show it an empty/forbidden state, and `PORTEIRO` already has the full queue in `/gate`. `ADMINISTRATOR`/`DIRECTOR`/`MANAGER` are included so staff can use the same simple lookup view for any lot they're linked to, though in practice they'll mostly use the Gatekeeper Dashboard queue.

Nav link in `Navbar.tsx`: add alongside the other `effectiveRole !== UserRole.PORTEIRO` / `!== UserRole.GUEST`-gated links (e.g. next to `/occurrences`), labeled `t("nav.packages", "Encomendas")`.

## Non-Goals

- No photo-of-package capture (per the draft; a future enhancement, not core to this parity gap).
- No SMS/push/email "your package arrived" notification — no such infrastructure exists in this app (per APRAS-26's roadmap notes); this is in-app-only, pull-based status checking (the resident must visit `/packages` to see it), not a push-based alert.
- No "un-pickup" / status-reversal action — `PICKED_UP` is terminal; a mis-click can only be corrected by an `ADMINISTRATOR` via direct DB access, same as this app's general lack of undo on terminal domain-state transitions elsewhere (e.g. `AccessLog` check-out has no undo).
- No automatic archival, expiry, or "lost package" terminal status for long-unclaimed `AWAITING_PICKUP` packages — they remain visible indefinitely (see "Old packages / retention" above). A future task can add this if it becomes an operational problem.
- No bulk logging of multiple packages in one submission — one package per create call, matching the granularity of `AccessLog`'s one-visitor-per-check-in.
- No changes to `_LOT_READ_ROLES` in `lots.py` — the pre-existing `RESIDENT`-excluded-from-`/lots`-reads gap identified above is out of scope for this task.
- No `DELETE /packages/{id}` endpoint — packages are immutable receipt records (see "Old packages / retention" above).

## Testing

### Backend (pytest, mirror `test_lots_rbac.py` / occurrence RBAC test structure)

- `create_package`: `ADMINISTRATOR`/`DIRECTOR`/`MANAGER`/`PORTEIRO` succeed (`201`); `RESIDENT`/`GUEST` get `403`; nonexistent `lot_id` gets `404`.
- `get_packages_for_lot`: gatekeeper roles can query any `lot_id`; a `RESIDENT` linked to the lot (via `UserLotLink`) can query it; a `RESIDENT` linked via an active `Resident` row can query it; a `RESIDENT` linked to a *different* lot gets `403` on this lot's query; `GUEST` gets `403` even when given a `lot_id` it *is* linked to via `UserLotLink`/`Resident` (this is the specific bypass scenario the RBAC review flagged — assert it explicitly, don't just test an unlinked `GUEST`).
- `get_awaiting_pickup_queue`: gatekeeper roles get `200` with cross-lot results; `RESIDENT` gets `403`; `GUEST` gets `403`.
- `get_package_by_id`: gatekeeper roles can fetch any package; a linked `RESIDENT` can fetch their own lot's package; a `RESIDENT` linked to a different lot gets `403`; `GUEST` gets `403` even when linked to the package's lot; nonexistent id gets `404`.
- `get_my_lots`: `RESIDENT` gets their linked lot(s); gatekeeper-role caller gets `403` (must use the queue instead); `GUEST` gets `403` even when linked to a lot via `UserLotLink`/`Resident`.
- `mark_picked_up`: gatekeeper roles succeed on any lot's package; a linked `RESIDENT` succeeds on their own lot's package and `picked_up_by_id` is set to that resident's id; a `RESIDENT` linked to a different lot gets `403`; `GUEST` gets `403` even when linked to the package's lot via `UserLotLink`/`Resident`; marking an already-`PICKED_UP` package again returns `409` (`PackageAlreadyPickedUpError`) regardless of caller role.
- `PackageRead` serialization: `lot_summary`, `received_by_name`, `picked_up_by_name` populate correctly and are `null` when the underlying FK is null (e.g. `received_by_id` after the referencing user is deleted, per `ondelete="SET NULL"`).
- Migration: `alembic upgrade head` / `alembic downgrade -1` round-trip cleanly against the test DB fixture (mirrors existing migration test conventions if this repo runs one — check `backend/tests/` for an existing "migrations apply cleanly" test pattern and follow it; if none exists, this is just verified manually via CI's migrate step, not a new dedicated test).

### Frontend (Vitest + @testing-library/react)

- `GatekeeperDashboard`: "Encomendas" section renders the log-arrival form and the awaiting-pickup queue; submitting the form with a selected lot calls `useCreatePackage`'s mutation with the right payload and the form disables while `!selectedLotId`; clicking "Confirmar retirada" on a queue row calls `useMarkPackagePickedUp` with that package's id.
- `PackageStatusPage`: renders packages grouped by the resident's own linked lot(s) (mock `useMyLots`/`usePackagesForLot`); "Já retirei" button on an `AWAITING_PICKUP` row calls the pickup mutation; a resident with zero linked lots sees an empty-state message, not an error.
- `usePackages`/`usePackageQueue` hooks: query keys and invalidation-on-mutation-success behavior (mirror `useVisitors.test.tsx`'s structure).

## Expected Results

1. A user with `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, or `PORTEIRO` role can log a new package's arrival for a given lot from the "Encomendas" section of `GatekeeperDashboard.tsx`, and it appears in the awaiting-pickup queue.
2. That same set of roles can mark a package as picked up from the queue, optionally recording free-text notes about who physically collected it; the package then disappears from the awaiting-pickup queue.
3. A `RESIDENT` user linked to a lot (via direct account link or active household-member `Resident` record) can view that lot's packages at `/packages`, and can mark their own lot's `AWAITING_PICKUP` package as picked up; they cannot view or affect another lot's packages (`403`).
4. `GUEST` users have no access to any package endpoint or the `/packages` page.
5. Marking an already-`PICKED_UP` package as picked up again is rejected with `409 Conflict`, regardless of caller role.
6. The new `package` table, its migration, and all new backend/frontend code pass CI's existing coverage gates (90% backend / 75% frontend) with no `RESIDENT`/`GUEST` cross-lot data leakage in any package endpoint response.
</content>
