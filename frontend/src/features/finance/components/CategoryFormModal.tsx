import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import type {
  FinanceCategoryCreatePayload,
  TransactionType,
} from "../../../types/finance";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Select } from "../../../components/ui/select";

interface CategoryFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: FinanceCategoryCreatePayload) => Promise<void>;
}

const CategoryFormInner: React.FC<Omit<CategoryFormModalProps, "open">> = ({
  onClose,
  onSubmit,
}) => {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [type, setType] = useState<TransactionType>("EXPENSE");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    try {
      await onSubmit({ name: name.trim(), type });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 my-8 overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
          {t("finance.categoryModal.title", "Nova Categoria")}
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
          <Label htmlFor="category-name">
            {t("finance.categoryModal.nameLabel", "Nome")} *
          </Label>
          <Input
            id="category-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ex: Água, Manutenção, Taxa Condominial"
            required
          />
        </div>

        <div>
          <Label htmlFor="category-type">
            {t("finance.categoryModal.typeLabel", "Tipo")}
          </Label>
          <Select
            id="category-type"
            value={type}
            onChange={(e) => setType(e.target.value as TransactionType)}
          >
            <option value="INCOME">{t("finance.type.INCOME", "Receita")}</option>
            <option value="EXPENSE">{t("finance.type.EXPENSE", "Despesa")}</option>
          </Select>
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
            {t("finance.categoryModal.save", "Salvar Categoria")}
          </Button>
        </div>
      </form>
    </div>
  );
};

export const CategoryFormModal: React.FC<CategoryFormModalProps> = ({
  open,
  onClose,
  onSubmit,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
      <CategoryFormInner onClose={onClose} onSubmit={onSubmit} />
    </div>
  );
};
