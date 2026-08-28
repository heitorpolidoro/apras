# APRAS-12 — PORTEIRO (Gatekeeper) Role and Dedicated Portaria Landing

**Date:** 2026-08-27
**Status:** Approved for implementation

## Dependency note

**This task must be implemented after `APRAS-10` is merged**, not concurrently. The "Post-login landing" section below adds a `PORTEIRO` branch directly alongside APRAS-10's `GUEST` → `/welcome` branch in `ProtectedRoute.tsx` (the `requiredMenu`-gated redirect check) and relies on APRAS-10's root-redirect and `ProtectedRoute` shape already existing in the codebase. Building this concurrently with APRAS-10 risks two independent agents reshaping the same `ProtectedRoute.tsx` logic at once. Tracked via `blockedBy: ["APRAS-10"]` in `.meridian/tasks.json`.

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

### `backend/app/api/v1/endpoints/lots.py` — required for check-in to work at all

`GatekeeperDashboard.tsx` calls `useLots()` (`GET /lots/`) to populate a mandatory lot selector — check-in is `disabled` in the UI without a selected lot. `GET /lots/` is gated by `_require_lot_read_permission()` → `_LOT_READ_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER}` (line 26), which does not include `PORTEIRO`. Without this fix, a `PORTEIRO` landing on `/gate` gets a 403 on the lot list and cannot check anyone in — the core deliverable of this task would not work. Fix: add `UserRole.PORTEIRO` to `_LOT_READ_ROLES`:

```python
_LOT_READ_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.PORTEIRO}
```

This only affects `GET /lots/` and `GET /lots/{id}` (both gated by `_require_lot_read_permission`) — `_LOT_WRITE_ROLES` (create/update/delete) is untouched, so `PORTEIRO` still cannot create or modify lots, only read the list needed to populate the selector.

### Close the PORTEIRO-exclusion gap on 4 endpoint modules with zero role checks today

Verified via grep: `backend/app/api/v1/endpoints/occurrences.py`, `documents.py`, `announcements.py`, and `authorizations.py` have no role-based authorization at all today — every handler depends only on `get_current_user` (authentication, not authorization), so any authenticated user, including a future `PORTEIRO`, can call every endpoint in all four files. This is a pre-existing gap this task's Goal ("no access to anything else") requires closing for `PORTEIRO` specifically. Rather than retrofitting full RBAC onto these four modules (a materially larger, unrelated effort — see `APRAS-8`, which was a dedicated task for exactly that kind of retrofit on Tarefas/Categorias), add one small local guard to each file, mirroring the existing `_require_*`/`_assert_*` local-helper convention already used in `lots.py`/`projects.py`/`access_logs.py`:

```python
def _assert_not_porteiro(current_user: User) -> None:
    """Raise 403 if the caller is PORTEIRO (gate-only role, no access here)."""
    if current_user.role == UserRole.PORTEIRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
```

Call `_assert_not_porteiro(current_user)` as the first line of every route handler body in each of the four files:
- `occurrences.py`: `list_occurrences`, `create_occurrence`, `get_occurrence`, `update_occurrence_status`, `add_timeline_note`.
- `documents.py`: `list_folder_tree`, `create_folder`, `update_folder`, `delete_folder`, `list_documents`, `create_document`, `create_document_version`, `download_document`, `delete_document`.
- `announcements.py`: `list_announcements`, `create_announcement`, `get_announcement`, `update_announcement`, `delete_announcement`, `upload_announcement_media`, `delete_announcement_media`, `list_comments`, `add_comment`, `delete_comment`, `mark_read`, `list_read_receipts`.
- `authorizations.py`: `list_lot_authorizations`, `create_lot_authorization`, `revoke_authorization`.

This changes behavior for `PORTEIRO` only — every other role's existing (unrestricted) access to these four modules is unchanged, so this is not a regression for anyone but the new role, and it is not a general RBAC rollout for these modules (that remains a separate, pre-existing gap for a future task to address for other roles/permission levels if ever needed).

### Any other endpoint `PORTEIRO` might touch

`visitors.py` currently has no role checks beyond authentication (any authenticated user can call it) — leave it unrestricted for now (it is not one of the four modules fixed above, since it isn't reachable from any of the six now-gated frontend routes and is core to `GatekeeperDashboard`'s own check-in flow). At implementation time, read `GatekeeperDashboard.tsx` to enumerate every endpoint it actually calls (`access_logs.py`, `lots.py`, and likely `visitors.py`) and confirm each either has no role restriction or already/now includes `PORTEIRO`, so the check-in/check-out flow works end-to-end. `authorizations.py` is already covered above (Close the PORTEIRO-exclusion gap section) — no separate action needed for it here.

## Frontend Changes

### `frontend/src/types/auth.ts`

Add `PORTEIRO: "PORTEIRO"` to the `UserRole` const.

### `frontend/src/App.tsx` — fix the pre-existing `/gate` gating gap

Add `requiredRoles={[UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.PORTEIRO]}` to the `/gate` route (currently has none).

