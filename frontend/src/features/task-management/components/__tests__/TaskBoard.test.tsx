import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import TaskBoard from "../TaskBoard";
import { TaskStatus, TaskPriority } from "../../types";
import { useSimulation } from "../../../user-administration/context/SimulationContext";
import { useRoles } from "../../../../hooks/useRoles";
import { PERMISSIONS_BY_ROLE } from "../../../../test/permissionFixtures";
import { useAuth } from "../../../user-administration/context/AuthContext";

/** The profile a *simulation* stands for; set per case where it varies. */
let mockSimulatedProfile = "MANAGER";

/** The profile each case's fixture stands for. */
const mockProfile = () => useAuth().user?.is_superuser ? "ADMINISTRATOR" : "MANAGER";

// IAM F5 (APRAS-49 §10.2): the component reads its *permissions* now, not a
// role. Mocking the access module keeps each case's signal exactly where it
// was — the `useAuth()` fixture this file already varies per test — while
// removing the `/permissions/me` query from the render path, which is what
// made a `QueryClientProvider` necessary.
vi.mock("../../../../features/user-administration/access/useCanAccess", () => {
  const build = (profile: string) => ({
    has: (permission: string) =>
      (PERMISSIONS_BY_ROLE[profile] ?? []).includes(permission),
    hasModule: (moduleName: string) =>
      (PERMISSIONS_BY_ROLE[profile] ?? []).some((permission) =>
        permission.startsWith(`${moduleName}:`),
      ),
    isLoading: false,
    all: new Set(PERMISSIONS_BY_ROLE[profile] ?? []),
  });
  return {
    // Display reads the **effective** set: while simulating it is the
    // simulated roles' union, not the real user's (APRAS-35's split, which
    // IAM F5 preserves — see `useCanAccess`'s two-set table).
    useEffectivePermissionSet: () =>
      build(useSimulation().isSimulating ? mockSimulatedProfile : mockProfile()),
    usePermissionSet: () => build(mockProfile()),
    useCanAccess: () => ({ allowed: true, isLoading: false }),
    useCanShowMenu: () => ({ allowed: true, isLoading: false }),
  };
});


// TaskBoard reads its effective identity via useEffectivePermissionSet, which
// combines useAuth with useSimulation. Default both to a non-simulating,
// roleless state so existing assertions are unaffected; simulation-specific
// tests below override these mocks.
vi.mock("../../../user-administration/context/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  })),
}));

vi.mock("../../../user-administration/context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

// useEffectivePermissionSet also calls useRoles (APRAS-9 role-type fold-in);
// default to no Roles so behavior matches pre-APRAS-9 expectations.
// Overridden per-test below for the role-type fallback assertions.
vi.mock("../../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({ data: [] })),
}));

const mockTasks = [
  {
    id: "1",
    title: "Task 1",
    description: "Description 1",
    status: TaskStatus.PENDING,
    priority: TaskPriority.MEDIUM,
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
    created_by_id: "user-1",
    assigned_to_id: "user-2",
    is_deleted: false,
    category_id: "cat-1",
    category_name: "General",
    category_color: "#808080",
    visible_to: [],
  },
  {
    id: "2",
    title: "Task 2",
    description: "Description 2",
    status: TaskStatus.IN_PROGRESS,
    priority: TaskPriority.HIGH,
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
    created_by_id: "user-1",
    assigned_to_id: "user-3",
    is_deleted: false,
    category_id: "cat-1",
    category_name: "General",
    category_color: "#808080",
    visible_to: [],
  },
];

