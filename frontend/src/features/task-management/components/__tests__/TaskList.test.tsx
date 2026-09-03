import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useTranslation } from "react-i18next";
import TaskList from "../TaskList";
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


// TaskList reads its effective identity via useEffectivePermissionSet, which
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
    description: "Desc 1",
    status: TaskStatus.PENDING,
    priority: TaskPriority.LOW,
    assigned_to_id: "user-1",
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
    created_by_id: "admin-1",
    is_deleted: false,
    category_id: "cat-1",
    category_name: "General",
    category_color: "#808080",
    visible_to: [],
  },
  {
    id: "2",
    title: "Task 2",
    description: "Desc 2",
    status: TaskStatus.COMPLETED,
    priority: TaskPriority.HIGH,
    assigned_to_id: "user-2",
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
    created_by_id: "admin-1",
    is_deleted: false,
    category_id: "cat-1",
    category_name: "General",
    category_color: "#808080",
    visible_to: [],
  },
];

const defaultFilters = {
  status: null,
  priority: null,
  assigned_to_id: null,
};

describe("TaskList", () => {
  it("renders loading state correctly", () => {
    render(
      <TaskList
        tasks={[]}
        isLoading={true}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText("Carregando tarefas...")).toBeInTheDocument();
  });

  it("renders error state correctly", () => {
    const errorMessage = "Failed to fetch";
    render(
      <TaskList
        tasks={[]}
        isLoading={false}
        isError={true}
        error={new Error(errorMessage)}
        filters={defaultFilters}
      />,
    );
    expect(
      screen.getByText(`Erro ao carregar tarefas: ${errorMessage}`),
    ).toBeInTheDocument();
  });

  it("renders 'Nenhuma tarefa encontrada' when list is empty", () => {
    render(
      <TaskList
        tasks={[]}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText("Nenhuma tarefa encontrada.")).toBeInTheDocument();
  });

  it("renders filtered tasks correctly", () => {
    render(
      <TaskList
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText("Task 1")).toBeInTheDocument();
    expect(screen.getByText("Task 2")).toBeInTheDocument();
  });

  it("filters tasks by status", () => {
    render(
      <TaskList
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{ ...defaultFilters, status: TaskStatus.PENDING }}
      />,
    );
    expect(screen.getByText("Task 1")).toBeInTheDocument();
    expect(screen.queryByText("Task 2")).not.toBeInTheDocument();
  });

  it("filters tasks by priority", () => {
    render(
      <TaskList
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{ ...defaultFilters, priority: TaskPriority.HIGH }}
      />,
    );
    expect(screen.queryByText("Task 1")).not.toBeInTheDocument();
    expect(screen.getByText("Task 2")).toBeInTheDocument();
  });

  it("filters tasks by assigned_to_id", () => {
    render(
      <TaskList
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{ ...defaultFilters, assigned_to_id: "user-1" }}
      />,
    );
    expect(screen.getByText("Task 1")).toBeInTheDocument();
    expect(screen.queryByText("Task 2")).not.toBeInTheDocument();
  });

  it("renders 'no match' message when filters exclude all tasks", () => {
    render(
      <TaskList
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={{ ...defaultFilters, status: TaskStatus.CANCELED }}
      />,
    );
    expect(
      screen.getByText("Nenhuma tarefa corresponde aos filtros selecionados."),
    ).toBeInTheDocument();
  });

  it("calls onTaskClick when a task card is clicked", () => {
    const onTaskClick = vi.fn();
    render(
      <TaskList
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
        onTaskClick={onTaskClick}
      />,
    );

    fireEvent.click(screen.getByText("Task 1"));
    expect(onTaskClick).toHaveBeenCalledWith("1");
  });

  it("shows no-category placeholder for tasks without category", () => {
    const tasksNoCategory = [
      {
        ...mockTasks[0],
        category_id: null,
        category_name: undefined,
        category_color: undefined,
      },
    ];
    render(
      <TaskList
        tasks={tasksNoCategory as any}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText("Sem categoria")).toBeInTheDocument();
  });

  it("shows assignee name when task has an assigned user", () => {
    const tasksWithAssignee = [
      { ...mockTasks[0], assigned_to_name: "João Silva" },
    ];
    render(
      <TaskList
        tasks={tasksWithAssignee}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText("João Silva")).toBeInTheDocument();
  });

  it("shows formatted due date when task has a due_date", () => {
    const tasksWithDate = [
      { ...mockTasks[0], due_date: "2024-06-15T00:00:00Z" },
    ];
    render(
      <TaskList
        tasks={tasksWithDate}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });

  it("shows category name with fallback color when category_color is missing", () => {
    const tasksNoColor = [
      { ...mockTasks[0], category_name: "Design", category_color: undefined },
    ];
    render(
      <TaskList
        tasks={tasksNoColor as any}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText("Design")).toBeInTheDocument();
  });

  it("uses en-US date format when language is not pt", () => {
    vi.mocked(useTranslation).mockReturnValueOnce({
      t: (key: string) => key,
      i18n: { language: "en", changeLanguage: vi.fn() },
    } as any);
    const tasksWithDate = [
      { ...mockTasks[0], due_date: "2024-01-20T12:00:00Z" },
    ];
    render(
      <TaskList
        tasks={tasksWithDate}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });

  it("renders without crashing when task has no description", () => {
    const tasksNoDesc = [{ ...mockTasks[0], description: undefined }];
    render(
      <TaskList
        tasks={tasksNoDesc as any}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(screen.getByText("Task 1")).toBeInTheDocument();
  });

  it("does not throw when row is clicked without onTaskClick callback", () => {
    render(
      <TaskList
        tasks={mockTasks}
        isLoading={false}
        isError={false}
        error={null}
        filters={defaultFilters}
      />,
    );
    expect(() => fireEvent.click(screen.getByText("Task 1"))).not.toThrow();
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
        <TaskList
          tasks={tasksWithVisibility as any} // skipcq: JS-0323
          isLoading={false}
          isError={false}
          error={null}
          filters={defaultFilters}
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
        <TaskList
          tasks={tasksWithVisibility as any} // skipcq: JS-0323
          isLoading={false}
          isError={false}
          error={null}
          filters={defaultFilters}
        />,
      );
      // The APRAS-9 fold-in this case was written for is **gone** (IAM F5,
      // APRAS-49 §10.3): `useEffectiveIdentity` returned the simulated ids
      // *unioned with* the role-implicit one, so Task 1 used to be visible
      // with nothing selected. The implicit membership became a real
      // `user_role_link` row at migration time, so a simulation with zero
      // roles selected now grants zero targets — which is the honest
      // preview of a user who belongs to nothing.
      expect(screen.queryByText("Task 1")).not.toBeInTheDocument();
      expect(screen.queryByText("Task 2")).not.toBeInTheDocument();
    });

    it("shows a read-only indicator on assigned tasks when simulating MANAGER", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRoleIds: [],
        isSimulating: true,
        setSimulatedRoleIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      render(
        <TaskList
          tasks={mockTasks}
          isLoading={false}
          isError={false}
          error={null}
          filters={defaultFilters}
        />,
      );
      // Both mock tasks have an assigned_to_id, so both are read-only for a
      // simulated MANAGER (no self-assignment concept in simulation).
      expect(screen.getAllByTestId("task-readonly-indicator")).toHaveLength(2);
    });

    it("does not show a read-only indicator when not simulating", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRoleIds: [],
        isSimulating: false,
        setSimulatedRoleIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      render(
        <TaskList
          tasks={mockTasks}
          isLoading={false}
          isError={false}
          error={null}
          filters={defaultFilters}
        />,
      );
      expect(
        screen.queryByTestId("task-readonly-indicator"),
      ).not.toBeInTheDocument();
    });

    it("shows all tasks and no read-only indicator when simulating ADMINISTRATOR", () => {
      mockSimulatedProfile = "ADMINISTRATOR";
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRoleIds: [],
        isSimulating: true,
        setSimulatedRoleIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      render(
        <TaskList
          tasks={mockTasks}
          isLoading={false}
          isError={false}
          error={null}
          filters={defaultFilters}
        />,
      );
      expect(screen.getByText("Task 1")).toBeInTheDocument();
      expect(screen.getByText("Task 2")).toBeInTheDocument();
      expect(
        screen.queryByTestId("task-readonly-indicator"),
      ).not.toBeInTheDocument();
    });
  });
});
