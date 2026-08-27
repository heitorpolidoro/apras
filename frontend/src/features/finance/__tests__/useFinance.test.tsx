import React from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as financeApi from "../../../api/finance";
import {
  useBudgetLines,
  useBudgetVsActual,
  useCashBalance,
  useCategories,
  useCategoryTransactions,
  useCreateBudgetLine,
  useCreateCategory,
  useCreateTransaction,
  useDeleteBudgetLine,
  useDeleteInvoice,
  useDeleteTransaction,
  useStatement,
  useTransactions,
  useUpdateBudgetLine,
  useUpdateCategory,
  useUpdateTransaction,
  useUploadInvoice,
} from "../../../hooks/useFinance";
import type {
  BudgetLine,
  BudgetVsActual,
  CashBalance,
  FinanceCategory,
  FinancialStatement,
  FinancialTransaction,
  PaginatedTransactions,
} from "../../../types/finance";

vi.mock("../../../api/finance");

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockCategory: FinanceCategory = {
  id: "cat-1",
  name: "Água",
  type: "EXPENSE",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockBudgetLine: BudgetLine = {
  id: "bl-1",
  category_id: "cat-1",
  category_name: "Água",
  category_type: "EXPENSE",
  fiscal_year: 2026,
  planned_amount: 500,
  notes: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockTransaction: FinancialTransaction = {
  id: "txn-1",
  type: "EXPENSE",
  category_id: "cat-1",
  category_name: "Água",
  description: "Conta de água",
  amount: 150,
  transaction_date: "2026-01-15",
  payment_method: "PIX",
  invoice_file_url: null,
  invoice_file_size_bytes: null,
  invoice_mime_type: null,
  created_by_id: "user-1",
  created_by_name: "Admin",
  created_at: "2026-01-15T00:00:00Z",
  updated_at: "2026-01-15T00:00:00Z",
};

const mockPaginated: PaginatedTransactions = {
  items: [mockTransaction],
  total: 1,
  skip: 0,
  limit: 50,
};

const mockBalance: CashBalance = {
  as_of_date: "2026-01-31",
  total_income: 1000,
  total_expense: 500,
  balance: 500,
};

const mockStatement: FinancialStatement = {
  start_date: "2026-01-01",
  end_date: "2026-01-31",
  opening_balance: 0,
  closing_balance: 500,
  entries: [],
};

const mockBudgetVsActual: BudgetVsActual = {
  fiscal_year: 2026,
  rows: [],
  total_planned: 0,
  total_executed: 0,
};

describe("useFinance hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(financeApi.getCategories).mockResolvedValue([mockCategory]);
    vi.mocked(financeApi.getBudgetLines).mockResolvedValue([mockBudgetLine]);
    vi.mocked(financeApi.getTransactions).mockResolvedValue(mockPaginated);
    vi.mocked(financeApi.getCashBalance).mockResolvedValue(mockBalance);
    vi.mocked(financeApi.getStatement).mockResolvedValue(mockStatement);
    vi.mocked(financeApi.getBudgetVsActual).mockResolvedValue(mockBudgetVsActual);
    vi.mocked(financeApi.getCategoryTransactions).mockResolvedValue(mockPaginated);
    vi.mocked(financeApi.createCategory).mockResolvedValue(mockCategory);
    vi.mocked(financeApi.updateCategory).mockResolvedValue(mockCategory);
    vi.mocked(financeApi.createBudgetLine).mockResolvedValue(mockBudgetLine);
    vi.mocked(financeApi.updateBudgetLine).mockResolvedValue(mockBudgetLine);
    vi.mocked(financeApi.deleteBudgetLine).mockResolvedValue(undefined);
    vi.mocked(financeApi.createTransaction).mockResolvedValue(mockTransaction);
    vi.mocked(financeApi.updateTransaction).mockResolvedValue(mockTransaction);
    vi.mocked(financeApi.deleteTransaction).mockResolvedValue(undefined);
    vi.mocked(financeApi.uploadInvoice).mockResolvedValue(mockTransaction);
    vi.mocked(financeApi.deleteInvoice).mockResolvedValue(undefined);
  });

  it("useCategories fetches categories", async () => {
    const { result } = renderHook(() => useCategories(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([mockCategory]);
  });

  it("useBudgetLines fetches budget lines for a fiscal year", async () => {
    const { result } = renderHook(() => useBudgetLines(2026), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(financeApi.getBudgetLines).toHaveBeenCalledWith(2026);
  });

  it("useTransactions fetches paginated transactions", async () => {
    const { result } = renderHook(() => useTransactions({ type: "EXPENSE" }), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total).toBe(1);
  });

  it("useCashBalance fetches the balance", async () => {
    const { result } = renderHook(() => useCashBalance("2026-01-31"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.balance).toBe(500);
  });

  it("useStatement fetches the statement for a date range", async () => {
    const { result } = renderHook(
      () => useStatement("2026-01-01", "2026-01-31"),
      { wrapper }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(financeApi.getStatement).toHaveBeenCalledWith(
      "2026-01-01",
      "2026-01-31"
    );
  });

  it("useBudgetVsActual fetches the budget-vs-actual table", async () => {
    const { result } = renderHook(() => useBudgetVsActual(2026), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(financeApi.getBudgetVsActual).toHaveBeenCalledWith(2026);
  });

  it("useCategoryTransactions fetches the drill-down list", async () => {
    const { result } = renderHook(
      () => useCategoryTransactions("cat-1", 2026),
      { wrapper }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(financeApi.getCategoryTransactions).toHaveBeenCalledWith(
      "cat-1",
      2026
    );
  });

  it("useCategoryTransactions is disabled without a category id", () => {
    const { result } = renderHook(() => useCategoryTransactions(null, 2026), {
      wrapper,
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(financeApi.getCategoryTransactions).not.toHaveBeenCalled();
  });

  it("useCreateCategory creates a category and invalidates the cache", async () => {
    const { result } = renderHook(() => useCreateCategory(), { wrapper });
    await result.current.mutateAsync({ name: "Água", type: "EXPENSE" });
    expect(financeApi.createCategory).toHaveBeenCalledWith({
      name: "Água",
      type: "EXPENSE",
    });
  });

  it("useUpdateCategory updates a category", async () => {
    const { result } = renderHook(() => useUpdateCategory(), { wrapper });
    await result.current.mutateAsync({
      id: "cat-1",
      data: { is_active: false },
    });
    expect(financeApi.updateCategory).toHaveBeenCalledWith("cat-1", {
      is_active: false,
    });
  });

  it("useCreateBudgetLine creates a budget line", async () => {
    const { result } = renderHook(() => useCreateBudgetLine(), { wrapper });
    await result.current.mutateAsync({
      category_id: "cat-1",
      fiscal_year: 2026,
      planned_amount: 500,
    });
    expect(financeApi.createBudgetLine).toHaveBeenCalled();
  });

  it("useUpdateBudgetLine updates a budget line", async () => {
    const { result } = renderHook(() => useUpdateBudgetLine(), { wrapper });
    await result.current.mutateAsync({
      id: "bl-1",
      data: { planned_amount: 600 },
    });
    expect(financeApi.updateBudgetLine).toHaveBeenCalledWith("bl-1", {
      planned_amount: 600,
    });
  });

  it("useDeleteBudgetLine deletes a budget line", async () => {
    const { result } = renderHook(() => useDeleteBudgetLine(), { wrapper });
    await result.current.mutateAsync("bl-1");
    expect(financeApi.deleteBudgetLine).toHaveBeenCalledWith("bl-1");
  });

  it("useCreateTransaction creates a transaction", async () => {
    const { result } = renderHook(() => useCreateTransaction(), { wrapper });
    await result.current.mutateAsync({
      type: "EXPENSE",
      category_id: "cat-1",
      description: "Conta de água",
      amount: 150,
      transaction_date: "2026-01-15",
    });
    expect(financeApi.createTransaction).toHaveBeenCalled();
  });

  it("useUpdateTransaction updates a transaction", async () => {
    const { result } = renderHook(() => useUpdateTransaction(), { wrapper });
    await result.current.mutateAsync({
      id: "txn-1",
      data: { description: "Atualizada" },
    });
    expect(financeApi.updateTransaction).toHaveBeenCalledWith("txn-1", {
      description: "Atualizada",
    });
  });

  it("useDeleteTransaction deletes a transaction", async () => {
    const { result } = renderHook(() => useDeleteTransaction(), { wrapper });
    await result.current.mutateAsync("txn-1");
    expect(financeApi.deleteTransaction).toHaveBeenCalledWith("txn-1");
  });

  it("useUploadInvoice uploads an invoice file", async () => {
    const { result } = renderHook(() => useUploadInvoice(), { wrapper });
    const file = new File(["pdf-bytes"], "nota.pdf", {
      type: "application/pdf",
    });
    await result.current.mutateAsync({ transactionId: "txn-1", file });
    expect(financeApi.uploadInvoice).toHaveBeenCalledWith("txn-1", file);
  });

  it("useDeleteInvoice deletes an invoice", async () => {
    const { result } = renderHook(() => useDeleteInvoice(), { wrapper });
    await result.current.mutateAsync("txn-1");
    expect(financeApi.deleteInvoice).toHaveBeenCalledWith("txn-1");
  });
});