describe("TaskBoard", () => {
  it("renders tasks in their respective columns", () => {
    render(
      <TaskBoard
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{}}
      />,
    );

    expect(screen.getByText("Task 1")).toBeInTheDocument();
    expect(screen.getByText("Task 2")).toBeInTheDocument();

    // Check if they are in the correct columns
    const pendingColumn = screen
      .getByRole("heading", { name: "Pendente" })
      .closest(".flex-1");
    const inProgressColumn = screen
      .getByRole("heading", { name: "Em andamento" })
      .closest(".flex-1");

    expect(pendingColumn).toHaveTextContent("Task 1");
    expect(inProgressColumn).toHaveTextContent("Task 2");
  });

  it("filters tasks by assigned_to_id", () => {
    render(
      <TaskBoard
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{ assigned_to_id: "user-2" }}
      />,
    );

    expect(screen.getByText("Task 1")).toBeInTheDocument();
    expect(screen.queryByText("Task 2")).not.toBeInTheDocument();
  });

  it("filters tasks by status", () => {
    render(
      <TaskBoard
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{ status: TaskStatus.PENDING }}
      />,
    );

    expect(screen.getByText("Task 1")).toBeInTheDocument();
    expect(screen.queryByText("Task 2")).not.toBeInTheDocument();
  });

  it("filters tasks by priority", () => {
    render(
      <TaskBoard
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{ priority: TaskPriority.HIGH }}
      />,
    );

    expect(screen.queryByText("Task 1")).not.toBeInTheDocument();
    expect(screen.getByText("Task 2")).toBeInTheDocument();
  });

  it("calls onTaskClick when a task is clicked", () => {
    const onTaskClick = vi.fn();
    render(
      <TaskBoard
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{}}
        onTaskClick={onTaskClick}
      />,
    );

    fireEvent.click(screen.getByText("Task 1"));
    expect(onTaskClick).toHaveBeenCalledWith("1");
  });

  it("renders loading state", () => {
    render(
      <TaskBoard
        tasks={[]}
        isLoading={true}
        isError={false}
        error={null}
        filters={{}}
      />,
    );

    expect(screen.getByText("Carregando tarefas...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(
      <TaskBoard
        tasks={[]}
        isLoading={false}
        isError={true}
        error={new Error("Test Error")}
        filters={{}}
      />,
    );

    expect(
      screen.getByText("Erro ao carregar tarefas: Test Error"),
    ).toBeInTheDocument();
  });

  describe("admin role simulation", () => {
    it("hides tasks not visible to the simulated MANAGER + Role combination", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRoleIds: ["type-1"],
        isSimulating: true,
        setSimulatedRoleIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      const tasksWithVisibility = [
        {
          ...mockTasks[0],
          visible_to: [{ id: "type-1", name: "type-1" }],
        },
        {
          ...mockTasks[1],
          visible_to: [{ id: "type-2", name: "type-2" }],
        },
      ];
      render(
        <TaskBoard
          tasks={tasksWithVisibility as any} // skipcq: JS-0323
          isLoading={false}
          isError={false}
          error={null}
          filters={{}}
        />,
      );
      expect(screen.getByText("Task 1")).toBeInTheDocument();
      expect(screen.queryByText("Task 2")).not.toBeInTheDocument();
    });

    it("hides every targeted task when simulating with no roles selected", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRoleIds: [],
        isSimulating: true,
        setSimulatedRoleIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      vi.mocked(useRoles).mockReturnValue({
        data: [
          {
            id: "role-type-manager",
            name: "Gerente (papel)",
          },
        ],
      } as any); // skipcq: JS-0323
      const tasksWithVisibility = [
        {
          ...mockTasks[0],
          visible_to: [
            { id: "role-type-manager", name: "Gerente (papel)" },
          ],
        },
        {
          ...mockTasks[1],
          visible_to: [{ id: "type-2", name: "type-2" }],
        },
      ];
      render(
        <TaskBoard
          tasks={tasksWithVisibility as any} // skipcq: JS-0323
          isLoading={false}
          isError={false}
          error={null}
          filters={{}}
        />,
      );
      // The APRAS-9 fold-in this case was written for is **gone** (IAM F5,
      // APRAS-49 §10.3): the implicit membership became a real
      // `user_role_link` row at migration time, so a simulation with zero
      // roles selected now grants zero targets.
      expect(screen.queryByText("Task 1")).not.toBeInTheDocument();
      expect(screen.queryByText("Task 2")).not.toBeInTheDocument();
    });

    it("marks assigned task cards read-only when simulating MANAGER", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRoleIds: [],
        isSimulating: true,
        setSimulatedRoleIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      render(
        <TaskBoard
          tasks={mockTasks}
          isLoading={false}
          isError={false}
          error={null}
          filters={{}}
        />,
      );
      // Both mock tasks have an assigned_to_id, so both cards are read-only.
      expect(screen.getAllByTestId("task-readonly-indicator")).toHaveLength(2);
    });

    it("does not mark cards read-only when not simulating", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRoleIds: [],
        isSimulating: false,
        setSimulatedRoleIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      render(
        <TaskBoard
          tasks={mockTasks}
          isLoading={false}
          isError={false}
          error={null}
          filters={{}}
        />,
      );
      expect(
        screen.queryByTestId("task-readonly-indicator"),
      ).not.toBeInTheDocument();
    });
  });
});
