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
| Manager's auto-default on task creation | When a Manager creates a task without specifying targets, default to their **full** effective UserType id set (not just the first one, which is today's behavior) — preserves the original intent (the task defaults to visible to the creator and their peers) while correctly generalizing to multiple targets. |
| Manager's validation on setting targets | A Manager may only set targets that are a subset of their own effective UserType ids (cannot grant visibility to a type they don't belong to) — same restriction as today's single-value check, generalized to a list. |

## Data Model

### New join table: `backend/app/models/task.py` (or a new small file if it grows the model file too much — developer's call, follow existing file-size conventions in this codebase)

```python
class TaskVisibleToLink(SQLModel, table=True):
    __tablename__ = "task_visible_to_link"
    __table_args__ = (
        UniqueConstraint("task_id", "user_type_id", name="uq_task_visible_to_link"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="task.id", ondelete="CASCADE", nullable=False, index=True)
    user_type_id: UUID = Field(foreign_key="user_type.id", ondelete="CASCADE", nullable=False, index=True)
```

Mirrors the existing `UserUserTypeLink` pattern exactly.

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

### `backend/app/api/v1/endpoints/tasks.py` — `list_tasks`'s SQL filter

The current `or_(Task.visible_to_id.is_(None), Task.visible_to_id.in_(user_type_ids))` becomes a query that includes tasks with **no** rows in `task_visible_to_link` OR **at least one** row whose `user_type_id` is in the Manager's effective ids — implement via an `EXISTS`/outer-join pattern appropriate for SQLModel/SQLAlchemy (the developer should follow this codebase's existing style for comparable list-filtering queries, e.g. how other many-to-many visibility/membership filters are written here, rather than inventing a new idiom).

### `backend/app/services/task_service.py`

- `create_task`: when a Manager doesn't specify `visible_to_ids` (empty/absent), default it to the **full** `get_effective_user_type_ids(current_user, session)` set (not just one id, per the Scope Decision above).
- `update_task`: when a Manager sets `visible_to_ids`, validate every id in the list is a member of `get_effective_user_type_ids(current_user, session)`; reject (existing `ForbiddenError` or equivalent) if any id falls outside that set.

## Frontend Changes

### `frontend/src/features/task-management/types/index.ts` (or wherever `Task`/`TaskCreate`/`TaskUpdate` types live)

`visible_to_id?: string` → `visible_to_ids: string[]` (create/update), `visible_to: UserType[]` (read).

### `TaskForm.tsx`

The current single `<Select>` for `visible_to_id` is replaced with the existing `UserTypeMultiSelect` component (already built for the admin-role-simulation feature, `frontend/src/features/user-administration/components/UserTypeMultiSelect.tsx`) bound to `visible_to_ids`.

### `simulatedPermissions.ts` (`canSeeSimulatedTask`)

Currently compares `task.visible_to_id` against a single value/list of simulated `userTypeIds`. Update to check `task.visible_to` (now an array of `UserTypeRead`) — visible if the array is empty or intersects the simulated effective type ids (mirroring the backend's `assert_manager_can_see_task` logic exactly, including APRAS-9's role-type fold-in, which by the time this task is implemented should already be present in `useEffectiveIdentity()`'s output per that spec).

### Any other consumer of `visible_to_id`

Grep the frontend for `visible_to_id` (e.g. `TaskCard.tsx`, `TaskDetailsView.tsx`, `AuditTimeline.tsx` if it renders visibility-change history) and update each to the new array shape — enumerate the actual list at implementation time via grep, since this spec cannot exhaustively name every display site without re-deriving it from the code as it exists at that point.

## Documentation

`AGENTS.md`'s `Task` domain-concept description ("Manager Visibility... Only Administrators and Directors can toggle this flag" / any mention of `visible_to_id` as a single target) needs updating to describe multiple targets.

## Non-Goals

- Not changing who can set task visibility (still Administrator/Director/self-scoped Manager, per existing rules) — only the cardinality of targets.
- Not adding a "visible to nobody" sentinel distinct from "visible to everyone" — the only two states remain "empty (everyone)" and "one or more specific targets."

## Testing

- **Backend**: `assert_manager_can_see_task` with zero, one, and multiple targets, including a Manager whose effective ids overlap with only one of several targets (should see it) and a Manager with no overlap at all (should not). `list_tasks` filter test with multiple targets. `create_task` auto-default assigns the Manager's full effective set. `update_task` rejects a Manager setting a target outside their effective set, accepts one within it. Migration test: an existing task's single `visible_to_id` correctly becomes a one-row `task_visible_to_link` entry after upgrade.
- **Frontend**: `TaskForm` multi-select round-trips correctly (submits `visible_to_ids`, pre-fills from `visible_to` on edit). `simulatedPermissions.ts` tests for zero/one/multiple targets under simulation.

## Expected Results

1. A task can be created/edited with zero or more UserType visibility targets.
2. A task with no targets remains visible to every Manager (unchanged from today's `null` behavior).
3. A task with multiple targets is visible to a Manager whose effective UserType ids overlap with at least one target.
4. Existing tasks' single `visible_to_id` values are preserved as one-row targets after migration.
5. `TaskForm`'s visibility field is a multi-select, not a single dropdown.
