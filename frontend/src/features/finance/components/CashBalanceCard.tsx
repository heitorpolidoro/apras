import React from "react";
import { useTranslation } from "react-i18next";
import { ArrowDownCircle, ArrowUpCircle, Wallet } from "lucide-react";
import type { CashBalance } from "../../../types/finance";

interface CashBalanceCardProps {
  balance: CashBalance | undefined;
  isLoading?: boolean;
}

const formatCurrency = (value: number): string =>
  value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const CashBalanceCard: React.FC<CashBalanceCardProps> = ({
  balance,
  isLoading = false,
}) => {
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex items-center gap-4">
        <div className="w-11 h-11 rounded-lg bg-indigo-50 dark:bg-indigo-950 flex items-center justify-center shrink-0">
          <Wallet className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("finance.balance.current", "Saldo Atual")}
          </p>
          <p
            data-testid="cash-balance-value"
            className="text-xl font-bold text-slate-900 dark:text-slate-100"
          >
            {isLoading || !balance ? "--" : formatCurrency(balance.balance)}
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex items-center gap-4">
        <div className="w-11 h-11 rounded-lg bg-emerald-50 dark:bg-emerald-950 flex items-center justify-center shrink-0">
          <ArrowUpCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("finance.balance.totalIncome", "Total de Entradas")}
          </p>
          <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
            {isLoading || !balance ? "--" : formatCurrency(balance.total_income)}
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex items-center gap-4">
        <div className="w-11 h-11 rounded-lg bg-red-50 dark:bg-red-950 flex items-center justify-center shrink-0">
          <ArrowDownCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("finance.balance.totalExpense", "Total de Saídas")}
          </p>
          <p className="text-xl font-bold text-red-600 dark:text-red-400">
            {isLoading || !balance ? "--" : formatCurrency(balance.total_expense)}
          </p>
        </div>
      </div>
    </div>
  );
};
