import { renderHook } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useTaskFiltering } from "../useTaskFiltering";
import { TaskStatus, TaskPriority } from "../../types";
import type { TaskRead } from "../../types";
import { UserRole } from "../../../../types/auth";

const mockTasks: TaskRead[] = [
  {
    id: "1",
    title: "Task 1",
    status: TaskStatus.PENDING,
    priority: TaskPriority.LOW,
    assigned_to_id: "user-1",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    created_by_id: "admin",
    category_id: "cat-1",
    visible_to_id: null,
  },
  {
    id: "2",
    title: "Task 2",
    status: TaskStatus.IN_PROGRESS,
    priority: TaskPriority.MEDIUM,
    assigned_to_id: "user-2",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    created_by_id: "admin",
    category_id: "cat-1",
    visible_to_id: null,
  },
  {
    id: "3",
    title: "Task 3",
    status: TaskStatus.COMPLETED,
    priority: TaskPriority.HIGH,
    assigned_to_id: "user-1",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    created_by_id: "admin",
    category_id: "cat-1",
    visible_to_id: null,
  },
];

describe("useTaskFiltering", () => {
  it("returns all tasks when no filters are applied", () => {
    const { result } = renderHook(() => useTaskFiltering(mockTasks, {}));
    expect(result.current).toHaveLength(3);
    expect(result.current).toEqual(mockTasks);
  });

  it("filters tasks by status", () => {
    const { result } = renderHook(() =>
      useTaskFiltering(mockTasks, { status: TaskStatus.PENDING }),
    );
    expect(result.current).toHaveLength(1);
    expect(result.current[0].id).toBe("1");
  });

  it("filters tasks by priority", () => {
    const { result } = renderHook(() =>
      useTaskFiltering(mockTasks, { priority: TaskPriority.MEDIUM }),
    );
    expect(result.current).toHaveLength(1);
    expect(result.current[0].id).toBe("2");
  });

  it("filters tasks by assigned_to_id", () => {
    const { result } = renderHook(() =>
      useTaskFiltering(mockTasks, { assigned_to_id: "user-1" }),
    );
    expect(result.current).toHaveLength(2);
    expect(result.current.map((t) => t.id)).toEqual(["1", "3"]);
  });

  it("filters tasks by multiple criteria", () => {
    const { result } = renderHook(() =>
      useTaskFiltering(mockTasks, {
        status: TaskStatus.COMPLETED,
        assigned_to_id: "user-1",
      }),
    );
    expect(result.current).toHaveLength(1);
    expect(result.current[0].id).toBe("3");
  });

  it("returns empty array when no tasks match filters", () => {
    const { result } = renderHook(() =>
      useTaskFiltering(mockTasks, { status: TaskStatus.CANCELED }),
    );
    expect(result.current).toHaveLength(0);
  });

  describe("admin role simulation filtering", () => {
    const simulationTasks: TaskRead[] = [
      { ...mockTasks[0], id: "pub", visible_to_id: null },
      { ...mockTasks[1], id: "typed", visible_to_id: "type-1" },
      { ...mockTasks[2], id: "other-typed", visible_to_id: "type-2" },
    ];

    it("is a no-op when no simulation option is passed", () => {
      const { result } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}),
      );
      expect(result.current).toHaveLength(3);
    });

    it("is a no-op when isSimulating is false", () => {
      const { result } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: false,
          role: UserRole.MANAGER,
          userTypeIds: [],
        }),
      );
      expect(result.current).toHaveLength(3);
    });

    it("hides every task when simulating GUEST", () => {
      const { result } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: true,
          role: UserRole.GUEST,
          userTypeIds: [],
        }),
      );
      expect(result.current).toHaveLength(0);
    });

    it("shows only public and matching-UserType tasks when simulating MANAGER", () => {
      const { result } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: true,
          role: UserRole.MANAGER,
          userTypeIds: ["type-1"],
        }),
      );
      expect(result.current.map((t) => t.id)).toEqual(["pub", "typed"]);
    });

    it("shows every task when simulating DIRECTOR or ADMINISTRATOR", () => {
      const { result: directorResult } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: true,
          role: UserRole.DIRECTOR,
          userTypeIds: [],
        }),
      );
      expect(directorResult.current).toHaveLength(3);

      const { result: adminResult } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: true,
          role: UserRole.ADMINISTRATOR,
          userTypeIds: [],
        }),
      );
      expect(adminResult.current).toHaveLength(3);
    });

    it("combines simulated visibility filtering with the explicit status/priority/assignee filters", () => {
      const { result } = renderHook(() =>
        useTaskFiltering(
          simulationTasks,
          { status: TaskStatus.PENDING },
          { isSimulating: true, role: UserRole.MANAGER, userTypeIds: [] },
        ),
      );
      // Only "pub" (visible_to_id null) is visible to this manager, and it
      // must also match the PENDING status filter.
      expect(result.current.map((t) => t.id)).toEqual(["pub"]);
    });
  });

  it("memoizes the result", () => {
    const filters = {};
    const { result, rerender } = renderHook(
      ({ tasks, filters }) => useTaskFiltering(tasks, filters),
      {
        initialProps: { tasks: mockTasks, filters },
      },
    );

    const firstResult = result.current;
    rerender({ tasks: mockTasks, filters });
    expect(result.current).toBe(firstResult); // Referential equality check
  });
});
