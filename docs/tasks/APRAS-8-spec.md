# APRAS-8 — Restrict Tarefas/Categorias Access by UserType

**Date:** 2026-08-27
**Status:** Approved for implementation

## Problem

Today, any authenticated user (any role) sees the "Tarefas" and "Categorias" nav links and can hit their APIs, gated only by role (e.g. Manager's task visibility is filtered by `Task.visible_to_id`, Category writes are Administrator/Director-only). There's no way to say "this specific group of staff/residents shouldn't see Tarefas/Categorias at all" — `UserType` exists as an admin-managed label but has never been wired to page/feature-level access.

## Goal

Let an Administrator control, per `UserType`, whether users carrying that type can access the Tarefas and Categorias features at all — as an additional gate layered in front of the existing role-based RBAC, not a replacement for it.

## Scope Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Which roles are subject to this gate? | Only `ADMINISTRATOR` is exempt (always has access, unconditionally). **`DIRECTOR` is now also subject to the UserType gate** — this is a deliberate change from `DIRECTOR`'s previously-unconditional "full CRUD on all tasks" guarantee (see AGENTS.md RBAC table, which this spec updates). |
| Config model | `UserType` gets a generic `allowed_menus: list[str]` field (not two fixed booleans) — chosen for extensibility if more menus get gated later. Valid keys today: `"tasks"`, `"categories"` (validated at the schema level even though storage is a generic list). |
| Multiple UserTypes, conflicting permissions | A user has access to a menu if **at least one** of their assigned UserTypes has that menu in `allowed_menus` (most-permissive-of-assigned-types wins; the restrictive default lives in *not having* that UserType at all, not in one UserType overriding another). |
| User with zero UserTypes assigned | **No access** (except Administrator). This is the strict, no-fallback interpretation — a Director or Manager with no UserType assigned loses Tarefas/Categorias entirely until an Administrator assigns them a UserType with the relevant permission. |
| Enforcement level | Both. Frontend hides the nav links/blocks the routes, **and** the backend independently enforces the same rule on every `tasks`/`categories` endpoint — this is not cosmetic. |
| Migration rollout | `allowed_menus` starts **empty** (`[]`) for every existing `UserType` row. **This is intentionally disruptive**: on deploy, every Director/Manager/Guest/Resident loses access to Tarefas/Categorias — the app's core feature — until an Administrator manually opens the UserType management screen and grants `"tasks"`/`"categories"` to the relevant types. This was explicitly chosen over a safer "backfill everything as allowed" migration. Flagging prominently here because it is the single highest-impact decision in this spec. |

## Interaction with existing RBAC (not a replacement)

This is a coarse **feature gate** checked before a request reaches the existing fine-grained logic:

```
Request to /tasks/* or /categories/* (any role except ADMINISTRATOR)
        │
        ▼
assert_menu_access(user, "tasks" | "categories")   <- NEW, this spec
        │  (403 if none of the user's UserTypes allow this menu)
        ▼
existing role/visibility logic, unchanged:
  - assert_manager_can_see_task / visible_to_id filtering (tasks)
  - _CATEGORY_WRITE_ROLES = {ADMINISTRATOR, DIRECTOR} (categories)
```

A user who passes the new gate still goes through every existing check exactly as today. Nothing about `Task.visible_to_id`, `assert_can_edit_task`, or category write-role restrictions changes.

## Backend Changes

### `backend/app/models/enums.py`

```python
class MenuKey(StrEnum):
    TASKS = "tasks"
    CATEGORIES = "categories"
```

### `backend/app/models/user_type.py`

Add a portable `JSON` column — **must NOT use `sqlalchemy.dialects.postgresql.ARRAY`**. `ARRAY` does not compile against SQLite, and `backend/tests/conftest.py`'s `session` fixture creates the schema with `SQLModel.metadata.create_all(engine)` against a `sqlite://` in-memory engine for **every single test in the backend suite** (not just tasks/categories tests) — an `ARRAY` column would raise at `create_all()` time and break the entire suite. `sqlalchemy.JSON` compiles on both SQLite and Postgres and stores a Python `list[str]` directly with no manual serialization step (unlike the manual-string-serialization pattern used by `project.py`'s `photos_json: str | None`, which is not needed here):

