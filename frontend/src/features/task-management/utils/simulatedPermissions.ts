import { UserRole, type UserRole as UserRoleType } from "../../../types/auth";
import type { TaskRead } from "../types";

/**
 * Mirrors the backend's `assert_manager_can_see_task`
 * (`backend/app/api/deps.py`) for the frontend "view-as" simulation.
 *
 * - GUEST never sees any task.
 * - MANAGER sees a task if it is public (`visible_to_id` is `null`) or
 *   targeted to one of the given UserType ids.
 * - ADMINISTRATOR and DIRECTOR see every task.
 */
export function canSeeSimulatedTask(
  task: TaskRead,
  role: UserRoleType,
  userTypeIds: string[],
): boolean {
  if (role === UserRole.GUEST) return false;
  if (role === UserRole.MANAGER) {
    if (task.visible_to_id == null) return true;
    return userTypeIds.includes(task.visible_to_id);
  }
  return true;
}

/**
 * Mirrors the backend's `assert_can_edit_task` (`backend/app/api/deps.py`)
 * for the frontend "view-as" simulation, adapted for the fact that a
 * role+UserType simulation has no concrete "self" to compare against.
 *
 * - GUEST can never edit.
 * - MANAGER can only edit unassigned tasks — tasks assigned to anyone are
 *   treated as non-editable in simulation, since there is no simulated user
 *   identity that could be the assignee (self-assigned editability is
 *   intentionally not simulated; see the design spec's Scope Decisions).
 * - ADMINISTRATOR and DIRECTOR can edit every task.
 */
export function canEditSimulatedTask(
  task: TaskRead,
  role: UserRoleType,
  userTypeIds: string[],
): boolean {
  // Kept in the signature for symmetry with canSeeSimulatedTask and to
  // mirror the backend function's shape; unused because manager
  // editability in simulation depends only on assignment, not UserType.
  void userTypeIds;
  if (role === UserRole.GUEST) return false;
  if (role === UserRole.MANAGER) {
    return task.assigned_to_id == null;
  }
  return true;
}
