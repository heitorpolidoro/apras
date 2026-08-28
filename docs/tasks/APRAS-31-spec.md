# APRAS-31 — Implement Space/Amenity Reservation System

**Date:** 2026-08-28
**Status:** Approved for implementation

## Source

This spec turns "Architectural Spec A — Space/Amenity Reservations" in `docs/tasks/APRAS-26-analysis.md` into a concrete, buildable task. The draft's core shape (two models, admin-managed spaces + resident bookings, mandatory server-side double-booking check, no recurring reservations, no payments) is carried forward. Several gaps in the draft are resolved below (approval-vs-auto-confirm flow, cancellation rules, edit-after-creation, masking of other users' bookings, notification behavior, exact RBAC per action, exact migration number) — each documented with its rationale where it isn't a mechanical copy of an existing pattern.

## Problem

Residents currently have no way to book shared amenities (party room, gym, pool, BBQ area, etc.). There is no availability calendar and no self-service booking flow anywhere in APRAS. This is a named parity gap versus COM21 (see APRAS-26).

## Scope

This task delivers:
1. Admin-managed `ReservableSpace` definitions (name, description, capacity, whether booking requires approval, active flag).
2. Resident (and staff) self-service `SpaceReservation` booking against a space, with a mandatory server-side double-booking check.
3. An approval workflow for spaces flagged `requires_approval`.
4. A cancellation flow.
5. Frontend: an admin CRUD screen for spaces, and a resident-facing booking view per space showing existing bookings and a create-reservation form.

This task does **not** cover recurring reservations, payment/fee collection, push/email notifications, or a full calendar-library UI (see Non-Goals).

## Data Model

### `backend/app/models/enums.py` — add

```python
class ReservationStatus(StrEnum):
    """Enumeration for space reservation status."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
```

### `backend/app/models/reservation.py` (new file)

```python
"""Database models for ReservableSpace and SpaceReservation."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ReservationStatus

if TYPE_CHECKING:
    from app.models.lot import Lot
    from app.models.user import User


class ReservableSpace(SQLModel, table=True):
    """Admin-managed definition of a bookable shared amenity."""

    __tablename__ = "reservable_space"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, nullable=False)
    description: str | None = Field(default=None)
    capacity: int | None = Field(default=None)
    requires_approval: bool = Field(default=False, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    reservations: list["SpaceReservation"] = Relationship(back_populates="space")


class SpaceReservation(SQLModel, table=True):
    """A resident/staff booking of a ReservableSpace for a specific time window."""

    __tablename__ = "space_reservation"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    space_id: UUID = Field(
        foreign_key="reservable_space.id", ondelete="CASCADE", nullable=False, index=True
    )
    reserved_by_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    lot_id: UUID | None = Field(
        default=None, foreign_key="lot.id", ondelete="SET NULL", nullable=True, index=True
    )
    start_time: datetime = Field(nullable=False, index=True)
    end_time: datetime = Field(nullable=False)
    status: ReservationStatus = Field(
        default=ReservationStatus.PENDING, nullable=False, index=True
    )
    notes: str | None = Field(default=None)
    decided_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    decided_at: datetime | None = Field(default=None)
    cancelled_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    space: "ReservableSpace" = Relationship(back_populates="reservations")
    reserved_by: "User" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SpaceReservation.reserved_by_id]"}
    )
    decided_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SpaceReservation.decided_by_id]"}
    )
    lot: Optional["Lot"] = Relationship()
```

Notes on deviations from the APRAS-26 draft:
- Added `created_at` to `ReservableSpace` (every other admin-managed/audit-relevant table in this codebase has it; `Category` is the sole exception and is the oldest table in the schema — not worth copying that omission forward).
- Added `decided_by_id`/`decided_at`/`cancelled_at` to `SpaceReservation`. The draft's model had only `status` with no record of who approved/rejected/cancelled a reservation or when — every other approval-style workflow in this codebase (`MediaAsset.approved_by_id`/`approved_at`, `Feedback.responded_by_id`/`responded_at`) records the actor and timestamp of the decision. Omitting it here would be an inconsistency, not a simplification.
- `name` is `unique=True` on `ReservableSpace`, matching `Category.name`'s uniqueness constraint (the admin-managed-label pattern this mirrors).
- Both FKs on `SpaceReservation` and `space_id`'s `ondelete="CASCADE"` are exactly as the draft specified. In practice `ReservableSpace` is only ever soft-deactivated via the API (see RBAC below), never hard-deleted, so the cascade is a safety net for direct DB maintenance, not a normal code path.

### Migration