```python
from sqlalchemy import JSON, Column

allowed_menus: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]"))
```

### `backend/app/schemas/user_type.py`

`UserTypeCreate`, `UserTypeUpdate`, `UserTypeRead` all gain `allowed_menus: list[MenuKey] = []`. No new validator needed beyond Pydantic's own enum-list validation (an invalid key like `"foo"` is rejected automatically).

### `backend/app/api/deps.py`

New dependency-style helper (not a FastAPI `Depends`, since it needs a per-request `menu_key` parameter — called explicitly at the top of each affected endpoint, mirroring how `assert_manager_can_see_task` is called explicitly rather than injected):

```python
def assert_menu_access(current_user: User, menu_key: MenuKey) -> None:
    """Raise ForbiddenError unless the user can access the given menu/feature.

    ADMINISTRATOR always passes. Every other role needs at least one
    assigned UserType with `menu_key` in its `allowed_menus`. A user with
    no UserTypes assigned is denied.
    """
    if current_user.role == UserRole.ADMINISTRATOR:
        return
    if any(menu_key.value in ut.allowed_menus for ut in current_user.user_types):
        return
    raise ForbiddenError(f"Not enough privileges to access {menu_key.value}")
```

### Migration

New Alembic revision (chain after the current head at implementation time — check `alembic heads` rather than assuming a number): adds the `allowed_menus` column to `user_type` as `sa.JSON()` (**not** a Postgres `ARRAY` — see model section above), `server_default='[]'`, `nullable=False`. No backfill logic beyond the column default — every existing row gets `[]` (empty), which is the intended disruptive rollout described above.

### Endpoints touched

- `backend/app/api/v1/endpoints/tasks.py`: every route (`list_tasks`, `create_task`, `get_task`, `update_task`, `delete_task`, comment routes, history route) calls `assert_menu_access(current_user, MenuKey.TASKS)` before its existing logic.
- `backend/app/api/v1/endpoints/categories.py`: every route calls `assert_menu_access(current_user, MenuKey.CATEGORIES)` before its existing logic.
- `backend/app/api/v1/endpoints/user_types.py`: **must be updated** — today `create_user_type` hard-assigns only `user_type = UserType(name=user_type_in.name)` and `update_user_type` hard-assigns only `db_type.name = user_type_in.name`, so both currently silently drop `allowed_menus` from any request body. `create_user_type` must pass `allowed_menus=user_type_in.allowed_menus` into the `UserType(...)` constructor, and `update_user_type` must assign `db_type.allowed_menus = user_type_in.allowed_menus` alongside the existing `db_type.name = user_type_in.name`.

## Frontend Changes

### `frontend/src/features/user-administration/context/useEffectiveIdentity.ts` (or a new small hook alongside it)

New hook `useMenuAccess(menuKey: "tasks" | "categories"): boolean`, combining `useEffectiveIdentity()` (role + `userTypeIds`, already simulation-aware from the admin-role-simulation feature — this hook should respect an active simulation the same way existing checks do) with the already-existing `useUserTypes()` data (`frontend/src/hooks/useUserTypes.ts`, which now includes `allowed_menus` per type): `role === ADMINISTRATOR` → true; else → true if any of the user's `userTypeIds` maps to a UserType whose `allowed_menus` includes `menuKey`.

Type updates needed: `frontend/src/types/auth.ts`'s `UserType` interface (currently just `{ id: string; name: string }`) needs `allowed_menus: string[]` added, and `useUserTypes()`'s return type (typed via that same `UserType` import) picks this up automatically once the interface is updated.

### `Navbar.tsx`

Tarefas and Categorias links wrapped in `{useMenuAccess("tasks") && ...}` / `{useMenuAccess("categories") && ...}` respectively (today they render unconditionally for any authenticated user).

### `ProtectedRoute.tsx`

