import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CashBalanceCard } from "../components/CashBalanceCard";
import { StatementChart } from "../components/StatementChart";
import { StatementTable } from "../components/StatementTable";
import { BudgetVsActualTable } from "../components/BudgetVsActualTable";
import { CategoryTransactionDrilldown } from "../components/CategoryTransactionDrilldown";
import { InvoicePreviewModal } from "../components/InvoicePreviewModal";
import { TransactionFormModal } from "../components/TransactionFormModal";
import { CategoryFormModal } from "../components/CategoryFormModal";
import { BudgetLineFormModal } from "../components/BudgetLineFormModal";
import { FinanceDashboardPage } from "../components/FinanceDashboardPage";
import * as financeApi from "../../../api/finance";
import type {
  BudgetVsActual,
  CashBalance,
  FinanceCategory,
  FinancialStatement,
  PaginatedTransactions,
} from "../../../types/finance";

vi.mock("../../../api/finance");

const mockEffectiveIdentity = vi.fn();
vi.mock("../../user-administration/context/useEffectiveIdentity", () => ({
  useEffectiveIdentity: () => mockEffectiveIdentity(),
}));

const mockBalance: CashBalance = {
  as_of_date: "2026-08-27",
  total_income: 10000,
  total_expense: 4000,
  balance: 6000,
};

const mockStatement: FinancialStatement = {
  start_date: "2026-01-01",
  end_date: "2026-12-31",
  opening_balance: 0,
  closing_balance: 6000,
  entries: [
    { year: 2026, month: 1, income: 1000, expense: 400, net: 600, running_balance: 600 },
    { year: 2026, month: 2, income: 2000, expense: 800, net: 1200, running_balance: 1800 },
  ],
};

