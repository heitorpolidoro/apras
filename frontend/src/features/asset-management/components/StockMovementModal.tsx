import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import type { Asset, MovementFormData } from "../../../types/asset";
import { MovementType } from "../../../types/asset";

interface StockMovementModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: Asset | null;
  canManageAdjustments?: boolean;
  onSubmit: (assetId: string, data: MovementFormData) => Promise<void>;
  isLoading?: boolean;
}

export const StockMovementModal: React.FC<StockMovementModalProps> = ({
  isOpen,
  onClose,
  asset,
  canManageAdjustments = false,
  onSubmit,
  isLoading,
}) => {
  const { t } = useTranslation();

  const [movementType, setMovementType] = useState<MovementType>(
    MovementType.ENTRADA
  );
  const [quantity, setQuantity] = useState<number>(1);
  const [reason, setReason] = useState<string>("");
  const [documentNumber, setDocumentNumber] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setMovementType(MovementType.ENTRADA);
      setQuantity(1);
      setReason("");
      setDocumentNumber("");
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen || !asset) return null;

  const allowedMovementTypes = canManageAdjustments
    ? Object.values(MovementType)
    : [MovementType.ENTRADA, MovementType.SAIDA];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError(t("assets.movement.reasonRequired", "O motivo/justificativa é obrigatório."));
      return;
    }

    if (movementType === MovementType.SAIDA && quantity > asset.current_quantity) {
      setError(
        t(
          "assets.movement.insufficientStock",
          "A quantidade de saída não pode ser maior que o saldo atual em estoque."
        )
      );
      return;
    }

    try {
      setError(null);
      await onSubmit(asset.id, {
        movement_type: movementType,
        quantity: Number(quantity),
        reason: reason.trim(),
        document_number: documentNumber.trim() || null,
      });
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t("common.genericError", "Erro ao registrar movimentação."));
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              {t("assets.movement.title", "Registrar Movimentação")}
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {asset.name} • Saldo atual:{" "}
              <span className="font-semibold text-gray-900">
                {asset.current_quantity} {asset.unit_of_measure || "un"}
              </span>
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
              {t("assets.movement.type", "Tipo de Movimentação *")}
            </label>
            <select
              value={movementType}
              onChange={(e) => setMovementType(e.target.value as MovementType)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {allowedMovementTypes.map((type) => (
                <option key={type} value={type}>
                  {t(`assets.movementTypes.${type}`, type)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
              {movementType === MovementType.AJUSTE_INVENTARIO
                ? t("assets.movement.newBalance", "Novo Saldo Contado *")
                : t("assets.movement.quantity", "Quantidade *")}
            </label>
            <input
              type="number"
              min={movementType === MovementType.AJUSTE_INVENTARIO ? 0 : 1}
              required
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
              {t("assets.movement.documentNumber", "Documento / NF / Requisição")}
            </label>
            <input
              type="text"
              value={documentNumber}
              onChange={(e) => setDocumentNumber(e.target.value)}
              placeholder="Ex: NF 9876, Req Manutenção 12"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
              {t("assets.movement.reason", "Motivo / Justificativa *")}
            </label>
            <textarea
              required
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t(
                "assets.movement.reasonPlaceholder",
                "Descreva a finalidade da movimentação, setor ou destino..."
              )}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isLoading}
            >
              {t("common.cancel", "Cancelar")}
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isLoading
                ? t("common.saving", "Gravando...")
                : t("assets.movement.confirm", "Confirmar Movimentação")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
