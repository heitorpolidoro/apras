import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import TaskFilterBar, { type ServerFilterState } from "../TaskFilterBar";
import { TaskStatus, TaskPriority } from "../../types";
import type { User } from "../../../../types/auth";

const categories = [
  { id: "cat-1", name: "Manutenção", color: "#808080", is_active: true },
];

const users: User[] = [
  {
    id: "user-1",
    email: "marta@apras.test",
    full_name: "Marta Nogueira",
    is_active: true,
    roles: [{ id: "role-1", name: "Síndica" }],
  },
];

const baseProps = {
  search: "",
  onSearchChange: vi.fn(),
  overdueOnly: false,
  onOverdueToggle: vi.fn(),
  overdueCount: 0,
  visibleCount: 12,
  totalCount: 47,
  filters: {
    status: null,
    priority: null,
    category_id: null,
    assigned_to_id: null,
  } as ServerFilterState,
  categories,
  users,
  onClearFilter: vi.fn(),
  onClearAll: vi.fn(),
};

const renderBar = (props: Partial<typeof baseProps> = {}) =>
  render(<TaskFilterBar {...baseProps} {...props} />);

describe("TaskFilterBar", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("states how many tasks are visible out of the total", () => {
    renderBar();
    expect(
      screen.getByText("Mostrando 12 de 47 tarefas"),
    ).toBeInTheDocument();
  });

  it("debounces the search before reporting it", () => {
    vi.useFakeTimers();
    const onSearchChange = vi.fn();
    renderBar({ onSearchChange });

    const input = screen.getByLabelText("Buscar tarefas");
    fireEvent.change(input, { target: { value: "manutencao" } });
    expect(onSearchChange).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(onSearchChange).toHaveBeenCalledWith("manutencao");
  });

  it("renders the typed text straight away", () => {
    renderBar();
    const input = screen.getByLabelText("Buscar tarefas");
    fireEvent.change(input, { target: { value: "elevador" } });
    expect(input).toHaveValue("elevador");
  });

  it("renders one removable chip per active filter", () => {
    renderBar({
      search: "manutencao",
      overdueOnly: true,
      filters: {
        status: TaskStatus.PENDING,
        priority: TaskPriority.HIGH,
        category_id: "cat-1",
        assigned_to_id: "user-1",
      },
    });

    expect(screen.getByText("Situação: Pendente")).toBeInTheDocument();
    expect(screen.getByText("Prioridade: Alta")).toBeInTheDocument();
    expect(screen.getByText("Categoria: Manutenção")).toBeInTheDocument();
    expect(screen.getByText("Responsável: Marta Nogueira")).toBeInTheDocument();
    expect(screen.getByText("“manutencao”")).toBeInTheDocument();
    expect(screen.getByText("Em atraso")).toBeInTheDocument();
  });

  it("renders no chip when nothing is filtered", () => {
    renderBar();
    expect(
      screen.queryByRole("button", { name: /Remover filtro/ }),
    ).not.toBeInTheDocument();
  });

  it("clears only the chip that was removed", () => {
    const onClearFilter = vi.fn();
    renderBar({
      onClearFilter,
      filters: {
        status: TaskStatus.PENDING,
        priority: TaskPriority.HIGH,
        category_id: null,
        assigned_to_id: null,
      },
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Remover filtro: Prioridade: Alta" }),
    );
    expect(onClearFilter).toHaveBeenCalledTimes(1);
    expect(onClearFilter).toHaveBeenCalledWith("priority");
  });

  it("clears the search from its own chip, with no debounce", () => {
    const onSearchChange = vi.fn();
    renderBar({ search: "manutencao", onSearchChange });

    fireEvent.click(
      screen.getByRole("button", { name: "Remover filtro: “manutencao”" }),
    );
    expect(onSearchChange).toHaveBeenCalledWith("");
    expect(screen.getByLabelText("Buscar tarefas")).toHaveValue("");
  });

  it("clears the overdue filter from its own chip", () => {
    const onOverdueToggle = vi.fn();
    renderBar({ overdueOnly: true, onOverdueToggle });

    fireEvent.click(
      screen.getByRole("button", { name: "Remover filtro: Em atraso" }),
    );
    expect(onOverdueToggle).toHaveBeenCalledTimes(1);
  });

  it("falls back to the raw id when a category or user is unknown", () => {
    renderBar({
      categories: [],
      users: [],
      filters: {
        status: null,
        priority: null,
        category_id: "cat-9",
        assigned_to_id: "user-9",
      },
    });
    expect(screen.getByText("Categoria: cat-9")).toBeInTheDocument();
    expect(screen.getByText("Responsável: user-9")).toBeInTheDocument();
  });

  it("offers an overdue counter that toggles the filter", () => {
    const onOverdueToggle = vi.fn();
    renderBar({ overdueCount: 3, onOverdueToggle });

    const counter = screen.getByRole("button", { name: /3 em atraso/ });
    expect(counter).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(counter);
    expect(onOverdueToggle).toHaveBeenCalledTimes(1);
  });

  it("marks the overdue counter as pressed while it filters", () => {
    renderBar({ overdueCount: 3, overdueOnly: true });
    expect(
      screen.getByRole("button", { name: /3 em atraso/ }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("hides the overdue counter when nothing is overdue", () => {
    renderBar({ overdueCount: 0 });
    expect(
      screen.queryByRole("button", { name: /em atraso/ }),
    ).not.toBeInTheDocument();
  });

  it("offers a clear-all control only while something is filtered", () => {
    const onClearAll = vi.fn();
    const { unmount } = renderBar({ onClearAll });
    expect(
      screen.queryByRole("button", { name: "Limpar filtros" }),
    ).not.toBeInTheDocument();
    unmount();

    renderBar({ onClearAll, search: "x" });
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }));
    expect(onClearAll).toHaveBeenCalledTimes(1);
  });

  it("keeps the summary and chips on screen for an empty result", () => {
    renderBar({ visibleCount: 0, search: "elevador panorâmico" });
    expect(screen.getByText("Mostrando 0 de 47 tarefas")).toBeInTheDocument();
    expect(screen.getByText("“elevador panorâmico”")).toBeInTheDocument();
  });

  it("empties the search box when every filter is cleared at once", () => {
    const onClearAll = vi.fn();
    renderBar({ search: "abc", onClearAll });

    const input = screen.getByLabelText("Buscar tarefas");
    expect(input).toHaveValue("abc");

    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }));
    expect(onClearAll).toHaveBeenCalledTimes(1);
    expect(input).toHaveValue("");
  });
});
