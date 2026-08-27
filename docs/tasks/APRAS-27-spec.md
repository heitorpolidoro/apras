# APRAS-27 — Fix missing RESIDENT value in Postgres userrole enum

## Problem

The Postgres `userrole` enum type only contains `ADMINISTRATOR, DIRECTOR, MANAGER, GUEST`.
`RESIDENT` was never added by any Alembic migration, even though `UserRole.RESIDENT`
(`backend/app/models/enums.py`) is used pervasively in application code — including
already-shipped features (e.g. APRAS-16 / T002, "Cadastro de Moradores"). Inserting a
real row with `role='RESIDENT'` against actual Postgres fails with
`psycopg2.errors.InvalidTextRepresentation`. This was invisible to the existing pytest
suite because tests run against SQLite, which stores the enum as a plain `VARCHAR` with
no native enum constraint. Discovered independently by QA while verifying APRAS-20
against a real Postgres instance.

## Expected Results

- Alembic migration adds `RESIDENT` to the Postgres `userrole` enum type (same idiom as
  migration `0003_add_guest_to_userrole_enum.py`).
- A test verifies the enum accepts `RESIDENT` against a real Postgres instance (not just
  SQLite).
- Migration runs cleanly upgrade+downgrade against a real Postgres instance.

## Approach

1. Added `backend/alembic/versions/0014_add_resident_userrole.py`, chained after the
   current head (`0013_add_construction_project`), mirroring `0003`'s exact idiom:
   `op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'RESIDENT'")` in `upgrade()`,
   and a no-op `downgrade()` with a comment explaining Postgres cannot drop enum values
   (same as `0003`'s downgrade).
   - Revision id kept short (`0014_add_resident_userrole`, 26 chars) to fit the
     `alembic_version.version_num VARCHAR(32)` column — discovered this the hard way
     during verification (a longer, more descriptive id overflowed the column and rolled
     back the entire migration batch since this repo's `env.py` runs all pending
     migrations within a single outer transaction).
2. Verified for real against a throwaway `postgres:16-alpine` Docker container:
   ran `alembic upgrade head` from a blank database (all 14 migrations applied cleanly),
   inserted a `user` row with `role='RESIDENT'` via raw SQL (succeeded), confirmed
   `alembic downgrade -1` succeeds and is a safe no-op (the enum value `RESIDENT` remains
   in the Postgres type afterward — Postgres has no `DROP VALUE` for enums, matching the
   `0003` precedent), then re-ran `upgrade head` to confirm idempotency via
   `IF NOT EXISTS`.
3. Added `backend/tests/test_migrations_postgres.py`: three tests (enum contains
   `RESIDENT`, inserting a `RESIDENT` user row succeeds, downgrade is a safe no-op) that
   run Alembic via subprocess against a real Postgres reachable at `TEST_POSTGRES_URL`.
   The whole module is skipped (not failed) when `TEST_POSTGRES_URL` is unset, since the
   project's CI (`ci.yml`) has no Postgres service container — this documents the known
   SQLite-can't-verify-Postgres-enums gap while still giving a real, runnable regression
   test for local/Docker verification.
4. Grepped the codebase for other places hardcoding the previous 4-value role list
   (`document.py`/`schemas/document.py`'s `allowed_roles` defaults, `0001_initial_schema.py`'s
   literal `sa.Enum(...)` column definition, various RBAC role-set checks). All of these
   already either include `RESIDENT` where relevant or intentionally exclude it for
   Administrator/Director/Manager-only gates — none needed changes for this
   database-enum-only fix. `0001_initial_schema.py` is a squashed historical migration
   already applied in production; it is left untouched.

## Scope

Strictly the database enum fix — no new resident-facing UI or business logic was added.
