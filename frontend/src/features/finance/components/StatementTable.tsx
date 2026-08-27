import React from "react";
import { useTranslation } from "react-i18next";
import type { MonthlyStatementEntry } from "../../../types/finance";

interface StatementTableProps {
  entries: MonthlyStatementEntry[];
}

const formatCurrency = (value: number): string =>
  value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const StatementTable: React.FC<StatementTableProps> = ({ entries }) => {
  const { t } = useTranslation();

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
          <th className="py-2">{t("finance.statement.month", "Mês")}</th>
          <th className="py-2 text-right">
            {t("finance.statement.income", "Entradas")}
          </th>
          <th className="py-2 text-right">
            {t("finance.statement.expense", "Saídas")}
          </th>
          <th className="py-2 text-right">{t("finance.statement.net", "Líquido")}</th>
          <th className="py-2 text-right">
            {t("finance.statement.runningBalance", "Saldo Acumulado")}
          </th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr
            key={`${entry.year}-${entry.month}`}
            className="border-b border-slate-100 dark:border-slate-800 last:border-0"
          >
            <td className="py-2 font-medium text-slate-800 dark:text-slate-200">
              {String(entry.month).padStart(2, "0")}/{entry.year}
            </td>
            <td className="py-2 text-right text-emerald-600 dark:text-emerald-400">
              {formatCurrency(entry.income)}
            </td>
            <td className="py-2 text-right text-red-600 dark:text-red-400">
              {formatCurrency(entry.expense)}
            </td>
            <td className="py-2 text-right font-semibold text-slate-800 dark:text-slate-200">
              {formatCurrency(entry.net)}
            </td>
            <td className="py-2 text-right font-semibold text-slate-900 dark:text-slate-100">
              {formatCurrency(entry.running_balance)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