Current alembic head (verified by walking `down_revision` chains in `backend/alembic/versions/`) is **`0021_add_feedback_table`** (landed via the concurrently-merged APRAS-25) — a single linear head, no open branches. **Re-verify with `alembic heads` at implementation time** in case another task has merged since this spec was written; do not assume `0021_add_feedback_table` is still current without checking — the code block below is a concrete example to adapt, not a value to copy-paste blindly if the real head has moved again.

New revision: `backend/alembic/versions/0022_add_space_reservation_tables.py`, `down_revision = "0021_add_feedback_table"`.

Follow `0009_add_occurrence_tables.py`'s exact conventions: plain `sa.String()` columns for the `status`/enum-like fields (no native Postgres `ENUM` type, no `CREATE TYPE`) — enum validation happens only at the Pydantic/SQLModel `StrEnum` layer, consistent with how `OccurrenceStatus`, `FeedbackStatus`, etc. are all stored.

```python
def upgrade() -> None:
    op.create_table(
        "reservable_space",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_reservable_space_name", "reservable_space", ["name"])

    op.create_table(
        "space_reservation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("reserved_by_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["space_id"], ["reservable_space.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reserved_by_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_space_reservation_space_id", "space_reservation", ["space_id"])
    op.create_index("ix_space_reservation_reserved_by_id", "space_reservation", ["reserved_by_id"])
    op.create_index("ix_space_reservation_lot_id", "space_reservation", ["lot_id"])
    op.create_index("ix_space_reservation_start_time", "space_reservation", ["start_time"])
    op.create_index("ix_space_reservation_status", "space_reservation", ["status"])
    # Composite index supporting the double-booking overlap query (WHERE space_id = ? AND status IN (...) AND ...).
    op.create_index(
        "ix_space_reservation_space_status_time",
        "space_reservation",
        ["space_id", "status", "start_time", "end_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_space_reservation_space_status_time", table_name="space_reservation")
    op.drop_index("ix_space_reservation_status", table_name="space_reservation")
    op.drop_index("ix_space_reservation_start_time", table_name="space_reservation")
    op.drop_index("ix_space_reservation_lot_id", table_name="space_reservation")
    op.drop_index("ix_space_reservation_reserved_by_id", table_name="space_reservation")
    op.drop_index("ix_space_reservation_space_id", table_name="space_reservation")
    op.drop_table("space_reservation")

    op.drop_index("ix_reservable_space_name", table_name="reservable_space")
    op.drop_table("reservable_space")
```

## RBAC — exact rules per action

