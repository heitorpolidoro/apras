# APRAS-11 — Multiple UserTypes per Task Visibility Target

**Date:** 2026-08-27
**Status:** Approved for implementation

## Dependency note

**This task must be implemented after `APRAS-9` is merged**, not concurrently. Both tasks modify the same functions (`assert_manager_can_see_task`, `list_tasks`'s SQL visibility filter, `TaskService.create_task`/`update_task`, `simulatedPermissions.ts`, `useEffectiveIdentity.ts`). Building APRAS-11 on top of APRAS-9's already-merged `get_effective_user_type_ids` helper (rather than duplicating or conflicting with it) avoids two independent agents reshaping the same functions at once. Tracked via `blockedBy: ["APRAS-9"]` in `.meridian/tasks.json`.

## Problem

`Task.visible_to_id` is a single nullable FK to `UserType.id` — a task can be targeted at exactly one UserType (or `null`, meaning visible to every Manager). There's no way to make a task visible to multiple UserTypes at once (e.g. "visible to both Financeiro and Jurídico") without either duplicating the task or leaving it untargeted.

## Goal

Let a task be targeted at any number of UserTypes (zero or more), preserving the existing "empty/no targets = visible to every Manager" semantics.

## Scope Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Multiple targets per task? | Yes — a task is visible to a Manager if it has no targets at all (current `null` behavior, unchanged) OR at least one of its targets is in the Manager's effective UserType ids (per APRAS-9). |
| Manager's auto-default on task creation | When a Manager creates a task without specifying targets, default to their **explicit** UserType ids (i.e. `current_user.user_types`, not the APRAS-9 effective set) — falling back to their role-type id alone **only if they have zero explicit UserTypes**. Using the full effective set unconditionally would be wrong: after APRAS-9, every Manager's effective set always includes the single shared `MANAGER` role-type id, so defaulting to the full effective set would make every auto-defaulted task visible to *every* Manager in the org, not just the creator's peers — the opposite of the "visible to peers" intent. Restricting the default to explicit ids (with the role-type id only as a last resort) actually preserves that intent: a Manager with a real department/type defaults to visibility scoped to that type; only a Manager with no explicit type at all falls back to the broad role-type default, same as `null` did before. |
| Manager's validation on setting targets | A Manager may only set targets that are a subset of their own effective UserType ids (cannot grant visibility to a type they don't belong to) — same restriction as today's single-value check, generalized to a list. |

## Data Model

### New join table: `backend/app/models/task.py` (or a new small file if it grows the model file too much — developer's call, follow existing file-size conventions in this codebase)

```python
class TaskVisibleToLink(SQLModel, table=True):
    __tablename__ = "task_visible_to_link"

    task_id: UUID = Field(foreign_key="task.id", primary_key=True)
    user_type_id: UUID = Field(foreign_key="user_type.id", primary_key=True)
```

This matches `backend/app/models/user_type_link.py`'s `UserUserTypeLink` exactly: composite primary key (`task_id`, `user_type_id`), no surrogate `id` column, no `ondelete`/`index` annotations. (An earlier draft of this spec added a surrogate `id`, a `UniqueConstraint`, `ondelete="CASCADE"`, and explicit `index=True` — none of that exists on `UserUserTypeLink`, so it was a spurious deviation, not a deliberate one; dropped in favor of consistency with the existing link-table convention.)

### `Task` model

Remove `visible_to_id: UUID | None`. Add:

```python
visible_to: list[UserType] = Relationship(link_model=TaskVisibleToLink)
```

### Migration

New Alembic revision (check `alembic heads` for the actual current head at implementation time):
1. Create `task_visible_to_link` table.
2. Backfill: for every existing `task` row with a non-null `visible_to_id`, insert one row into `task_visible_to_link` (`task_id`, that `visible_to_id` value).
3. Drop the `task.visible_to_id` column.

Downgrade: re-add `visible_to_id` (nullable), backfill it from `task_visible_to_link` by picking one arbitrary target per task if multiple exist (document this as lossy — downgrading after multiple targets have been assigned to any task loses data beyond the first target; this is acceptable for a downgrade path, not a normal operation), then drop the join table.

This exact pattern — an `INSERT INTO ... SELECT` backfill on upgrade and an arbitrary `LIMIT 1` lossy downgrade — already has precedent in this codebase: `backend/alembic/versions/3f75bcd3d49f_many_to_many_user_types_and_task_.py` did the structurally identical thing when it introduced the current `visible_to_id` single-FK from an earlier state. Follow that migration's approach directly rather than inventing a new one.

## Backend Changes

### `backend/app/schemas/task.py`

- `TaskCreate`/`TaskUpdate`: replace `visible_to_id: UUID | None = None` with `visible_to_ids: list[UUID] = []`.
- `TaskRead`: replace `visible_to_id` with `visible_to: list[UserTypeRead] = []` (full nested objects, not just ids — matches how the frontend needs to display target names, not just match ids).

