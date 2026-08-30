import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, Trash2, X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import type {
  PurchaseQuote,
  QuoteExtraField,
  QuoteFormData,
} from "../../../types/purchase";
import { formatCurrency } from "../utils/formatters";

/** Maximum number of extra fields the backend accepts on a quote (APRAS-37). */
export const MAX_EXTRA_FIELDS = 20;

/**
 * The parent remounts this modal with a `key` derived from the quote being
 * edited, so the fields below can be seeded with plain `useState`
 * initialisers instead of a reset effect (react-hooks/set-state-in-effect).
 */
interface QuoteFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  quote: PurchaseQuote | null;
  onSubmit: (data: QuoteFormData) => Promise<void>;
  isLoading?: boolean;
}

export const QuoteFormModal: React.FC<QuoteFormModalProps> = ({
  isOpen,
  onClose,
  quote,
  onSubmit,
  isLoading,
}) => {
  const { t } = useTranslation();

  const [supplierName, setSupplierName] = useState<string>(
    quote?.supplier_name ?? "",
  );
  const [supplierContact, setSupplierContact] = useState<string>(
    quote?.supplier_contact ?? "",
  );
  const [unitPrice, setUnitPrice] = useState<string>(
    String(quote?.unit_price ?? 0),
  );
  const [quantity, setQuantity] = useState<string>(String(quote?.quantity ?? 1));
  const [notes, setNotes] = useState<string>(quote?.notes ?? "");
  const [extraFields, setExtraFields] = useState<QuoteExtraField[]>(() =>
    quote?.extra_fields ? [...quote.extra_fields] : [],
  );
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const parsedUnitPrice = Number(unitPrice);
  const parsedQuantity = Number(quantity);
  const total =
    Number.isFinite(parsedUnitPrice) && Number.isFinite(parsedQuantity)
      ? parsedUnitPrice * parsedQuantity
      : 0;
  const isAtMaxExtraFields = extraFields.length >= MAX_EXTRA_FIELDS;

  const updateExtraField = (
    index: number,
    key: keyof QuoteExtraField,
    value: string,
  ) => {
    setExtraFields((current) =>
      current.map((field, i) => (i === index ? { ...field, [key]: value } : field)),
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!supplierName.trim()) {
      setError(
        t("purchases.quote.supplierNameRequired", "O nome do fornecedor é obrigatório."),
      );
      return;
    }
    if (!Number.isFinite(parsedUnitPrice) || parsedUnitPrice < 0) {
      setError(
        t("purchases.quote.unitPriceInvalid", "O preço unitário não pode ser negativo."),
      );
      return;
    }
    if (!Number.isFinite(parsedQuantity) || parsedQuantity <= 0) {
      setError(
        t("purchases.quote.quantityInvalid", "A quantidade deve ser maior que zero."),
      );
      return;
    }

    const normalized = extraFields.map((field) => ({
      label: field.label.trim(),
      value: field.value.trim(),
    }));
    if (normalized.some((field) => !field.label)) {
      setError(
        t("purchases.extraFields.labelRequired", "Todo campo extra precisa de um rótulo."),
      );
      return;
    }
    const labels = normalized.map((field) => field.label.toLocaleLowerCase());
    if (new Set(labels).size !== labels.length) {
      setError(
        t(
          "purchases.extraFields.duplicateLabel",
          "Há rótulos repetidos entre os campos extras.",
        ),
      );
      return;
    }

    try {
      setError(null);
      await onSubmit({
        supplier_name: supplierName.trim(),
        supplier_contact: supplierContact.trim() || null,
        unit_price: parsedUnitPrice,
        quantity: parsedQuantity,
        notes: notes.trim() || null,
        extra_fields: normalized,
      });
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t("common.genericError", "Erro ao salvar o orçamento."),
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">
            {quote
              ? t("purchases.quote.editTitle", "Editar Orçamento")
              : t("purchases.quote.createTitle", "Novo Orçamento")}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="close">
            <X className="w-5 h-5" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4" data-testid="quote-form">
          {error && (
            <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200">
              {error}
            </div>
          )}

          <div>
            <label
              htmlFor="quote-supplier-name"
              className="block text-xs font-semibold text-gray-700 uppercase mb-1"
            >
              {t("purchases.quote.supplierName", "Fornecedor *")}
            </label>
            <Input
              id="quote-supplier-name"
              value={supplierName}
              onChange={(e) => setSupplierName(e.target.value)}
              placeholder={t(
                "purchases.quote.supplierNamePlaceholder",
                "Ex: Hidráulica Central Ltda",
              )}
            />
          </div>

          <div>
            <label
              htmlFor="quote-supplier-contact"
              className="block text-xs font-semibold text-gray-700 uppercase mb-1"
            >
              {t("purchases.quote.supplierContact", "Contato do fornecedor")}
            </label>
            <Input
              id="quote-supplier-contact"
              value={supplierContact}
              onChange={(e) => setSupplierContact(e.target.value)}
              placeholder={t(
                "purchases.quote.supplierContactPlaceholder",
                "Telefone, e-mail ou vendedor",
              )}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="quote-unit-price"
                className="block text-xs font-semibold text-gray-700 uppercase mb-1"
              >
                {t("purchases.quote.unitPrice", "Preço unitário (R$) *")}
              </label>
              <Input
                id="quote-unit-price"
                type="number"
                min={0}
                step="0.01"
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
              />
            </div>
            <div>
              <label
                htmlFor="quote-quantity"
                className="block text-xs font-semibold text-gray-700 uppercase mb-1"
              >
                {t("purchases.quote.quantity", "Quantidade *")}
              </label>
              <Input
                id="quote-quantity"
                type="number"
                min={1}
                step="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
          </div>

          <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-700 uppercase">
              {t("purchases.quote.total", "Total do orçamento")}
            </span>
            <span
              className="text-lg font-bold text-gray-900"
              data-testid="quote-total"
            >
              {formatCurrency(total)}
            </span>
          </div>

          <div>
            <label
              htmlFor="quote-notes"
              className="block text-xs font-semibold text-gray-700 uppercase mb-1"
            >
              {t("purchases.quote.notes", "Observações do orçamento")}
            </label>
            <Textarea
              id="quote-notes"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t(
                "purchases.quote.notesPlaceholder",
                "Condições de pagamento, validade da proposta...",
              )}
            />
          </div>

          <div className="border-t border-gray-200 pt-4">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-bold text-gray-900">
                {t("purchases.extraFields.title", "Campos extras")}
              </h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isAtMaxExtraFields}
                onClick={() =>
                  setExtraFields((current) => [...current, { label: "", value: "" }])
                }
              >
                <Plus className="w-4 h-4 mr-1" />
                {t("purchases.extraFields.add", "Adicionar campo")}
              </Button>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              {t(
                "purchases.extraFields.hint",
                "Adicione informações livres deste orçamento (até 20 campos).",
              )}
            </p>
            {isAtMaxExtraFields && (
              <p className="text-xs text-amber-600 mb-3">
                {t(
                  "purchases.extraFields.maxReached",
                  "Um orçamento aceita no máximo 20 campos extras.",
                )}
              </p>
            )}

            <div className="space-y-2">
              {extraFields.map((field, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input
                    data-testid={`extra-field-label-${index}`}
                    aria-label={`${t("purchases.extraFields.label", "Rótulo")} ${index + 1}`}
                    value={field.label}
                    onChange={(e) => updateExtraField(index, "label", e.target.value)}
                    placeholder={t(
                      "purchases.extraFields.labelPlaceholder",
                      "Ex: Prazo de entrega",
                    )}
                  />
                  <Input
                    data-testid={`extra-field-value-${index}`}
                    aria-label={`${t("purchases.extraFields.value", "Valor")} ${index + 1}`}
                    value={field.value}
                    onChange={(e) => updateExtraField(index, "value", e.target.value)}
                    placeholder={t(
                      "purchases.extraFields.valuePlaceholder",
                      "Ex: 15 dias",
                    )}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label={t("purchases.extraFields.remove", "Remover campo")}
                    title={t("purchases.extraFields.remove", "Remover campo")}
                    onClick={() =>
                      setExtraFields((current) =>
                        current.filter((_, i) => i !== index),
                      )
                    }
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              {t("purchases.actions.cancel", "Cancelar")}
            </Button>
            <Button type="submit" disabled={isLoading}>
              {t("purchases.quote.submit", "Salvar Orçamento")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default QuoteFormModal;