### `frontend/src/App.tsx` — close the PORTEIRO-exclusion gap on 6 other unguarded routes

Verified directly against `App.tsx`: `/lots`, `/authorizations`, `/occurrences`, `/documents`, `/projects`, and `/announcements` are each wrapped in a bare `<ProtectedRoute>` with no `requiredRole`/`requiredRoles`/`requiredMenu` at all — every authenticated user, including a future `PORTEIRO`, has full frontend access to all six today. This directly contradicts this task's own Goal ("no access to anything else"), so it is fixed here rather than deferred, since the fix is small and targeted (excluding one role from each route), not a full RBAC redesign of these six features.

Add `requiredRoles={[UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.RESIDENT, UserRole.GUEST]}` (i.e. every current role except `PORTEIRO`) to each of these six routes:

```tsx
<Route
  path="/lots"
  element={
    <ProtectedRoute
      requiredRoles={[UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.RESIDENT, UserRole.GUEST]}
    >
      <LotsPage />
    </ProtectedRoute>
  }
/>
```

...and identically for `/authorizations`, `/occurrences`, `/documents`, `/projects`, `/announcements` (swap the wrapped element only). This preserves every existing role's access to these six routes exactly as it is today (no regression for `ADMINISTRATOR`/`DIRECTOR`/`MANAGER`/`RESIDENT`/`GUEST`) and only newly excludes `PORTEIRO` — consistent with `PORTEIRO` being purely additive elsewhere in this spec.