`ReservableSpace` (mirrors `Category`'s admin-managed-label pattern in `backend/app/api/v1/endpoints/categories.py` exactly, including its `_require_*_write_permission`-style helper and plain `HTTPException`, not a `DomainError` subclass):

| Action | Rule |
|---|---|
| List spaces (`GET`) | Any authenticated user, **including `GUEST`** — mirrors the broad resident-facing read access already granted to `GUEST` on `/occurrences`, `/documents`, `/projects`, `/lots`, `/authorizations`, `/announcements` (see `frontend/src/App.tsx`'s `requiredRoles` lists). Browsing what amenities exist is informational, not a resource commitment. |
| Create/Update/Deactivate | `ADMINISTRATOR`/`DIRECTOR` only, exactly like `_require_category_write_permission`. |
| Delete | No hard delete exposed via the API — "delete" means `is_active = False` (soft deactivate), matching `CategoryService.delete_category` exactly. |

No `MenuKey`/`assert_menu_access` gating is added for this feature. `MenuKey` currently only has two valid values (`tasks`, `categories`, per `backend/app/models/enums.py` and `AGENTS.md`'s `UserType` section) and is deliberately scoped to those two menus; every other feature shipped after APRAS-8 (`Occurrence`, `Feedback`, `Finance`, `Project`, `Announcement`, `Document`) uses plain role checks only, not the UserType menu gate. Adding a new `MenuKey` value is out of scope here and would require its own APRAS-8-style design pass.

`SpaceReservation`:

| Action | Rule |
|---|---|
| Create | Any authenticated user **except `GUEST`** — mirrors `Task`'s create-role convention (`backend/app/api/v1/endpoints/tasks.py`'s `create_task`: `if current_user.role == UserRole.GUEST: raise ForbiddenError(...)`), not Feedback's "anyone including GUEST" convention. Rationale (per the APRAS-26 draft, confirmed): a reservation is a resource commitment against a shared amenity, unlike free-text feedback; `GUEST` is a restricted/view-only role in this app's broader RBAC intent. |
| List (own space's calendar / own bookings) | Any authenticated user except `GUEST`. See "Visibility & masking" below for exactly what's returned. |
| View one reservation by id | `ADMINISTRATOR`/`DIRECTOR` (any), or the reservation's own `reserved_by_id` (their own). Anyone else gets 404 (not 403 — mirrors `TaskNotFoundError`'s "don't reveal existence" pattern used for `assert_manager_can_see_task`). |
| Approve / Reject a `PENDING` reservation | `ADMINISTRATOR`/`DIRECTOR` only. |
| Cancel | The reservation's own `reserved_by_id` **or** `ADMINISTRATOR`/`DIRECTOR`. See cancellation rules below for the exact state/timing constraints. |
| Edit (change `start_time`/`end_time`/`space_id`/`notes` after creation) | **Not supported.** See "No edit endpoint" decision below. |

### Approval / auto-confirm flow (resolves a gap in the draft)

The draft didn't specify what status a reservation starts at when the space does *not* require approval. Decision:
- `space.requires_approval == False` → new reservation is created directly with `status = CONFIRMED`.
- `space.requires_approval == True` → new reservation is created with `status = PENDING`, awaiting an `ADMINISTRATOR`/`DIRECTOR` decision via the approve/reject endpoint.
- Approve: `PENDING → CONFIRMED`, sets `decided_by_id`/`decided_at`.
- Reject: `PENDING → REJECTED`, sets `decided_by_id`/`decided_at`. A rejected reservation's slot is immediately free for others (rejected is excluded from the double-booking check, see below).
- Approving is **not** unconditional: since two overlapping `PENDING` requests for the same `requires_approval` space can coexist (each individually passed the create-time check against the *other* `CONFIRMED`/`PENDING` rows at the time it was created, but a second one could still be filed before the first is decided), the approve action **re-runs the double-booking check** (excluding the reservation being approved) against that space's current `CONFIRMED` reservations before flipping status. If a conflict is found, approving raises `SpaceReservationConflictError` (409) — the admin must reject this one or resolve the conflict manually; approving does not silently reject the other side.

### Cancellation rules (resolves a gap in the draft)

- Allowed states to cancel from: `PENDING` or `CONFIRMED` only (mirrors `SpaceReservation`'s only two "active/blocking" statuses — the same two the double-booking check considers). Cancelling a `CANCELLED`/`REJECTED` reservation is a no-op 404/409 (not found in an active state).
- **The reserving user** (`reserved_by_id`) may cancel their own reservation only while `start_time` is still in the future (`start_time > now`). This prevents cancelling something already in progress or finished — there is no "no-show" or partial-refund concept since there's no payment (Non-Goals).
- **`ADMINISTRATOR`/`DIRECTOR`** may cancel any reservation regardless of timing (e.g. taking a space out of service for emergency maintenance overrides a resident's booking).
- Cancelling sets `status = CANCELLED` and `cancelled_at = now`; it does not clear `decided_by_id`/`decided_at` if the reservation had already been approved (history is preserved, matching this codebase's general preference for append-only audit fields over destructive updates — see `TaskHistory`, `OccurrenceTimeline`).
- This mirrors the ownership shape of `Occurrence`'s reporter/staff split (a non-privileged actor can only affect their own row; staff — `ADMINISTRATOR`/`DIRECTOR` — can affect any row) rather than `Task`'s broader "any non-Manager staff can edit any task" shape, because a reservation's timing constraint (`start_time` in the future) has no analog in either existing precedent and needed to be decided fresh.

### No edit endpoint (resolves a gap in the draft)

There is no `PATCH /space-reservations/{id}` to change `start_time`/`end_time`/`notes` after creation. To change the time of a booking, the user cancels the existing reservation and creates a new one. Rationale: an edit endpoint would need to re-run the double-booking check against a moving target (excluding the reservation being edited, but only if the edited version doesn't overlap someone else) and would need its own state-machine rules for whether editing a `CONFIRMED` reservation on a `requires_approval` space reopens approval — that's meaningfully more complexity than a v1, one-off-bookings-only feature needs. `Occurrence` and `Feedback` both similarly avoid a general-purpose edit endpoint in favor of explicit status-transition actions; this follows the same shape. `notes` in particular is set once at creation and is not editable afterward (it is not sensitive enough to warrant a dedicated small-edit endpoint on its own, and bundling it with a "real" edit endpoint isn't worth doing for one field).

### Visibility & masking

- `ADMINISTRATOR`/`DIRECTOR`: see full detail (who, lot, notes, status) for every reservation.
- Any other non-`GUEST` user calling `GET /space-reservations?space_id=...` (the "what's already booked" calendar view needed before creating a new reservation) sees every `PENDING`/`CONFIRMED` reservation for that space as a **busy time slot only** — `start_time`, `end_time`, `status` — with `reserved_by_id`/`reserved_by_name`/`lot_id`/`notes` all nulled out, **unless** the row is their own (`reserved_by_id == current_user.id`), in which case they see full detail on their own row. **This is new territory for this codebase, not a precedented pattern** — `Feedback`'s masking (`FeedbackRead` nulling identity fields based on viewer role) only ever hides an anonymous reporter's identity from *staff*; a non-staff `Feedback` viewer never sees another peer's row at all (`list_feedback` restricts non-staff to their own submissions only). There is no existing case in this codebase of one peer seeing another peer's row with some fields nulled out — that mechanism is introduced fresh by this task, and only the general "mask fields based on viewer identity, computed server-side" *shape* is borrowed from `Feedback`, not the specific "who sees what" rule. `CANCELLED`/`REJECTED` reservations are never returned in the calendar view (they're not blocking, and there's no legitimate reason for another resident to see a stranger's rejected/cancelled request).
- `GET /space-reservations?mine=true` returns only the caller's own reservations, full detail, any status — this is their personal booking history. **`mine=true` always wins**, for every role: it restricts the result set to the caller's own rows regardless of role (yes, even `ADMINISTRATOR`/`DIRECTOR`) and regardless of whether `space_id` is also passed (if both are given, the result is the caller's own rows for that specific space, full detail — `space_id` narrows, `mine` never widens). Precedence summary:
  - `mine=true` (with or without `space_id`): caller's own rows only, full detail, any status, for every role.
  - `mine` omitted/false, `space_id` omitted, caller is `ADMINISTRATOR`/`DIRECTOR`: every reservation, full detail (the staff inbox view).
  - `mine` omitted/false, `space_id` omitted, caller is not staff: caller's own rows only, full detail — same result as `mine=true`, just the default for a non-staff caller with no filters (this is the "or no filters, for a non-staff caller" default mentioned above).
  - `mine` omitted/false, `space_id` set, caller is `ADMINISTRATOR`/`DIRECTOR`: every reservation for that space, full detail — staff always get full detail per the unconditional rule above; `space_id` only narrows *which* rows are returned for them, it never triggers masking for a staff caller.
  - `mine` omitted/false, `space_id` set, caller is not staff: the masked busy-slot calendar view described above (others' rows masked, caller's own row, if any, unmasked).

## Backend Changes

### `backend/app/core/exceptions.py` — add

```python
class ReservableSpaceNotFoundError(DomainError):
    """Raised when a reservable space is not found."""

    def __init__(self, space_id: "UUID") -> None:
        super().__init__(f"Reservable space with ID {space_id} not found")


class SpaceReservationNotFoundError(DomainError):
    """Raised when a space reservation is not found or not visible to the caller."""

    def __init__(self, reservation_id: "UUID") -> None:
        super().__init__(f"Reservation with ID {reservation_id} not found")


class SpaceReservationConflictError(DomainError):
    """Raised when a reservation would overlap an existing CONFIRMED/PENDING booking."""

    def __init__(self) -> None:
        super().__init__("This space is already booked for the requested time window")
```

(Reuse the existing generic `ForbiddenError` for all RBAC rejections on `SpaceReservation` actions — no new forbidden-subclass needed, matching how `Task`'s create-role check reuses the generic `ForbiddenError` rather than defining a `TaskForbiddenError`.)

### `backend/app/core/exception_handlers.py`

Add `ReservableSpaceNotFoundError`, `SpaceReservationNotFoundError` to the `404` tuple; add `SpaceReservationConflictError` to the `409` tuple (alongside `ResidentCPFConflictError`, `BudgetLineAlreadyExistsError`, `FinanceCategoryAlreadyExistsError`). Import all three at the top of the file alongside the existing imports.

### `backend/app/schemas/reservation.py` (new file)

```python
"""Schemas for ReservableSpace and SpaceReservation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ReservationStatus


class ReservableSpaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    capacity: int | None = Field(default=None, gt=0)
    requires_approval: bool = False


class ReservableSpaceCreate(ReservableSpaceBase):
    pass


class ReservableSpaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    capacity: int | None = Field(default=None, gt=0)
    requires_approval: bool | None = None
    is_active: bool | None = None


class ReservableSpaceRead(ReservableSpaceBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpaceReservationCreate(BaseModel):
    space_id: UUID
    lot_id: UUID | None = None
    start_time: datetime
    end_time: datetime
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_time_window(self) -> "SpaceReservationCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class SpaceReservationRead(BaseModel):
    id: UUID
    space_id: UUID
    space_name: str | None = None
    reserved_by_id: UUID | None = None
    reserved_by_name: str | None = None
    lot_id: UUID | None = None
    start_time: datetime
    end_time: datetime
    status: ReservationStatus
    notes: str | None = None
    decided_by_id: UUID | None = None
    decided_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpaceReservationDecision(BaseModel):
    """Body for the approve/reject endpoint. No fields needed today (kept as an
    empty model, not a bare 204, so a future rejection-reason field — mirroring
    MediaAsset's rejection_reason — can be added without a breaking route change)."""

    pass
```

`end_time > start_time` validation lives in the Pydantic schema (fails fast, 422) — this is a basic sanity check, separate from and in addition to the double-booking check, which lives in the service layer since it requires a DB query.

### `backend/app/services/reservation_service.py` (new file)

Structure mirrors `category_service.py` (for `ReservableSpaceService`, static methods, thin CRUD) and `occurrence_service.py` (for `SpaceReservationService`, service-layer RBAC + masking):

- `ReservableSpaceService.create_space(session, space_in) -> ReservableSpace`
- `ReservableSpaceService.get_spaces(session, only_active=True) -> list[ReservableSpace]`
- `ReservableSpaceService.update_space(session, db_space, space_in) -> ReservableSpace`
- `ReservableSpaceService.deactivate_space(session, db_space) -> None` (sets `is_active = False`)
- `SpaceReservationService.check_conflict(session, space_id, start_time, end_time, exclude_reservation_id=None) -> bool`: the mandatory double-booking check. Query:
  ```python
  statement = (
      select(SpaceReservation)
      .where(SpaceReservation.space_id == space_id)
      .where(SpaceReservation.status.in_([ReservationStatus.CONFIRMED, ReservationStatus.PENDING]))
      .where(SpaceReservation.start_time < end_time)
      .where(SpaceReservation.end_time > start_time)
  )
  if exclude_reservation_id:
      statement = statement.where(SpaceReservation.id != exclude_reservation_id)
  return session.exec(statement).first() is not None
  ```
  (Standard half-open interval overlap test: two windows `[a, b)` and `[c, d)` overlap iff `a < d and c < b`.) This must run inside the same transaction as the insert/update that depends on it — call it, then immediately `session.add`/`session.commit` the new/updated row without any intervening commit, to minimize (not eliminate — this app has no `SELECT ... FOR UPDATE` precedent anywhere and this task does not introduce one) the race window. A genuinely airtight lock is out of scope for v1; document this as an accepted limitation (see Non-Goals).
- `SpaceReservationService.create_reservation(session, current_user, reservation_in) -> SpaceReservation`: loads the space (404 via `ReservableSpaceNotFoundError` if missing/inactive), runs `check_conflict`, raises `SpaceReservationConflictError` if it returns `True`, otherwise inserts with `status = PENDING if space.requires_approval else CONFIRMED`, `reserved_by_id = current_user.id`.
- `SpaceReservationService.list_reservations(session, current_user, space_id=None, mine=False) -> list[SpaceReservationRead]`: builds the read list applying the exact precedence rules from "Visibility & masking" above (`mine=True` always restricts to the caller's own rows for any role, regardless of `space_id`; otherwise staff with no `space_id` get everything, staff with `space_id` get full detail scoped to that space, non-staff with no `space_id` get their own rows only, non-staff with `space_id` get the masked busy-slot view).
- `SpaceReservationService.get_reservation(session, current_user, reservation_id) -> SpaceReservationRead`: `SpaceReservationNotFoundError` (404) unless caller is `ADMINISTRATOR`/`DIRECTOR` or `reserved_by_id == current_user.id`.
- `SpaceReservationService.decide_reservation(session, current_user, reservation_id, approve: bool) -> SpaceReservation`: `ForbiddenError` unless `ADMINISTRATOR`/`DIRECTOR`; 404 if not found; `SpaceReservationConflictError` (409) if `approve=True` and a re-run `check_conflict` (excluding self) finds an overlapping `CONFIRMED` row; otherwise sets status/`decided_by_id`/`decided_at`.
- `SpaceReservationService.cancel_reservation(session, current_user, reservation_id) -> SpaceReservation`: 404 if not found or not `PENDING`/`CONFIRMED`; `ForbiddenError` unless caller is `ADMINISTRATOR`/`DIRECTOR` or (`reserved_by_id == current_user.id` and `start_time > datetime.utcnow()`); sets `status = CANCELLED`, `cancelled_at = now`.

### `backend/app/api/v1/endpoints/reservations.py` (new file)

Routes (registered under a new `/api/v1/space-reservations` prefix — kept separate from a `/api/v1/reservable-spaces` prefix so the two resources have independent, unambiguous URLs):

- `GET /reservable-spaces/` — list spaces (any authenticated user).
- `POST /reservable-spaces/` — create space (`ADMINISTRATOR`/`DIRECTOR`).
- `PATCH /reservable-spaces/{space_id}` — update space (`ADMINISTRATOR`/`DIRECTOR`).
- `DELETE /reservable-spaces/{space_id}` — deactivate space, `204` (`ADMINISTRATOR`/`DIRECTOR`).
- `POST /space-reservations/` — create reservation (any non-`GUEST`), `201`.
- `GET /space-reservations/?space_id=...&mine=...` — list per visibility rules above.
- `GET /space-reservations/{id}` — get one, per visibility rules above.
- `POST /space-reservations/{id}/approve` — `ADMINISTRATOR`/`DIRECTOR` only.
- `POST /space-reservations/{id}/reject` — `ADMINISTRATOR`/`DIRECTOR` only.
- `POST /space-reservations/{id}/cancel` — per cancellation rules above.

All routes use `Depends(api_deps.get_current_user)` only (no `assert_menu_access` — see RBAC section); role/ownership checks happen in the endpoint (for the simple space-CRUD role gate, mirroring `categories.py`'s inline `_require_category_write_permission`) or in the service layer (for the ownership/state-dependent `SpaceReservation` checks, mirroring `occurrence_service.py`).

### `backend/app/api/v1/api.py`

Register both routers: `api_router.include_router(reservations.router, prefix="/reservable-spaces", tags=["reservable-spaces"])` and a second `include_router` call for the `/space-reservations` prefix (or split into two router objects in the same file — developer's call, consistent with how this codebase sometimes puts multiple related routers in one endpoints module and sometimes splits them; either is fine as long as the two URL prefixes above are correct).

## Frontend Changes

### `frontend/src/types/reservation.ts` (new file)

TypeScript mirrors of `ReservableSpaceRead`, `ReservableSpaceCreate/Update`, `SpaceReservationRead`, `SpaceReservationCreate`, `ReservationStatus` — follow the existing convention in `frontend/src/types/occurrence.ts` for shape/naming.

### `frontend/src/api/reservations.ts` (new file)

Axios wrapper functions (`getReservableSpaces`, `createReservableSpace`, `updateReservableSpace`, `deactivateReservableSpace`, `getSpaceReservations`, `createSpaceReservation`, `approveSpaceReservation`, `rejectSpaceReservation`, `cancelSpaceReservation`) — mirror `frontend/src/api/occurrences.ts`'s shape exactly (thin functions wrapping the shared `client` from `frontend/src/api/client.ts`).

### New feature directory `frontend/src/features/space-reservation-management/`

- `components/ReservableSpacesPage.tsx`: admin CRUD screen for `ReservableSpace` — mirror `CategoriesPage.tsx`'s exact pattern: inline create form behind a `showForm` toggle, inline edit-in-place per row, and confirm-before-delete as an **inline confirm row** (the list item is replaced in place by a row with inline Cancel/Confirm buttons when `confirmDeleteId === <id>` — this is `CategoriesPage.tsx`'s actual delete-confirmation mechanism; `AlertModal` in that file is used only to surface error messages, e.g. a failed create/update/delete, not for delete confirmation). `canWrite = role === ADMINISTRATOR || role === DIRECTOR` gate sourced from `useEffectiveIdentity()`. Fields: name, description (textarea), capacity (number input), requires-approval (checkbox). No color picker (not applicable here). "Delete" button calls the deactivate endpoint, same soft-delete semantics as Categories.
- `components/SpaceBookingPage.tsx`: resident-facing view. Lists active spaces (from `useReservableSpaces()`); selecting one shows:
  - A simple list of that space's existing `PENDING`/`CONFIRMED` reservations sorted by `start_time` (each row: date/time range + status badge; masked rows show no name, matching the backend's masking — render them as "Reservado" / "Booked" with no identity), **not** a full calendar-grid widget. Per the APRAS-26 draft's own assessment, this is new UI territory for this app with no existing calendar component to mirror — a date-range picker (two native `<input type="datetime-local">` fields, following the existing precedent in `frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx` (its `validFrom`/`validUntil` inputs, both `type="datetime-local"`) rather than `TaskForm.tsx`'s `due_date` field, which is a plain `type="date"` input with no time component) plus this list is sufficient for v1 and avoids pulling in a calendar library purely for this one feature.
  - A booking form: start/end `datetime-local` inputs, optional notes textarea, submit button. On submit, calls `createSpaceReservation`; on a `409` (conflict), surface the error inline (reuse the `AlertModal` pattern from `CategoriesPage.tsx`) rather than a generic toast, since "someone else just booked this slot" is a specific, actionable message.
  - "My reservations" section (or a separate `MyReservationsPage.tsx`/tab — developer's call) listing the current user's own bookings across all spaces with a cancel button, gated by the cancellation rule (only enabled while `PENDING`/`CONFIRMED` and `start_time` in the future — mirror the backend rule client-side for immediate UX feedback, but the backend remains the source of truth and re-validates).
  - For `ADMINISTRATOR`/`DIRECTOR`: an additional "Pending approvals" list (reservations with `status === PENDING`) with approve/reject buttons, visible only to those two roles (same `useEffectiveIdentity()` gate pattern as `CategoriesPage.tsx`).
- `hooks/useReservations.ts`: TanStack Query hooks (`useReservableSpaces`, `useCreateReservableSpace`, `useUpdateReservableSpace`, `useDeactivateReservableSpace`, `useSpaceReservations(spaceId?, mine?)`, `useCreateSpaceReservation`, `useApproveReservation`, `useRejectReservation`, `useCancelReservation`) — mirror `useOccurrences.ts`'s exact shape (query keys, `invalidateQueries` on mutation success).

### `App.tsx`

Two new routes:
```tsx
<Route path="/spaces" element={<ProtectedRoute requiredRoles={[UserRole.ADMINISTRATOR, UserRole.DIRECTOR]}><ReservableSpacesPage /></ProtectedRoute>} />
<Route path="/reservations" element={<ProtectedRoute requiredRoles={[UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.RESIDENT, UserRole.GUEST]}><SpaceBookingPage /></ProtectedRoute>} />
```
`/reservations` includes `GUEST` in `requiredRoles` (can browse/view, per the backend's read-access rule) even though the booking form itself is hidden/disabled for `GUEST` inside the page (the create button/form only renders when `effectiveRole !== UserRole.GUEST`, mirroring how `Task`'s creation UI is gated). `/spaces` (the admin CRUD screen) is `ADMINISTRATOR`/`DIRECTOR` only, matching `/categories`'s narrower gate style (`ProtectedRoute requiredMenu="categories"` uses the menu system for Categories specifically; since this feature doesn't use `MenuKey`, use `requiredRoles` directly instead, matching `/finance`'s and `/admin/access-control`'s pattern of role-list gating without a menu key).

### `Navbar.tsx`

Add a `/reservations` link visible to `effectiveRole !== UserRole.PORTEIRO` (mirrors the `/occurrences` link's exact gating, i.e. visible to `GUEST` too), labeled via `t("nav.reservations", "Reservas")`. Add a `/spaces` link visible only when `effectiveRole === UserRole.ADMINISTRATOR || effectiveRole === UserRole.DIRECTOR`, labeled `t("nav.manageSpaces", "Espaços")`.

### i18n

New top-level `reservations` namespace in `frontend/src/i18n/locales/en.json` and `pt.json`, following the existing per-feature namespace convention (see `occurrences`, `projects`, `finance` for the level of key granularity to match — labels, placeholders, status labels, error messages, confirm-delete/cancel copy). Add `nav.reservations` and `nav.manageSpaces` keys to the existing `nav` namespace.

## Non-Goals

- No recurring reservations — one-off bookings only (v1), per the APRAS-26 draft.
- No payment/fee collection for reservations, per the APRAS-26 draft (consistent with APRAS-22's finance module being a separate, unlinked concern from operational booking).
- No push/email/SMS notification when a reservation is approved/rejected/about to start. No such infrastructure exists anywhere in this app today (per APRAS-26's own roadmap section); this feature relies entirely on in-app state (the "Pending approvals" list for staff, "My reservations" list with current status for residents) — there is no unread-indicator equivalent to `Feedback.response_seen_by_reporter` built here, since a reservation's `status` field itself already communicates the outcome the next time the user opens the page (no separate "have you seen this" flag is needed the way it was for Feedback's free-text response body).
- No editing of an existing reservation's time window or notes — cancel and rebook instead (see "No edit endpoint" above).
- No true row-level locking (`SELECT ... FOR UPDATE`) around the double-booking check — this app has no existing precedent for it, and introducing one is out of scope for this task. The application-level check-then-insert has a narrow theoretical race window under concurrent requests for the exact same slot; accepted as a known limitation for v1, consistent with how tightly this mirrors the draft's own framing of the check as "the core value proposition" rather than a fully lock-free-race-proof guarantee.
- No lot-picker UI in the booking form for v1. `SpaceReservation.lot_id` exists in the model/schema (nullable) for future use but is not collected by `SpaceBookingPage.tsx`'s create form — this exactly mirrors the real, already-shipped precedent in `Occurrence`: `OccurrenceCreate.lot_id` exists in the schema, but `NewOccurrenceModal.tsx` never collects it. Populating it later (e.g. from the user's `UserLotLink` records) is a natural follow-up, not part of this task.
- No calendar-grid widget / calendar library dependency — a date-range form plus a sorted list of existing bookings, per the Approach above.
- Not adding a new `MenuKey` value or extending the APRAS-8/9 UserType-menu-gate system to this feature.

## Testing

- **Backend** (`backend/tests/test_reservable_spaces.py`, `backend/tests/test_space_reservations.py` — new files, mirror `test_categories.py`'s and `test_occurrences.py`'s structure):
  - `ReservableSpace` CRUD: `ADMINISTRATOR`/`DIRECTOR` can create/update/deactivate; any other role gets 403 on write, 200 on list (including a `GUEST` client). Deactivating sets `is_active = False` and the space still exists (soft delete, not a real `DELETE`).
  - `create_reservation`: succeeds for `RESIDENT`/`MANAGER`/`DIRECTOR`/`ADMINISTRATOR`; 403 for `GUEST`. `requires_approval=False` space → created as `CONFIRMED`. `requires_approval=True` space → created as `PENDING`.
  - Double-booking: two reservations with overlapping windows on the same space, both `CONFIRMED`/`PENDING`-eligible → second one gets `409 SpaceReservationConflictError`. Adjacent-but-non-overlapping windows (`end_time` of one == `start_time` of the next) succeed (half-open interval, not inclusive). Overlapping windows on *different* spaces both succeed (conflict check is scoped to `space_id`). A `CANCELLED`/`REJECTED` reservation does not block a new overlapping one.
  - Approve/reject: `ADMINISTRATOR`/`DIRECTOR` only (403 for others); approving a `PENDING` reservation that now conflicts with a `CONFIRMED` one (created after the `PENDING` one, e.g. two overlapping requests on the same `requires_approval` space, second one directly approved first) returns `409` and leaves the first `PENDING`; rejecting always succeeds regardless of conflicts and frees the slot for a subsequent create.
  - Cancellation: owner can cancel their own future `PENDING`/`CONFIRMED` reservation; owner cannot cancel a reservation whose `start_time` has already passed (403); owner cannot cancel someone else's reservation (403/404 — pick whichever this codebase's `TaskNotFoundError`-style precedent suggests, i.e. 404 to avoid confirming existence to a non-owner, and use that consistently for `get_reservation` and `cancel_reservation` alike); `ADMINISTRATOR`/`DIRECTOR` can cancel any reservation including already-started ones.
  - Visibility/masking: a non-owner, non-staff `GET /space-reservations?space_id=...` sees other users' `PENDING`/`CONFIRMED` rows with identity/notes nulled but their own row unmasked; `ADMINISTRATOR`/`DIRECTOR` see full detail on every row; `CANCELLED`/`REJECTED` rows are excluded from this masked list entirely.
  - Migration test (if this codebase's convention includes one for new tables — check an existing migration-adjacent test, e.g. any test asserting a table/column exists post-upgrade, and follow the same approach; if no such precedent exists, skip a dedicated migration test and rely on the app-level model tests exercising the real DB via the test fixtures, consistent with how `test_categories.py` doesn't have a standalone migration test either).
- **Frontend**:
  - `ReservableSpacesPage` renders CRUD form only for `ADMINISTRATOR`/`DIRECTOR` (mirror `CategoriesPage.test.tsx`'s `canWrite` assertions).
  - `SpaceBookingPage` renders the booking form for non-`GUEST` roles and hides/disables it for `GUEST`; renders the "Pending approvals" section only for `ADMINISTRATOR`/`DIRECTOR`; a `409` response from `createSpaceReservation` surfaces the conflict message via `AlertModal` rather than crashing/silently failing.
  - `useReservations.ts` hooks invalidate the correct query keys on each mutation's success (mirror `useOccurrences.test`-style coverage if one exists, or the pattern used for `useCategories.ts`'s mutation hooks).

## Expected Results

1. An `ADMINISTRATOR`/`DIRECTOR` can create, update, and deactivate `ReservableSpace` rows via `/spaces`; no other role can write, all authenticated roles (including `GUEST`) can list active spaces.
2. Any authenticated non-`GUEST` user can create a `SpaceReservation` against an active space; `GUEST` gets `403`.
3. A reservation against a `requires_approval=False` space is immediately `CONFIRMED`; against a `requires_approval=True` space it starts `PENDING` and only an `ADMINISTRATOR`/`DIRECTOR` approve/reject action changes that.
4. Creating a reservation that overlaps an existing `CONFIRMED`/`PENDING` reservation on the **same** space is rejected with `409`, enforced server-side (verified by a test that bypasses/ignores any client-side calendar check). Overlaps on different spaces, or against `CANCELLED`/`REJECTED` reservations, are allowed.
5. Approving a `PENDING` reservation that would newly conflict with an already-`CONFIRMED` one is rejected with `409` and does not silently double-book the space.
6. The reserving user can cancel their own future `PENDING`/`CONFIRMED` reservation but not a past one nor someone else's; `ADMINISTRATOR`/`DIRECTOR` can cancel any reservation at any time.
7. There is no endpoint to edit an existing reservation's time window — only create and cancel/approve/reject are exposed.
8. A non-owner, non-staff viewer of a space's reservation list sees other users' bookings as anonymous busy slots (no identity, no notes) but sees full detail on their own bookings.
9. The frontend `/spaces` admin screen and `/reservations` resident-facing booking screen both exist, route-gated as specified, and round-trip create/approve/reject/cancel actions against the real API.
</content>
