import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TaskCard from "../TaskCard";
import { TaskStatus, TaskPriority } from "../../types";
import { useTranslation } from "react-i18next";

vi.mock("react-i18next", () => ({
  useTranslation: vi.fn(),
}));

const mockTask = {
  id: "1",
  title: "Test Task",
  description: "Test Description",
  status: TaskStatus.PENDING,
  priority: TaskPriority.MEDIUM,
  created_at: "2023-01-01T10:00:00Z",
  updated_at: "2023-01-01T10:00:00Z",
  created_by_id: "user-1",
  assigned_to_id: "user-2",
  due_date: "2023-12-31T23:59:59Z",
  is_deleted: false,
  category_id: "cat-1",
  category_name: "General",
  category_color: "#808080",
  visible_to: [],
};

describe("TaskCard", () => {
  beforeEach(() => {
    vi.mocked(useTranslation).mockReturnValue({
      t: (s: string) => {
        const map: Record<string, string> = {
          "tasks.details.statusPending": "Pendente",
          "tasks.details.statusInProgress": "Em andamento",
          "tasks.details.statusCompleted": "Concluída",
          "tasks.details.statusCanceled": "Cancelada",
          "tasks.card.noDescription": "Sem descrição",
          "tasks.priority.LOW": "Baixa",
          "tasks.priority.MEDIUM": "Média",
          "tasks.priority.HIGH": "Alta",
          "tasks.priority.URGENT": "Urgente",
        };
        return map[s] || s;
      },
      i18n: { language: "pt" },
    } as any);
  });

  it("renders task basic details correctly", () => {
    render(<TaskCard task={mockTask} />);

    expect(screen.getByText("Test Task")).toBeInTheDocument();
    expect(screen.getByText("Test Description")).toBeInTheDocument();
    expect(screen.getByText("Pendente")).toBeInTheDocument();
    expect(screen.getByText("Média")).toBeInTheDocument();
    // A deadline long past now reads as relative overdue wording, not a
    // raw date (APRAS-62). The icon is asserted too: never colour alone.
    expect(screen.getByTestId("due-date-icon")).toBeInTheDocument();
  });

  it("renders 'Sem descrição' when description is missing", () => {
    const taskWithoutDesc = { ...mockTask, description: "" };
    render(<TaskCard task={taskWithoutDesc} />);
    expect(screen.getByText("Sem descrição")).toBeInTheDocument();
  });

  it("does not render due date when it is missing", () => {
    const taskWithoutDate = { ...mockTask, due_date: undefined };
    render(<TaskCard task={taskWithoutDate} />);
    expect(
      screen.queryByText(/\d{1,2}\/\d{1,2}\/\d{4}/),
    ).not.toBeInTheDocument();
  });

  it("calls onClick when Enter or Space is pressed", () => {
    const onClick = vi.fn();
    render(<TaskCard task={mockTask} onClick={onClick} />);

    const card = screen.getByRole("button");

    fireEvent.keyDown(card, { key: "Enter" });
    expect(onClick).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(card, { key: " " });
    expect(onClick).toHaveBeenCalledTimes(2);

    fireEvent.keyDown(card, { key: "Tab" });
    expect(onClick).toHaveBeenCalledTimes(2);
  });

  it("renders status badges for all statuses", () => {
    const statuses = [
      { status: TaskStatus.PENDING, expected: "Pendente" },
      { status: TaskStatus.IN_PROGRESS, expected: "Em andamento" },
      { status: TaskStatus.COMPLETED, expected: "Concluída" },
      { status: TaskStatus.CANCELED, expected: "Cancelada" },
    ];

    statuses.forEach(({ status, expected }) => {
      const { unmount } = render(<TaskCard task={{ ...mockTask, status }} />);
      expect(screen.getByText(expected)).toBeInTheDocument();
      unmount();
    });
  });

  it("renders priority badges for all priorities", () => {
    const priorities = [
      TaskPriority.LOW,
      TaskPriority.MEDIUM,
      TaskPriority.HIGH,
      TaskPriority.URGENT,
    ];

    const labels = ["Baixa", "Média", "Alta", "Urgente"];
    priorities.forEach((priority, i) => {
      const { unmount } = render(<TaskCard task={{ ...mockTask, priority }} />);
      expect(screen.getByText(labels[i])).toBeInTheDocument();
      unmount();
    });
  });

  it("renders assigned user initials when assigned_to_name is provided", () => {
    const taskWithAssignee = {
      ...mockTask,
      assigned_to_name: "John Doe Senior",
    };
    render(<TaskCard task={taskWithAssignee} />);

    // Initials should be "JD" (first letters of first two words, up to 2 chars)
    // Wait, the logic is: split(" ").map(n => n[0]).join("").substring(0, 2)
    // "John Doe Senior" -> ["John", "Doe", "Senior"] -> ["J", "D", "S"] -> "JDS" -> "JD"
    expect(screen.getByText("JD")).toBeInTheDocument();
    expect(screen.getByTitle("John Doe Senior")).toBeInTheDocument();
  });

  it("handles unknown status and priority with default variants", () => {
    const strangeTask = {
      ...mockTask,
      status: "UNKNOWN_STATUS" as any,
      priority: "UNKNOWN_PRIORITY" as any,
    };

    render(<TaskCard task={strangeTask} />);

    expect(screen.getByText("UNKNOWN_STATUS")).toBeInTheDocument();
    expect(screen.getByText("UNKNOWN_PRIORITY")).toBeInTheDocument();
  });

  it("renders due date in US format when language is en", () => {
    vi.mocked(useTranslation).mockReturnValue({
      t: (s: string) => s,
      i18n: { language: "en" },
    } as any);

    // A distant deadline keeps the absolute date (APRAS-62's `future`
    // state); "today" is whenever this suite runs, so the fixture is
    // computed from it rather than frozen.
    const far = new Date();
    far.setFullYear(far.getFullYear() + 2);
    render(<TaskCard task={{ ...mockTask, due_date: far.toISOString() }} />);

    expect(
      screen.getByText(far.toLocaleDateString("en-US")),
    ).toBeInTheDocument();
  });

  it("renders category badge with name and color dot", () => {
    render(<TaskCard task={mockTask} />);

    expect(screen.getByText("General")).toBeInTheDocument();
    const dot = document.querySelector(
      '[style*="background-color: rgb(128, 128, 128)"], [style*="background-color:#808080"], [style*="backgroundColor"]',
    );
    expect(dot).toBeTruthy();
  });

  it("does not render category badge when category_name is null", () => {
    const taskWithoutCategory = { ...mockTask, category_name: null };
    render(<TaskCard task={taskWithoutCategory} />);

    expect(screen.queryByText("General")).not.toBeInTheDocument();
  });

  it("does not render the read-only indicator by default", () => {
    render(<TaskCard task={mockTask} />);
    expect(
      screen.queryByTestId("task-readonly-indicator"),
    ).not.toBeInTheDocument();
  });

  it("renders the read-only indicator when readOnly is true", () => {
    render(<TaskCard task={mockTask} readOnly />);
    expect(screen.getByTestId("task-readonly-indicator")).toBeInTheDocument();
  });

  it("renders category color dot with fallback when category_color is null", () => {
    const taskWithoutColor = {
      ...mockTask,
      category_name: "General",
      category_color: null,
    };
    render(<TaskCard task={taskWithoutColor as any} />);
    expect(screen.getByText("General")).toBeInTheDocument();
    const dot = document.querySelector(
      '[style*="background-color"]',
    ) as HTMLElement | null;
    expect(dot).toBeTruthy();
    expect(dot?.style.backgroundColor).toBe("rgb(128, 128, 128)");
  });
});

