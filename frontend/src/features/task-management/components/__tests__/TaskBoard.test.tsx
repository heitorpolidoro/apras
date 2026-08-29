import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import TaskBoard from "../TaskBoard";
import { TaskStatus, TaskPriority } from "../../types";
import { UserRole } from "../../../../types/auth";
import { useSimulation } from "../../../user-administration/context/SimulationContext";
import { useUserTypes } from "../../../../hooks/useUserTypes";

// TaskBoard reads its effective identity via useEffectiveIdentity, which
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
    simulatedRole: null,
    simulatedUserTypeIds: [],
    isSimulating: false,
    setSimulatedRole: vi.fn(),
    setSimulatedUserTypeIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

// useEffectiveIdentity also calls useUserTypes (APRAS-9 role-type fold-in);
// default to no UserTypes so behavior matches pre-APRAS-9 expectations.
// Overridden per-test below for the role-type fallback assertions.
vi.mock("../../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({ data: [] })),
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
    it("hides tasks not visible to the simulated MANAGER + UserType combination", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRole: UserRole.MANAGER,
        simulatedUserTypeIds: ["type-1"],
        isSimulating: true,
        setSimulatedRole: vi.fn(),
        setSimulatedUserTypeIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      const tasksWithVisibility = [
        {
          ...mockTasks[0],
          visible_to: [{ id: "type-1", name: "type-1", allowed_menus: [] }],
        },
        {
          ...mockTasks[1],
          visible_to: [{ id: "type-2", name: "type-2", allowed_menus: [] }],
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

    it("resolves visibility via the role-type fallback when simulating MANAGER with zero simulated UserTypes (APRAS-9)", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRole: UserRole.MANAGER,
        simulatedUserTypeIds: [],
        isSimulating: true,
        setSimulatedRole: vi.fn(),
        setSimulatedUserTypeIds: vi.fn(),
        stopSimulation: vi.fn(),
      });
      vi.mocked(useUserTypes).mockReturnValue({
        data: [
          {
            id: "role-type-manager",
            name: "Gerente (papel)",
            allowed_menus: [],
            role: "MANAGER",
          },
        ],
      } as any); // skipcq: JS-0323
      const tasksWithVisibility = [
        {
          ...mockTasks[0],
          visible_to: [
            { id: "role-type-manager", name: "Gerente (papel)", allowed_menus: [] },
          ],
        },
        {
          ...mockTasks[1],
          visible_to: [{ id: "type-2", name: "type-2", allowed_menus: [] }],
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

    it("marks assigned task cards read-only when simulating MANAGER", () => {
      vi.mocked(useSimulation).mockReturnValue({
        simulatedRole: UserRole.MANAGER,
        simulatedUserTypeIds: [],
        isSimulating: true,
        setSimulatedRole: vi.fn(),
        setSimulatedUserTypeIds: vi.fn(),
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
        simulatedRole: null,
        simulatedUserTypeIds: [],
        isSimulating: false,
        setSimulatedRole: vi.fn(),
        setSimulatedUserTypeIds: vi.fn(),
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
