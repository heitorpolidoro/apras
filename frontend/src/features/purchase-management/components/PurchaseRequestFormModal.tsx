import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, Trash2, X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import type {
  PurchaseRequest,
  PurchaseRequestFormData,
  PurchaseRequestItemInput,
} from "../../../types/purchase";
import { PurchaseRequestStatus } from "../../../types/purchase";

/** Maximum number of lines the backend accepts on a request (APRAS-73 D6). */
export const MAX_REQUEST_ITEMS = 50;

/**
 * One row of the line editor. `id` is present only for a line that already
 * exists: resubmitting it is what keeps the row — and every quote cell
 * attached to it — alive through the wholesale rewrite (D7).
 */
interface LineRow {
  id?: string;
  description: string;
  quantity: string;
}

/**
 * Whether the submitted enumeration says anything the request does not already
 * say. Order matters: `position` is derived server-side from the submitted
 * index (D7), so a reorder is a change like any other.
 */
const linesChanged = (
  submitted: PurchaseRequestItemInput[],
  existing: PurchaseRequest["items"],
): boolean =>
  submitted.length !== existing.length
  || submitted.some((item, index) => {
    const current = existing[index];
    return (
      item.id !== current.id
      || item.description !== current.description
      || item.quantity !== current.quantity
    );
  });

/**
 * The parent remounts this modal with a `key` derived from the request being
 * edited, so the fields below can be seeded with plain `useState`
 * initialisers instead of a reset effect (react-hooks/set-state-in-effect).
 */
interface PurchaseRequestFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  request: PurchaseRequest | null;
  /**
   * How many quotes already exist on this request. Removing a line that
   * suppliers priced deletes their cells for it, and the form says so before
   * the submit rather than after (D7).
   */
  quoteCount?: number;
  onSubmit: (data: PurchaseRequestFormData) => Promise<void>;
  isLoading?: boolean;
}

