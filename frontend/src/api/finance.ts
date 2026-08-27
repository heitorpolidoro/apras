import apiClient from "./client";
import type {
  BudgetLine,
  BudgetLineCreatePayload,
  BudgetLineUpdatePayload,
  BudgetVsActual,
  CashBalance,
  FinanceCategory,
  FinanceCategoryCreatePayload,
  FinanceCategoryUpdatePayload,
  FinancialStatement,
  FinancialTransaction,
  FinancialTransactionCreatePayload,
  FinancialTransactionUpdatePayload,
  PaginatedTransactions,
  TransactionType,
} from "../types/finance";

// -----------------------------------------------------------------------------
// Categories
// -----------------------------------------------------------------------------

export interface CategoryFilterParams {
  type?: TransactionType;
  include_inactive?: boolean;
}

export const getCategories = async (
  params?: CategoryFilterParams
): Promise<FinanceCategory[]> => {
  const response = await apiClient.get<FinanceCategory[]>("/finance/categories", {
    params,
  });
  return response.data;
};

export const createCategory = async (
  data: FinanceCategoryCreatePayload
): Promise<FinanceCategory> => {
  const response = await apiClient.post<FinanceCategory>("/finance/categories", data);
  return response.data;
};

export const updateCategory = async (
  id: string,
  data: FinanceCategoryUpdatePayload
): Promise<FinanceCategory> => {
  const response = await apiClient.put<FinanceCategory>(
    `/finance/categories/${id}`,
    data
  );
  return response.data;
};

// -----------------------------------------------------------------------------
// Budget Lines
// -----------------------------------------------------------------------------

export const getBudgetLines = async (fiscalYear: number): Promise<BudgetLine[]> => {
  const response = await apiClient.get<BudgetLine[]>("/finance/budget-lines", {
    params: { fiscal_year: fiscalYear },
  });
  return response.data;
};

export const createBudgetLine = async (
  data: BudgetLineCreatePayload
): Promise<BudgetLine> => {
  const response = await apiClient.post<BudgetLine>("/finance/budget-lines", data);
  return response.data;
};

export const updateBudgetLine = async (
  id: string,
  data: BudgetLineUpdatePayload
): Promise<BudgetLine> => {
  const response = await apiClient.put<BudgetLine>(
    `/finance/budget-lines/${id}`,
    data
  );
  return response.data;
};

export const deleteBudgetLine = async (id: string): Promise<void> => {
  await apiClient.delete(`/finance/budget-lines/${id}`);
};

// -----------------------------------------------------------------------------
// Transactions
// -----------------------------------------------------------------------------

export interface TransactionFilterParams {
  type?: TransactionType;
  category_id?: string;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
}

export const getTransactions = async (
  params?: TransactionFilterParams
): Promise<PaginatedTransactions> => {
  const response = await apiClient.get<PaginatedTransactions>("/finance/transactions", {
    params,
  });
  return response.data;
};

export const getTransactionById = async (id: string): Promise<FinancialTransaction> => {
  const response = await apiClient.get<FinancialTransaction>(
    `/finance/transactions/${id}`
  );
  return response.data;
};

export const createTransaction = async (
  data: FinancialTransactionCreatePayload
): Promise<FinancialTransaction> => {
  const response = await apiClient.post<FinancialTransaction>(
    "/finance/transactions",
    data
  );
  return response.data;
};

export const updateTransaction = async (
  id: string,
  data: FinancialTransactionUpdatePayload
): Promise<FinancialTransaction> => {
  const response = await apiClient.put<FinancialTransaction>(
    `/finance/transactions/${id}`,
    data
  );
  return response.data;
};

export const deleteTransaction = async (id: string): Promise<void> => {
  await apiClient.delete(`/finance/transactions/${id}`);
};

export const uploadInvoice = async (
  transactionId: string,
  file: File
): Promise<FinancialTransaction> => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<FinancialTransaction>(
    `/finance/transactions/${transactionId}/invoice`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
};

export const deleteInvoice = async (transactionId: string): Promise<void> => {
  await apiClient.delete(`/finance/transactions/${transactionId}/invoice`);
};

// -----------------------------------------------------------------------------
// Reporting
// -----------------------------------------------------------------------------

export const getCashBalance = async (asOf?: string): Promise<CashBalance> => {
  const response = await apiClient.get<CashBalance>("/finance/balance", {
    params: asOf ? { as_of: asOf } : undefined,
  });
  return response.data;
};

export const getStatement = async (
  startDate: string,
  endDate: string
): Promise<FinancialStatement> => {
  const response = await apiClient.get<FinancialStatement>("/finance/statement", {
    params: { start_date: startDate, end_date: endDate },
  });
  return response.data;
};

export const getBudgetVsActual = async (fiscalYear: number): Promise<BudgetVsActual> => {
  const response = await apiClient.get<BudgetVsActual>("/finance/budget-vs-actual", {
    params: { fiscal_year: fiscalYear },
  });
  return response.data;
};

export const getCategoryTransactions = async (
  categoryId: string,
  fiscalYear: number,
  params?: { skip?: number; limit?: number }
): Promise<PaginatedTransactions> => {
  const response = await apiClient.get<PaginatedTransactions>(
    `/finance/budget-vs-actual/${categoryId}/transactions`,
    { params: { fiscal_year: fiscalYear, ...params } }
  );
  return response.data;
};
