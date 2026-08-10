# Admin Role Simulation — Design Spec

**Meridian task:** `admin-role-simulation`
**Date:** 2026-08-10
**Status:** Approved for planning

## Problem

Administrators need a way to validate that role/UserType-based permissions (RBAC + dynamic task visibility) behave correctly in the frontend UI, without creating throwaway test users or logging in/out repeatedly. There is no way today to preview what a Director, Manager (with specific UserTypes), or Guest would see.

## Goal

Let a real Administrator switch the frontend into a "view as" mode: pick a role and a set of UserTypes, and see the UI (controls) and data (task list) exactly as that role/UserType combination would experience them — read-only, with zero risk of mutating real data.

## Non-Goals

- No backend changes of any kind. This is a purely client-side presentation feature.
- Not true impersonation — no token swap, no backend request executes as another identity.
- No audit trail / logging of simulation sessions.
- Not tied to a specific real user — the admin picks an arbitrary role + UserType combination, which may not match any existing user.

## Scope Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Backend or frontend-only simulation? | Frontend-only "view-as". All API calls that read data still run with the real admin's full privileges. |
| Does simulation affect task data, not just UI controls? | Yes — the task list is filtered client-side to match what the simulated role/UserType would see. |
| How is the target selected? | Free combination: any of Director/Manager/Guest role, plus any set of UserTypes (not tied to a real user). |
| What happens if a mutating action is triggered while simulating (e.g. a UI bug leaves a button visible)? | Blocked unconditionally on the client — no mutating request is ever sent while simulation is active, because there is no real user identity behind the simulated role. |
| Do protected routes (e.g. `/admin/users`) honor the simulated role? | No — route access always uses the real admin's role, so the admin can never get locked out of ending the simulation. |
| UserType select: single or multi, and does it disable for non-Manager roles? | Always multi-select, always enabled for every role (Guest can have UserTypes too, even though they don't currently affect Guest visibility). |
| Initial state when opening the simulation panel? | Both selects start empty. Simulation only becomes "active" once a role is chosen. |
| Persistent visual indicator while simulating? | Yes — a fixed banner on every page, in addition to the controls in the Navbar. |
| How to handle "self-assigned" tasks for a simulated Manager (no concrete user to be "self")? | Only unassigned tasks are treated as editable. Tasks assigned to anyone are treated as non-editable in simulation. |

## Architecture

### 1. `SimulationContext`

New React context, modeled after the existing `AuthContext` (`frontend/src/features/user-administration/context/AuthContext.tsx`), added in `frontend/src/features/user-administration/context/SimulationContext.tsx`:

```ts
interface SimulationState {
  simulatedRole: UserRole | null;       // null = not simulating
  simulatedUserTypeIds: string[];
}
```

- `isSimulating = simulatedRole !== null`.
- Exposes `setSimulatedRole`, `setSimulatedUserTypeIds`, `stopSimulation()`.
- Persists to `sessionStorage` (keys `simulation.role`, `simulation.userTypeIds`) so a page refresh doesn't lose an in-progress test. Cleared on `stopSimulation()` and on logout (hook into `AuthContext.logout`).
- Mounted in `App.tsx`, nested inside `AuthProvider`, only meaningfully used when the real user is an Administrator (the UI entry point is Administrator-only, so a non-admin can never populate it).

### 2. Module-level simulation state mirror

The Axios client (`frontend/src/api/client.ts`) is not a React component and can't consume context directly. `SimulationContext` writes every state change into a tiny singleton module, `frontend/src/features/user-administration/context/simulationState.ts`:

```ts
let current: { isSimulating: boolean } = { isSimulating: false };
export const setSimulationState = (s: { isSimulating: boolean }) => { current = s; };
export const getSimulationState = () => current;
```

This mirrors the existing pattern of reading `accessToken` from storage inside the Axios interceptor — no new architectural concept, just applied to simulation flag instead of a token.

### 3. Mutation guard (Axios interceptor)

In `api/client.ts`, a request interceptor checks `getSimulationState().isSimulating` for any request whose method is `post`, `put`, `patch`, or `delete`, and rejects it before it leaves the browser:

```ts
return Promise.reject({
  response: { data: { detail: t("simulation.mutationBlocked") } },
});
```

This shape matches exactly what `parseApiError` (`frontend/src/api/errors.ts`) already expects, so every existing form/mutation error-display path (e.g. `TaskForm`'s `serverError`) surfaces this message with zero new UI code. GET requests are never blocked — they're required to fetch the real data that gets client-filtered for the simulated view.

### 4. `useEffectiveIdentity()` hook

New hook in `frontend/src/features/user-administration/context/useEffectiveIdentity.ts`:

```ts
function useEffectiveIdentity(): {
  role: UserRole | undefined;
  userTypeIds: string[];
  isSimulating: boolean;
}
```

Returns the simulated role/UserTypes when `isSimulating`, otherwise the real `user.role` / `user.user_types` from `AuthContext`. Existing call sites that read `user?.role` for permission decisions switch to this hook:

- `frontend/src/features/user-administration/components/Navbar.tsx` — admin nav link visibility (line 57).
- `frontend/src/features/task-management/components/CategoriesPage.tsx` — `canWrite` (line 70).
- `frontend/src/features/task-management/components/TaskForm.tsx` — manager field hiding (line 287), and gating of the create/edit submit action.

`ProtectedRoute.tsx` and `AdminUserDashboard.tsx` are **not** touched — the former must keep using the real role (route guards always reflect real access, per the scope decision), and the latter's `user.role` references are about the *listed* users in the admin table, unrelated to the current actor.

### 5. Task visibility & edit simulation

New pure functions in `frontend/src/features/task-management/utils/simulatedPermissions.ts`, deliberately mirroring the backend rules in `backend/app/api/deps.py`:

```ts
function canSeeSimulatedTask(task: TaskRead, role: UserRole, userTypeIds: string[]): boolean
function canEditSimulatedTask(task: TaskRead, role: UserRole, userTypeIds: string[]): boolean
```

- `canSeeSimulatedTask` mirrors `assert_manager_can_see_task`: Guest → always false. Manager → true if `task.visible_to_id` is `null` or is in `userTypeIds`. Administrator/Director → always true.
- `canEditSimulatedTask` mirrors `assert_can_edit_task`, adapted for the "no concrete self" constraint: Guest → false. Manager → true only if `task.assigned_to_id` is `null` (assigned tasks are never editable in simulation, per the scope decision — no self-assignment concept exists). Administrator/Director → always true.

`useTaskFiltering` (`frontend/src/features/task-management/hooks/useTaskFiltering.ts`) is the single point both rendering views (`TaskList.tsx` and `TaskBoard.tsx`) funnel through after `TaskDashboard` fetches tasks via `useTasks`. It gains an additional filter step applying `canSeeSimulatedTask` when `isSimulating` is true, using the full unfiltered list the real admin already receives from `GET /tasks/`. Per-task edit affordances (edit button, rendered by `TaskList`/`TaskBoard`/`TaskCard`) use `canEditSimulatedTask` the same way.

### 6. UI Components

**`SimulationControls`** (`frontend/src/features/user-administration/components/SimulationControls.tsx`) — rendered in `Navbar.tsx`, visible only when the *real* user is Administrator (independent of simulated role, so the control is never hidden by its own simulation). A button "Simular" toggles an inline panel containing:
- A `Select` for role (options: Diretor, Gerente, Convidado — Administrator omitted, simulating yourself is meaningless).
- A new lightweight `UserTypeMultiSelect` component (checkbox list in a dropdown, built on existing `Button`/`Badge` primitives — no multi-select primitive exists yet in `components/ui`), always enabled, sourced from the existing `useUserTypes()` hook.
- An "Encerrar simulação" button, shown once `isSimulating` is true.

Both selects start empty; picking a role activates the simulation immediately. Changing either select afterward updates all consuming views live (they all derive from `SimulationContext` via `useEffectiveIdentity`).

**`SimulationBanner`** (`frontend/src/features/user-administration/components/SimulationBanner.tsx`) — mounted once near the top of the layout in `App.tsx` (below `Navbar`), rendered only when `isSimulating`. Shows "Visualizando como: {role label} ({UserType names, or 'nenhum tipo' if empty})" and a secondary "Encerrar" action, so simulation is unmistakable from any page.

## Data Flow Summary

```
Admin picks role+UserTypes in SimulationControls
        │
        ▼
SimulationContext updates (+ sessionStorage, + simulationState singleton)
        │
        ├─▶ SimulationBanner renders "Visualizando como…"
        │
        ├─▶ useEffectiveIdentity() re-derives {role, userTypeIds} everywhere it's used
        │       ├─▶ Navbar admin-link visibility
        │       ├─▶ CategoriesPage canWrite
        │       └─▶ TaskForm field visibility / submit gating
        │
        ├─▶ Task list pipeline applies canSeeSimulatedTask / canEditSimulatedTask
        │       over the admin's already-fetched full task list
        │
        └─▶ Axios interceptor blocks any POST/PUT/PATCH/DELETE while isSimulating
```

## Error Handling

- Blocked mutations reject through the same `response.data.detail` shape the app already parses everywhere (`parseApiError`), so no new error UI is introduced — a translated message ("Ação bloqueada: você está em modo de simulação") appears exactly where a real 403 would.
- If `sessionStorage` contains a `simulatedRole` value that no longer maps to a valid `UserRole` (e.g. stale data from a future app version), `SimulationContext` treats it as `null` (not simulating) rather than throwing.

## Testing

- **Unit** (Vitest): `canSeeSimulatedTask` / `canEditSimulatedTask` against the same scenarios covered by the backend's `test_tasks_rbac.py`, so both layers stay behaviorally aligned.
- **Component**: `SimulationControls` (role/UserType selection updates context), `SimulationBanner` (renders only when simulating, correct label), Axios interceptor (mutating call rejected with expected shape while simulating; GET calls unaffected).
- **Integration**: `TaskDashboard` (or wherever the list renders) shows the correct filtered subset for a Manager+UserType combination, an empty list for Guest, and the full list for Director.
- No backend test changes — no backend code changes.

## Files Touched (expected)

**New:**
- `frontend/src/features/user-administration/context/SimulationContext.tsx`
- `frontend/src/features/user-administration/context/simulationState.ts`
- `frontend/src/features/user-administration/context/useEffectiveIdentity.ts`
- `frontend/src/features/user-administration/components/SimulationControls.tsx`
- `frontend/src/features/user-administration/components/SimulationBanner.tsx`
- `frontend/src/features/user-administration/components/UserTypeMultiSelect.tsx`
- `frontend/src/features/task-management/utils/simulatedPermissions.ts`

**Modified:**
- `frontend/src/App.tsx` (mount `SimulationProvider`, render `SimulationBanner`)
- `frontend/src/api/client.ts` (mutation-blocking interceptor)
- `frontend/src/features/user-administration/components/Navbar.tsx` (mount `SimulationControls`, use `useEffectiveIdentity` for admin link)
- `frontend/src/features/user-administration/context/AuthContext.tsx` (clear simulation state on logout)
- `frontend/src/features/task-management/components/CategoriesPage.tsx` (use `useEffectiveIdentity`)
- `frontend/src/features/task-management/components/TaskForm.tsx` (use `useEffectiveIdentity`)
- `frontend/src/features/task-management/hooks/useTaskFiltering.ts` (apply simulated visibility filtering)
- `frontend/src/features/task-management/components/TaskList.tsx`, `TaskBoard.tsx` (apply simulated edit-affordance gating)
- `frontend/src/i18n/locales/en.json`, `pt.json` (new strings: banner label, mutation-blocked message, control labels)

No backend files are touched.
