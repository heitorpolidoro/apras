# APRAS-12 — PORTEIRO (Gatekeeper) Role and Dedicated Portaria Landing

**Date:** 2026-08-27
**Status:** Approved for implementation

## Problem

Gatekeeper functionality (visitor/contractor check-in and check-out) exists (`/gate`, `GatekeeperDashboard.tsx`, `access_logs.py`'s `_assert_gatekeeper_or_admin`) but is only usable by staff already holding `ADMINISTRATOR`/`DIRECTOR`/`MANAGER` roles — there's no role for a front-desk/security employee whose *only* job is checking visitors in and out, with no legitimate need for task management, financial data, documents, or anything else in the app. Handing such a person a `MANAGER` account today over-provisions them with access to everything a Manager can see.

Also discovered incidentally while scoping this: `/gate`'s route in `App.tsx` has no `requiredRole`/`requiredRoles` guard at all — any authenticated user can reach it directly by URL today (masked only by the Navbar link being hidden for non-staff roles). This is a pre-existing gap this task's own scope naturally touches (adding role gating to `/gate` for the first time), so it's fixed here rather than filed separately.

## Goal

Add a new `PORTEIRO` role, scoped to exactly one feature (`/gate`), with no access to anything else — including `/gate-monitor` (a separate, facial-recognition device-monitoring feature, out of scope here) — and land a `PORTEIRO` on `/gate` immediately after login instead of `/dashboard`.

## Scope Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Does `PORTEIRO` replace existing staff access to `/gate`? | No. `ADMINISTRATOR`/`DIRECTOR`/`MANAGER` keep exactly the gatekeeping access they have today — no regression. `PORTEIRO` is purely additive. |
| How restricted is `PORTEIRO`? | Maximally: `/gate` only. Every other authenticated route (Tarefas, Categorias, Lotes, Ocorrências, Documentos, Comunicados, Financeiro, Obras, Autorizações, Central de Contato, Administração, `/gate-monitor`) is blocked for this role. |
| Does `PORTEIRO` get `/gate-monitor` (facial-recognition device monitoring, APRAS-19)? | No — the task is specifically about manual visitor check-in/check-out, a different feature with a different (more sensitive, device-configuration-adjacent) audience. |
| Post-login landing | `PORTEIRO` lands on `/gate` directly after login, mirroring the `GUEST` → `/welcome` pattern from APRAS-10 (same root-redirect/`ProtectedRoute` mechanism, generalized to a second role). |

## Backend Changes

### `backend/app/models/enums.py`

Add `PORTEIRO = "PORTEIRO"` to `UserRole`.

### Migration

New Alembic revision (check `alembic heads` for the actual current head — do not assume a number): `op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'PORTEIRO'")`, mirroring `0003_add_guest_to_userrole_enum.py`/`0014_add_resident_userrole.py` exactly. Downgrade is a no-op (Postgres cannot drop enum values), same precedent.

**Critical lesson from APRAS-27**: that task's entire existence was because a prior enum-add migration (`RESIDENT`) was never actually applied against the real production database, silently breaking resident creation for an extended period. This migration must be verified to actually run — real Postgres upgrade/downgrade/re-upgrade cycle via Docker at implementation time, and confirm `migrate.yml` succeeds after merge (check the workflow run, don't just assume the merge succeeded).

### `backend/app/api/v1/endpoints/access_logs.py`

`_assert_gatekeeper_or_admin()` — rename to `_assert_gatekeeper_access()` (the old name becomes misleading once a non-admin-adjacent role is included) and add `PORTEIRO` to its allowed set: `(UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.PORTEIRO)`.

### Any other endpoint `PORTEIRO` might touch

`visitors.py`/`authorizations.py` currently have no role checks beyond authentication (any authenticated user can call them) — confirm at implementation time whether `PORTEIRO` needs anything beyond what `access_logs.py`'s check-in/check-out endpoints already allow (per `GatekeeperDashboard.tsx`'s actual API usage — read the component to enumerate every endpoint it calls, and confirm each either has no role restriction or already/now includes `PORTEIRO`).

## Frontend Changes

### `frontend/src/types/auth.ts`

Add `PORTEIRO: "PORTEIRO"` to the `UserRole` const.

### `frontend/src/App.tsx` — fix the pre-existing `/gate` gating gap

Add `requiredRoles={[UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.PORTEIRO]}` to the `/gate` route (currently has none).

### Post-login landing for `PORTEIRO`

