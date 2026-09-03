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
    visible_to: [],
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
    visible_to: [],
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
    visible_to: [],
  },
];

const role = (id: string) => ({ id, name: id });

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
    /**
     * The permission predicate each retired role value carried, for the two
     * strings `canSeeSimulatedTask` reads (IAM F5, APRAS-49 §10.2). Every
     * case below asserts the **same** outcome it asserted when the option
     * was an enum value, so the rewrite is a re-expression rather than a new
     * set of claims.
     */
    const has = (profile: string) => (permission: string) =>
      ({
        ADMINISTRATOR: ["tasks:read", "tasks:read_all"],
        DIRECTOR: ["tasks:read", "tasks:read_all"],
        MANAGER: ["tasks:read"],
        GUEST: [] as string[],
      })[profile]!.includes(permission);

    const simulationTasks: TaskRead[] = [
      { ...mockTasks[0], id: "pub", visible_to: [] },
      { ...mockTasks[1], id: "typed", visible_to: [role("type-1")] },
      { ...mockTasks[2], id: "other-typed", visible_to: [role("type-2")] },
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
          has: has("GUEST"),
          roleIds: [],
        }),
      );
      expect(result.current).toHaveLength(3);
    });

    it("hides every task when simulating GUEST", () => {
      const { result } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: true,
          has: has("GUEST"),
          roleIds: [],
        }),
      );
      expect(result.current).toHaveLength(0);
    });

    it("shows only public and matching-Role tasks when simulating MANAGER", () => {
      const { result } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: true,
          has: has("MANAGER"),
          roleIds: ["type-1"],
        }),
      );
      expect(result.current.map((t) => t.id)).toEqual(["pub", "typed"]);
    });

    it("resolves visibility through an ordinary role id in roleIds", () => {
      // The APRAS-9 distinction this case policed — "explicit" versus
      // "role-implicit" ids — is gone: migration `0033` turned the implicit
      // membership into a real `user_role_link` row, so every id reaching
      // this hook is an ordinary membership and the hook still needs no
      // change.
      const roleTypeTasks: TaskRead[] = [
        { ...mockTasks[0], id: "pub", visible_to: [] },
        {
          ...mockTasks[1],
          id: "via-role-type",
          visible_to: [role("role-type-manager")],
        },
        { ...mockTasks[2], id: "other-typed", visible_to: [role("type-2")] },
      ];
      const { result } = renderHook(() =>
        useTaskFiltering(roleTypeTasks, {}, {
          isSimulating: true,
          has: has("MANAGER"),
          roleIds: ["role-type-manager"],
        }),
      );
      expect(result.current.map((t) => t.id)).toEqual(["pub", "via-role-type"]);
    });

    it("shows every task when simulating DIRECTOR or ADMINISTRATOR", () => {
      const { result: directorResult } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: true,
          has: has("DIRECTOR"),
          roleIds: [],
        }),
      );
      expect(directorResult.current).toHaveLength(3);

      const { result: adminResult } = renderHook(() =>
        useTaskFiltering(simulationTasks, {}, {
          isSimulating: true,
          has: has("ADMINISTRATOR"),
          roleIds: [],
        }),
      );
      expect(adminResult.current).toHaveLength(3);
    });

    it("combines simulated visibility filtering with the explicit status/priority/assignee filters", () => {
      const { result } = renderHook(() =>
        useTaskFiltering(
          simulationTasks,
          { status: TaskStatus.PENDING },
          { isSimulating: true, has: has("MANAGER"), roleIds: [] },
        ),
      );
      // Only "pub" (empty visible_to) is visible to this manager, and it
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