// ── APRAS-62: search highlight, due-date wording and mouse-only dragging ──
describe("TaskCard — APRAS-62", () => {
  beforeEach(() => {
    vi.mocked(useTranslation).mockReturnValue({
      t: (s: string) => s,
      i18n: { language: "pt" },
    } as unknown as ReturnType<typeof useTranslation>);
  });

  it("exposes exactly one button role, and it is the draggable root", () => {
    render(<TaskCard task={mockTask} draggable />);

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveAttribute("draggable", "true");
  });

  it("is not draggable unless the board says so", () => {
    render(<TaskCard task={mockTask} />);
    expect(screen.getByRole("button")).toHaveAttribute("draggable", "false");
  });

  it("is not draggable when the card is read-only", () => {
    render(<TaskCard task={mockTask} draggable readOnly />);
    expect(screen.getByRole("button")).toHaveAttribute("draggable", "false");
  });

  it("puts the task id on the dataTransfer and reports the drag start", () => {
    const onDragStart = vi.fn();
    const onDragEnd = vi.fn();
    render(
      <TaskCard
        task={mockTask}
        draggable
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
      />,
    );

    const setData = vi.fn();
    fireEvent.dragStart(screen.getByRole("button"), {
      dataTransfer: { setData, effectAllowed: "" },
    });
    expect(setData).toHaveBeenCalledWith("text/plain", mockTask.id);
    expect(onDragStart).toHaveBeenCalledWith(mockTask.id);

    fireEvent.dragEnd(screen.getByRole("button"));
    expect(onDragEnd).toHaveBeenCalledTimes(1);
  });

  it("starts a drag even when the event carries no dataTransfer", () => {
    const onDragStart = vi.fn();
    render(<TaskCard task={mockTask} draggable onDragStart={onDragStart} />);

    fireEvent.dragStart(screen.getByRole("button"));
    expect(onDragStart).toHaveBeenCalledWith(mockTask.id);
  });

  it("has no grab/move/drop key handling: arrow keys do nothing", () => {
    const onClick = vi.fn();
    const onDragStart = vi.fn();
    render(
      <TaskCard
        task={mockTask}
        draggable
        onClick={onClick}
        onDragStart={onDragStart}
      />,
    );

    const card = screen.getByRole("button");
    fireEvent.keyDown(card, { key: "ArrowLeft" });
    fireEvent.keyDown(card, { key: "ArrowRight" });
    fireEvent.keyDown(card, { key: "ArrowUp" });
    fireEvent.keyDown(card, { key: "ArrowDown" });

    expect(onClick).not.toHaveBeenCalled();
    expect(onDragStart).not.toHaveBeenCalled();
    expect(card).not.toHaveAttribute("aria-grabbed");
  });

  it("renders the grip affordance as decorative, never as a control", () => {
    render(<TaskCard task={mockTask} draggable />);

    const grip = screen.getByTestId("task-card-grip");
    expect(grip).toHaveAttribute("aria-hidden", "true");
    expect(grip.tagName).toBe("SPAN");
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });

  it("does not render the grip when the card is not draggable", () => {
    render(<TaskCard task={mockTask} />);
    expect(screen.queryByTestId("task-card-grip")).not.toBeInTheDocument();
  });

  it("wraps the searched fragment in a mark, in title and description", () => {
    const task = {
      ...mockTask,
      title: "Revisão da manutenção",
      description: "Contrato de manutenção anual",
    };
    const { container } = render(<TaskCard task={task} search="manutencao" />);

    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(2);
    expect(marks[0].textContent).toBe("manutenção");
  });

  it("renders no mark without a search", () => {
    const { container } = render(<TaskCard task={mockTask} />);
    expect(container.querySelectorAll("mark")).toHaveLength(0);
  });

  it("renders the overdue wording and an icon for a past deadline", () => {
    render(<TaskCard task={mockTask} />);

    expect(screen.getByTestId("due-date-icon")).toBeInTheDocument();
    expect(screen.getByText("tasks.dueDate.overdueMany")).toBeInTheDocument();
  });
});
