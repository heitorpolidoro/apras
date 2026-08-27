import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, TrendingUp, DollarSign } from 'lucide-react';
import { Badge } from '../../../components/ui/badge';
import { formatCurrency } from '../utils/currency';

interface BudgetVsActualProgressBarProps {
  totalBudget: number;
  executedBudget: number;
}

export const BudgetVsActualProgressBar: React.FC<BudgetVsActualProgressBarProps> = ({
  totalBudget,
  executedBudget,
}) => {
  const { t } = useTranslation();

  const percentage =
    totalBudget > 0 ? Math.min(Math.round((executedBudget / totalBudget) * 100), 999) : 0;
  const isOverBudget = executedBudget > totalBudget;
  const remaining = totalBudget - executedBudget;

  let progressColor = 'bg-emerald-500';
  if (isOverBudget) {
    progressColor = 'bg-red-500';
  } else if (percentage > 80) {
    progressColor = 'bg-amber-500';
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">
            {t('projects.budget.title', 'Acompanhamento Orçamentário')}
          </h3>
        </div>
        {isOverBudget ? (
          <Badge variant="destructive" className="flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            {t('projects.budget.overBudget', 'Orçamento Estourado')} ({percentage}%)
          </Badge>
        ) : (
          <Badge variant="secondary" className="flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
            {percentage}% {t('projects.budget.executionPct', 'Executado')}
          </Badge>
        )}
      </div>

      {/* Progress Track */}
      <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-3 overflow-hidden">
        <div
          data-testid="budget-progress-fill"
          className={`h-full transition-all duration-500 ${progressColor}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>

      {/* Financial Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
        <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {t('projects.budget.total', 'Orçamento Total')}
          </div>
          <div className="text-base font-bold text-slate-800 dark:text-slate-200 mt-0.5">
            {formatCurrency(totalBudget)}
          </div>
        </div>

        <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {t('projects.budget.executed', 'Total Executado')}
          </div>
          <div
            className={`text-base font-bold mt-0.5 ${
              isOverBudget
                ? 'text-red-600 dark:text-red-400'
                : 'text-slate-800 dark:text-slate-200'
            }`}
          >
            {formatCurrency(executedBudget)}
          </div>
        </div>

        <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {t('projects.budget.remaining', 'Saldo Restante')}
          </div>
          <div
            className={`text-base font-bold mt-0.5 ${
              isOverBudget
                ? 'text-red-600 dark:text-red-400'
                : 'text-emerald-600 dark:text-emerald-400'
            }`}
          >
            {formatCurrency(remaining)}
          </div>
        </div>
      </div>
    </div>
  );
};
