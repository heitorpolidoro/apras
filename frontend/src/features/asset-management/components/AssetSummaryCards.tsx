import React from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Archive, Box, DollarSign } from "lucide-react";
import type { AssetSummary } from "../../../types/asset";

interface AssetSummaryCardsProps {
  summary?: AssetSummary;
  isLoading?: boolean;
}

export const AssetSummaryCards: React.FC<AssetSummaryCardsProps> = ({
  summary,
  isLoading,
}) => {
  const { t } = useTranslation();

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return "R$ 0,00";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(val);
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Fixed Assets */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            {t("assets.summary.totalAssets", "Ativos Patrimoniais")}
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {isLoading ? "..." : summary?.total_assets ?? 0}
          </p>
        </div>
        <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
          <Box className="w-6 h-6" />
        </div>
      </div>

      {/* Total Consumables */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            {t("assets.summary.totalConsumables", "Itens de Consumo")}
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {isLoading ? "..." : summary?.total_consumables ?? 0}
          </p>
        </div>
        <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
          <Archive className="w-6 h-6" />
        </div>
      </div>

      {/* Low Stock Alerts */}
      <div
        className={`bg-white p-5 rounded-xl border shadow-sm flex items-center justify-between ${
          (summary?.low_stock_count ?? 0) > 0
            ? "border-amber-300 bg-amber-50/20"
            : "border-gray-200"
        }`}
      >
        <div>
          <p className="text-xs font-medium text-amber-700 uppercase tracking-wider">
            {t("assets.summary.lowStockCount", "Estoque Baixo")}
          </p>
          <p className="text-2xl font-bold text-amber-900 mt-1">
            {isLoading ? "..." : summary?.low_stock_count ?? 0}
          </p>
        </div>
        <div className="p-3 bg-amber-100 text-amber-600 rounded-lg">
          <AlertTriangle className="w-6 h-6" />
        </div>
      </div>

      {/* Total Patrimonial Value */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            {t("assets.summary.totalValue", "Valor do Patrimônio")}
          </p>
          <p className="text-2xl font-bold text-emerald-700 mt-1">
            {isLoading ? "..." : formatCurrency(summary?.total_patrimonial_value)}
          </p>
        </div>
        <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
          <DollarSign className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
};
