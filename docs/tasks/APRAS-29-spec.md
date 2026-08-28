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

### Correction: the Problem section's "zero references outside declarations" claim is wrong

Independent spec review found `block_lot` is actually constructed/asserted on directly in 7 backend test functions (not just the model/schema declarations):
- `backend/tests/test_models.py`: `test_user_model_profile_fields_default_to_none`, `test_user_model_profile_fields_accept_strings`
- `backend/tests/test_schemas.py`: `test_user_create_accepts_request_without_profile_fields`, `test_user_create_accepts_request_with_profile_fields`, `test_user_update_accepts_request_without_profile_fields`, `test_user_update_accepts_request_with_profile_fields`, `test_user_read_serializes_profile_fields`

Update each of these 7 tests: remove the `block_lot` keyword argument and any assertion on it, keeping the rest of each test's `phone`/`address` coverage intact. Update any docstring/comment in these files that lists "phone, address, block_lot" to drop `block_lot`. Frontend has no such references (confirmed via grep) — this correction is backend-test-only.

## Non-Goals

- Not touching `Lot`/`UserLotLink`/`Resident` — this task only removes the superseded field, it doesn't change the replacement system.

## Testing

- **Backend**: after updating the 7 tests listed above, the full suite passes with no remaining references to `block_lot` anywhere (`grep -r block_lot backend/` returns nothing). Migration upgrade/downgrade verified against real Postgres if Docker is available.
- **Frontend**: existing test suite passes unmodified.

## Expected Results

1. Confirmed (already verified in this spec's Problem section) that no code reads `User.block_lot` before removal.
2. Alembic migration drops the `block_lot` column from the `user` table.
3. `User` model and schemas no longer reference `block_lot`.