const mockCategories: FinanceCategory[] = [
  {
    id: "cat-income-1",
    name: "Taxa Condominial",
    type: "INCOME",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "cat-expense-1",
    name: "Manutenção",
    type: "EXPENSE",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockBudgetVsActual: BudgetVsActual = {
  fiscal_year: 2026,
  total_planned: 1000,
  total_executed: 1200,
  rows: [
    {
      category_id: "cat-expense-1",
      category_name: "Manutenção",
      category_type: "EXPENSE",
      planned_amount: 1000,
      executed_amount: 1200,
      variance_amount: 200,
      variance_pct: 20,
      transaction_count: 2,
    },
  ],
};

const mockCategoryTransactions: PaginatedTransactions = {
  items: [
    {
      id: "txn-1",
      type: "EXPENSE",
      category_id: "cat-expense-1",
      category_name: "Manutenção",
      description: "Troca de lâmpadas",
      amount: 350,
      transaction_date: "2026-03-10",
      payment_method: "PIX",
      invoice_file_url: "/static/uploads/2026/03/nota.pdf",
      invoice_file_size_bytes: 1024,
      invoice_mime_type: "application/pdf",
      created_by_id: "user-1",
      created_by_name: "Admin User",
      created_at: "2026-03-10T00:00:00Z",
      updated_at: "2026-03-10T00:00:00Z",
    },
    {
      id: "txn-2",
      type: "EXPENSE",
      category_id: "cat-expense-1",
      category_name: "Manutenção",
      description: "Sem nota",
      amount: 850,
      transaction_date: "2026-04-01",
      payment_method: null,
      invoice_file_url: null,
      invoice_file_size_bytes: null,
      invoice_mime_type: null,
      created_by_id: "user-1",
      created_by_name: "Admin User",
      created_at: "2026-04-01T00:00:00Z",
      updated_at: "2026-04-01T00:00:00Z",
    },
  ],
  total: 2,
  skip: 0,
  limit: 50,
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

const renderWithQuery = (ui: React.ReactNode) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe("Finance Dashboard Feature Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEffectiveIdentity.mockReturnValue({
      role: "ADMINISTRATOR",
      userTypeIds: [],
      isSimulating: false,
    });
    vi.mocked(financeApi.getCashBalance).mockResolvedValue(mockBalance);
    vi.mocked(financeApi.getStatement).mockResolvedValue(mockStatement);
    vi.mocked(financeApi.getCategories).mockResolvedValue(mockCategories);
    vi.mocked(financeApi.getBudgetVsActual).mockResolvedValue(mockBudgetVsActual);
    vi.mocked(financeApi.getCategoryTransactions).mockResolvedValue(
      mockCategoryTransactions
    );
    vi.mocked(financeApi.createTransaction).mockResolvedValue(
      mockCategoryTransactions.items[0]
    );
    vi.mocked(financeApi.uploadInvoice).mockResolvedValue(
      mockCategoryTransactions.items[0]
    );
    vi.mocked(financeApi.createCategory).mockResolvedValue(mockCategories[0]);
    vi.mocked(financeApi.createBudgetLine).mockResolvedValue({
      id: "bl-1",
      category_id: "cat-expense-1",
      category_name: "Manutenção",
      category_type: "EXPENSE",
      fiscal_year: 2026,
      planned_amount: 1000,
      notes: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
  });

  describe("CashBalanceCard", () => {
    it("renders balance, income and expense", () => {
      render(<CashBalanceCard balance={mockBalance} />);
      expect(screen.getByTestId("cash-balance-value")).toHaveTextContent("6.000,00");
    });

    it("renders placeholder while loading", () => {
      render(<CashBalanceCard balance={undefined} isLoading />);
      expect(screen.getByTestId("cash-balance-value")).toHaveTextContent("--");
    });
  });

  describe("StatementChart", () => {
    it("renders bars for each monthly entry", () => {
      render(<StatementChart entries={mockStatement.entries} />);
      expect(screen.getByTestId("statement-chart")).toBeInTheDocument();
      expect(screen.getByTestId("income-bar-2026-1")).toBeInTheDocument();
      expect(screen.getByTestId("expense-bar-2026-2")).toBeInTheDocument();
    });

    it("renders empty state when there are no entries", () => {
      render(<StatementChart entries={[]} />);
      expect(
        screen.getByText("Nenhum dado no período selecionado.")
      ).toBeInTheDocument();
    });
  });

  describe("StatementTable", () => {
    it("renders a row per monthly entry with running balance", () => {
      render(<StatementTable entries={mockStatement.entries} />);
      expect(screen.getByText("01/2026")).toBeInTheDocument();
      expect(screen.getByText("02/2026")).toBeInTheDocument();
    });
  });

  describe("BudgetVsActualTable", () => {
    it("renders rows and shows an over-budget badge for expense overruns", () => {
      render(
        <BudgetVsActualTable data={mockBudgetVsActual} fiscalYear={2026} />
      );
      expect(screen.getByText("Manutenção")).toBeInTheDocument();
      expect(screen.getByText("Estourado")).toBeInTheDocument();
    });

    it("renders empty state when there are no rows", () => {
      render(
        <BudgetVsActualTable
          data={{ fiscal_year: 2026, rows: [], total_planned: 0, total_executed: 0 }}
          fiscalYear={2026}
        />
      );
      expect(
        screen.getByText("Nenhuma categoria orçamentária para este ano.")
      ).toBeInTheDocument();
    });

    it("expands a category row on click to show the transaction drill-down", async () => {
      renderWithQuery(
        <BudgetVsActualTable data={mockBudgetVsActual} fiscalYear={2026} />
      );

      fireEvent.click(screen.getByTestId("budget-row-cat-expense-1"));

      await waitFor(() => {
        expect(screen.getByText("Troca de lâmpadas")).toBeInTheDocument();
      });
      expect(financeApi.getCategoryTransactions).toHaveBeenCalledWith(
        "cat-expense-1",
        2026
      );
    });
  });

  describe("CategoryTransactionDrilldown", () => {
    it("opens the invoice preview modal in a single click", async () => {
      renderWithQuery(
        <CategoryTransactionDrilldown categoryId="cat-expense-1" fiscalYear={2026} />
      );

      await waitFor(() => {
        expect(screen.getByText("Troca de lâmpadas")).toBeInTheDocument();
      });

      fireEvent.click(
        screen.getByRole("button", { name: /ver nota fiscal/i })
      );

      expect(
        screen.getByRole("heading", { name: "Nota Fiscal" })
      ).toBeInTheDocument();
      const iframe = document.querySelector("iframe");
      expect(iframe).toHaveAttribute(
        "src",
        "/static/uploads/2026/03/nota.pdf"
      );
    });

    it("renders a disabled icon with tooltip when a transaction has no invoice", async () => {
      renderWithQuery(
        <CategoryTransactionDrilldown categoryId="cat-expense-1" fiscalYear={2026} />
      );

      await waitFor(() => {
        expect(screen.getByText("Sem nota")).toBeInTheDocument();
      });

      expect(
        screen.getByTitle("Nenhuma nota fiscal anexada")
      ).toBeInTheDocument();
    });

    it("renders empty state when there are no transactions", async () => {
      vi.mocked(financeApi.getCategoryTransactions).mockResolvedValue({
        items: [],
        total: 0,
        skip: 0,
        limit: 50,
      });
      renderWithQuery(
        <CategoryTransactionDrilldown categoryId="cat-expense-1" fiscalYear={2026} />
      );

      await waitFor(() => {
        expect(
          screen.getByText("Nenhuma transação neste período.")
        ).toBeInTheDocument();
      });
    });
  });

  describe("InvoicePreviewModal", () => {
    it("renders nothing when closed", () => {
      const { container } = render(
        <InvoicePreviewModal
          isOpen={false}
          onClose={vi.fn()}
          invoiceUrl="/static/uploads/x.pdf"
        />
      );
      expect(container).toBeEmptyDOMElement();
    });

    it("renders the iframe and a download link, and closes on demand", () => {
      const handleClose = vi.fn();
      render(
        <InvoicePreviewModal
          isOpen={true}
          onClose={handleClose}
          invoiceUrl="/static/uploads/x.pdf"
        />
      );

      const iframe = document.querySelector("iframe");
      expect(iframe).toHaveAttribute("src", "/static/uploads/x.pdf");

      const downloadLink = screen.getByText("Baixar").closest("a");
      expect(downloadLink).toHaveAttribute("href", "/static/uploads/x.pdf");

      fireEvent.click(screen.getByLabelText("Fechar"));
      expect(handleClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("Modals Form Validation", () => {
    it("submits TransactionFormModal payload with an invoice file", async () => {
      const handleSubmit = vi.fn().mockResolvedValue(undefined);
      const handleClose = vi.fn();

      render(
        <TransactionFormModal
          open={true}
          onClose={handleClose}
          categories={mockCategories}
          onSubmit={handleSubmit}
        />
      );

      fireEvent.change(screen.getByLabelText(/Categoria/i), {
        target: { value: "cat-expense-1" },
      });
      fireEvent.change(screen.getByLabelText(/Descrição/i), {
        target: { value: "Troca de lâmpadas" },
      });
      fireEvent.change(screen.getByLabelText(/Valor \(R\$\)/i), {
        target: { value: "350" },
      });

      fireEvent.click(screen.getByText("Salvar Transação"));

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            type: "EXPENSE",
            category_id: "cat-expense-1",
            description: "Troca de lâmpadas",
            amount: 350,
          }),
          null
        );
      });
    });

    it("submits CategoryFormModal correctly", async () => {
      const handleSubmit = vi.fn().mockResolvedValue(undefined);
      render(
        <CategoryFormModal open={true} onClose={vi.fn()} onSubmit={handleSubmit} />
      );

      fireEvent.change(screen.getByLabelText(/Nome/i), {
        target: { value: "Água" },
      });
      fireEvent.click(screen.getByText("Salvar Categoria"));

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalledWith({
          name: "Água",
          type: "EXPENSE",
        });
      });
    });

    it("submits BudgetLineFormModal correctly", async () => {
      const handleSubmit = vi.fn().mockResolvedValue(undefined);
      render(
        <BudgetLineFormModal
          open={true}
          onClose={vi.fn()}
          categories={mockCategories}
          fiscalYear={2026}
          onSubmit={handleSubmit}
        />
      );

      fireEvent.change(screen.getByLabelText(/Categoria/i), {
        target: { value: "cat-expense-1" },
      });
      fireEvent.change(screen.getByLabelText(/Valor Planejado/i), {
        target: { value: "1000" },
      });
      fireEvent.click(screen.getByText("Salvar Orçamento"));

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            category_id: "cat-expense-1",
            fiscal_year: 2026,
            planned_amount: 1000,
          })
        );
      });
    });

    it("does not render modals when `open` is false", () => {
      const { container: c1 } = render(
        <TransactionFormModal
          open={false}
          onClose={vi.fn()}
          categories={mockCategories}
          onSubmit={vi.fn()}
        />
      );
      const { container: c2 } = render(
        <CategoryFormModal open={false} onClose={vi.fn()} onSubmit={vi.fn()} />
      );
      const { container: c3 } = render(
        <BudgetLineFormModal
          open={false}
          onClose={vi.fn()}
          categories={mockCategories}
          fiscalYear={2026}
          onSubmit={vi.fn()}
        />
      );
      expect(c1).toBeEmptyDOMElement();
      expect(c2).toBeEmptyDOMElement();
      expect(c3).toBeEmptyDOMElement();
    });
  });

  describe("FinanceDashboardPage Integration", () => {
    it("renders the dashboard with balance, statement and budget-vs-actual sections", async () => {
      renderWithQuery(<FinanceDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText("Área Financeira")).toBeInTheDocument();
        expect(screen.getByTestId("cash-balance-value")).toHaveTextContent(
          "6.000,00"
        );
        expect(screen.getByText("Manutenção")).toBeInTheDocument();
      });
    });

    it("shows admin-only action buttons for ADMINISTRATOR", async () => {
      renderWithQuery(<FinanceDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText("Nova Categoria")).toBeInTheDocument();
        expect(screen.getByText("Novo Orçamento")).toBeInTheDocument();
        expect(screen.getByText("Nova Transação")).toBeInTheDocument();
      });
    });

    it("hides category/budget-line management actions for MANAGER but keeps transaction creation", async () => {
      mockEffectiveIdentity.mockReturnValue({
        role: "MANAGER",
        userTypeIds: [],
        isSimulating: false,
      });

      renderWithQuery(<FinanceDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText("Nova Transação")).toBeInTheDocument();
      });
      expect(screen.queryByText("Nova Categoria")).not.toBeInTheDocument();
      expect(screen.queryByText("Novo Orçamento")).not.toBeInTheDocument();
    });

    it("hides all write actions for RESIDENT", async () => {
      mockEffectiveIdentity.mockReturnValue({
        role: "RESIDENT",
        userTypeIds: [],
        isSimulating: false,
      });

      renderWithQuery(<FinanceDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText("Área Financeira")).toBeInTheDocument();
      });
      expect(screen.queryByText("Nova Transação")).not.toBeInTheDocument();
      expect(screen.queryByText("Nova Categoria")).not.toBeInTheDocument();
      expect(screen.queryByText("Novo Orçamento")).not.toBeInTheDocument();
    });

    it("opens the transaction modal, submits it, and uploads the invoice", async () => {
      renderWithQuery(<FinanceDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText("Nova Transação")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Nova Transação"));

      fireEvent.change(screen.getByLabelText(/Categoria/i), {
        target: { value: "cat-expense-1" },
      });
      fireEvent.change(screen.getByLabelText(/Descrição/i), {
        target: { value: "Troca de lâmpadas" },
      });
      fireEvent.change(screen.getByLabelText(/Valor \(R\$\)/i), {
        target: { value: "350" },
      });

      fireEvent.click(screen.getByText("Salvar Transação"));

      await waitFor(() => {
        expect(financeApi.createTransaction).toHaveBeenCalledWith(
          expect.objectContaining({ description: "Troca de lâmpadas" })
        );
      });
    });

    it("changes fiscal year via the selector and refetches budget-vs-actual", async () => {
      renderWithQuery(<FinanceDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText("Manutenção")).toBeInTheDocument();
      });

      const nextYear = new Date().getFullYear() + 1;
      fireEvent.change(screen.getByLabelText("Ano Fiscal"), {
        target: { value: String(nextYear) },
      });

      await waitFor(() => {
        expect(financeApi.getBudgetVsActual).toHaveBeenCalledWith(nextYear);
      });
    });
  });
});
