import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import type { Asset, AssetFormData } from "../../../types/asset";
import { AssetCategory, AssetCondition } from "../../../types/asset";

interface AssetFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: AssetFormData) => Promise<void>;
  initialData?: Asset | null;
  isLoading?: boolean;
}

export const AssetFormModal: React.FC<AssetFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isLoading,
}) => {
  const { t } = useTranslation();

  const [formData, setFormData] = useState<AssetFormData>({
    name: "",
    category: AssetCategory.OUTROS,
    serial_number: "",
    asset_tag: "",
    location: "",
    acquisition_date: "",
    acquisition_value: undefined,
    condition: AssetCondition.BOM,
    is_consumable: false,
    current_quantity: 1,
    min_quantity: undefined,
    unit_of_measure: "un",
    notes: "",
  });

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setFormData({
        name: initialData.name,
        category: initialData.category,
        serial_number: initialData.serial_number || "",
        asset_tag: initialData.asset_tag || "",
        location: initialData.location,
        acquisition_date: initialData.acquisition_date || "",
        acquisition_value:
          initialData.acquisition_value !== null
            ? initialData.acquisition_value
            : undefined,
        condition: initialData.condition,
        is_consumable: initialData.is_consumable,
        current_quantity: initialData.current_quantity,
        min_quantity:
          initialData.min_quantity !== null
            ? initialData.min_quantity
            : undefined,
        unit_of_measure: initialData.unit_of_measure || "un",
        notes: initialData.notes || "",
      });
    } else {
      setFormData({
        name: "",
        category: AssetCategory.OUTROS,
        serial_number: "",
        asset_tag: "",
        location: "",
        acquisition_date: "",
        acquisition_value: undefined,
        condition: AssetCondition.BOM,
        is_consumable: false,
        current_quantity: 1,
        min_quantity: undefined,
        unit_of_measure: "un",
        notes: "",
      });
    }
    setError(null);
  }, [initialData, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError(t("assets.form.nameRequired", "O nome do item é obrigatório."));
      return;
    }
    if (!formData.location.trim()) {
      setError(t("assets.form.locationRequired", "A localização é obrigatória."));
      return;
    }

    try {
      setError(null);
      await onSubmit({
        ...formData,
        serial_number: formData.serial_number || null,
        asset_tag: formData.asset_tag || null,
        acquisition_date: formData.acquisition_date || null,
        acquisition_value:
          formData.acquisition_value !== undefined &&
          formData.acquisition_value !== null &&
          !isNaN(Number(formData.acquisition_value))
            ? Number(formData.acquisition_value)
            : null,
        min_quantity:
          formData.min_quantity !== undefined &&
          formData.min_quantity !== null &&
          formData.min_quantity !== ("" as unknown as number)
            ? Number(formData.min_quantity)
            : null,
        notes: formData.notes || null,
      });
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t("common.genericError", "Erro ao salvar ativo."));
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">
            {initialData
              ? t("assets.form.editTitle", "Editar Ativo / Item")
              : t("assets.form.createTitle", "Novo Ativo / Item de Estoque")}
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.name", "Nome do Item *")}
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder={t("assets.form.namePlaceholder", "Ex: Cortador de grama, Lâmpada LED")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.category", "Categoria *")}
              </label>
              <select
                value={formData.category}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    category: e.target.value as AssetCategory,
                  }))
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {Object.values(AssetCategory).map((cat) => (
                  <option key={cat} value={cat}>
                    {t(`assets.categories.${cat}`, cat)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.location", "Localização *")}
              </label>
              <input
                type="text"
                required
                value={formData.location}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, location: e.target.value }))
                }
                placeholder={t("assets.form.locationPlaceholder", "Ex: Almoxarifado, Portaria 1, DML")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="sm:col-span-2 flex items-center gap-3 py-2 border-y border-gray-100">
              <input
                type="checkbox"
                id="is_consumable"
                checked={formData.is_consumable}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    is_consumable: e.target.checked,
                  }))
                }
                className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              />
              <label
                htmlFor="is_consumable"
                className="text-sm font-medium text-gray-800 cursor-pointer"
              >
                {t(
                  "assets.form.isConsumable",
                  "Este item é material de consumo / estoque (ex: lâmpadas, sacos de cimento, limpeza)"
                )}
              </label>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.assetTag", "Etiqueta / Tag Patrimonial")}
              </label>
              <input
                type="text"
                value={formData.asset_tag || ""}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, asset_tag: e.target.value }))
                }
                placeholder="Ex: PAT-00120"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.serialNumber", "Número de Série")}
              </label>
              <input
                type="text"
                value={formData.serial_number || ""}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    serial_number: e.target.value,
                  }))
                }
                placeholder="Ex: SN-982348"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.condition", "Estado de Conservação")}
              </label>
              <select
                value={formData.condition}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    condition: e.target.value as AssetCondition,
                  }))
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {Object.values(AssetCondition).map((cond) => (
                  <option key={cond} value={cond}>
                    {t(`assets.conditions.${cond}`, cond)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.acquisitionDate", "Data de Aquisição")}
              </label>
              <input
                type="date"
                value={formData.acquisition_date || ""}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    acquisition_date: e.target.value,
                  }))
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.acquisitionValue", "Valor de Aquisição (R$)")}
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={
                  formData.acquisition_value !== undefined &&
                  formData.acquisition_value !== null
                    ? formData.acquisition_value
                    : ""
                }
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    acquisition_value:
                      e.target.value === "" ? undefined : Number(e.target.value),
                  }))
                }
                placeholder="0.00"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.unitOfMeasure", "Unidade de Medida")}
              </label>
              <input
                type="text"
                value={formData.unit_of_measure || "un"}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    unit_of_measure: e.target.value,
                  }))
                }
                placeholder="un, kg, L, caixa, m"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {!initialData && (
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                  {t("assets.form.initialQuantity", "Quantidade Inicial")}
                </label>
                <input
                  type="number"
                  min="0"
                  value={formData.current_quantity ?? 1}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      current_quantity: Number(e.target.value),
                    }))
                  }
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.minQuantity", "Quantidade Mínima (Alerta)")}
              </label>
              <input
                type="number"
                min="0"
                value={
                  formData.min_quantity !== undefined &&
                  formData.min_quantity !== null
                    ? formData.min_quantity
                    : ""
                }
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    min_quantity:
                      e.target.value === "" ? undefined : Number(e.target.value),
                  }))
                }
                placeholder="Ex: 5"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                {t("assets.form.notes", "Observações")}
              </label>
              <textarea
                rows={2}
                value={formData.notes || ""}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, notes: e.target.value }))
                }
                placeholder={t("assets.form.notesPlaceholder", "Detalhes adicionais, fornecedor, garantia...")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
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
                ? t("common.saving", "Salvando...")
                : initialData
                ? t("common.save", "Salvar Alterações")
                : t("assets.form.createButton", "Cadastrar Item")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
