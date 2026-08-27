import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import type {
  FinanceCategory,
  FinancialTransactionCreatePayload,
  TransactionType,
} from "../../../types/finance";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Select } from "../../../components/ui/select";

interface TransactionFormModalProps {
  open: boolean;
  onClose: () => void;
  categories: FinanceCategory[];
  onSubmit: (
    payload: FinancialTransactionCreatePayload,
    invoiceFile: File | null
  ) => Promise<void>;
}

const TransactionFormInner: React.FC<
  Omit<TransactionFormModalProps, "open">
> = ({ onClose, categories, onSubmit }) => {
  const { t } = useTranslation();
  const [type, setType] = useState<TransactionType>("EXPENSE");
  const [categoryId, setCategoryId] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState<number | "">("");
  const [transactionDate, setTransactionDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [paymentMethod, setPaymentMethod] = useState("");
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const filteredCategories = categories.filter((c) => c.type === type);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || !description.trim() || !amount) return;

    setIsSubmitting(true);
    try {
      await onSubmit(
        {
          type,
          category_id: categoryId,
          description: description.trim(),
          amount: Number(amount),
          transaction_date: transactionDate,
          payment_method: paymentMethod.trim() || null,
        },
        invoiceFile
      );
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 my-8 overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
          {t("finance.transactionModal.title", "Nova Transação")}
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
          <Label htmlFor="txn-type">
            {t("finance.transactionModal.typeLabel", "Tipo")}
          </Label>
          <Select
            id="txn-type"
            value={type}
            onChange={(e) => {
              setType(e.target.value as TransactionType);
              setCategoryId("");
            }}
          >
            <option value="INCOME">
              {t("finance.type.INCOME", "Receita")}
            </option>
            <option value="EXPENSE">
              {t("finance.type.EXPENSE", "Despesa")}
            </option>
          </Select>
        </div>

        <div>
          <Label htmlFor="txn-category">
            {t("finance.transactionModal.categoryLabel", "Categoria")} *
          </Label>
          <Select
            id="txn-category"
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            required
          >
            <option value="" disabled>
              {t("finance.transactionModal.selectCategory", "Selecione uma categoria")}
            </option>
            {filteredCategories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <Label htmlFor="txn-description">
            {t("finance.transactionModal.descriptionLabel", "Descrição")} *
          </Label>
          <Input
            id="txn-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="txn-amount">
              {t("finance.transactionModal.amountLabel", "Valor (R$)")} *
            </Label>
            <Input
              id="txn-amount"
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) =>
                setAmount(e.target.value === "" ? "" : Number(e.target.value))
              }
              required
            />
          </div>
          <div>
            <Label htmlFor="txn-date">
              {t("finance.transactionModal.dateLabel", "Data")} *
            </Label>
            <Input
              id="txn-date"
              type="date"
              value={transactionDate}
              onChange={(e) => setTransactionDate(e.target.value)}
              required
            />
          </div>
        </div>

        <div>
          <Label htmlFor="txn-payment-method">
            {t("finance.transactionModal.paymentMethodLabel", "Forma de Pagamento")}
          </Label>
          <Input
            id="txn-payment-method"
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            placeholder="PIX, Boleto, Transferência..."
          />
        </div>

        <div>
          <Label htmlFor="txn-invoice">
            {t("finance.transactionModal.invoiceLabel", "Nota Fiscal (PDF)")}
          </Label>
          <input
            id="txn-invoice"
            type="file"
            accept="application/pdf"
            onChange={(e) => setInvoiceFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-600 dark:text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
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
            {t("finance.transactionModal.save", "Salvar Transação")}
          </Button>
        </div>
      </form>
    </div>
  );
};

export const TransactionFormModal: React.FC<TransactionFormModalProps> = ({
  open,
  onClose,
  categories,
  onSubmit,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
      <TransactionFormInner
        onClose={onClose}
        categories={categories}
        onSubmit={onSubmit}
      />
    </div>
  );
};