### `backend/app/api/deps.py` — `assert_manager_can_see_task`

Change the check from `task.visible_to_id is None or task.visible_to_id in effective_ids` to:

```python
if task.visible_to and not ({vt.id for vt in task.visible_to} & get_effective_user_type_ids(current_user, session)):
    raise TaskNotFoundError(task.id)
```

(An empty `task.visible_to` list is falsy, preserving "no targets = visible to everyone" exactly as `None` did before.)

### `backend/app/api/v1/endpoints/tasks.py` — `list_tasks`

This codebase has no existing EXISTS/join-based membership filter to follow as precedent — the only comparable pattern (`user.user_types`) is always resolved by loading into a Python list and filtering with `.in_()`, never a SQL EXISTS. Since `Task.visible_to` is now many-to-many, a naive join in the main row-selecting query (like today's `.join(UserType, Task.visible_to_id == UserType.id, isouter=True)`) would fan out one row per `(task, target)` pair and corrupt the result set. The fix has two independent parts:

**1. WHERE-clause filter (gating, not row assembly).** Drop the joined `UserType` column from the main `select(...)` entirely — the query goes back to selecting only `Task, creator_alias.full_name, assignee_alias.full_name, Category.name, Category.color` (no `UserType.name`, no `.join(UserType, ...)`). For the `UserRole.MANAGER` branch, replace the `or_(Task.visible_to_id.is_(None), Task.visible_to_id.in_(user_type_ids))` clause with a `NOT EXISTS(...) OR EXISTS(...)` pair built from `TaskVisibleToLink`, e.g.:

```python
from sqlalchemy import exists

effective_ids = get_effective_user_type_ids(current_user, session)
has_any_target = exists(
    select(TaskVisibleToLink.task_id).where(TaskVisibleToLink.task_id == Task.id)
)
has_matching_target = exists(
    select(TaskVisibleToLink.task_id).where(
        TaskVisibleToLink.task_id == Task.id,
        TaskVisibleToLink.user_type_id.in_(effective_ids),
    )
)
statement = statement.where(or_(~has_any_target, has_matching_target))
```

(Adapt exact syntax to this repo's SQLModel/SQLAlchemy version — e.g. `sqlmodel.select` vs `sqlalchemy.select` for the inner subquery — but this is the concrete shape to implement, not a placeholder to redesign.)

**2. Result assembly (batch-fetch, not per-row join).** After `results = session.exec(statement).all()` produces the filtered `(Task, creator_name, assignee_name, category_name, category_color)` tuples, collect the task ids, then run one follow-up query: `select(TaskVisibleToLink.task_id, UserType).join(UserType, TaskVisibleToLink.user_type_id == UserType.id).where(TaskVisibleToLink.task_id.in_(task_ids))`. Group the resulting `UserType` rows by `task_id` in Python (e.g. a `dict[UUID, list[UserType]]`), then for each task in the main loop set `task_data["visible_to"] = [UserTypeRead.model_validate(ut) for ut in grouped.get(db_task.id, [])]` instead of the old `task_data["visible_to_name"] = visible_to_name` assignment. Tasks with no targets simply get `visible_to = []`.

### `backend/app/services/task_service.py`

- `create_task`: when a Manager doesn't specify `visible_to_ids` (empty/absent), default it to `{ut.id for ut in current_user.user_types}` (explicit ids only — **not** `get_effective_user_type_ids(current_user, session)`); if that set is empty (the Manager has zero explicit UserTypes), fall back to the role-type id alone, i.e. `get_effective_user_type_ids(current_user, session)` in that case reduces to exactly the role-type id since there are no explicit ids to combine with. See the Scope Decisions table above for the rationale.
- `update_task`: when a Manager sets `visible_to_ids`, validate every id in the list is a member of `get_effective_user_type_ids(current_user, session)`; reject (existing `ForbiddenError` or equivalent) if any id falls outside that set.
- **Call site updated — `get_task_with_names`** (~lines 160-172): currently does `session.get(UserType, db_task.visible_to_id)` and sets `task_data["visible_to_name"] = visible_to.name if visible_to else None`. This is used by both `create_task` and `update_task` in `tasks.py` to build their `TaskRead` responses, so it must change alongside them. Replace the `session.get(UserType, ...)` lookup with `db_task.visible_to` (the new `Relationship`) and set `task_data["visible_to"] = [UserTypeRead.model_validate(ut) for ut in db_task.visible_to]`. Since this reads the relationship off `db_task` directly (not a separate query), the caller must ensure `db_task.visible_to` is loaded/refreshed after `create_task`/`update_task` commits the link rows — use `session.refresh(db_task, attribute_names=["visible_to"])` (or equivalent) before calling `get_task_with_names` if it isn't already fresh.

## Frontend Changes

### `frontend/src/features/task-management/types/index.ts` (or wherever `Task`/`TaskCreate`/`TaskUpdate` types live)

`visible_to_id?: string` → `visible_to_ids: string[]` (create/update), `visible_to: UserType[]` (read).

### `TaskForm.tsx`

The current single `<Select>` for `visible_to_id` is replaced with the existing `UserTypeMultiSelect` component (already built for the admin-role-simulation feature, `frontend/src/features/user-administration/components/UserTypeMultiSelect.tsx`) bound to `visible_to_ids`.

### `simulatedPermissions.ts` (`canSeeSimulatedTask`)

Currently compares `task.visible_to_id` against a single value/list of simulated `userTypeIds`. Update to check `task.visible_to` (now an array of `UserTypeRead`) — visible if the array is empty or intersects the simulated effective type ids (mirroring the backend's `assert_manager_can_see_task` logic exactly, including APRAS-9's role-type fold-in, which by the time this task is implemented should already be present in `useEffectiveIdentity()`'s output per that spec).

### Any other consumer of `visible_to_id`

The complete current list of frontend files referencing `visible_to_id` is: `frontend/src/features/task-management/types/index.ts`, `TaskForm.tsx`, and `simulatedPermissions.ts` (all three already named above). `TaskCard.tsx`, `TaskDetailsView.tsx`, and `AuditTimeline.tsx` were checked and contain zero references to `visible_to_id` — no changes needed in those three files.

## Documentation

`AGENTS.md` is already stale relative to the *current* code, independent of this task: its `Target Users` table (line ~15: "Sees only tasks explicitly marked as `manager_visible`") and its `### Task` domain-concept bullet (line ~285: "**Manager Visibility** (`manager_visible`): Controls whether users with the Manager role can see this task. Only Administrators and Directors can toggle this flag.") and the RBAC table (lines ~311-313, the `manager_visible`-toggle cells for `ADMINISTRATOR`/`DIRECTOR`/`MANAGER`) all still describe a `manager_visible` **boolean flag** — a field removed and replaced by the single-FK `visible_to_id` back in `3f75bcd3d49f_many_to_many_user_types_and_task_.py`. There is no accurate "single target" baseline to update from.

This task must therefore **write these rows fresh** to describe the new `visible_to` list, not "update" them incrementally:
- The `Gerente (Manager)` row in the `Target Users` table: describe visibility as "sees tasks with no visibility targets, or at least one target matching one of the Manager's effective UserTypes" (not `manager_visible`).
- The `### Task` bullet: replace the `manager_visible` sentence with one describing `visible_to: list[UserType]` — zero or more UserType targets, empty meaning visible to every Manager, settable by Administrator/Director/self-scoped Manager per existing role rules.
- The RBAC table's `ADMINISTRATOR`/`DIRECTOR`/`MANAGER` cells: replace "toggle `manager_visible`" / "cannot toggle visibility" phrasing with "set/edit `visible_to` targets" phrasing, consistent with the rest of this task's semantics.
- The `### UserType` section's closing sentence ("...it does not affect fine-grained rules like `Task.visible_to_id` filtering...") must also be corrected to reference `Task.visible_to` (list), since `visible_to_id` no longer exists after this task.

## Non-Goals

- Not changing who can set task visibility (still Administrator/Director/self-scoped Manager, per existing rules) — only the cardinality of targets.
- Not adding a "visible to nobody" sentinel distinct from "visible to everyone" — the only two states remain "empty (everyone)" and "one or more specific targets."

## Testing

- **Backend**: `assert_manager_can_see_task` with zero, one, and multiple targets, including a Manager whose effective ids overlap with only one of several targets (should see it) and a Manager with no overlap at all (should not). `list_tasks` filter test with multiple targets. `create_task` auto-default assigns the Manager's explicit UserType ids when they have at least one, and falls back to the role-type id alone when they have zero explicit UserTypes (assert it does *not* pull in the shared role-type id when explicit ids exist). `update_task` rejects a Manager setting a target outside their effective set, accepts one within it. Migration test: an existing task's single `visible_to_id` correctly becomes a one-row `task_visible_to_link` entry after upgrade.
- **Frontend**: `TaskForm` multi-select round-trips correctly (submits `visible_to_ids`, pre-fills from `visible_to` on edit). `simulatedPermissions.ts` tests for zero/one/multiple targets under simulation.

## Expected Results

1. A task can be created/edited with zero or more UserType visibility targets.
2. A task with no targets remains visible to every Manager (unchanged from today's `null` behavior).
3. A task with multiple targets is visible to a Manager whose effective UserType ids overlap with at least one target.
4. Existing tasks' single `visible_to_id` values are preserved as one-row targets after migration.
5. `TaskForm`'s visibility field is a multi-select, not a single dropdown.
