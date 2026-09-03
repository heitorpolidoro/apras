import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import AuditTimeline from "../AuditTimeline";
import { useTaskHistory } from "../../hooks/useTasks";
import { useTranslation } from "react-i18next";
import ptData from "../../../../i18n/locales/pt.json";

type MockTaskHistory = ReturnType<typeof useTaskHistory>;
type MockUseTranslation = ReturnType<typeof useTranslation>;

// Mock hooks
vi.mock("../../hooks/useTasks", () => ({
  useTaskHistory: vi.fn(),
}));

describe("AuditTimeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset to default mock from setup.ts if it was overridden
    vi.mocked(useTranslation).mockReturnValue({
      t: (key: string, options?: any) => {
        const keys = key.split(".");
        let value: any = ptData;
        for (const k of keys) {
          value = value?.[k];
        }
        if (typeof value === "string" && options) {
          Object.keys(options).forEach((k) => {
            value = value.replace(`{{${k}}}`, options[k]);
          });
        }
        return value || key;
      },
      i18n: { language: "pt", changeLanguage: vi.fn() },
    } as unknown as MockUseTranslation);
  });

  it("renders loading state", () => {
    vi.mocked(useTaskHistory).mockReturnValue({
      isLoading: true,
      error: null,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);
    expect(screen.getByText(/Carregando histórico.../i)).toBeInTheDocument();
  });

  it("renders error state", () => {
    vi.mocked(useTaskHistory).mockReturnValue({
      isLoading: false,
      error: new Error("Fetch error"),
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);
    expect(
      screen.getByText(/Erro ao carregar histórico./i),
    ).toBeInTheDocument();
  });

  it("renders empty state when no history is returned", () => {
    vi.mocked(useTaskHistory).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    expect(
      screen.getByText(/Nenhuma alteração registrada ainda./i),
    ).toBeInTheDocument();
  });

  it("renders a list of history entries correctly", () => {
    const mockHistory = [
      {
        id: 1,
        task_id: "test-id",
        user_id: "user-1",
        user_name: "John Doe",
        field_name: "status",
        old_value: "PENDING",
        new_value: "IN_PROGRESS",
        timestamp: "2023-10-27T10:00:00Z",
        resolved_old_value: null,
        resolved_new_value: null,
      },
    ];

    vi.mocked(useTaskHistory).mockReturnValue({
      data: mockHistory,
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("status")).toBeInTheDocument();
    expect(screen.getByText("PENDING")).toBeInTheDocument();
    expect(screen.getByText("IN_PROGRESS")).toBeInTheDocument();
  });

  it('formats null values as "Nenhum"', () => {
    const mockHistory = [
      {
        id: 1,
        task_id: "test-id",
        user_id: "user-1",
        user_name: "John Doe",
        field_name: "description",
        old_value: null,
        new_value: "New description",
        timestamp: "2023-10-27T09:00:00Z",
        resolved_old_value: null,
        resolved_new_value: null,
      },
    ];

    vi.mocked(useTaskHistory).mockReturnValue({
      data: mockHistory,
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    expect(screen.getAllByText("Nenhum").length).toBeGreaterThan(0);
    expect(screen.getByText("New description")).toBeInTheDocument();
  });

  it('formats empty string values as "Vazio"', () => {
    const mockHistory = [
      {
        id: 1,
        task_id: "test-id",
        user_id: "user-1",
        user_name: "John Doe",
        field_name: "description",
        old_value: "Old",
        new_value: "",
        timestamp: "2023-10-27T10:00:00Z",
        resolved_old_value: null,
        resolved_new_value: null,
      },
    ];

    vi.mocked(useTaskHistory).mockReturnValue({
      data: mockHistory,
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    expect(screen.getByText("Vazio")).toBeInTheDocument();
  });

  it("renders in English when language is not pt", () => {
    vi.mocked(useTranslation).mockReturnValue({
      t: (s: string) => s,
      i18n: { language: "en" },
    } as unknown as MockUseTranslation);

    const mockHistory = [
      {
        id: 1,
        task_id: "test-id",
        user_id: "user-1",
        user_name: "John Doe",
        field_name: "task_title",
        old_value: "Old",
        new_value: "New",
        timestamp: "2023-10-27T10:00:00Z",
        resolved_old_value: null,
        resolved_new_value: null,
      },
    ];

    vi.mocked(useTaskHistory).mockReturnValue({
      data: mockHistory,
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    const toggleBtn = screen.getByRole("button", {
      name: /tasks.audit.title/i,
    });
    fireEvent.click(toggleBtn);

    // Check English date format (Oct 27, 2023)
    expect(screen.getByText(/Oct 27, 2023/)).toBeInTheDocument();
    // Check field name formatting (task title)
    expect(screen.getByText("task title")).toBeInTheDocument();
  });

  it('formats "null" string as "Nenhum"', () => {
    const mockHistory = [
      {
        id: 1,
        task_id: "test-id",
        user_id: "user-1",
        user_name: "John Doe",
        field_name: "description",
        old_value: "null",
        new_value: "New description",
        timestamp: "2023-10-27T09:00:00Z",
        resolved_old_value: null,
        resolved_new_value: null,
      },
    ];

    vi.mocked(useTaskHistory).mockReturnValue({
      data: mockHistory,
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    expect(screen.getAllByText("Nenhum").length).toBeGreaterThan(0);
  });

  it("formatFieldName handles empty string field_name gracefully", () => {
    vi.mocked(useTaskHistory).mockReturnValue({
      data: [
        {
          id: 1,
          task_id: "test-id",
          user_id: "user-1",
          user_name: "John Doe",
          field_name: "",
          old_value: "old",
          new_value: "new",
          timestamp: "2023-10-27T10:00:00Z",
          resolved_old_value: null,
          resolved_new_value: null,
        },
      ],
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("is collapsed by default — entries not visible", () => {
    vi.mocked(useTaskHistory).mockReturnValue({
      data: [
        {
          id: "1",
          task_id: "test-id",
          user_name: "John Doe",
          field_name: "status",
          old_value: "PENDING",
          new_value: "IN_PROGRESS",
          timestamp: "2023-10-27T10:00:00Z",
          changed_by_id: "user-1",
          resolved_old_value: null,
          resolved_new_value: null,
        },
      ],
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    expect(screen.queryByText("John Doe")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /histórico de alterações/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("(1)")).toBeInTheDocument();
  });

  it("expands when toggle button is clicked", () => {
    vi.mocked(useTaskHistory).mockReturnValue({
      data: [
        {
          id: "1",
          task_id: "test-id",
          user_name: "Jane Smith",
          field_name: "status",
          old_value: "PENDING",
          new_value: "IN_PROGRESS",
          timestamp: "2023-10-27T10:00:00Z",
          changed_by_id: "user-1",
          resolved_old_value: null,
          resolved_new_value: null,
        },
      ],
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
  });

  it("renders when history data is undefined (count defaults to 0)", () => {
    // Covers the `history?.length ?? 0` fallback branch (line 56)
    vi.mocked(useTaskHistory).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);

    // Button renders with no count badge (count === 0)
    expect(
      screen.getByRole("button", { name: /histórico de alterações/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/\(\d+\)/)).not.toBeInTheDocument();
  });

  it("falls back to raw new_value when resolved_new_value is null for assigned_to_id", () => {
    // Covers the `entry.new_value` branch of the ternary on line 38
    vi.mocked(useTaskHistory).mockReturnValue({
      data: [
        {
          id: "3",
          task_id: "test-id",
          user_name: "Admin",
          field_name: "assigned_to_id",
          old_value: null,
          new_value: "ghost-uuid",
          timestamp: "2023-10-27T10:00:00Z",
          changed_by_id: "admin-1",
          resolved_old_value: null,
          resolved_new_value: null,
        },
      ],
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);
    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    // Both resolved values are null → falls back to raw value display
    expect(screen.getByText("ghost-uuid")).toBeInTheDocument();
  });

  it("displays resolved name and role for assigned_to_id entries", () => {
    vi.mocked(useTaskHistory).mockReturnValue({
      data: [
        {
          id: "2",
          task_id: "test-id",
          user_name: "Admin User",
          field_name: "assigned_to_id",
          old_value: null,
          new_value: "some-uuid",
          timestamp: "2023-10-27T10:00:00Z",
          changed_by_id: "admin-1",
          resolved_old_value: null,
          resolved_new_value: { name: "João Silva", roles: ["Diretor (papel)"] },
        },
      ],
      isLoading: false,
    } as unknown as MockTaskHistory);

    render(<AuditTimeline taskId="test-id" />);
    const toggleBtn = screen.getByRole("button", {
      name: /histórico de alterações/i,
    });
    fireEvent.click(toggleBtn);

    // Should show "João Silva (Diretor (papel))" -- the role **names**
    // since IAM F5 (§8.2) -- and not the raw UUID.
    expect(screen.getByText(/João Silva/)).toBeInTheDocument();
    expect(screen.getByText(/Diretor/)).toBeInTheDocument();
    expect(screen.queryByText("some-uuid")).not.toBeInTheDocument();
  });
});
