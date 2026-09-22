import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { limitDecimals, MONEY_DECIMALS } from "../../../lib/money";
import { Plus, Trash2, X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import type {
  PurchaseQuote,
  PurchaseQuoteItemInput,
  PurchaseRequestItem,
  QuoteExtraField,
  QuoteFormData,
} from "../../../types/purchase";
import { formatCurrency } from "../utils/formatters";

/** Maximum number of extra fields the backend accepts on a quote (APRAS-37). */
export const MAX_EXTRA_FIELDS = 20;

/** Maximum number of priced lines the backend accepts (APRAS-73 D6). */
export const MAX_QUOTE_ITEMS = 50;

/**
 * What the supplier filled in for one request line. Both halves are
 * skippable: a row the supplier left blank sends **no item at all** (D5), so
 * "did not quote" and "quoted zero" stay different facts all the way down.
 */
interface PricedRow {
  model: string;
  unitPrice: string;
}

/** A line the supplier added that the request never asked for (D3). */
interface ExtraRow {
  description: string;
  quantity: string;
  model: string;
  unitPrice: string;
}

const EMPTY_ROW: PricedRow = { model: "", unitPrice: "" };

/** A row counts as priced once it carries a usable, non-negative number. */
const isPriced = (row: PricedRow): boolean => {
  const trimmed = row.unitPrice.trim();
  if (trimmed === "") return false;
  const value = Number(trimmed);
  return Number.isFinite(value) && value >= 0;
};

const toNumber = (value: string): number => {
  const parsed = Number(value.trim());
  return Number.isFinite(parsed) ? parsed : 0;
};

/**
 * The parent remounts this modal with a `key` derived from the quote being
 * edited, so the fields below can be seeded with plain `useState`
 * initialisers instead of a reset effect (react-hooks/set-state-in-effect).
 */
interface QuoteFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  quote: PurchaseQuote | null;
  /** The lines the request enumerates: one fixed row each, in order. */
  requestItems: PurchaseRequestItem[];
  onSubmit: (data: QuoteFormData) => Promise<void>;
  isLoading?: boolean;
}

