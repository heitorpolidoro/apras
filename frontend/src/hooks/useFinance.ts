import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type CategoryFilterParams,
  createBudgetLine,
  createCategory,
  createTransaction,
  deleteBudgetLine,
  deleteInvoice,
  deleteTransaction,
  getBudgetLines,
  getBudgetVsActual,
  getCashBalance,
  getCategories,
  getCategoryTransactions,
  getStatement,
  getTransactions,
  type TransactionFilterParams,
  updateBudgetLine,
  updateCategory,
  updateTransaction,
  uploadInvoice,
} from "../api/finance";
import type {
  BudgetLineCreatePayload,
  BudgetLineUpdatePayload,
  FinanceCategoryCreatePayload,
  FinanceCategoryUpdatePayload,
  FinancialTransactionCreatePayload,
  FinancialTransactionUpdatePayload,
} from "../types/finance";

export const FINANCE_CATEGORIES_QUERY_KEY = ["finance", "categories"];
export const FINANCE_BUDGET_LINES_QUERY_KEY = ["finance", "budget-lines"];
export const FINANCE_TRANSACTIONS_QUERY_KEY = ["finance", "transactions"];
export const FINANCE_BALANCE_QUERY_KEY = ["finance", "balance"];
export const FINANCE_STATEMENT_QUERY_KEY = ["finance", "statement"];
export const FINANCE_BUDGET_VS_ACTUAL_QUERY_KEY = ["finance", "budget-vs-actual"];
export const FINANCE_CATEGORY_TRANSACTIONS_QUERY_KEY = [
  "finance",
  "category-transactions",
];

// -----------------------------------------------------------------------------
// Queries
// -----------------------------------------------------------------------------

export function useCategories(params?: CategoryFilterParams) {
  return useQuery({
    queryKey: [...FINANCE_CATEGORIES_QUERY_KEY, params],
    queryFn: () => getCategories(params),
  });
}

export function useBudgetLines(fiscalYear: number) {
  return useQuery({
    queryKey: [...FINANCE_BUDGET_LINES_QUERY_KEY, fiscalYear],
    queryFn: () => getBudgetLines(fiscalYear),
  });
}

export function useTransactions(filters?: TransactionFilterParams) {
  return useQuery({
    queryKey: [...FINANCE_TRANSACTIONS_QUERY_KEY, filters],
    queryFn: () => getTransactions(filters),
  });
}

export function useCashBalance(asOf?: string) {
  return useQuery({
    queryKey: [...FINANCE_BALANCE_QUERY_KEY, asOf],
    queryFn: () => getCashBalance(asOf),
  });
}

export function useStatement(startDate: string, endDate: string) {
  return useQuery({
    queryKey: [...FINANCE_STATEMENT_QUERY_KEY, startDate, endDate],
    queryFn: () => getStatement(startDate, endDate),
    enabled: Boolean(startDate && endDate),
  });
}

export function useBudgetVsActual(fiscalYear: number) {
  return useQuery({
    queryKey: [...FINANCE_BUDGET_VS_ACTUAL_QUERY_KEY, fiscalYear],
    queryFn: () => getBudgetVsActual(fiscalYear),
  });
}

export function useCategoryTransactions(
  categoryId: string | null,
  fiscalYear: number
) {
  return useQuery({
    queryKey: [...FINANCE_CATEGORY_TRANSACTIONS_QUERY_KEY, categoryId, fiscalYear],
    queryFn: () =>
      categoryId
        ? getCategoryTransactions(categoryId, fiscalYear)
        : Promise.reject(new Error("No category ID")),
    enabled: Boolean(categoryId),
  });
}

// -----------------------------------------------------------------------------
// Mutations: Categories
// -----------------------------------------------------------------------------

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: FinanceCategoryCreatePayload) => createCategory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FINANCE_CATEGORIES_QUERY_KEY });
    },
  });
}

export function useUpdateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: FinanceCategoryUpdatePayload;
    }) => updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FINANCE_CATEGORIES_QUERY_KEY });
    },
  });
}

// -----------------------------------------------------------------------------
// Mutations: Budget Lines
// -----------------------------------------------------------------------------

export function useCreateBudgetLine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BudgetLineCreatePayload) => createBudgetLine(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FINANCE_BUDGET_LINES_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: FINANCE_BUDGET_VS_ACTUAL_QUERY_KEY,
      });
    },
  });
}

export function useUpdateBudgetLine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BudgetLineUpdatePayload }) =>
      updateBudgetLine(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FINANCE_BUDGET_LINES_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: FINANCE_BUDGET_VS_ACTUAL_QUERY_KEY,
      });
    },
  });
}

export function useDeleteBudgetLine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteBudgetLine(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FINANCE_BUDGET_LINES_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: FINANCE_BUDGET_VS_ACTUAL_QUERY_KEY,
      });
    },
  });
}

// -----------------------------------------------------------------------------
// Mutations: Transactions & Invoices
// -----------------------------------------------------------------------------

function invalidateTransactionQueries(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: FINANCE_TRANSACTIONS_QUERY_KEY });
  queryClient.invalidateQueries({ queryKey: FINANCE_BALANCE_QUERY_KEY });
  queryClient.invalidateQueries({ queryKey: FINANCE_STATEMENT_QUERY_KEY });
  queryClient.invalidateQueries({ queryKey: FINANCE_BUDGET_VS_ACTUAL_QUERY_KEY });
  queryClient.invalidateQueries({
    queryKey: FINANCE_CATEGORY_TRANSACTIONS_QUERY_KEY,
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: FinancialTransactionCreatePayload) => createTransaction(data),
    onSuccess: () => invalidateTransactionQueries(queryClient),
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: FinancialTransactionUpdatePayload;
    }) => updateTransaction(id, data),
    onSuccess: () => invalidateTransactionQueries(queryClient),
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteTransaction(id),
    onSuccess: () => invalidateTransactionQueries(queryClient),
  });
}

export function useUploadInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ transactionId, file }: { transactionId: string; file: File }) =>
      uploadInvoice(transactionId, file),
    onSuccess: () => invalidateTransactionQueries(queryClient),
  });
}

export function useDeleteInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (transactionId: string) => deleteInvoice(transactionId),
    onSuccess: () => invalidateTransactionQueries(queryClient),
  });
}
