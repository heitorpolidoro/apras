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

Add a Postgres array column:

```python
from sqlalchemy import ARRAY, String, Column

allowed_menus: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), nullable=False, server_default="{}"))
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

New Alembic revision (chain after the current head at implementation time — check `alembic heads` rather than assuming a number): adds the `allowed_menus` Postgres array column to `user_type`, `server_default='{}'`, `nullable=False`. No backfill logic beyond the column default — every existing row gets `{}` (empty), which is the intended disruptive rollout described above.

### Endpoints touched

- `backend/app/api/v1/endpoints/tasks.py`: every route (`list_tasks`, `create_task`, `get_task`, `update_task`, `delete_task`, comment routes, history route) calls `assert_menu_access(current_user, MenuKey.TASKS)` before its existing logic.
- `backend/app/api/v1/endpoints/categories.py`: every route calls `assert_menu_access(current_user, MenuKey.CATEGORIES)` before its existing logic.

## Frontend Changes

### `frontend/src/features/user-administration/context/useEffectiveIdentity.ts` (or a new small hook alongside it)

New hook `useMenuAccess(menuKey: "tasks" | "categories"): boolean`, combining `useEffectiveIdentity()` (role + `userTypeIds`, already simulation-aware from the admin-role-simulation feature — this hook should respect an active simulation the same way existing checks do) with the already-existing `useUserTypes()` data (which now includes `allowed_menus` per type): `role === ADMINISTRATOR` → true; else → true if any of the user's `userTypeIds` maps to a UserType whose `allowed_menus` includes `menuKey`.

### `Navbar.tsx`

Tarefas and Categorias links wrapped in `{useMenuAccess("tasks") && ...}` / `{useMenuAccess("categories") && ...}` respectively (today they render unconditionally for any authenticated user).

### `ProtectedRoute.tsx`

New optional prop `requiredMenu?: "tasks" | "categories"`. When present, in addition to any `requiredRole`/`requiredRoles` check, the route also requires `useMenuAccess(requiredMenu)` to be true. **Unlike the existing `requiredRole` check (which redirects to `/dashboard`), a failed `requiredMenu` check does not redirect** — `/dashboard` is itself one of the two gated routes, so redirecting there risks a loop for a user blocked from both, and no other route is guaranteed reachable for every role/UserType combination. Instead, render a small inline "Acesso restrito" message component in place of `children`, with no navigation — the user stays on the URL they tried, sees why they can't proceed, and can navigate elsewhere via the Navbar links they *do* have.

`App.tsx`: `/dashboard` route gets `requiredMenu="tasks"`, `/categories` route gets `requiredMenu="categories"`.

### `AdminUserDashboard`'s UserType management UI

The existing "Add type" / edit-type UI (a name-only input today) gains a checkbox pair (or small multi-select) for `allowed_menus`, following the same checkbox-list visual pattern already used for `user_type_ids` assignment in the same file.

## Documentation

`AGENTS.md`'s RBAC table row for `DIRECTOR` ("Full CRUD on all tasks; toggle `manager_visible`") needs a note that this is now conditional on UserType-based menu access (Administrator is the only role with an unconditional guarantee).

## Non-Goals

- Not touching `Task.visible_to_id` / existing manager visibility filtering — unchanged.
- Not gating any other menu/feature beyond Tarefas and Categorias (the generic `allowed_menus` list makes future additions cheap, but none are in scope here).
- Not building any migration/backfill tooling to bulk-assign permissions — an Administrator does this by hand, one UserType at a time, via the existing management UI.

## Testing

- **Backend**: `assert_menu_access` unit-testable in isolation (Administrator always passes; a role with a matching UserType passes; a role with only non-matching UserTypes is denied; a role with zero UserTypes is denied). Endpoint-level tests for both `tasks.py` and `categories.py`: a Director/Manager/Guest/Resident with no qualifying UserType gets 403 on every route; granting the right `allowed_menus` value restores access; Administrator is never blocked regardless of UserType. Existing `test_tasks_rbac.py`/category tests must be updated to grant the necessary `allowed_menus` to their fixture users, or they'll start failing under the new default-deny posture — this is expected and should be treated as "fixture setup catching up to the new gate," not a regression.
- **Frontend**: `useMenuAccess` hook tests for Administrator-always-true, matching-UserType-true, no-UserType-false; `Navbar` link visibility tests per role/UserType combination; `ProtectedRoute` tests for the new `requiredMenu` prop: denying renders the inline restricted-access message (no navigation/redirect), allowing renders `children` normally.

## Expected Results

1. `UserType.allowed_menus` (Postgres array, default empty) exists and is editable via the API and the UserType management UI.
2. `GET/POST/PUT/DELETE` on `/tasks/*` and `/categories/*` return 403 for any non-Administrator user unless at least one of their assigned UserTypes has the corresponding key in `allowed_menus`.
3. Administrator is never blocked by this gate, regardless of their own UserTypes.
4. Navbar hides the Tarefas/Categorias links, and `ProtectedRoute` blocks direct navigation to `/dashboard`/`/categories`, for users failing the gate.
5. `AGENTS.md`'s RBAC table is updated to reflect that Director's task access is now conditional on UserType.
