import React from "react";
import { useTranslation } from "react-i18next";
import { ArrowDownLeft, ArrowUpRight, Clock, RefreshCw, X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import type { Asset } from "../../../types/asset";
import { MovementType } from "../../../types/asset";
import { useAsset } from "../hooks/useAssets";

interface AssetMovementHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: Asset | null;
}

export const AssetMovementHistoryModal: React.FC<
  AssetMovementHistoryModalProps
> = ({ isOpen, onClose, asset }) => {
  const { t } = useTranslation();
  const { data: assetDetail, isLoading } = useAsset(asset?.id || "");

  if (!isOpen || !asset) return null;

  const getMovementTypeBadge = (type: MovementType) => {
    switch (type) {
      case MovementType.ENTRADA:
        return (
          <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 text-xs px-2 py-0.5 rounded-full font-medium">
            <ArrowDownLeft className="w-3 h-3 text-emerald-600" />
            {t("assets.movementTypes.ENTRADA", "Entrada")}
          </span>
        );
      case MovementType.SAIDA:
        return (
          <span className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full font-medium">
            <ArrowUpRight className="w-3 h-3 text-blue-600" />
            {t("assets.movementTypes.SAIDA", "Saída")}
          </span>
        );
      case MovementType.AJUSTE_INVENTARIO:
        return (
          <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded-full font-medium">
            <RefreshCw className="w-3 h-3 text-amber-600" />
            {t("assets.movementTypes.AJUSTE_INVENTARIO", "Ajuste")}
          </span>
        );
      case MovementType.BAIXA_PATRIMONIAL:
        return (
          <span className="inline-flex items-center gap-1 bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded-full font-medium">
            <X className="w-3 h-3 text-red-600" />
            {t("assets.movementTypes.BAIXA_PATRIMONIAL", "Baixa")}
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-indigo-600" />
              {t("assets.history.title", "Histórico de Movimentações")}
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

        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="text-center py-8 text-gray-500">
              {t("common.loading", "Carregando histórico...")}
            </div>
          ) : !assetDetail?.movements || assetDetail.movements.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              {t("assets.history.noMovements", "Nenhuma movimentação registrada para este item.")}
            </div>
          ) : (
            <div className="space-y-3">
              {assetDetail.movements.map((mov) => (
                <div
                  key={mov.id}
                  className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getMovementTypeBadge(mov.movement_type)}
                      <span className="text-xs font-semibold text-gray-700">
                        {mov.previous_quantity} → {mov.new_quantity}{" "}
                        {asset.unit_of_measure || "un"} (
                        {mov.new_quantity >= mov.previous_quantity ? "+" : ""}
                        {mov.new_quantity - mov.previous_quantity})
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(mov.created_at).toLocaleString("pt-BR")}
                    </span>
                  </div>

                  <div className="text-sm text-gray-800 font-medium">
                    {mov.reason}
                  </div>

                  <div className="flex items-center justify-between text-xs text-gray-500 pt-1 border-t border-gray-200/60">
                    <span>
                      {t("assets.history.by", "Registrado por:")}{" "}
                      <strong className="text-gray-700">
                        {mov.performed_by_name || "Sistema"}
                      </strong>
                    </span>
                    {mov.document_number && (
                      <span className="bg-white px-2 py-0.5 rounded border border-gray-200 font-mono text-gray-600">
                        {mov.document_number}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-200 flex justify-end">
          <Button variant="outline" onClick={onClose}>
            {t("common.close", "Fechar")}
          </Button>
        </div>
      </div>
    </div>
  );
};
