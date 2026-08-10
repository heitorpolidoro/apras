import { renderHook } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useTaskFiltering } from "../useTaskFiltering";
import { TaskStatus, TaskPriority } from "../../types";
import type { TaskRead } from "../../types";

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
