# APRAS-9 — Treat UserRole as a UserType for Permission Evaluation

**Date:** 2026-08-27
**Status:** Approved for implementation

## Problem

APRAS-8 gated Tarefas/Categorias behind `UserType.allowed_menus`, and a user with zero explicitly-assigned UserTypes gets zero access (except Administrator) — deliberately, but it means an Administrator has to remember to assign an explicit UserType to every Director/Manager/Guest/Resident just to restore baseline access. Separately, `Task.visible_to_id` (targeting a task at a UserType) has the same limitation: there's no way to target "all Managers" without first creating and assigning an explicit UserType to every manager.

## Goal

Let a user's own `UserRole` act as an implicit `UserType` for both permission systems (APRAS-8's menu gate and `Task.visible_to_id` targeting), so an Administrator can configure baseline permissions once per role instead of per individually-assigned UserType — without touching the disruptive default from APRAS-8 (role-based types still start with empty `allowed_menus`; this task provides the *mechanism*, it does not silently restore access on its own).

## Scope Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Which systems does this feed? | Both: APRAS-8's `assert_menu_access` gate, and `Task.visible_to_id` targeting/visibility filtering. One mechanism, not two. |
| Implementation mechanism | Materialize one real `UserType` row per `UserRole` value (not a parallel/separate structure), so `Task.visible_to_id` (already an FK to `UserType.id`) and the existing UserType management UI work with zero special-casing. |
| Membership mechanism | Implicit/computed, not a stored link. No new row is added to the `UserUserTypeLink` join table. Permission-evaluation code computes "effective UserType ids" = explicitly-assigned types ∪ {the UserType matching the user's own role}, on every check. This means a role change takes effect immediately with no sync step. |
| Default `allowed_menus` for role-types | Empty (`[]`), matching APRAS-8's already-established disruptive-by-default philosophy. This task is the tool for an Administrator to configure baseline-by-role permissions; it does not use that tool on their behalf. |
| Which roles get a row? | All five (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `GUEST`, `RESIDENT`), for consistency and so `visible_to_id` targeting is available uniformly — even though Administrator's own row is functionally moot for the menu gate (Administrator already bypasses it unconditionally). |
| Can role-types be deleted or renamed? | Not deleted (a dedicated `role` column identifies them; the delete action is disabled in the UI when this column is set — not a fragile name-string match, so renaming the display name never breaks the mapping). Renaming the display name is allowed. |

## Data Model

### `backend/app/models/user_type.py`

Add a nullable column identifying a role-linked type:

```python
role: UserRole | None = Field(default=None, nullable=True, unique=True)
```

`unique=True` guarantees at most one `UserType` per role value. Both Postgres and SQLite treat `NULL` as distinct from itself in a `UNIQUE` constraint (standard SQL semantics), so admin-created types (`role IS NULL`) are never limited to one row by this constraint — only a second row with the *same non-null* role value would be rejected, which is exactly the intent. No partial index needed; a plain `unique=True` column behaves identically on both databases here.

### `backend/app/schemas/user_type.py`

`UserTypeRead` gains `role: UserRole | None`. `UserTypeCreate`/`UserTypeUpdate` do **not** gain a settable `role` field — role-types are only created by the migration/seed step below, never through the regular create/update API, to prevent an admin from accidentally minting a second "role type" for the same role or repurposing an arbitrary UserType into one.

### Migration

New Alembic revision (check `alembic heads` for the actual current head — do not assume a specific prior number) that:
1. Adds the `role` column to `user_type` (nullable, unique or partial-unique index per the note above).
2. Seeds exactly 5 rows, one per `UserRole` value, each with `allowed_menus = []` and a human-readable `name` distinguishing them from admin-created types (e.g. `"Administrador (papel)"`, `"Diretor (papel)"`, `"Gerente (papel)"`, `"Convidado (papel)"`, `"Morador (papel)"`), each with its `role` column set to the corresponding enum value.

Downgrade removes the seeded rows (matched by `role IS NOT NULL`, not by name) and drops the column.

## Backend Changes

### New helper: effective UserType ids

Add to `backend/app/api/deps.py` (alongside `assert_menu_access`):

```python
def get_effective_user_type_ids(user: User, session: Session) -> set[UUID]:
    """Return the user's explicitly-assigned UserType ids plus the id of
    the UserType matching their own role, if one exists."""
    explicit_ids = {ut.id for ut in user.user_types}
    role_type = session.exec(select(UserType).where(UserType.role == user.role)).first()
    if role_type:
        explicit_ids.add(role_type.id)
    return explicit_ids
```

### Call sites updated to use effective ids instead of raw `user.user_types`

`assert_menu_access` and `assert_manager_can_see_task` currently take no `Session` and are called as plain functions (not via `Depends`). Both must gain a `session: Session` parameter, and every call site must be updated to pass it. `session` is already in scope (as a FastAPI-injected parameter) at every one of these call sites — verified by reading the endpoint modules — so this is a mechanical signature change, no new dependency wiring needed:

- `assert_menu_access(current_user, menu_key)` → `assert_menu_access(current_user, menu_key, session)` (or keyword; exact param order is an implementation detail). Body: replace its `ut.allowed_menus for ut in current_user.user_types` iteration with a check against `get_effective_user_type_ids(current_user, session)`.
  - Update all 8 call sites in `backend/app/api/v1/endpoints/tasks.py` (`create_task`, `list_tasks`, `update_task`, `get_task_history`, `delete_task`, `list_comments`, `create_comment`, `update_comment`).
  - Update all 4 call sites in `backend/app/api/v1/endpoints/categories.py` (`list_categories`, `create_category`, `update_category`, `delete_category`).
- `assert_manager_can_see_task(current_user, task)` → `assert_manager_can_see_task(current_user, task, session)`. Body: replace `[ut.id for ut in current_user.user_types]` with `get_effective_user_type_ids(current_user, session)`.
  - Update all 5 call sites in `backend/app/api/v1/endpoints/tasks.py` (`update_task`, `get_task_history`, `list_comments`, `create_comment`, `update_comment`).
- `list_tasks`'s SQL visibility filter (`backend/app/api/v1/endpoints/tasks.py`, the `Task.visible_to_id.in_(user_type_ids)` clause guarding `UserRole.MANAGER`): `user_type_ids` must be built from `get_effective_user_type_ids(current_user, session)`, not the raw ORM traversal `[ut.id for ut in current_user.user_types]` it uses today.

That's 8 + 5 + 4 + 1 = 18 call-site edits total across `tasks.py` (14) and `categories.py` (4), plus the two helper-function signature changes themselves. This is the real footprint of this change in `deps.py`/`tasks.py`/`categories.py` — size estimation and review effort should account for all of it, not just the one SQL-filter line.

### `backend/app/services/task_service.py` — two more call sites needing the same fix

`TaskService.create_task` (currently ~lines 33-35) auto-defaults a new task's `visible_to_id` to `current_user.user_types[0].id` when a `MANAGER` creates a task without specifying one. A Manager relying solely on their role-type (the exact scenario this task fixes — zero explicit UserTypes) gets no auto-default here, since `current_user.user_types` is empty for them. Replace the `if current_user.user_types: db_task.visible_to_id = current_user.user_types[0].id` block with logic built on `get_effective_user_type_ids(current_user, session)`: pick a stable, deterministic member of that set (e.g. sorted, or prefer an explicit id over the role-type id if both exist) rather than an arbitrary first element — either is acceptable as long as it's deterministic and covers the role-type-only case.

`TaskService.update_task` (currently ~lines 51-57) validates a `MANAGER`'s new `visible_to_id` against `[ut.id for ut in current_user.user_types]` only — same gap: a Manager with only a role-type can never successfully set `visible_to_id` to their own role-type's id. Replace the `user_type_ids = [ut.id for ut in current_user.user_types]` line with `get_effective_user_type_ids(current_user, session)`.

Both `create_task` and `update_task` are `@staticmethod`s that already receive both `session` and `current_user` as parameters — no signature change is needed on either method; only their internal bodies change to call `get_effective_user_type_ids(current_user, session)` instead of traversing `current_user.user_types` directly.

No other RBAC logic changes — `assert_can_edit_task`, category write-role restrictions, etc. are untouched.

## Frontend Changes

### `frontend/src/types/auth.ts`

`UserType` interface gains `role?: string | null`.

### `useEffectiveIdentity.ts` (`frontend/src/features/user-administration/context/`) — the single fold-in point

This hook, not `useTaskFiltering.ts`/`useMenuAccess.ts`/`simulatedPermissions.ts` individually, is where the role-linked UserType id must be folded in. Rationale: `useEffectiveIdentity()`'s `userTypeIds` output is already consumed independently by three separate call sites — `useTaskFiltering.ts:48` (via a `simulation` prop built by its callers), and `TaskList.tsx:111` / `TaskBoard.tsx:130` (which call `canEditSimulatedTask` directly with `userTypeIds` destructured from `useEffectiveIdentity()` at `TaskList.tsx:34` / `TaskBoard.tsx:29`). Folding the role-type id in at the source means all three get correct behavior automatically, with **zero changes** to `useTaskFiltering.ts`, `TaskList.tsx`, or `TaskBoard.tsx` themselves.

Change `useEffectiveIdentity()` so its returned `userTypeIds` already includes the id of the `UserType` whose `role` matches the effective `role` (real or simulated), in addition to the explicitly-assigned ids it returns today. This mirrors how `useMenuAccess` already combines `useEffectiveIdentity()` + `useUserTypes()` in the same file's neighborhood — `useEffectiveIdentity` can call `useUserTypes()` itself (or receive its data) to look up the role-matching row and add its id to the returned `userTypeIds` set, for both the real-identity branch and the `isSimulating` branch (a simulated role must also get its role-type id folded in, not just the real user's).

