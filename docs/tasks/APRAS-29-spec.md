# APRAS-29 — Remove Orphaned User.block_lot Column

**Date:** 2026-08-27
**Status:** Approved for implementation

## Problem

`User.block_lot` was added in APRAS-6 before the Lot/Resident subsystem (APRAS-15/16) existed. It's now fully superseded by `Lot`/`UserLotLink` for anyone who actually lives in a unit. APRAS-7 already confirmed and rescoped its UI work to exclude this field. Verified via grep: the only remaining references anywhere in the codebase are the raw field/type declarations themselves — no endpoint, service, form, or component reads or writes `block_lot`.

## Fix

Remove the field entirely:

- `backend/app/models/user.py`: remove `block_lot: str | None = Field(default=None)`.
- `backend/app/schemas/user.py`: remove `block_lot: str | None = None` from `UserBase` and from `UserUpdate`. (Coordinate with APRAS-30 if both land close together — APRAS-30 also touches `UserBase`'s field list; whichever merges second should rebase cleanly since both are small, non-overlapping edits to the same class.)
- `frontend/src/types/auth.ts`: remove `block_lot?: string` from the `User` interface.
- New Alembic migration (check `alembic heads` for the actual current head — do not assume a number): `op.drop_column("user", "block_lot")`. Downgrade re-adds it as nullable (data is not recoverable on downgrade — acceptable, since the column has never been populated by any UI path).

## Non-Goals

- Not touching `Lot`/`UserLotLink`/`Resident` — this task only removes the superseded field, it doesn't change the replacement system.

## Testing

- **Backend**: existing test suite passes unmodified (no test should reference `block_lot` — if one does, that's a signal the grep-based "nothing reads it" claim was wrong and needs re-checking before removal). Migration upgrade/downgrade verified against real Postgres if Docker is available.
- **Frontend**: existing test suite passes unmodified.

## Expected Results

1. Confirmed (already verified in this spec's Problem section) that no code reads `User.block_lot` before removal.
2. Alembic migration drops the `block_lot` column from the `user` table.
3. `User` model and schemas no longer reference `block_lot`.
