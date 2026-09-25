import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { PiggyBank, Plus, Tag, Wallet } from "lucide-react";
import { useEffectivePermissionSet } from "../../user-administration/access/useCanAccess";
import { useBudgetVsActual, useCashBalance, useCategories, useCreateBudgetLine, useCreateCategory, useCreateTransaction, useStatement, useUploadInvoice,  } from "../../../hooks/useFinance";
import { Button } from "../../../components/ui/button";
import { CashBalanceCard } from "./CashBalanceCard";
import { StatementChart } from "./StatementChart";
import { StatementTable } from "./StatementTable";
import { BudgetVsActualTable } from "./BudgetVsActualTable";
import { TransactionFormModal } from "./TransactionFormModal";
import { CategoryFormModal } from "./CategoryFormModal";
import { BudgetLineFormModal } from "./BudgetLineFormModal";

const currentYear = new Date().getFullYear();

export const FinanceDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { has } = useEffectivePermissionSet();

  const canManageCategories =
    has("finance:category_create");
  const canCreateTransaction =
    has("finance:transaction_create");

  const [fiscalYear, setFiscalYear] = useState(currentYear);
  const [transactionModalOpen, setTransactionModalOpen] = useState(false);
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [budgetLineModalOpen, setBudgetLineModalOpen] = useState(false);

  const startDate = `${fiscalYear}-01-01`;
  const endDate = `${fiscalYear}-12-31`;

  const { data: balance, isLoading: isLoadingBalance } = useCashBalance();
  const { data: statement } = useStatement(startDate, endDate);
  const { data: budgetVsActual, isLoading: isLoadingBudget } =
    useBudgetVsActual(fiscalYear);
  const { data: categories = [] } = useCategories();

  const createTransactionMutation = useCreateTransaction();
  const uploadInvoiceMutation = useUploadInvoice();
  const createCategoryMutation = useCreateCategory();
  const createBudgetLineMutation = useCreateBudgetLine();

  const entries = statement?.entries ?? [];

  return (
    <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card p-6 rounded-2xl border border-border shadow-xs">
        <div>
          <div className="flex items-center gap-2.5">
            <Wallet className="w-7 h-7 text-primary" />
            <h1 className="text-2xl font-bold text-foreground">
              {t("finance.pageTitle", "Área Financeira")}
            </h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {t(
              "finance.pageSubtitle",
              "Saldo de caixa, extrato de entradas/saídas e execução orçamentária da associação."
            )}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <label htmlFor="fiscal-year-select" className="sr-only">
            {t("finance.fiscalYear", "Ano Fiscal")}
          </label>
          <select
            id="fiscal-year-select"
            value={fiscalYear}
            onChange={(e) => setFiscalYear(Number(e.target.value))}
            className="rounded-lg border border-input bg-card px-3 py-2 text-sm text-foreground"
          >
            {[currentYear - 1, currentYear, currentYear + 1].map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>

          {canManageCategories && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCategoryModalOpen(true)}
              className="flex items-center gap-1.5"
            >
              <Tag className="w-4 h-4" />
              <span className="hidden sm:inline">
                {t("finance.newCategory", "Nova Categoria")}
              </span>
            </Button>
          )}

          {canManageCategories && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setBudgetLineModalOpen(true)}
              className="flex items-center gap-1.5"
            >
              <PiggyBank className="w-4 h-4" />
              <span className="hidden sm:inline">
                {t("finance.newBudgetLine", "Novo Orçamento")}
              </span>
            </Button>
          )}

          {canCreateTransaction && (
            <Button
              onClick={() => setTransactionModalOpen(true)}
              className="flex items-center gap-1.5 bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              <Plus className="w-4 h-4" />
              <span>{t("finance.newTransaction", "Nova Transação")}</span>
            </Button>
          )}
        </div>
      </div>

      <CashBalanceCard balance={balance} isLoading={isLoadingBalance} />

      <div className="bg-card border border-border rounded-xl p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-foreground">
          {t("finance.statement.title", "Extrato de Entradas e Saídas")}
        </h2>
        <StatementChart entries={entries} />
        <StatementTable entries={entries} />
      </div>

      <div className="bg-card border border-border rounded-xl p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-foreground">
          {t("finance.budgetVsActual.title", "Orçado vs. Executado")}
        </h2>
        <BudgetVsActualTable
          data={budgetVsActual}
          isLoading={isLoadingBudget}
          fiscalYear={fiscalYear}
        />
      </div>

      <TransactionFormModal
        open={transactionModalOpen}
        onClose={() => setTransactionModalOpen(false)}
        categories={categories.filter((c) => c.is_active)}
        onSubmit={async (payload, invoiceFile) => {
          const created = await createTransactionMutation.mutateAsync(payload);
          if (invoiceFile) {
            await uploadInvoiceMutation.mutateAsync({
              transactionId: created.id,
              file: invoiceFile,
            });
          }
        }}
      />

      <CategoryFormModal
        open={categoryModalOpen}
        onClose={() => setCategoryModalOpen(false)}
        onSubmit={async (payload) => {
          await createCategoryMutation.mutateAsync(payload);
        }}
      />

      <BudgetLineFormModal
        open={budgetLineModalOpen}
        onClose={() => setBudgetLineModalOpen(false)}
        categories={categories.filter((c) => c.is_active)}
        fiscalYear={fiscalYear}
        onSubmit={async (payload) => {
          await createBudgetLineMutation.mutateAsync(payload);
        }}
      />
    </div>
  );
};