New optional prop `requiredMenu?: "tasks" | "categories"`. When present, in addition to any `requiredRole`/`requiredRoles` check, the route also requires `useMenuAccess(requiredMenu)` to be true; if both a role-based prop and `requiredMenu` are present on the same route, both must pass (they are independent, `AND`-ed gates — this spec does not add any route using both together, but the precedence should hold in the general case for future routes). **Unlike the existing `requiredRole` check (which redirects to `/dashboard`), a failed `requiredMenu` check does not redirect** — `/dashboard` is itself one of the two gated routes, so redirecting there risks a loop for a user blocked from both, and no other route is guaranteed reachable for every role/UserType combination. Instead, render a small inline "Acesso restrito" message component in place of `children`, with no navigation — the user stays on the URL they tried, sees why they can't proceed, and can navigate elsewhere via the Navbar links they *do* have.

`App.tsx`: `/dashboard` route gets `requiredMenu="tasks"`, `/categories` route gets `requiredMenu="categories"`.

**Note on using `useEffectiveIdentity` (simulated identity) for a route guard:** `useEffectiveIdentity.ts` currently carries a doc comment stating route guards "must always reflect the real user's access so the admin can never get locked out of ending a simulation," and `useMenuAccess` (built on `useEffectiveIdentity`) is wired into `ProtectedRoute` specifically to diverge from that. This divergence is intentional and correct here, not an oversight: the entire point of admin-role-simulation is to let an Administrator preview the app as another role/UserType would see it, and if `requiredMenu` checks used the admin's *real* (always-passing) identity instead of the simulated one, an Administrator could never preview what a menu-gated page (`/dashboard`, `/categories`) looks like when blocked — the feature would be silently inert on exactly the two routes this spec adds gating to. The lockout scenario the original comment warns about does not reapply: the exit-simulation control (`SimulationBanner`, in `frontend/src/features/user-administration/components/SimulationBanner.tsx`) is rendered in `App.tsx` as a sibling of `<Routes>` (inside the top-level `<div className="App">`, alongside `<Navbar />`), not inside any `ProtectedRoute`/`<Route>` — so it stays on screen and clickable regardless of what any `ProtectedRoute` renders, and an admin can always end a simulation no matter how many routes are blocked under the simulated identity.

Update `useEffectiveIdentity.ts`'s doc comment to carve out this one exception, e.g.:

```
 * Route guards (`ProtectedRoute`) intentionally do NOT use this hook for
 * requiredRole/requiredRoles checks — those must always reflect the real
 * user's access so the admin can never get locked out of ending a
 * simulation. The one exception is `requiredMenu` checks (via
 * `useMenuAccess`), which intentionally DO use simulated identity so
 * admin-role-simulation can preview menu-gated pages; this is safe because
 * the exit-simulation control (`SimulationBanner`) is rendered outside
 * `ProtectedRoute`/`<Routes>` in App.tsx and is always reachable.
```

### `AdminUserDashboard`'s UserType management UI — net-new edit affordance

Verified against `frontend/src/features/user-administration/pages/AdminUserDashboard.tsx`: the "User Types" section today only has (a) a name-only create form (`newTypeName` input + `createTypeMutation` → `POST /user-types/`) and (b) a `×` delete button per `UserType` `Badge` (`deleteTypeMutation` → `DELETE /user-types/{id}`). There is **no edit UI for a `UserType` itself and no `PATCH` mutation for it anywhere in this file** — the existing "Edit User" modal (`editingUser`/`handleSaveEdit`) only edits a *User's* name and its assigned `user_type_ids`, it does not touch a `UserType`'s own fields. This spec must build this edit affordance from scratch:

- Add an edit button (or make the `Badge` itself clickable) next to each `UserType` in the badge list, opening a small modal/form (mirroring the existing "Edit User" modal's structure: local state + open/close + save button) with a checkbox per valid `MenuKey` (`"tasks"`, `"categories"`) reflecting/toggling that UserType's `allowed_menus`.
- Add a new `updateUserTypeMutation` (`useMutation`, following the same shape as `createTypeMutation`/`deleteTypeMutation`) that calls the existing backend `PATCH /user-types/{id}` with `{ name, allowed_menus }`, invalidates the `["user-types"]` query on success, and surfaces errors via the existing `actionError`/`AlertModal` pattern.
- Local state: e.g. `editingType: UserType | null`, `editTypeAllowedMenus: string[]`, following the same naming/structural convention as `editingUser`/`editTypeIds` already in this file.

## Documentation

`AGENTS.md`'s RBAC table row for `DIRECTOR` ("Full CRUD on all tasks; toggle `manager_visible`") needs a note that this is now conditional on UserType-based menu access (Administrator is the only role with an unconditional guarantee).

Note: `AGENTS.md`'s RBAC table is already missing a `RESIDENT` row entirely (a pre-existing gap, unrelated to this spec). Fully reconciling the table is out of scope here, but the `DIRECTOR`-row edit above should be written so it doesn't imply the rest of the table is otherwise complete/current.

## Non-Goals

- Not touching `Task.visible_to_id` / existing manager visibility filtering — unchanged.
- Not gating any other menu/feature beyond Tarefas and Categorias (the generic `allowed_menus` list makes future additions cheap, but none are in scope here).
- Not building any migration/backfill tooling to bulk-assign permissions — an Administrator does this by hand, one UserType at a time, via the existing management UI.

## Testing

- **Backend**: `assert_menu_access` unit-testable in isolation (Administrator always passes; a role with a matching UserType passes; a role with only non-matching UserTypes is denied; a role with zero UserTypes is denied). Endpoint-level tests for both `tasks.py` and `categories.py`: a Director/Manager/Guest/Resident with no qualifying UserType gets 403 on every route; granting the right `allowed_menus` value restores access; Administrator is never blocked regardless of UserType.

  **Blast radius — this is bigger than `test_tasks_rbac.py`/category tests.** `normal_user` (a `DIRECTOR`, defined once in `backend/tests/conftest.py`'s `normal_user_fixture`) is reused across roughly 19 other test files in `backend/tests/`, and it currently has no `UserType` assigned at all. Since `DIRECTOR` is newly subject to the menu gate (per the Scope Decisions table — this is intentional, not being revisited here), every test that has `normal_user` hit a `tasks`/`categories` endpoint will start getting 403s where it previously got 200s, purely as a side effect of this change. At minimum, the following files call task/category endpoints as `normal_user` and would break: `test_tasks_api.py`, `test_task_comments.py`, `test_filters.py`, `test_soft_delete.py`, `test_e2e_flow.py`, `test_coverage_fix.py`, `test_missing_coverage.py` (verify the exact set at implementation time — new tests may have been added since this spec was written).

  **Fix strategy**: do not patch each of these files individually. Instead, update the shared `normal_user_fixture` in `backend/tests/conftest.py` to also create (or reuse) a `UserType` with `allowed_menus: ["tasks", "categories"]` and assign it to `normal_user` before returning it, so the fixture itself carries forward the access `normal_user` previously had unconditionally. `test_tasks_rbac.py`/category-specific tests that need a user *without* menu access (to exercise the new 403 path) should build that user explicitly in-test rather than relying on `normal_user`, since `normal_user` is now expected to have standing access by construction of the shared fixture.
- **Frontend**: `useMenuAccess` hook tests for Administrator-always-true, matching-UserType-true, no-UserType-false; `Navbar` link visibility tests per role/UserType combination; `ProtectedRoute` tests for the new `requiredMenu` prop: denying renders the inline restricted-access message (no navigation/redirect), allowing renders `children` normally.

## Expected Results

1. `UserType.allowed_menus` (portable `sqlalchemy.JSON` column, not `ARRAY`, default empty) exists and is editable via the API (`create_user_type`/`update_user_type` persist it) and the new UserType edit UI.
2. `GET/POST/PUT/DELETE` on `/tasks/*` and `/categories/*` return 403 for any non-Administrator user unless at least one of their assigned UserTypes has the corresponding key in `allowed_menus`.
3. Administrator is never blocked by this gate, regardless of their own UserTypes.
4. Navbar hides the Tarefas/Categorias links, and `ProtectedRoute` blocks rendering of `/dashboard`/`/categories` (inline "Acesso restrito" message, no redirect) for users failing the gate.
5. `AGENTS.md`'s RBAC table is updated to reflect that Director's task access is now conditional on UserType.
