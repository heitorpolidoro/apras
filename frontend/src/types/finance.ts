export type TransactionType = "INCOME" | "EXPENSE";

export interface FinanceCategory {
  id: string;
  name: string;
  type: TransactionType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BudgetLine {
  id: string;
  category_id: string;
  category_name: string;
  category_type: TransactionType;
  fiscal_year: number;
  planned_amount: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialTransaction {
  id: string;
  type: TransactionType;
  category_id: string;
  category_name: string;
  description: string;
  amount: number;
  transaction_date: string;
  payment_method?: string | null;
  invoice_file_url?: string | null;
  invoice_file_size_bytes?: number | null;
  invoice_mime_type?: string | null;
  created_by_id: string;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedTransactions {
  items: FinancialTransaction[];
  total: number;
  skip: number;
  limit: number;
}

export interface CashBalance {
  as_of_date: string;
  total_income: number;
  total_expense: number;
  balance: number;
}

export interface MonthlyStatementEntry {
  year: number;
  month: number;
  income: number;
  expense: number;
  net: number;
  running_balance: number;
}

export interface FinancialStatement {
  start_date: string;
  end_date: string;
  opening_balance: number;
  closing_balance: number;
  entries: MonthlyStatementEntry[];
}

export interface BudgetVsActualRow {
  category_id: string;
  category_name: string;
  category_type: TransactionType;
  planned_amount: number;
  executed_amount: number;
  variance_amount: number;
  variance_pct: number | null;
  transaction_count: number;
}

export interface BudgetVsActual {
  fiscal_year: number;
  rows: BudgetVsActualRow[];
  total_planned: number;
  total_executed: number;
}

export interface FinanceCategoryCreatePayload {
  name: string;
  type: TransactionType;
}

export interface FinanceCategoryUpdatePayload {
  name?: string;
  is_active?: boolean;
}

export interface BudgetLineCreatePayload {
  category_id: string;
  fiscal_year: number;
  planned_amount: number;
  notes?: string | null;
}

export interface BudgetLineUpdatePayload {
  planned_amount?: number;
  notes?: string | null;
}

export interface FinancialTransactionCreatePayload {
  type: TransactionType;
  category_id: string;
  description: string;
  amount: number;
  transaction_date: string;
  payment_method?: string | null;
}

export interface FinancialTransactionUpdatePayload {
  type?: TransactionType;
  category_id?: string;
  description?: string;
  amount?: number;
  transaction_date?: string;
  payment_method?: string | null;
}