export const PurchaseRequestFormModal: React.FC<PurchaseRequestFormModalProps> = ({
  isOpen,
  onClose,
  request,
  quoteCount = 0,
  onSubmit,
  isLoading,
}) => {
  const { t } = useTranslation();

  const [title, setTitle] = useState<string>(request?.title ?? "");
  const [description, setDescription] = useState<string>(
    request?.description ?? "",
  );
  const [generalNotes, setGeneralNotes] = useState<string>(
    request?.general_notes ?? "",
  );
  const [lines, setLines] = useState<LineRow[]>(() =>
    (request?.items ?? []).map((item) => ({
      id: item.id,
      description: item.description,
      quantity: String(item.quantity),
    })),
  );
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  // D7: the enumeration is only editable while the request is OPEN — the
  // server refuses `items` on a request whose quotes are frozen. A request
  // being created has no status yet and is editable by definition.
  const canEditLines =
    request === null || request.status === PurchaseRequestStatus.OPEN;
  const existingItems = request?.items ?? [];
  const existingIds = new Set(existingItems.map((item) => item.id));
  const keptIds = new Set(lines.map((line) => line.id).filter(Boolean));
  const removedPricedLines =
    quoteCount > 0 &&
    [...existingIds].some((id) => !keptIds.has(id));
  const isAtMaxLines = lines.length >= MAX_REQUEST_ITEMS;

  const updateLine = (index: number, key: keyof LineRow, value: string) => {
    setLines((current) =>
      current.map((line, i) => (i === index ? { ...line, [key]: value } : line)),
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError(t("purchases.form.titleRequired", "O título do pedido é obrigatório."));
      return;
    }

    const items: PurchaseRequestItemInput[] = lines.map((line) => ({
      ...(line.id ? { id: line.id } : {}),
      description: line.description.trim(),
      quantity: Number(line.quantity),
    }));
    if (items.some((item) => !item.description)) {
      setError(
        t(
          "purchases.items.descriptionRequired",
          "Todo item avulso precisa de uma descrição.",
        ),
      );
      return;
    }
    if (items.some((item) => !Number.isInteger(item.quantity) || item.quantity <= 0)) {
      setError(
        t("purchases.quote.quantityInvalid", "A quantidade deve ser maior que zero."),
      );
      return;
    }

    try {
      setError(null);
      // `items` travels only when it carries a change. An absent key is what
      // makes the server skip the frozen-quote guard and leave the existing
      // lines (and the quote cells attached to them) alone — `items: []` is a
      // wholesale rewrite to nothing, which is a different request entirely.
      const sendItems = canEditLines && linesChanged(items, existingItems);
      await onSubmit({
        title: title.trim(),
        description: description.trim() || null,
        general_notes: generalNotes.trim() || null,
        ...(sendItems ? { items } : {}),
      });
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t("common.genericError", "Erro ao salvar o pedido."),
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">
            {request
              ? t("purchases.form.editTitle", "Editar Pedido de Compra")
              : t("purchases.form.createTitle", "Novo Pedido de Compra")}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="close">
            <X className="w-5 h-5" />
          </Button>
        </div>

        <form
          onSubmit={handleSubmit}
          className="p-6 space-y-4"
          data-testid="purchase-request-form"
        >
          {error && (
            <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200">
              {error}
            </div>
          )}

          <div>
            <label
              htmlFor="purchase-request-title"
              className="block text-xs font-semibold text-gray-700 uppercase mb-1"
            >
              {t("purchases.form.title", "Título do Pedido *")}
            </label>
            <Input
              id="purchase-request-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t(
                "purchases.form.titlePlaceholder",
                "Ex: Troca das bombas d'água",
              )}
            />
          </div>

          <div>
            <label
              htmlFor="purchase-request-description"
              className="block text-xs font-semibold text-gray-700 uppercase mb-1"
            >
              {t("purchases.form.description", "Descrição do que será comprado")}
            </label>
            <Textarea
              id="purchase-request-description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t(
                "purchases.form.descriptionPlaceholder",
                "Especificações, quantidades, marcas aceitas...",
              )}
            />
          </div>

          <div>
            <label
              htmlFor="purchase-request-general-notes"
              className="block text-xs font-semibold text-gray-700 uppercase mb-1"
            >
              {t("purchases.form.generalNotes", "Anotações gerais do pedido")}
            </label>
            <Textarea
              id="purchase-request-general-notes"
              rows={3}
              value={generalNotes}
              onChange={(e) => setGeneralNotes(e.target.value)}
              placeholder={t(
                "purchases.form.generalNotesPlaceholder",
                "Prazos, contatos, observações da diretoria...",
              )}
            />
          </div>

          <div className="border-t border-gray-200 pt-4">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-bold text-gray-900">
                {t("purchases.items.requestTitle", "Itens do pedido")}
              </h3>
              {canEditLines && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isAtMaxLines}
                onClick={() =>
                  setLines((current) => [
                    ...current,
                    { description: "", quantity: "1" },
                  ])
                }
              >
                <Plus className="w-4 h-4 mr-1" />
                {t("purchases.items.addLine", "Adicionar item")}
              </Button>
              )}
            </div>
            {canEditLines && (
              <p className="text-xs text-gray-500 mb-3">
                {t(
                  "purchases.items.requestHint",
                  "Enumere o que será comprado. Cada orçamento preenche o modelo e o preço de cada item.",
                )}
              </p>
            )}

            {removedPricedLines && (
              <p
                role="alert"
                data-testid="request-item-removal-warning"
                className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"
              >
                {t("purchases.items.removalWarning", {
                  count: quoteCount,
                  defaultValue:
                    "Ao remover este item, os preços já lançados por {{count}} orçamento(s) para ele serão apagados.",
                })}
              </p>
            )}

            {!canEditLines && (
              <>
                <p
                  data-testid="request-items-locked"
                  className="mb-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600"
                >
                  {t(
                    "purchases.items.lockedHint",
                    "Os itens de um pedido decidido ou cancelado não podem ser alterados.",
                  )}
                </p>
                <ul className="text-sm text-gray-800 space-y-0.5">
                  {existingItems.map((item) => (
                    <li
                      key={item.id}
                      data-testid={`request-item-readonly-${item.id}`}
                    >
                      {item.quantity} × {item.description}
                    </li>
                  ))}
                </ul>
              </>
            )}

            {canEditLines && (
            <div className="space-y-2">
              {lines.map((line, index) => (
                <div
                  key={line.id ?? `new-${index}`}
                  data-testid={`request-item-${index}`}
                  className="flex items-center gap-2"
                >
                  <Input
                    data-testid={`request-item-description-${index}`}
                    aria-label={`${t("purchases.items.description", "Descrição")} ${index + 1}`}
                    value={line.description}
                    onChange={(e) => updateLine(index, "description", e.target.value)}
                    placeholder={t(
                      "purchases.items.requestPlaceholder",
                      "Ex: Câmeras IP 4MP",
                    )}
                  />
                  <Input
                    data-testid={`request-item-quantity-${index}`}
                    aria-label={`${t("purchases.items.quantity", "Quantidade")} ${index + 1}`}
                    type="number"
                    min={1}
                    step="1"
                    className="w-24"
                    value={line.quantity}
                    onChange={(e) => updateLine(index, "quantity", e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label={t("purchases.items.removeLine", "Remover item")}
                    title={t("purchases.items.removeLine", "Remover item")}
                    onClick={() =>
                      setLines((current) => current.filter((_, i) => i !== index))
                    }
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              {t("purchases.actions.cancel", "Cancelar")}
            </Button>
            <Button type="submit" disabled={isLoading}>
              {t("purchases.form.submit", "Salvar Pedido")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PurchaseRequestFormModal;
