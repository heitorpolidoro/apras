import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import TaskForm from "../TaskForm";
import { TaskPriority, TaskStatus } from "../../types";
import { useCreateTask, useUpdateTask } from "../../hooks/useTasks";
import { useAssignableUsers } from "../../../../hooks/useUsers";
import { useCategories } from "../../hooks/useCategories";
import { useUserTypes } from "../../../../hooks/useUserTypes";
import {
  useAuth,
  UserRole,
} from "../../../user-administration/context/AuthContext";

// Mock the hooks
vi.mock("../../hooks/useTasks", () => ({
  useCreateTask: vi.fn(),
  useUpdateTask: vi.fn(),
}));

vi.mock("../../../../hooks/useUsers", () => ({
  useUsers: vi.fn(),
  useAssignableUsers: vi.fn(),
}));

vi.mock("../../hooks/useCategories", () => ({
  useCategories: vi.fn(),
}));

vi.mock("../../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(),
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
        user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
      })),
    };
  },
);

describe("TaskForm", () => {
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();
  const mockCreateMutate = vi.fn();
  const mockUpdateMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useCreateTask).mockReturnValue({
      mutate: mockCreateMutate,
      isPending: false,
      error: null,
    } as any); // skipcq: JS-0323

    vi.mocked(useUpdateTask).mockReturnValue({
      mutate: mockUpdateMutate,
      isPending: false,
      error: null,
    } as any); // skipcq: JS-0323

    vi.mocked(useAssignableUsers).mockReturnValue({
      data: [
        { id: "user-1", full_name: "User 1", username: "user1" },
        { id: "user-2", full_name: "User 2", username: "user2" },
      ],
      isLoading: false,
    } as any); // skipcq: JS-0323

    vi.mocked(useCategories).mockReturnValue({
      data: [{ id: "cat-1", name: "Geral", color: "#808080", is_active: true }],
      isLoading: false,
    } as any); // skipcq: JS-0323

    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Gerente" }],
      isLoading: false,
    } as any);
  });

  it("renders correctly in creation mode", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    expect(screen.getByText(/Nova Tarefa/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Título \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Descrição/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Prioridade/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Data de entrega/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Status/i)).not.toBeInTheDocument();
  });

  it("renders correctly with initial values in edit mode", () => {
    const mockTask = {
      id: "1",
      title: "Existing Task",
      description: "Existing Description",
      priority: TaskPriority.HIGH,
      status: TaskStatus.IN_PROGRESS,
      assigned_to_id: "user-1",
      due_date: "2023-10-27T10:00:00Z",
      created_by_id: "admin",
      created_at: new Date(),
      updated_at: new Date(),
      category_id: "cat-1",
    };

    render(
      <TaskForm
        task={mockTask as any} // skipcq: JS-0323
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />,
    );

    expect(screen.getByText(/Editar Tarefa/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Existing Task")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Existing Description"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Status/i)).toBeInTheDocument();
    // Test initial state date formatting
    expect(screen.getByLabelText(/Data de entrega/i)).toHaveValue("2023-10-27");
    // Test assigned_to_id rendering
    expect(screen.getByLabelText(/Atribuído a/i)).toHaveValue("user-1");
  });

  it("handles fallback logic for missing fields in edit mode", () => {
    const mockTask = {
      id: "1",
      title: "Task with missing fields",
      description: null,
      assigned_to_id: null,
      due_date: null,
      priority: TaskPriority.MEDIUM,
      status: TaskStatus.PENDING,
    };

    render(
      <TaskForm
        task={mockTask as any} // skipcq: JS-0323
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />,
    );

    expect(screen.getByLabelText(/Descrição/i)).toHaveValue("");
    expect(screen.getByLabelText(/Atribuído a/i)).toHaveValue("");
    expect(screen.getByLabelText(/Data de entrega/i)).toHaveValue("");
  });

  it("shows validation error when title is empty", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    fireEvent.click(screen.getByRole("button", { name: /Criar tarefa/i }));

    expect(screen.getByText(/Título é obrigatório/i)).toBeInTheDocument();
    expect(mockCreateMutate).not.toHaveBeenCalled();

    // Clear error on change
    fireEvent.change(screen.getByLabelText(/Título \*/i), {
      target: { value: "A" },
    });
    expect(screen.queryByText(/Título é obrigatório/i)).not.toBeInTheDocument();
  });

  it("handles null/missing description and assigned_to_id in submission", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);
    fireEvent.change(screen.getByLabelText(/Título \\*/i), {
      target: { value: "Minimal Task" },
    });
    fireEvent.change(screen.getByLabelText(/Categoria/i), {
      target: { name: "category_id", value: "cat-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Criar tarefa/i }));

    expect(mockCreateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        description: null,
        assigned_to_id: null,
      }),
      expect.any(Object),
    );
  });

  it("submits with due date converted to Date object", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    fireEvent.change(screen.getByLabelText(/Título \\*/i), {
      target: { value: "Task with Date" },
    });
    fireEvent.change(screen.getByLabelText(/Data de entrega/i), {
      target: { value: "2023-12-25" },
    });
    fireEvent.change(screen.getByLabelText(/Categoria/i), {
      target: { name: "category_id", value: "cat-1" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Criar tarefa/i }));

    expect(mockCreateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        due_date: expect.any(Date),
      }),
      expect.any(Object),
    );

    const submittedDate = mockCreateMutate.mock.calls[0][0].due_date;
    expect(submittedDate.toISOString()).toContain("2023-12-25");
  });

  it("handles changes in textarea and select elements", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    const description = screen.getByLabelText(/Descrição/i);
    const priority = screen.getByLabelText(/Prioridade/i);

    fireEvent.change(description, {
      target: { name: "description", value: "New Desc" },
    });
    fireEvent.change(priority, {
      target: { name: "priority", value: TaskPriority.URGENT },
    });

    expect(description).toHaveValue("New Desc");
    expect(priority).toHaveValue(TaskPriority.URGENT);
  });

  it("calls useCreateTask mutate with correct data on submission", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    fireEvent.change(screen.getByLabelText(/Título \\*/i), {
      target: { value: "New Task" },
    });
    fireEvent.change(screen.getByLabelText(/Descrição/i), {
      target: { value: "New Description" },
    });
    fireEvent.change(screen.getByLabelText(/Prioridade/i), {
      target: { value: TaskPriority.HIGH },
    });
    fireEvent.change(screen.getByLabelText(/Categoria/i), {
      target: { name: "category_id", value: "cat-1" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Criar tarefa/i }));

    expect(mockCreateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "New Task",
        description: "New Description",
        priority: TaskPriority.HIGH,
      }),
      expect.any(Object),
    );
  });

  it("calls useUpdateTask mutate with correct data on submission in edit mode", () => {
    const mockTask = {
      id: "1",
      title: "Old Title",
      priority: TaskPriority.LOW,
      status: TaskStatus.PENDING,
      created_by_id: "admin",
      created_at: new Date(),
      updated_at: new Date(),
      category_id: "cat-1",
    };

    render(
      <TaskForm
        task={mockTask as any} // skipcq: JS-0323
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Título \\*/i), {
      target: { value: "Updated Title" },
    });
    fireEvent.change(screen.getByLabelText(/Status/i), {
      target: { value: TaskStatus.COMPLETED },
    });

    fireEvent.click(screen.getByRole("button", { name: /Atualizar tarefa/i }));

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      {
        id: "1",
        data: expect.objectContaining({
          title: "Updated Title",
          status: TaskStatus.COMPLETED,
        }),
      },
      expect.any(Object),
    );
  });

  it("shows loading state and disables fields when creating", () => {
    vi.mocked(useCreateTask).mockReturnValue({
      mutate: mockCreateMutate,
      isPending: true,
      error: null,
    } as any); // skipcq: JS-0323

    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    expect(screen.getByRole("button", { name: /Salvando.../i })).toBeDisabled();
    expect(screen.getByLabelText(/Título \\*/i)).toBeDisabled();
    expect(screen.getByLabelText(/Descrição/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /Cancel/i })).toBeDisabled();
  });

  it("shows loading state and disables fields when updating", () => {
    const mockTask = {
      id: "1",
      title: "Old Title",
      priority: TaskPriority.LOW,
      status: TaskStatus.PENDING,
    };
    vi.mocked(useUpdateTask).mockReturnValue({
      mutate: mockUpdateMutate,
      isPending: true,
      error: null,
    } as any); // skipcq: JS-0323

    render(
      <TaskForm
        task={mockTask as any} // skipcq: JS-0323
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />,
    );

    expect(screen.getByRole("button", { name: /Salvando.../i })).toBeDisabled();
    expect(screen.getByLabelText(/Título \\*/i)).toBeDisabled();
    expect(screen.getByLabelText(/Status/i)).toBeDisabled();
  });

  it("calls onCancel when Cancel button is clicked", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it("displays server error detail for create mutation", () => {
    vi.mocked(useCreateTask).mockReturnValue({
      mutate: mockCreateMutate,
      isPending: false,
      error: {
        response: {
          data: { detail: "Create error" },
        },
      } as any, // skipcq: JS-0323
    } as any); // skipcq: JS-0323

    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    expect(screen.getByText("Create error")).toBeInTheDocument();
  });

  it("displays server error detail for update mutation", () => {
    vi.mocked(useUpdateTask).mockReturnValue({
      mutate: mockUpdateMutate,
      isPending: false,
      error: {
        response: {
          data: { detail: "Update error" },
        },
      } as any, // skipcq: JS-0323
    } as any); // skipcq: JS-0323

    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    expect(screen.getByText("Update error")).toBeInTheDocument();
  });

  it("displays default server error when detail is missing", () => {
    vi.mocked(useCreateTask).mockReturnValue({
      mutate: mockCreateMutate,
      isPending: false,
      error: new Error("Generic error"),
    } as any); // skipcq: JS-0323

    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    expect(
      screen.getByText("Ocorreu um erro ao salvar a tarefa."),
    ).toBeInTheDocument();
  });

  it("renders user options correctly, including fallback to username", () => {
    vi.mocked(useAssignableUsers).mockReturnValue({
      data: [
        { id: "user-1", full_name: "Full Name", email: "user1@test.com" },
        { id: "user-2", full_name: "", email: "user2_only" },
      ],
      isLoading: false,
    } as any); // skipcq: JS-0323

    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    const select = screen.getByLabelText(/Atribuído a/i);
    const options = Array.from(select.querySelectorAll("option"));

    expect(
      options.find((o) => o.textContent === "Full Name"),
    ).toBeInTheDocument();
    expect(
      options.find((o) => o.textContent === "user2_only"),
    ).toBeInTheDocument();
  });

  it("shows validation error when category is not selected", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    fireEvent.click(screen.getByRole("button", { name: /Criar tarefa/i }));

    expect(screen.getByText(/Categoria é obrigatória/i)).toBeInTheDocument();
    expect(mockCreateMutate).not.toHaveBeenCalled();
  });

  it("includes category_id in create payload", () => {
    render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    fireEvent.change(screen.getByLabelText(/Título \*/i), {
      target: { value: "Task with Category" },
    });
    fireEvent.change(screen.getByLabelText(/Categoria/i), {
      target: { name: "category_id", value: "cat-1" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Criar tarefa/i }));

    expect(mockCreateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        category_id: "cat-1",
      }),
      expect.any(Object),
    );
  });

  it("shows title field for DIRECTOR when editing a task", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "director-1", role: UserRole.DIRECTOR },
    } as any); // skipcq: JS-0323

    const mockTask = {
      id: "1",
      title: "Old Title",
      description: "Old Description",
      priority: TaskPriority.LOW,
      status: TaskStatus.PENDING,
      assigned_to_id: "user-1",
      created_by_id: "director-1",
      created_at: new Date(),
      updated_at: new Date(),
      category_id: "cat-1",
    };

    render(
      <TaskForm
        task={mockTask as any} // skipcq: JS-0323
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />,
    );

    expect(screen.getByLabelText(/Título \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Prioridade/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Data de entrega/i)).toBeInTheDocument();
  });

  it("submits update payload for director editing", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "director-1", role: UserRole.DIRECTOR },
    } as any); // skipcq: JS-0323

    const mockTask = {
      id: "1",
      title: "Old Title",
      description: "Old Description",
      priority: TaskPriority.LOW,
      status: TaskStatus.PENDING,
      assigned_to_id: "user-1",
      created_by_id: "director-1",
      created_at: new Date(),
      updated_at: new Date(),
      category_id: "cat-1",
    };

    render(
      <TaskForm
        task={mockTask as any} // skipcq: JS-0323
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />,
    );

    expect(screen.getByLabelText(/Título \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Prioridade/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Data de entrega/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Descrição/i), {
      target: { name: "description", value: "Updated Description" },
    });
    fireEvent.change(screen.getByLabelText(/Status/i), {
      target: { name: "status", value: TaskStatus.COMPLETED },
    });

    fireEvent.click(screen.getByRole("button", { name: /Atualizar tarefa/i }));

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      {
        id: "1",
        data: expect.objectContaining({
          status: TaskStatus.COMPLETED,
          description: "Updated Description",
          assigned_to_id: "user-1",
          category_id: "cat-1",
          title: "Old Title",
          priority: TaskPriority.LOW,
        }),
      },
      expect.any(Object),
    );
  });

  it("submits update payload for administrator editing", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
    } as any); // skipcq: JS-0323

    const mockTask = {
      id: "1",
      title: "Old Title",
      description: "Old Description",
      priority: TaskPriority.LOW,
      status: TaskStatus.PENDING,
      assigned_to_id: "user-1",
      created_by_id: "admin-1",
      created_at: "2023-01-01T10:00:00Z",
      updated_at: "2023-01-01T10:00:00Z",
      category_id: "cat-1",
    };

    render(
      <TaskForm
        task={mockTask as any} // skipcq: JS-0323
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />,
    );

    expect(screen.getByLabelText(/Título \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Prioridade/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Atualizar tarefa/i }));

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      {
        id: "1",
        data: {
          title: "Old Title",
          description: "Old Description",
          priority: TaskPriority.LOW,
          due_date: null,
          assigned_to_id: "user-1",
          category_id: "cat-1",
          status: TaskStatus.PENDING,
          visible_to_id: null,
        },
      },
      expect.any(Object),
    );
  });

  describe("visible_to_id field", () => {
    const existingTask = {
      id: "1",
      title: "Existing Task",
      description: "Some description",
      priority: TaskPriority.MEDIUM,
      status: TaskStatus.PENDING,
      assigned_to_id: "user-1",
      created_by_id: "admin-1",
      created_at: new Date(),
      updated_at: new Date(),
      category_id: "cat-1",
      visible_to_id: "",
    };

    it("shows visible_to_id select for ADMINISTRATOR in edit mode", () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
      } as any); // skipcq: JS-0323

      render(
        <TaskForm
          task={existingTask as any} // skipcq: JS-0323
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />,
      );

      expect(
        screen.getByLabelText(/visibilidade/i),
      ).toBeInTheDocument();
    });

    it("shows visible_to_id select for DIRECTOR in edit mode", () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { id: "director-1", role: UserRole.DIRECTOR },
      } as any); // skipcq: JS-0323

      render(
        <TaskForm
          task={existingTask as any} // skipcq: JS-0323
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />,
      );

      expect(
        screen.getByLabelText(/visibilidade/i),
      ).toBeInTheDocument();
    });

    it("does NOT show visible_to_id select for MANAGER", () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { id: "manager-1", role: UserRole.MANAGER },
      } as any); // skipcq: JS-0323

      render(
        <TaskForm
          task={existingTask as any} // skipcq: JS-0323
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />,
      );

      expect(
        screen.queryByLabelText(/visibilidade/i),
      ).not.toBeInTheDocument();
    });

    it("shows visible_to_id select in create mode for ADMIN", () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
      } as any); // skipcq: JS-0323

      render(<TaskForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

      expect(
        screen.getByLabelText(/visibilidade/i),
      ).toBeInTheDocument();
    });

    it("selecting a user type in the select updates visible_to_id in form state", () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
      } as any); // skipcq: JS-0323

      render(
        <TaskForm
          task={existingTask as any} // skipcq: JS-0323
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />,
      );

      const select = screen.getByLabelText(/visibilidade/i) as HTMLSelectElement;
      expect(select.value).toBe("");
      fireEvent.change(select, { target: { value: "type-1" } });
      expect(select.value).toBe("type-1");
    });
  });

  it("submits update payload for director editing with empty fields", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "director-1", role: UserRole.DIRECTOR },
    } as any); // skipcq: JS-0323

    const mockTask = {
      id: "1",
      title: "Old Title",
      description: "",
      priority: TaskPriority.LOW,
      status: TaskStatus.PENDING,
      assigned_to_id: "",
      created_by_id: "director-1",
      created_at: new Date(),
      updated_at: new Date(),
      category_id: "cat-1",
    };

    render(
      <TaskForm
        task={mockTask as any} // skipcq: JS-0323
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Atualizar tarefa/i }));

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      {
        id: "1",
        data: expect.objectContaining({
          status: TaskStatus.PENDING,
          description: null,
          assigned_to_id: null,
          category_id: "cat-1",
          title: "Old Title",
          priority: TaskPriority.LOW,
        }),
      },
      expect.any(Object),
    );
  });
});