Because `useMenuAccess.ts` already filters purely via `userTypeIds.includes(userType.id) && userType.allowed_menus.includes(menuKey)` (no other role-matching logic of its own), once `useEffectiveIdentity()` folds the role-type id into `userTypeIds`, **`useMenuAccess.ts` needs no code change at all** — it inherits the fix for free. This supersedes any earlier note about extending `useMenuAccess.ts` directly.

### `simulatedPermissions.ts` (`frontend/src/features/task-management/utils/`)

No changes needed to `canSeeSimulatedTask`/`canEditSimulatedTask` themselves, nor to their callers (`useTaskFiltering.ts`, `TaskList.tsx`, `TaskBoard.tsx`): since all of them source `userTypeIds` from `useEffectiveIdentity()` (real or simulated), the fold-in above flows through to every caller unchanged.

### `AdminUserDashboard.tsx` — UserType management UI

- The delete (`×`) button and the create-form are unaffected for regular types.
- For a `UserType` row where `role` is set: disable/hide the delete button (with a tooltip/label indicating it's a role-linked type), but keep the existing edit-`allowed_menus` affordance (built in APRAS-8) fully functional — this is the whole point of the feature.
- No new UI is needed to *create* a role-type (the migration seeds them; the API doesn't allow creating new ones per the schema decision above).

### `TaskForm.tsx`'s `visible_to_id` dropdown

No code change needed — it already lists whatever `useUserTypes()` returns, so the 5 seeded role-types appear automatically, labeled by their seeded `name` (e.g. "Gerente (papel)").

## Documentation

`AGENTS.md`'s `### UserType` section (added by APRAS-8) currently states: "A user with no UserTypes assigned has no access to gated menus." This becomes false once APRAS-9 ships: such a user's access is now determined by their role-type's `allowed_menus` (still empty by default, but administrator-configurable, and no longer hard-denied by the absence of an explicit UserType). Update this sentence to describe the role-type fallback and reference `get_effective_user_type_ids` as the mechanism, e.g.: "A user with no explicitly-assigned UserTypes falls back to the UserType implicitly linked to their own role (see APRAS-9); since that role-type starts with empty `allowed_menus`, the practical effect is the same until an Administrator configures it."

Also review the `DIRECTOR`/`MANAGER` RBAC table rows (lines ~311-313) referencing "at least one of the [role]'s assigned UserTypes" — reword to "assigned or role-linked UserTypes" (or equivalent) so the table doesn't imply only explicit assignments count.

## Non-Goals

- Not creating a UI to add role-types beyond the 5 seeded ones, or to link a role to more than one UserType.
- Not changing `assert_can_edit_task`, category RBAC, or any RBAC logic untouched by this spec.
- Not restoring pre-APRAS-8 access levels — role-types start empty, same as any other UserType would.
- Not exposing a way to change which role a seeded row maps to (the `role` column is set once, at seed time, and never editable via the API).

## Testing

- **Backend**: `get_effective_user_type_ids` unit tests (explicit types only, role-type only, both combined, deduplication if a user happens to have both). Migration test: exactly 5 role-types seeded with the correct role values and empty `allowed_menus`; the unique-per-role constraint actually prevents a second row with the same `role`. Endpoint tests: a Director with zero explicit UserTypes still gets 403 on `/tasks/*` (role-type starts empty, so this is *not* a regression — assert this explicitly so a future change to the default doesn't silently break the test's intent unnoticed); after setting the "Diretor (papel)" type's `allowed_menus` to `["tasks"]` via `PATCH /user-types/{id}`, that same Director (still with zero explicit types) now succeeds on `/tasks/*`. A task with `visible_to_id` set to the "Gerente (papel)" id is visible to a Manager with zero explicit UserTypes. Attempting `DELETE /user-types/{id}` on a role-type returns 403/400 (not 204).
- **Frontend**: `useEffectiveIdentity` test confirming `userTypeIds` includes the role-matching `UserType` id for both the real-identity branch and the `isSimulating` branch, with no explicit UserTypes assigned/simulated. `useMenuAccess` test for role-type-only access (no explicit UserType assigned) — should pass unchanged once `useEffectiveIdentity` is fixed, proving no `useMenuAccess.ts` code change was needed. `useTaskFiltering`/`TaskList`/`TaskBoard` tests confirming a simulated role with no simulated UserTypes selected still resolves the role-type's visibility/edit rules via `simulatedPermissions.ts`, with no changes to those three files. `AdminUserDashboard` test confirming the delete button is disabled/absent for a role-linked type row.

## Expected Results

1. Exactly one `UserType` row exists per `UserRole` value, each starting with `allowed_menus: []`.
2. A user with zero explicitly-assigned UserTypes has their menu access and task visibility determined by their role-type's current `allowed_menus`/`visible_to_id` matches, not hard-denied by default.
3. Role-type `allowed_menus` is editable via the existing `PATCH /user-types/{id}` endpoint and UI, and takes effect immediately for every user of that role with no explicit UserType.
4. Role-types cannot be deleted via the API or UI.
5. `Task.visible_to_id` can target a role-type, making a task visible to every Manager (or Director, etc.) without any explicit UserType assignment.
6. `AGENTS.md`'s `### UserType` section and the `DIRECTOR`/`MANAGER` RBAC table rows no longer claim a user with zero explicit UserTypes has "no access"/"is blocked" outright — both now describe the role-type fallback.
