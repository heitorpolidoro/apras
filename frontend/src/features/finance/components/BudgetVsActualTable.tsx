import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { BudgetVsActual } from "../../../types/finance";
import { Badge } from "../../../components/ui/badge";
import { CategoryTransactionDrilldown } from "./CategoryTransactionDrilldown";

interface BudgetVsActualTableProps {
  data: BudgetVsActual | undefined;
  isLoading?: boolean;
  fiscalYear: number;
}

const formatCurrency = (value: number): string =>
  value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const BudgetVsActualTable: React.FC<BudgetVsActualTableProps> = ({
  data,
  isLoading = false,
  fiscalYear,
}) => {
  const { t } = useTranslation();
  const [expandedCategoryId, setExpandedCategoryId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        {t("common.loading", "Carregando...")}
      </p>
    );
  }

  const rows = data?.rows ?? [];

  if (rows.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        {t(
          "finance.budgetVsActual.empty",
          "Nenhuma categoria orçamentária para este ano."
        )}
      </p>
    );
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
          <th className="py-2 w-6" />
          <th className="py-2">{t("finance.budgetVsActual.category", "Categoria")}</th>
          <th className="py-2 text-right">
            {t("finance.budgetVsActual.planned", "Orçado")}
          </th>
          <th className="py-2 text-right">
            {t("finance.budgetVsActual.executed", "Executado")}
          </th>
          <th className="py-2 text-right">
            {t("finance.budgetVsActual.variance", "Variação")}
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const isExpanded = expandedCategoryId === row.category_id;
          const isOverBudget =
            row.category_type === "EXPENSE" && row.variance_amount > 0;

          return (
            <React.Fragment key={row.category_id}>
              <tr
                data-testid={`budget-row-${row.category_id}`}
                className="border-t border-slate-100 dark:border-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50"
                onClick={() =>
                  setExpandedCategoryId(isExpanded ? null : row.category_id)
                }
              >
                <td className="py-2 pl-1">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  )}
                </td>
                <td className="py-2 font-medium text-slate-800 dark:text-slate-200">
                  {row.category_name}
                  {isOverBudget && (
                    <Badge variant="inactive" className="ml-2 text-[10px]">
                      {t("finance.budgetVsActual.overBudget", "Estourado")}
                    </Badge>
                  )}
                </td>
                <td className="py-2 text-right">{formatCurrency(row.planned_amount)}</td>
                <td className="py-2 text-right">
                  {formatCurrency(row.executed_amount)}
                </td>
                <td
                  className={`py-2 text-right font-semibold ${
                    row.variance_amount > 0 ? "text-red-600" : "text-emerald-600"
                  }`}
                >
                  {formatCurrency(row.variance_amount)}
                  {row.variance_pct !== null && (
                    <span className="text-xs font-normal text-slate-400 ml-1">
                      ({row.variance_pct.toFixed(1)}%)
                    </span>
                  )}
                </td>
              </tr>
              {isExpanded && (
                <tr>
                  <td colSpan={5} className="bg-slate-50 dark:bg-slate-900/60 px-4 py-3">
                    <CategoryTransactionDrilldown
                      categoryId={row.category_id}
                      fiscalYear={fiscalYear}
                    />
                  </td>
                </tr>
              )}
            </React.Fragment>
          );
        })}
      </tbody>
    </table>
  );
};
