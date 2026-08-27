import React from "react";
import { useTranslation } from "react-i18next";
import type { MonthlyStatementEntry } from "../../../types/finance";

interface StatementChartProps {
  entries: MonthlyStatementEntry[];
}

const MONTH_LABELS = [
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

export const StatementChart: React.FC<StatementChartProps> = ({ entries }) => {
  const { t } = useTranslation();

  const maxValue = Math.max(
    1,
    ...entries.map((e) => Math.max(e.income, e.expense))
  );

  if (entries.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        {t("finance.statement.empty", "Nenhum dado no período selecionado.")}
      </p>
    );
  }

  return (
    <div
      data-testid="statement-chart"
      className="flex items-end gap-3 h-48 overflow-x-auto pb-2"
    >
      {entries.map((entry) => (
        <div
          key={`${entry.year}-${entry.month}`}
          className="flex flex-col items-center gap-1 min-w-[48px]"
        >
          <div className="flex items-end gap-0.5 h-36">
            <div
              data-testid={`income-bar-${entry.year}-${entry.month}`}
              className="w-3 bg-emerald-500 rounded-t-sm"
              style={{ height: `${(entry.income / maxValue) * 100}%` }}
              title={t("finance.statement.income", "Entradas")}
            />
            <div
              data-testid={`expense-bar-${entry.year}-${entry.month}`}
              className="w-3 bg-red-500 rounded-t-sm"
              style={{ height: `${(entry.expense / maxValue) * 100}%` }}
              title={t("finance.statement.expense", "Saídas")}
            />
          </div>
          <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">
            {MONTH_LABELS[entry.month - 1]}/{String(entry.year).slice(-2)}
          </span>
        </div>
      ))}
    </div>
  );
};
