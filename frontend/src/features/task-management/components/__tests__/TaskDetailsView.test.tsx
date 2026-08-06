import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import TaskDetailsView from "../TaskDetailsView";
import { TaskPriority, TaskStatus } from "../../types";
import { useUpdateTask, useTaskHistory } from "../../hooks/useTasks";
import { useAssignableUsers } from "../../../../hooks/useUsers";
import { useCategories } from "../../hooks/useCategories";
import { useTranslation } from "react-i18next";

// Mock the hooks
vi.mock("../../hooks/useTasks", () => ({
  useUpdateTask: vi.fn(),
  useTaskHistory: vi.fn(),
  useComments: vi.fn(() => ({ data: [], isLoading: false })),
  useCreateComment: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUpdateComment: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("../../../../hooks/useUsers", () => ({
  useAssignableUsers: vi.fn(),
}));

vi.mock("../../hooks/useCategories", () => ({
  useCategories: vi.fn(),
  useCreateCategory: vi.fn(),
  useUpdateCategory: vi.fn(),
  useDeleteCategory: vi.fn(),
}));

vi.mock(
  "../../../user-administration/context/AuthContext",
  async (importOriginal) => {
    const actual =
      await importOriginal<
        typeof import("../../../user-administration/context/AuthContext")
      >();
    return {
      ...actual,
      useAuth: vi.fn(() => ({
        user: { id: "admin-1", role: actual.UserRole.ADMINISTRATOR },
      })),
    };
  },
);

describe("TaskDetailsView", () => {
  const mockOnEdit = vi.fn();
  const mockOnClose = vi.fn();
  const mockUpdateMutate = vi.fn();

  const mockTask = {
    id: "1",
    title: "Test Task",
    description: "Test Description",
    priority: TaskPriority.MEDIUM,
    status: TaskStatus.PENDING,
    assigned_to_id: "user1",
    assigned_to_name: "Alice Smith",
    created_by_id: "admin",
    created_by_name: "admin",
    due_date: "2023-12-31T23:59:59Z",
    created_at: "2023-01-01T10:00:00Z",
    updated_at: "2023-01-01T10:00:00Z",
    category_id: "cat-1",
    category_name: "General",
    category_color: "#808080",
    manager_visible: false,
  };

  const mockAssignableUsers = [
    {
      id: "user1",
      full_name: "Alice Smith",
      username: "alice",
      role: "DIRECTOR",
      is_active: true,
      type: { id: "t1", name: "Analista" },
    },
    {
      id: "user2",
      full_name: "Bob Jones",
      username: "bob",
      role: "DIRECTOR",
      is_active: true,
      type: { id: "t1", name: "Analista" },
    },
  ];

  const mockCategories = [
    { id: "cat-1", name: "General", color: "#808080", is_active: true },
    { id: "cat-2", name: "Feature", color: "#ff0000", is_active: true },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useUpdateTask).mockReturnValue({
      mutate: mockUpdateMutate,
      isPending: false,
    } as any); // skipcq: JS-0323

    vi.mocked(useTaskHistory).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any); // skipcq: JS-0323

    vi.mocked(useAssignableUsers).mockReturnValue({
      data: mockAssignableUsers,
      isLoading: false,
    } as any); // skipcq: JS-0323

    vi.mocked(useCategories).mockReturnValue({
      data: mockCategories,
      isLoading: false,
    } as any); // skipcq: JS-0323
  });

  it("renders all task metadata correctly", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    expect(screen.getByText("Test Task")).toBeInTheDocument();
    expect(screen.getByText("Test Description")).toBeInTheDocument();
    expect(screen.getAllByText("Pendente").length).toBeGreaterThan(0);
    expect(screen.getByRole("combobox", { name: "priority" })).toHaveValue(
      TaskPriority.MEDIUM,
    );
    expect(screen.getByRole("combobox", { name: "assigned_to" })).toHaveValue(
      "user1",
    );
    expect(screen.getByText("admin")).toBeInTheDocument();
    const dateElements = screen.getAllByText(/2023/);
    expect(dateElements.length).toBeGreaterThan(0);
  });

  it("triggers onEdit callback when Edit button is clicked", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Editar/i }));

    expect(mockOnEdit).toHaveBeenCalled();
  });

  it("triggers onClose callback when Close button is clicked", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Fechar/i }));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("triggers updateTask mutation when status select is changed", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    const statusSelect = screen.getByRole("combobox", { name: "status" });
    fireEvent.change(statusSelect, {
      target: { value: TaskStatus.IN_PROGRESS },
    });

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "1",
        data: { status: TaskStatus.IN_PROGRESS },
      }),
    );
  });

  it("triggers updateTask mutation when priority select is changed", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    const prioritySelect = screen.getByRole("combobox", { name: "priority" });
    fireEvent.change(prioritySelect, { target: { value: TaskPriority.HIGH } });

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "1",
        data: { priority: TaskPriority.HIGH },
      }),
    );
  });

  it("triggers updateTask mutation when assigned_to select is changed", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    const assignedToSelect = screen.getByRole("combobox", {
      name: "assigned_to",
    });
    fireEvent.change(assignedToSelect, { target: { value: "user2" } });

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "1",
        data: { assigned_to_id: "user2" },
      }),
    );
  });

  it("triggers updateTask with null when assigned_to is cleared", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    const assignedToSelect = screen.getByRole("combobox", {
      name: "assigned_to",
    });
    fireEvent.change(assignedToSelect, { target: { value: "" } });

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "1",
        data: { assigned_to_id: null },
      }),
    );
  });

  it("triggers updateTask mutation when category select is changed", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    const categorySelect = screen.getByRole("combobox", { name: "category" });
    fireEvent.change(categorySelect, { target: { value: "cat-2" } });

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "1",
        data: { category_id: "cat-2" },
      }),
    );
  });

  it("renders 'Não atribuído' option when assigned_to_id is null", () => {
    const incompleteTask = {
      ...mockTask,
      assigned_to_id: null,
      assigned_to_name: null,
      due_date: null,
    };

    render(
      <TaskDetailsView
        task={incompleteTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    expect(screen.getByRole("combobox", { name: "assigned_to" })).toHaveValue(
      "",
    );
    expect(screen.getAllByText("Não definido").length).toBeGreaterThan(0);
  });

  it("applies correct status classes", () => {
    const statuses = Object.values(TaskStatus);

    statuses.forEach((status) => {
      const { rerender } = render(
        <TaskDetailsView
          task={{ ...mockTask, status } as any} // skipcq: JS-0323
          onEdit={mockOnEdit}
          onClose={mockOnClose}
        />,
      );
      const expectedText =
        status === TaskStatus.PENDING
          ? "Pendente"
          : status === TaskStatus.IN_PROGRESS
            ? "Em andamento"
            : status === TaskStatus.BLOCKED
              ? "Bloqueada"
              : status === TaskStatus.COMPLETED
                ? "Concluída"
                : "Cancelada";

      const badge = screen.getAllByText(expectedText)[0];
      expect(badge).toBeInTheDocument();
      rerender(<></>);
    });
  });

  it("renders 'Nenhuma descrição fornecida.' when description is empty or null", () => {
    const { rerender } = render(
      <TaskDetailsView
        task={{ ...mockTask, description: "" } as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );
    expect(
      screen.getByText("Nenhuma descrição fornecida."),
    ).toBeInTheDocument();

    rerender(
      <TaskDetailsView
        task={{ ...mockTask, description: null } as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );
    expect(
      screen.getByText("Nenhuma descrição fornecida."),
    ).toBeInTheDocument();
  });

  it("disables all selects when updateTaskMutation.isPending is true", () => {
    vi.mocked(useUpdateTask).mockReturnValue({
      mutate: mockUpdateMutate,
      isPending: true,
    } as any); // skipcq: JS-0323

    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    expect(screen.getByRole("combobox", { name: "status" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "priority" })).toBeDisabled();
    expect(
      screen.getByRole("combobox", { name: "assigned_to" }),
    ).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "category" })).toBeDisabled();
  });

  it("formatDate handles all falsy values", () => {
    const { rerender } = render(
      <TaskDetailsView
        task={{ ...mockTask, due_date: null } as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );
    expect(screen.getAllByText("Não definido").length).toBeGreaterThan(0);

    rerender(
      <TaskDetailsView
        task={{ ...mockTask, due_date: undefined } as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );
    expect(screen.getAllByText("Não definido").length).toBeGreaterThan(0);

    rerender(
      <TaskDetailsView
        task={{ ...mockTask, due_date: "" } as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );
    expect(screen.getAllByText("Não definido").length).toBeGreaterThan(0);
  });

  it("handles unknown status and renders it in the status select", () => {
    const strangeTask = {
      ...mockTask,
      status: "UNKNOWN_STATUS",
    };

    render(
      <TaskDetailsView
        task={strangeTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    // Unknown statuses are appended to the status select options
    expect(screen.getByText("UNKNOWN_STATUS")).toBeInTheDocument();
  });

  it("formats dates in English locale when language is not pt", () => {
    vi.mocked(useTranslation).mockReturnValue({
      t: (s: string) => s,
      i18n: { language: "en" },
    } as any); // skipcq: JS-0323

    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    const dateEls = screen.getAllByText(/2023/);
    expect(dateEls.length).toBeGreaterThan(0);
  });

  it("renders color dot using task.category_color and selects current category", () => {
    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    expect(screen.getByRole("combobox", { name: "category" })).toHaveValue(
      "cat-1",
    );
    const colorDot = screen.getByTestId("category-color-dot");
    expect(colorDot).toHaveStyle({ backgroundColor: "#808080" });
  });

  it("renders only active categories in the category select", () => {
    vi.mocked(useCategories).mockReturnValue({
      data: [
        { id: "cat-1", name: "General", color: "#808080", is_active: true },
        {
          id: "cat-archived",
          name: "Archived",
          color: "#ccc",
          is_active: false,
        },
      ],
      isLoading: false,
    } as any); // skipcq: JS-0323

    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    expect(screen.getByText("General")).toBeInTheDocument();
    expect(screen.queryByText("Archived")).not.toBeInTheDocument();
  });

  it("falls back to created_by_id when created_by_name is null", () => {
    render(
      <TaskDetailsView
        task={{ ...mockTask, created_by_name: null } as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    expect(screen.getByText("admin")).toBeInTheDocument();
  });

  it("falls back to email when user has no full_name", () => {
    vi.mocked(useAssignableUsers).mockReturnValue({
      data: [
        {
          id: "user3",
          full_name: "",
          email: "charlie",
          role: "DIRECTOR",
          is_active: true,
          type: { id: "t1", name: "Analista" },
        },
      ],
      isLoading: false,
    } as any); // skipcq: JS-0323

    render(
      <TaskDetailsView
        task={{ ...mockTask, assigned_to_id: "user3" } as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    expect(screen.getByRole("option", { name: "charlie" })).toBeInTheDocument();
  });

  it("includes inactive current category as the first option when task category is inactive", () => {
    vi.mocked(useCategories).mockReturnValue({
      data: [
        {
          id: "cat-active",
          name: "Active Cat",
          color: "#00ff00",
          is_active: true,
        },
        { id: "cat-old", name: "Old Cat", color: "#cccccc", is_active: false },
      ],
      isLoading: false,
    } as any); // skipcq: JS-0323

    render(
      <TaskDetailsView
        task={
          {
            ...mockTask,
            category_id: "cat-old",
            category_color: "#cccccc",
          } as any // skipcq: JS-0323
        }
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    expect(screen.getByRole("option", { name: "Old Cat" })).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Active Cat" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "category" })).toHaveValue(
      "cat-old",
    );
  });

  it("renders color dot with no background color when category_color is null", () => {
    render(
      <TaskDetailsView
        task={{ ...mockTask, category_color: null } as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    const colorDot = screen.getByTestId("category-color-dot");
    expect(colorDot).toHaveStyle({ backgroundColor: "" });
  });

  it("renders empty category select when categories is undefined", () => {
    vi.mocked(useCategories).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as any); // skipcq: JS-0323

    render(
      <TaskDetailsView
        task={mockTask as any} // skipcq: JS-0323
        onEdit={mockOnEdit}
        onClose={mockOnClose}
      />,
    );

    const categorySelect = screen.getByRole("combobox", { name: "category" });
    expect(categorySelect).toBeInTheDocument();
    expect(categorySelect.querySelectorAll("option")).toHaveLength(0);
  });
});
