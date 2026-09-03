import { useMemo } from "react";
import type { TaskRead, TaskStatus, TaskPriority } from "../types";
import { canSeeSimulatedTask, type Has } from "../utils/simulatedPermissions";

export interface TaskFilters {
  status?: TaskStatus | null;
  priority?: TaskPriority | null;
  assigned_to_id?: string | null;
}

/**
 * Effective identity to apply the admin role simulation's visibility rules.
 * Omit (or pass `isSimulating: false`) to skip simulated filtering entirely.
 */
export interface SimulationFilterOptions {
  isSimulating: boolean;
  /** The simulated permission predicate (IAM F5, APRAS-49 §10.3). */
  has: Has;
  roleIds: string[];
}

/**
 * Hook to filter a list of tasks based on status, priority, assigned user,
 * and — while an administrator is simulating another role — the
 * simulated roles' task visibility rules.
 *
 * @param tasks - The list of tasks to filter.
 * @param filters - The filter criteria.
 * @param simulation - Optional simulated identity used to additionally
 *   filter out tasks the simulated role/Role would not see.
 * @returns The filtered list of tasks.
 */
export const useTaskFiltering = (
  tasks: TaskRead[],
  filters: TaskFilters,
  simulation?: SimulationFilterOptions,
) => {
  return useMemo(() => {
    return tasks.filter((task) => {
      if (filters.status && task.status !== filters.status) return false;
      if (filters.priority && task.priority !== filters.priority) return false;
      if (
        filters.assigned_to_id &&
        task.assigned_to_id !== filters.assigned_to_id
      )
        return false;
      if (simulation?.isSimulating) {
        if (!canSeeSimulatedTask(task, simulation.has, simulation.roleIds)) {
          return false;
        }
      }
      return true;
    });
  }, [tasks, filters, simulation]);
};
