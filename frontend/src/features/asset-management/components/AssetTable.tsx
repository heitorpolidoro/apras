import React from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  ArrowUpDown,
  Edit2,
  History,
  Trash2,
} from "lucide-react";
import { Button } from "../../../components/ui/button";
import type { Asset } from "../../../types/asset";
import { AssetCondition } from "../../../types/asset";

interface AssetTableProps {
  assets: Asset[];
  isLoading?: boolean;
  canManage?: boolean;
  onOpenMovement: (asset: Asset) => void;
  onOpenHistory: (asset: Asset) => void;
  onEdit: (asset: Asset) => void;
  onDelete: (asset: Asset) => void;
}

export const AssetTable: React.FC<AssetTableProps> = ({
  assets,
  isLoading,
  canManage = false,
  onOpenMovement,
  onOpenHistory,
  onEdit,
  onDelete,
}) => {
  const { t } = useTranslation();

  const getConditionBadgeClass = (condition: Asset["condition"]) => {
    switch (condition) {
      case AssetCondition.NOVO:
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
      case AssetCondition.BOM:
        return "bg-blue-100 text-blue-800 border-blue-200";
      case AssetCondition.REGULAR:
        return "bg-amber-100 text-amber-800 border-amber-200";
      case AssetCondition.RUIM:
      case AssetCondition.DANIFICADO:
        return "bg-orange-100 text-orange-800 border-orange-200";
      case AssetCondition.BAIXADO:
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getCategoryBadgeClass = (category: Asset["category"]) => {
    switch (category) {
      case "ELETRONICOS":
        return "bg-cyan-50 text-cyan-700 border-cyan-200";
      case "FERRAMENTAS":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "MOBILIARIO":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "SEGURANCA":
        return "bg-red-50 text-red-700 border-red-200";
      case "LIMPEZA":
        return "bg-teal-50 text-teal-700 border-teal-200";
      case "MANUTENCAO":
        return "bg-indigo-50 text-indigo-700 border-indigo-200";
      default:
        return "bg-gray-50 text-gray-700 border-gray-200";
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
        {t("common.loading", "Carregando...")}
      </div>
    );
  }

  if (assets.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
        {t("assets.noAssetsFound", "Nenhum ativo ou item encontrado.")}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 text-xs font-semibold text-gray-700 uppercase border-b border-gray-200">
            <tr>
              <th scope="col" className="px-6 py-3">
                {t("assets.table.item", "Item / Identificação")}
              </th>
              <th scope="col" className="px-6 py-3">
                {t("assets.table.category", "Categoria")}
              </th>
              <th scope="col" className="px-6 py-3">
                {t("assets.table.location", "Localização")}
              </th>
              <th scope="col" className="px-6 py-3">
                {t("assets.table.condition", "Estado")}
              </th>
              <th scope="col" className="px-6 py-3">
                {t("assets.table.quantity", "Saldo / Quantidade")}
              </th>
              <th scope="col" className="px-6 py-3 text-right">
                {t("assets.table.actions", "Ações")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {assets.map((asset) => (
              <tr
                key={asset.id}
                className="hover:bg-gray-50/75 transition-colors"
              >
                <td className="px-6 py-4">
                  <div className="font-medium text-gray-900">{asset.name}</div>
                  <div className="text-xs text-gray-400 flex items-center gap-2 mt-0.5">
                    {asset.asset_tag && (
                      <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                        {asset.asset_tag}
                      </span>
                    )}
                    {asset.serial_number && (
                      <span>S/N: {asset.serial_number}</span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getCategoryBadgeClass(
                      asset.category
                    )}`}
                  >
                    {t(`assets.categories.${asset.category}`, asset.category)}
                  </span>
                </td>
                <td className="px-6 py-4 font-medium text-gray-800">
                  {asset.location}
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getConditionBadgeClass(
                      asset.condition
                    )}`}
                  >
                    {t(`assets.conditions.${asset.condition}`, asset.condition)}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900">
                      {asset.current_quantity}
                    </span>
                    <span className="text-xs text-gray-400">
                      {asset.unit_of_measure || "un"}
                    </span>
                    {asset.is_low_stock && (
                      <span
                        title={t(
                          "assets.lowStockWarning",
                          "Estoque abaixo do mínimo recomendado"
                        )}
                        className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded-full font-medium"
                      >
                        <AlertTriangle className="w-3 h-3 text-amber-600" />
                        {t("assets.lowStock", "Estoque Baixo")}
                      </span>
                    )}
                  </div>
                  {asset.min_quantity !== null && asset.min_quantity !== undefined && (
                    <div className="text-xs text-gray-400 mt-0.5">
                      Mín: {asset.min_quantity} {asset.unit_of_measure || "un"}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onOpenMovement(asset)}
                      title={t("assets.actions.recordMovement", "Movimentar")}
                      className="text-gray-600 hover:text-blue-600"
                    >
                      <ArrowUpDown className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onOpenHistory(asset)}
                      title={t("assets.actions.history", "Histórico")}
                      className="text-gray-600 hover:text-indigo-600"
                    >
                      <History className="w-4 h-4" />
                    </Button>
                    {canManage && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onEdit(asset)}
                          title={t("assets.actions.edit", "Editar")}
                          className="text-gray-600 hover:text-amber-600"
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onDelete(asset)}
                          title={t("assets.actions.delete", "Excluir")}
                          className="text-gray-600 hover:text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