Note on why each of the six needs this despite differing backend states: `/projects`'s backend (`_PROJECT_READ_ROLES` in `projects.py`, unchanged by this task) already excludes `PORTEIRO` by omission, so this frontend change for `/projects` is a UX-consistency fix only (no dead click-through to a page whose API calls will 403). `/lots` is the opposite case — this task's own fix to `_LOT_READ_ROLES` (see Backend Changes, required for `GatekeeperDashboard`'s lot selector) newly *grants* `PORTEIRO` backend read access to `GET /lots/`, so without this frontend gate a `PORTEIRO` could now navigate directly to the full `LotsPage` UI and have its data calls succeed — making the frontend route gate a real security requirement here, not just cosmetic. `/authorizations`, `/occurrences`, `/documents`, `/announcements` have zero backend role checks at all today (see Backend Changes below), so their frontend gates are also load-bearing until the corresponding backend guard lands, and remain defense-in-depth afterward.

### Post-login landing for `PORTEIRO`

Generalize APRAS-10's `GUEST` → `/welcome` redirect mechanism (root redirect using the real role, `ProtectedRoute`'s `requiredMenu`-adjacent branch using the effective/simulated role for direct-URL-navigation cases) to also handle `PORTEIRO` → `/gate`. Concretely:
- Root redirect (`App.tsx`): `GUEST` → `/welcome`, `PORTEIRO` → `/gate`, everyone else → `/dashboard` (unchanged).
- **Redirect trace, settled**: a `PORTEIRO` denied by `requiredRole`/`requiredRoles` on some other route (e.g. `/finance`, or any of the six routes fixed above) is bounced by `ProtectedRoute`'s existing branch to `/dashboard`. `/dashboard` has no `requiredRole` of its own — only APRAS-8's `requiredMenu="tasks"` — so this does **not** loop: it resolves in exactly one more hop to whatever `ProtectedRoute` does for `requiredMenu` when the effective role is `PORTEIRO` (see next bullet). This was verified by reading `ProtectedRoute.tsx` and `App.tsx`'s `/dashboard` route directly, not deferred to implementation time.
- **Resolution, chosen now**: generalize APRAS-10's `ProtectedRoute` `GUEST`-redirect branch (the one gated on `requiredMenu`, added immediately before the `requiredMenu && !hasMenuAccess` restricted-message check) to also cover `PORTEIRO` → `/gate`, for symmetry with `GUEST` → `/welcome`:
  ```tsx
  if (requiredMenu && effectiveRole === UserRole.GUEST) {
    return <Navigate to="/welcome" replace />;
  }

  if (requiredMenu && effectiveRole === UserRole.PORTEIRO) {
    return <Navigate to="/gate" replace />;
  }

  if (requiredMenu && !hasMenuAccess) {
    return <RestrictedAccessMessage />;
  }
  ```
  This is chosen over leaving `PORTEIRO` to dead-end on `/dashboard`'s generic restricted-access message: it's the more polished UX, it mirrors what APRAS-10 already built for `GUEST` on the same two `requiredMenu` routes (`/dashboard`, `/categories`), and it composes cleanly with the existing `requiredRole`/`requiredRoles` → `/dashboard` bounce — a `PORTEIRO` blocked anywhere else now lands on `/gate` after at most one intermediate hop through `/dashboard`, with no loop (the `requiredMenu` branch above short-circuits before the restricted-message branch, and `/gate` itself has no `requiredMenu` so there's no risk of re-entering this branch). Uses `effectiveRole` from `useEffectiveIdentity()`, matching APRAS-10's existing convention for this branch (an Administrator simulating `PORTEIRO` sees the same `/gate` redirect as a real `PORTEIRO`, consistent with how the `GUEST` case already behaves under simulation).

### i18n

If `roles.*` i18n keys (used for role display, e.g. `AdminUserDashboard`'s role dropdown/badge) exist for the existing roles, add `roles.PORTEIRO` to `en.json`/`pt.json` (e.g. "Porteiro"/"Gatekeeper").

## Non-Goals

- Not touching `/gate-monitor` or its RBAC.
- Not changing `ADMINISTRATOR`/`DIRECTOR`/`MANAGER`'s existing gatekeeping access.
- Not building any new gatekeeper-specific UI beyond reusing the existing `GatekeeperDashboard.tsx` — "dedicated Portaria dashboard" is satisfied by `PORTEIRO` landing on the already-built `/gate` page, not a new page.
- Not retrofitting general RBAC onto `occurrences.py`/`documents.py`/`announcements.py`/`authorizations.py` for roles other than `PORTEIRO` — these four modules have no role-based authorization for *any* role today (only authentication), and this task closes that gap for `PORTEIRO` specifically (see Backend Changes) without designing or building a broader permission scheme for those modules. Whether `GUEST`/`RESIDENT` should also be restricted on these routes is a separate, pre-existing question this task does not address.
- Every route that already had a `requiredRole`/`requiredRoles` allowlist before this task (e.g. `/finance`, `/admin/users`, `/admin/access-control`, `/gate-monitor`) excludes `PORTEIRO` by construction, since `PORTEIRO` is never added to any of those allowlists — no further changes needed there. This is distinct from the six previously-unguarded routes and four previously-unchecked backend modules explicitly fixed above, which needed an active change, not just omission, to exclude `PORTEIRO`.

## Testing

- **Backend**: `PORTEIRO` succeeds on check-in/check-out endpoints; `PORTEIRO` succeeds on `GET /lots/` (required for the `GatekeeperDashboard` lot selector) but is still rejected on lot write endpoints (`_LOT_WRITE_ROLES` unchanged); `PORTEIRO` gets 403 from every handler in `occurrences.py`, `documents.py`, `announcements.py`, `authorizations.py` (one test per handler, or parametrized across all of them), while every other existing role's access to those four modules is unchanged (regression check — pick one non-`PORTEIRO` role and confirm it still succeeds where it did before); migration upgrade/downgrade/re-upgrade verified against real Postgres; confirm the enum value is actually present in a live database, not just the Python enum (the APRAS-27 lesson).
- **Frontend**: `/gate` route now requires one of the four allowed roles (previously unguarded — add a test proving a `GUEST`/`RESIDENT` is blocked, since this is a new restriction with no prior test coverage). Each of the six newly-gated routes (`/lots`, `/authorizations`, `/occurrences`, `/documents`, `/projects`, `/announcements`) blocks `PORTEIRO` and still allows every previously-allowed role (regression check per route). Root redirect sends `PORTEIRO` to `/gate`. A `PORTEIRO` denied by `requiredRole`/`requiredRoles` on some other route (e.g. `/finance`) is redirected to `/gate`, not left on `/dashboard`'s restricted-access message (the generalized `ProtectedRoute` branch) — verify this resolves in exactly one intermediate hop through `/dashboard`, with no loop. `PORTEIRO` is blocked from every other named route (spot-check a representative sample: `/dashboard` via the new `requiredMenu`+`PORTEIRO` redirect branch, `/lots` via `requiredRoles`, `/finance` via `requiredRoles`). An Administrator simulating `PORTEIRO` navigating directly to `/dashboard` is also redirected to `/gate` (effective-identity check, mirroring APRAS-10's `GUEST` simulation test), while a real Administrator's own root-redirect and post-login navigation are unaffected by that active simulation. Navbar shows only the "Portaria" link for `PORTEIRO`, nothing else.

## Expected Results

1. `PORTEIRO` role exists in the database enum (verified against real Postgres, not just Python).
2. `PORTEIRO` can check visitors in and out via the existing `/gate` flow, including successfully loading the lot selector (`GET /lots/` now permits `PORTEIRO`).
3. `ADMINISTRATOR`/`DIRECTOR`/`MANAGER` retain unchanged access to `/gate` and to `/lots`, `/authorizations`, `/occurrences`, `/documents`, `/projects`, `/announcements`.
4. `/gate` route is now properly role-gated (fixes the pre-existing unguarded-route gap), and so are `/lots`, `/authorizations`, `/occurrences`, `/documents`, `/projects`, `/announcements` (fixes the same class of gap for `PORTEIRO` specifically).
5. `PORTEIRO` lands on `/gate` after login and cannot reach any other authenticated route, including `/gate-monitor` — and a `PORTEIRO` denied elsewhere by `requiredRole`/`requiredRoles` is redirected to `/gate` rather than dead-ending on `/dashboard`'s restricted-access message.
6. Backend endpoints in `occurrences.py`, `documents.py`, `announcements.py`, and `authorizations.py` reject `PORTEIRO` with 403 while continuing to allow every other role that could call them before this task.
