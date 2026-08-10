# User Profile Fields (Data Layer Only) — Design Spec

**Meridian task:** `user-profile-fields`
**Date:** 2026-08-10
**Status:** Approved for planning

## Problem

The `User` model has no way to record a resident's phone number, address, or condo block/lot — information that's core to a HOA/building-manager tool but currently has to live outside the system.

## Goal

Add `phone`, `address`, and `block_lot` to the `User` model and the API layer (Pydantic schemas), so the data can already be stored and read through the API. **No UI is built in this task.**

## Scope Decision

The original Meridian task description mentioned "signup form, and admin user dashboard" as part of the work. During brainstorming this was explicitly descoped: this task covers **only the data layer** (SQLModel, Alembic migration, Pydantic schemas, and the frontend TS type for consistency). Building the actual screen(s) to let users/admins view and edit these fields is deferred to a new backlog task (see "Follow-up" below) — it deserves its own design pass (e.g., is it self-service, admin-only, part of signup, a new "my profile" page?).

## Field Design

| Field | Type | Required? | Format |
|---|---|---|---|
| `phone` | `str \| None` | No | Free text, no validation |
| `address` | `str \| None` | No | Free text, no structured sub-fields (street/city/etc.) |
| `block_lot` | `str \| None` | No | Single free-text field (e.g. `"Bloco A, Lote 12"`), not split into separate `block`/`lot` columns |

Unlike `cpf` (mandatory, validated, unique, backfilled for existing rows), these three fields are optional with no validation — a deliberate simplification since the real UX (masks, required-ness, structure) will be decided when the screen is designed.

## Changes

### Backend

- **`backend/app/models/user.py`**: add `phone: str | None = Field(default=None)`, `address: str | None = Field(default=None)`, `block_lot: str | None = Field(default=None)` to the `User` SQLModel.
- **`backend/alembic/versions/0005_add_profile_fields_to_user.py`** (`down_revision = "0004_add_cpf_to_user"`): `op.add_column` for all three as nullable `sa.String()`, no backfill needed (optional fields), no index/unique constraint. `downgrade()` drops the three columns.
- **`backend/app/schemas/user.py`**: add `phone: str | None = None`, `address: str | None = None`, `block_lot: str | None = None` to `UserBase` (inherited by `UserCreate` and `UserRead`) and to `UserUpdate`. No `field_validator` needed — free text.
- **`backend/app/seed.py`**: no changes required (fields default to `None`); optionally leave seed users without these values.

### Frontend

- **`frontend/src/types/auth.ts`**: add `phone?: string`, `address?: string`, `block_lot?: string` to the `User` interface, so the type stays in sync with the API response shape. No component, form, or page is touched.

## Non-Goals

- No signup form changes.
- No admin dashboard UI changes.
- No format validation (phone masks, CEP/address lookup, etc.) — deferred to the screen-design task.
- No self-service "my profile" page (doesn't exist today; whether to add one is a decision for the follow-up task).

## Testing

- **Backend**: model test confirming the three fields default to `None` and accept strings; schema tests confirming `UserCreate`/`UserUpdate` accept requests with and without these fields (existing signup/update tests must keep passing unmodified — these fields must not become implicitly required); a smoke check that `UserRead` serializes them.
- **Frontend**: none needed beyond type-checking (no runtime behavior changes).

## Follow-up

A new Meridian task (`status: "backlog"`) will be created for building the actual UI: a screen (or screens) to let these fields be set/edited, covering signup form fields, admin dashboard display/edit, and whether end users get any self-service editing at all (today only administrators can edit user records — see `backend/app/api/v1/endpoints/users.py:update_user`, restricted to `get_current_active_admin`). That task will need its own brainstorming pass to decide required-ness, formatting/masking, and who can edit what.
