import { useMemo } from "react";
import type { TaskRead, TaskStatus, TaskPriority } from "../types";
import type { UserRole } from "../../../types/auth";
import { canSeeSimulatedTask } from "../utils/simulatedPermissions";

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
  role?: UserRole;
  userTypeIds: string[];
}

/**
 * Hook to filter a list of tasks based on status, priority, assigned user,
 * and — while an Administrator is simulating another role — the
 * simulated role/UserType's task visibility rules.
 *
 * @param tasks - The list of tasks to filter.
 * @param filters - The filter criteria.
 * @param simulation - Optional simulated identity used to additionally
 *   filter out tasks the simulated role/UserType would not see.
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
      if (simulation?.isSimulating && simulation.role) {
        if (!canSeeSimulatedTask(task, simulation.role, simulation.userTypeIds)) {
          return false;
        }
      }
      return true;
    });
  }, [tasks, filters, simulation]);
};
