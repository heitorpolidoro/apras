import type { TaskRead } from "../types";

/** The subset of `PermissionSet` these two predicates need. */
export type Has = (permission: string) => boolean;

/**
 * Mirrors the backend's `assert_manager_can_see_task`
 * (`backend/app/api/deps.py`) for the frontend "view-as" simulation.
 *
 * IAM F5 (APRAS-49 §10.2) re-expressed it on the two permissions that
 * replaced the enum tiers, so it is now a literal mirror of the backend
 * function rather than a second encoding of the same tiers:
 *
 * - no `tasks:read`  -> sees nothing (was: GUEST);
 * - no `tasks:read_all` -> scoped by `visible_to` (was: MANAGER);
 * - otherwise, every task.
 */
export function canSeeSimulatedTask(
  task: TaskRead,
  has: Has,
  roleIds: string[],
): boolean {
  if (!has("tasks:read")) return false;
  if (!has("tasks:read_all")) {
    if (!task.visible_to || task.visible_to.length === 0) return true;
    return task.visible_to.some((role) => roleIds.includes(role.id));
  }
  return true;
}

/**
 * Mirrors the backend's `assert_can_edit_task` (`backend/app/api/deps.py`)
 * for the frontend "view-as" simulation, adapted for the fact that a role
 * simulation has no concrete "self" to compare against.
 *
 * - no `tasks:update` -> can never edit (was: GUEST);
 * - no `tasks:update_any` -> can only edit unassigned tasks, since there is
 *   no simulated identity that could be the assignee (self-assigned
 *   editability is intentionally not simulated) (was: MANAGER);
 * - otherwise, every task.
 */
export function canEditSimulatedTask(
  task: TaskRead,
  has: Has,
  roleIds: string[],
): boolean {
  // Kept in the signature for symmetry with canSeeSimulatedTask; unused
  // because editability in simulation depends only on assignment.
  void roleIds;
  if (!has("tasks:update")) return false;
  if (!has("tasks:update_any")) {
    return task.assigned_to_id == null;
  }
  return true;
}
