import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import type { Lot, LotCreate, LotUpdate } from "../../../types/lot";
import { LotStatus } from "../../../types/lot";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";

interface LotFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: LotCreate | LotUpdate) => Promise<void>;
  initialData?: Lot | null;
  isLoading?: boolean;
}

export const LotFormModal: React.FC<LotFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isLoading,
}) => {
  const { t } = useTranslation();

  const [block, setBlock] = useState("");
  const [lotNumber, setLotNumber] = useState("");
  const [address, setAddress] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [areaSqm, setAreaSqm] = useState<string>("");
  const [fractionIdeal, setFractionIdeal] = useState<string>("");
  const [status, setStatus] = useState<LotStatus>(LotStatus.VACANT);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setBlock(initialData.block);
      setLotNumber(initialData.lot_number);
      setAddress(initialData.address || "");
      setPostalCode(initialData.postal_code || "");
      setAreaSqm(initialData.area_sqm !== null && initialData.area_sqm !== undefined ? String(initialData.area_sqm) : "");
      setFractionIdeal(initialData.fraction_ideal !== null && initialData.fraction_ideal !== undefined ? String(initialData.fraction_ideal) : "");
      setStatus(initialData.status);
      setNotes(initialData.notes || "");
    } else {
      setBlock("");
      setLotNumber("");
      setAddress("");
      setPostalCode("");
      setAreaSqm("");
      setFractionIdeal("");
      setStatus(LotStatus.VACANT);
      setNotes("");
    }
    setError(null);
  }, [initialData, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!block.trim() || !lotNumber.trim()) {
      setError(t("common.requiredField", "Preencha os campos obrigatórios"));
      return;
    }

    try {
      setError(null);
      const payload: LotCreate = {
        block: block.trim(),
        lot_number: lotNumber.trim(),
        address: address.trim() || null,
        postal_code: postalCode.trim() || null,
        area_sqm: areaSqm !== "" ? parseFloat(areaSqm) : null,
        fraction_ideal: fractionIdeal !== "" ? parseFloat(fractionIdeal) : null,
        status,
        notes: notes.trim() || null,
      };

      await onSubmit(payload);
      onClose();
    } catch (err: unknown) {
      if (typeof err === "object" && err !== null && "response" in err) {
        const apiError = err as { response?: { data?: { detail?: string } } };
        setError(apiError.response?.data?.detail || "Erro ao salvar lote");
      } else {
        setError("Erro ao salvar lote");
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            {initialData ? t("lots.editLot") : t("lots.newLot")}
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            <X className="size-4" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("lots.block")} *
              </label>
              <Input
                value={block}
                onChange={(e) => setBlock(e.target.value)}
                placeholder="Ex: A"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("lots.lotNumber")} *
              </label>
              <Input
                value={lotNumber}
                onChange={(e) => setLotNumber(e.target.value)}
                placeholder="Ex: 101"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("lots.address")}
            </label>
            <Input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Ex: Alameda das Palmeiras, 100"
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("lots.postalCode")}
              </label>
              <Input
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                placeholder="00000-000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("lots.areaSqm")}
              </label>
              <Input
                type="number"
                step="any"
                value={areaSqm}
                onChange={(e) => setAreaSqm(e.target.value)}
                placeholder="450.0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("lots.fractionIdeal")}
              </label>
              <Input
                type="number"
                step="any"
                value={fractionIdeal}
                onChange={(e) => setFractionIdeal(e.target.value)}
                placeholder="0.025"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("lots.status")}
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as LotStatus)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            >
              <option value={LotStatus.VACANT}>{t("lots.statusVacant")}</option>
              <option value={LotStatus.OCCUPIED}>{t("lots.statusOccupied")}</option>
              <option value={LotStatus.UNDER_CONSTRUCTION}>
                {t("lots.statusUnderConstruction")}
              </option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("lots.notes")}
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-slate-300 bg-white p-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              placeholder="Informações adicionais..."
            />
          </div>

          <div className="flex items-center justify-end space-x-3 border-t border-slate-100 pt-4 dark:border-slate-800">
            <Button type="button" variant="outline" onClick={onClose}>
              {t("lots.cancel")}
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Salvando..." : t("lots.save")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
