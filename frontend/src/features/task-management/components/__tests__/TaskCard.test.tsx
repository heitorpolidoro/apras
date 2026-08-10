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
  manager_visible: false,
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
    // Date is rendered without "Due:" prefix
    const dateEl = screen.getByText(/\d{1,2}\/\d{1,2}\/\d{4}/);
    expect(dateEl).toBeInTheDocument();
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

    render(<TaskCard task={mockTask} />);

    // In US format it might be MM/DD/YYYY or M/D/YYYY
    // 12/31/2023
    expect(screen.getByText("12/31/2023")).toBeInTheDocument();
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
