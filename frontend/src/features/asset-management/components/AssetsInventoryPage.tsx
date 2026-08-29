import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  Archive,
  Box,
  Layers,
  Plus,
  Search,
} from "lucide-react";
import { AlertModal } from "../../../components/ui/alert-modal";
import { Button } from "../../../components/ui/button";
import type {
  Asset,
  AssetCategory as AssetCategoryType,
  AssetCondition as AssetConditionType,
  AssetFormData,
  MovementFormData,
} from "../../../types/asset";
import { AssetCategory, AssetCondition } from "../../../types/asset";
import { UserRole } from "../../../types/auth";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import {
  useAssets,
  useAssetSummary,
  useCreateAsset,
  useDeleteAsset,
  useRecordMovement,
  useUpdateAsset,
} from "../hooks/useAssets";
import { AssetFormModal } from "./AssetFormModal";
import { AssetMovementHistoryModal } from "./AssetMovementHistoryModal";
import { AssetSummaryCards } from "./AssetSummaryCards";
import { AssetTable } from "./AssetTable";
import { StockMovementModal } from "./StockMovementModal";

type FilterTab = "all" | "fixed" | "consumable" | "low_stock";

export const AssetsInventoryPage: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();

  const canManage =
    role === UserRole.ADMINISTRATOR || role === UserRole.DIRECTOR;
  const canAdjust = canManage;

  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedCondition, setSelectedCondition] = useState<string>("");

  // Modals state
  const [isFormModalOpen, setIsFormModalOpen] = useState<boolean>(false);
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);

  const [isMovementModalOpen, setIsMovementModalOpen] = useState<boolean>(false);
  const [movementAsset, setMovementAsset] = useState<Asset | null>(null);

  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState<boolean>(false);
  const [historyAsset, setHistoryAsset] = useState<Asset | null>(null);

  const [assetToDelete, setAssetToDelete] = useState<Asset | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Queries & Mutations
  const filterParams = useMemo(() => {
    const params: {
      category?: AssetCategoryType;
      condition?: AssetConditionType;
      search?: string;
      is_consumable?: boolean;
      low_stock_only?: boolean;
    } = {};

    if (searchQuery.trim()) {
      params.search = searchQuery.trim();
    }
    if (selectedCategory) {
      params.category = selectedCategory as AssetCategoryType;
    }
    if (selectedCondition) {
      params.condition = selectedCondition as AssetConditionType;
    }

    if (activeTab === "fixed") {
      params.is_consumable = false;
    } else if (activeTab === "consumable") {
      params.is_consumable = true;
    } else if (activeTab === "low_stock") {
      params.low_stock_only = true;
    }

    return params;
  }, [activeTab, searchQuery, selectedCategory, selectedCondition]);

  const { data: assetsData, isLoading: isLoadingAssets } =
    useAssets(filterParams);
  const { data: summaryData, isLoading: isLoadingSummary } = useAssetSummary();

  const createMutation = useCreateAsset();
  const updateMutation = useUpdateAsset();
  const deleteMutation = useDeleteAsset();
  const movementMutation = useRecordMovement();

  // Handlers
  const handleOpenCreateModal = () => {
    setEditingAsset(null);
    setIsFormModalOpen(true);
  };

  const handleOpenEditModal = (asset: Asset) => {
    setEditingAsset(asset);
    setIsFormModalOpen(true);
  };

  const handleFormSubmit = async (data: AssetFormData) => {
    if (editingAsset) {
      await updateMutation.mutateAsync({ id: editingAsset.id, data });
    } else {
      await createMutation.mutateAsync(data);
    }
  };

  const handleOpenMovementModal = (asset: Asset) => {
    setMovementAsset(asset);
    setIsMovementModalOpen(true);
  };

  const handleMovementSubmit = async (
    assetId: string,
    data: MovementFormData
  ) => {
    await movementMutation.mutateAsync({ assetId, data });
  };

  const handleOpenHistoryModal = (asset: Asset) => {
    setHistoryAsset(asset);
    setIsHistoryModalOpen(true);
  };

  const handleDeleteClick = (asset: Asset) => {
    setAssetToDelete(asset);
  };

  const handleConfirmDelete = async () => {
    if (!assetToDelete) return;
    try {
      await deleteMutation.mutateAsync(assetToDelete.id);
      setAssetToDelete(null);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(t("common.genericError", "Erro ao excluir ativo."));
      }
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
            <Box className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {t("assets.pageTitle", "Patrimônio & Estoque")}
            </h1>
            <p className="text-sm text-gray-500">
              {t(
                "assets.pageSubtitle",
                "Gerenciamento de bens patrimoniais e controle de estoque do condomínio."
              )}
            </p>
          </div>
        </div>

        {canManage && (
          <Button
            onClick={handleOpenCreateModal}
            className="gap-2 bg-blue-600 hover:bg-blue-700 text-white shrink-0"
          >
            <Plus className="w-4 h-4" />
            {t("assets.actions.newAsset", "Novo Item / Ativo")}
          </Button>
        )}
      </div>

      {/* Summary Cards */}
      <AssetSummaryCards
        summary={summaryData}
        isLoading={isLoadingSummary}
      />

      {/* Tabs and Filters */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm space-y-4">
        {/* Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 pb-3">
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "all"
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <Layers className="w-4 h-4" />
            {t("assets.tabs.all", "Todos os Itens")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("fixed")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "fixed"
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <Box className="w-4 h-4" />
            {t("assets.tabs.fixed", "Bens Patrimoniais")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("consumable")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "consumable"
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <Archive className="w-4 h-4" />
            {t("assets.tabs.consumable", "Itens de Consumo / Estoque")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("low_stock")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "low_stock"
                ? "bg-amber-50 text-amber-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            {t("assets.tabs.lowStock", "Alertas de Estoque Baixo")}
            {(summaryData?.low_stock_count ?? 0) > 0 && (
              <span className="bg-amber-200 text-amber-900 text-xs px-1.5 py-0.5 rounded-full font-bold">
                {summaryData?.low_stock_count}
              </span>
            )}
          </button>
        </div>

        {/* Filter Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t(
                "assets.searchPlaceholder",
                "Buscar por nome, tag, serial ou local..."
              )}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">
                {t("assets.filterByCategory", "Todas as Categorias")}
              </option>
              {Object.values(AssetCategory).map((cat) => (
                <option key={cat} value={cat}>
                  {t(`assets.categories.${cat}`, cat)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={selectedCondition}
              onChange={(e) => setSelectedCondition(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">
                {t("assets.filterByCondition", "Todos os Estados")}
              </option>
              {Object.values(AssetCondition).map((cond) => (
                <option key={cond} value={cond}>
                  {t(`assets.conditions.${cond}`, cond)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Assets Table */}
      <AssetTable
        assets={assetsData?.items || []}
        isLoading={isLoadingAssets}
        canManage={canManage}
        onOpenMovement={handleOpenMovementModal}
        onOpenHistory={handleOpenHistoryModal}
        onEdit={handleOpenEditModal}
        onDelete={handleDeleteClick}
      />

      {/* Modals */}
      <AssetFormModal
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        onSubmit={handleFormSubmit}
        initialData={editingAsset}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      <StockMovementModal
        isOpen={isMovementModalOpen}
        onClose={() => setIsMovementModalOpen(false)}
        asset={movementAsset}
        canManageAdjustments={canAdjust}
        onSubmit={handleMovementSubmit}
        isLoading={movementMutation.isPending}
      />

      <AssetMovementHistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        asset={historyAsset}
      />

      {/* Delete Confirmation Modal */}
      {assetToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900">
              {t("assets.deleteConfirmTitle", "Excluir Item do Patrimônio")}
            </h3>
            <p className="text-sm text-gray-600">
              {t(
                "assets.deleteConfirmMessage",
                "Tem certeza de que deseja excluir o item '{{name}}'? Todo o histórico de movimentações também será removido.",
                { name: assetToDelete.name }
              )}
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => setAssetToDelete(null)}
                disabled={deleteMutation.isPending}
              >
                {t("common.cancel", "Cancelar")}
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmDelete}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending
                  ? t("common.deleting", "Excluindo...")
                  : t("common.confirm", "Confirmar")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Error AlertModal */}
      <AlertModal
        open={!!errorMessage}
        onClose={() => setErrorMessage(null)}
        variant="destructive"
        title="Erro"
        message={errorMessage ?? ""}
      />
    </div>
  );
};

export default AssetsInventoryPage;
