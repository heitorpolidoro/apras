import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import type {
  BudgetLineCreatePayload,
  FinanceCategory,
} from "../../../types/finance";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Select } from "../../../components/ui/select";
import { Textarea } from "../../../components/ui/textarea";

interface BudgetLineFormModalProps {
  open: boolean;
  onClose: () => void;
  categories: FinanceCategory[];
  fiscalYear: number;
  onSubmit: (payload: BudgetLineCreatePayload) => Promise<void>;
}

const BudgetLineFormInner: React.FC<
  Omit<BudgetLineFormModalProps, "open">
> = ({ onClose, categories, fiscalYear, onSubmit }) => {
  const { t } = useTranslation();
  const [categoryId, setCategoryId] = useState("");
  const [year, setYear] = useState<number>(fiscalYear);
  const [plannedAmount, setPlannedAmount] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || plannedAmount === "") return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        category_id: categoryId,
        fiscal_year: year,
        planned_amount: Number(plannedAmount),
        notes: notes.trim() || null,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 my-8 overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
          {t("finance.budgetLineModal.title", "Novo Orçamento")}
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-4">
        <div>
          <Label htmlFor="budget-category">
            {t("finance.budgetLineModal.categoryLabel", "Categoria")} *
          </Label>
          <Select
            id="budget-category"
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            required
          >
            <option value="" disabled>
              {t(
                "finance.transactionModal.selectCategory",
                "Selecione uma categoria"
              )}
            </option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="budget-year">
              {t("finance.budgetLineModal.yearLabel", "Ano Fiscal")} *
            </Label>
            <Input
              id="budget-year"
              type="number"
              min={2000}
              max={2100}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              required
            />
          </div>
          <div>
            <Label htmlFor="budget-amount">
              {t("finance.budgetLineModal.amountLabel", "Valor Planejado (R$)")} *
            </Label>
            <Input
              id="budget-amount"
              type="number"
              min="0"
              step="0.01"
              value={plannedAmount}
              onChange={(e) =>
                setPlannedAmount(
                  e.target.value === "" ? "" : Number(e.target.value)
                )
              }
              required
            />
          </div>
        </div>

        <div>
          <Label htmlFor="budget-notes">
            {t("finance.budgetLineModal.notesLabel", "Observações")}
          </Label>
          <Textarea
            id="budget-notes"
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isSubmitting}
          >
            {t("common.cancel", "Cancelar")}
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {t("finance.budgetLineModal.save", "Salvar Orçamento")}
          </Button>
        </div>
      </form>
    </div>
  );
};

export const BudgetLineFormModal: React.FC<BudgetLineFormModalProps> = ({
  open,
  onClose,
  categories,
  fiscalYear,
  onSubmit,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
      <BudgetLineFormInner
        onClose={onClose}
        categories={categories}
        fiscalYear={fiscalYear}
        onSubmit={onSubmit}
      />
    </div>
  );
};
