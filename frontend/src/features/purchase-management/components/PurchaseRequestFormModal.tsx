import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import type {
  PurchaseRequest,
  PurchaseRequestFormData,
} from "../../../types/purchase";

/**
 * The parent remounts this modal with a `key` derived from the request being
 * edited, so the fields below can be seeded with plain `useState`
 * initialisers instead of a reset effect (react-hooks/set-state-in-effect).
 */
interface PurchaseRequestFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  request: PurchaseRequest | null;
  onSubmit: (data: PurchaseRequestFormData) => Promise<void>;
  isLoading?: boolean;
}

export const PurchaseRequestFormModal: React.FC<PurchaseRequestFormModalProps> = ({
  isOpen,
  onClose,
  request,
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
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError(t("purchases.form.titleRequired", "O título do pedido é obrigatório."));
      return;
    }

    try {
      setError(null);
      await onSubmit({
        title: title.trim(),
        description: description.trim() || null,
        general_notes: generalNotes.trim() || null,
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