Generalize APRAS-10's `GUEST` → `/welcome` redirect mechanism (root redirect using the real role, `ProtectedRoute`'s new `requiredMenu`-adjacent branch using the effective/simulated role for direct-URL-navigation cases) to also handle `PORTEIRO` → `/gate`. Concretely:
- Root redirect (`App.tsx`): `GUEST` → `/welcome`, `PORTEIRO` → `/gate`, everyone else → `/dashboard` (unchanged).
- `PORTEIRO` does not need the `ProtectedRoute`-level "redirect away from a route I can't use" treatment APRAS-10 built for `GUEST`+`requiredMenu`, because `PORTEIRO`'s restriction is via `requiredRole`/`requiredRoles` (not `requiredMenu`), and `ProtectedRoute`'s existing `requiredRole`/`requiredRoles` handling already redirects an unauthorized role to `/dashboard` — which `PORTEIRO` also can't access. **This is a real gap**: a `PORTEIRO` denied by `requiredRole`/`requiredRoles` on some other route today would bounce to `/dashboard`, which they also can't see (per the "every other route blocked" scope decision) — read on `/dashboard`'s own guard for what a `PORTEIRO` there actually experiences. Since `/dashboard` currently has no `requiredRole` of its own (only APRAS-8's `requiredMenu="tasks"`), a `PORTEIRO` bounced to `/dashboard` by `ProtectedRoute`'s `requiredRole` mismatch elsewhere will hit `requiredMenu`'s restricted-access message there instead of a further bounce loop — confirm this resolves cleanly (no redirect loop) at implementation time by tracing the actual flow, since it wasn't a concern APRAS-10 had to handle (its only fully-restricted role, `GUEST`, got the `ProtectedRoute`-level `/welcome` redirect specifically to avoid this exact scenario). If a `PORTEIRO` bounced from an unauthorized `requiredRole` route ending up on `/dashboard`'s restricted-access message (rather than being redirected to `/gate`) is judged unacceptable, generalize APRAS-10's `ProtectedRoute` `GUEST`-redirect branch to also cover `PORTEIRO` → `/gate` for symmetry. Default to generalizing it (do the symmetric thing) unless it proves awkward at implementation time.

### i18n

If `roles.*` i18n keys (used for role display, e.g. `AdminUserDashboard`'s role dropdown/badge) exist for the existing roles, add `roles.PORTEIRO` to `en.json`/`pt.json` (e.g. "Porteiro"/"Gatekeeper").

## Non-Goals

- Not touching `/gate-monitor` or its RBAC.
- Not changing `ADMINISTRATOR`/`DIRECTOR`/`MANAGER`'s existing gatekeeping access.
- Not building any new gatekeeper-specific UI beyond reusing the existing `GatekeeperDashboard.tsx` — "dedicated Portaria dashboard" is satisfied by `PORTEIRO` landing on the already-built `/gate` page, not a new page.
- Not auditing every single route in the app individually for `PORTEIRO` exclusion beyond what's already covered by existing `requiredRole`/`requiredRoles` allowlists (which, by construction, already exclude any role not explicitly listed — `PORTEIRO` is excluded from everything by default simply by never being added to any other route's allowlist).

## Testing

- **Backend**: `PORTEIRO` succeeds on check-in/check-out endpoints; migration upgrade/downgrade/re-upgrade verified against real Postgres; confirm the enum value is actually present in a live database, not just the Python enum (the APRAS-27 lesson).
- **Frontend**: `/gate` route now requires one of the four allowed roles (previously unguarded — add a test proving a `GUEST`/`RESIDENT` is blocked, since this is a new restriction with no prior test coverage). Root redirect sends `PORTEIRO` to `/gate`. `PORTEIRO` is blocked from every other named route (spot-check a representative sample: `/dashboard` via `requiredMenu`, `/lots` via `requiredRoles`, `/finance` via `requiredRoles`). Navbar shows only the "Portaria" link for `PORTEIRO`, nothing else.

## Expected Results

1. `PORTEIRO` role exists in the database enum (verified against real Postgres, not just Python).
2. `PORTEIRO` can check visitors in and out via the existing `/gate` flow.
3. `ADMINISTRATOR`/`DIRECTOR`/`MANAGER` retain unchanged access to `/gate`.
4. `/gate` route is now properly role-gated (fixes the pre-existing unguarded-route gap).
5. `PORTEIRO` lands on `/gate` after login and cannot reach any other authenticated route, including `/gate-monitor`.