export const QuoteFormModal: React.FC<QuoteFormModalProps> = ({
  isOpen,
  onClose,
  quote,
  requestItems,
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
  const [priced, setPriced] = useState<Record<string, PricedRow>>(() =>
    Object.fromEntries(
      requestItems.map((item) => {
        const line = quote?.items.find(
          (candidate) => candidate.request_item_id === item.id,
        );
        return [
          item.id,
          line
            ? { model: line.model ?? "", unitPrice: String(line.unit_price) }
            : { ...EMPTY_ROW },
        ];
      }),
    ),
  );
  const [extras, setExtras] = useState<ExtraRow[]>(() =>
    (quote?.items ?? [])
      .filter((line) => line.request_item_id === null)
      .map((line) => ({
        description: line.description,
        quantity: String(line.quantity),
        model: line.model ?? "",
        unitPrice: String(line.unit_price),
      })),
  );
  const [notes, setNotes] = useState<string>(quote?.notes ?? "");
  const [extraFields, setExtraFields] = useState<QuoteExtraField[]>(() =>
    quote?.extra_fields ? [...quote.extra_fields] : [],
  );
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const isAtMaxExtraFields = extraFields.length >= MAX_EXTRA_FIELDS;
  const lineCount =
    requestItems.filter((item) => isPriced(priced[item.id] ?? EMPTY_ROW)).length +
    extras.length;
  const isAtMaxItems = lineCount >= MAX_QUOTE_ITEMS;

  const requestLineTotal = (item: PurchaseRequestItem): number => {
    const row = priced[item.id] ?? EMPTY_ROW;
    return isPriced(row) ? toNumber(row.unitPrice) * item.quantity : 0;
  };
  const extraLineTotal = (row: ExtraRow): number =>
    toNumber(row.unitPrice) * toNumber(row.quantity);

  const total =
    requestItems.reduce((sum, item) => sum + requestLineTotal(item), 0) +
    extras.reduce((sum, row) => sum + extraLineTotal(row), 0);

  const updatePriced = (id: string, key: keyof PricedRow, value: string) => {
    setPriced((current) => ({
      ...current,
      [id]: { ...(current[id] ?? EMPTY_ROW), [key]: value },
    }));
  };

  const updateExtra = (index: number, key: keyof ExtraRow, value: string) => {
    setExtras((current) =>
      current.map((row, i) => (i === index ? { ...row, [key]: value } : row)),
    );
  };

  const updateExtraField = (
    index: number,
    key: keyof QuoteExtraField,
    value: string,
  ) => {
    setExtraFields((current) =>
      current.map((field, i) => (i === index ? { ...field, [key]: value } : field)),
    );
  };

  const collectItems = (): PurchaseQuoteItemInput[] | string => {
    const items: PurchaseQuoteItemInput[] = [];
    for (const item of requestItems) {
      const row = priced[item.id] ?? EMPTY_ROW;
      if (!isPriced(row)) continue;
      items.push({
        request_item_id: item.id,
        model: row.model.trim() || null,
        unit_price: toNumber(row.unitPrice),
      });
    }
    for (const row of extras) {
      const description = row.description.trim();
      const quantity = toNumber(row.quantity);
      if (!description) {
        return t(
          "purchases.items.descriptionRequired",
          "Todo item avulso precisa de uma descrição.",
        );
      }
      if (!Number.isInteger(quantity) || quantity <= 0) {
        return t(
          "purchases.quote.quantityInvalid",
          "A quantidade deve ser maior que zero.",
        );
      }
      if (!isPriced(row)) {
        return t(
          "purchases.quote.unitPriceInvalid",
          "O preço unitário não pode ser negativo.",
        );
      }
      items.push({
        description,
        quantity,
        model: row.model.trim() || null,
        unit_price: toNumber(row.unitPrice),
      });
    }
    if (items.length === 0) {
      return t(
        "purchases.items.atLeastOne",
        "Informe o preço de ao menos um item para salvar o orçamento.",
      );
    }
    return items;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!supplierName.trim()) {
      setError(
        t("purchases.quote.supplierNameRequired", "O nome do fornecedor é obrigatório."),
      );
      return;
    }

    const items = collectItems();
    if (typeof items === "string") {
      setError(items);
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
        items,
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

          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-bold text-gray-900">
              {t("purchases.items.quoteTitle", "Itens do pedido")}
            </h3>
            <p className="text-xs text-gray-500 mb-3">
              {t(
                "purchases.items.quoteHint",
                "Preencha o preço dos itens que este fornecedor cota. Deixe em branco o que ele não atende — não será somado.",
              )}
            </p>

            {requestItems.length === 0 && (
              <p className="text-xs text-gray-500 mb-3" data-testid="no-request-items">
                {t(
                  "purchases.items.requestHasNone",
                  "Este pedido não enumerou itens. Adicione abaixo o que o fornecedor está cotando.",
                )}
              </p>
            )}

            <div className="space-y-2">
              {requestItems.map((item) => {
                const row = priced[item.id] ?? EMPTY_ROW;
                return (
                  <div
                    key={item.id}
                    data-testid={`quote-line-${item.id}`}
                    className="rounded-lg border border-gray-200 p-3"
                  >
                    <div className="text-xs font-semibold text-gray-700 mb-2">
                      {item.quantity} × {item.description}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        data-testid={`quote-line-model-${item.id}`}
                        aria-label={`${t("purchases.items.model", "Modelo ofertado")} ${item.description}`}
                        value={row.model}
                        onChange={(e) => updatePriced(item.id, "model", e.target.value)}
                        placeholder={t(
                          "purchases.items.modelPlaceholder",
                          "Modelo ofertado (opcional)",
                        )}
                      />
                      <Input
                        data-testid={`quote-line-price-${item.id}`}
                        aria-label={`${t("purchases.items.unitPrice", "Preço unitário")} ${item.description}`}
                        type="number"
                        min={0}
                        step="0.01"
                        inputMode="decimal"
                        value={row.unitPrice}
                        onChange={(e) =>
                          updatePriced(
                            item.id,
                            "unitPrice",
                            limitDecimals(e.target.value, MONEY_DECIMALS),
                          )
                        }
                        placeholder={t("purchases.items.unitPrice", "Preço unitário")}
                      />
                    </div>
                    <div
                      className="mt-2 text-right text-xs text-gray-600"
                      data-testid={`quote-line-total-${item.id}`}
                    >
                      {isPriced(row)
                        ? formatCurrency(requestLineTotal(item))
                        : t("purchases.items.notQuoted", "Não cotado")}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between mt-4 mb-1">
              <h4 className="text-xs font-semibold text-gray-700 uppercase">
                {t("purchases.items.extraTitle", "Itens avulsos do fornecedor")}
              </h4>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isAtMaxItems}
                onClick={() =>
                  setExtras((current) => [
                    ...current,
                    { description: "", quantity: "1", model: "", unitPrice: "" },
                  ])
                }
              >
                <Plus className="w-4 h-4 mr-1" />
                {t("purchases.items.addExtra", "Adicionar item")}
              </Button>
            </div>

            <div className="space-y-2">
              {extras.map((row, index) => (
                <div
                  key={index}
                  data-testid={`quote-extra-${index}`}
                  className="rounded-lg border border-dashed border-gray-300 p-3"
                >
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      data-testid={`quote-extra-description-${index}`}
                      aria-label={`${t("purchases.items.description", "Descrição")} ${index + 1}`}
                      value={row.description}
                      onChange={(e) =>
                        updateExtra(index, "description", e.target.value)
                      }
                      placeholder={t(
                        "purchases.items.descriptionPlaceholder",
                        "Ex: Nobreak 1,2 kVA",
                      )}
                    />
                    <Input
                      data-testid={`quote-extra-quantity-${index}`}
                      aria-label={`${t("purchases.items.quantity", "Quantidade")} ${index + 1}`}
                      type="number"
                      min={1}
                      step="1"
                      value={row.quantity}
                      onChange={(e) => updateExtra(index, "quantity", e.target.value)}
                    />
                    <Input
                      data-testid={`quote-extra-model-${index}`}
                      aria-label={`${t("purchases.items.model", "Modelo ofertado")} ${index + 1}`}
                      value={row.model}
                      onChange={(e) => updateExtra(index, "model", e.target.value)}
                      placeholder={t(
                        "purchases.items.modelPlaceholder",
                        "Modelo ofertado (opcional)",
                      )}
                    />
                    <Input
                      data-testid={`quote-extra-price-${index}`}
                      aria-label={`${t("purchases.items.unitPrice", "Preço unitário")} ${index + 1}`}
                      type="number"
                      min={0}
                      step="0.01"
                      inputMode="decimal"
                      value={row.unitPrice}
                      onChange={(e) =>
                        updateExtra(
                          index,
                          "unitPrice",
                          limitDecimals(e.target.value, MONEY_DECIMALS),
                        )
                      }
                    />
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span
                      className="text-xs text-gray-600"
                      data-testid={`quote-extra-total-${index}`}
                    >
                      {formatCurrency(extraLineTotal(row))}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label={t("purchases.items.removeExtra", "Remover item")}
                      title={t("purchases.items.removeExtra", "Remover item")}
                      onClick={() =>
                        setExtras((current) => current.filter((_, i) => i !== index))
                      }
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
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
