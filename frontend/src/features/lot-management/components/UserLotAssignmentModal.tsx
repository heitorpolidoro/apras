import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { useUsers } from "../../../hooks/useUsers";
import type { UserLotLinkCreate } from "../../../types/lot";
import { LotAssociationType } from "../../../types/lot";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";

interface UserLotAssignmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: UserLotLinkCreate) => Promise<void>;
  lotBlock: string;
  lotNumber: string;
  isLoading?: boolean;
}

export const UserLotAssignmentModal: React.FC<UserLotAssignmentModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  lotBlock,
  lotNumber,
  isLoading,
}) => {
  const { t } = useTranslation();
  const { data: users = [], isLoading: isLoadingUsers } = useUsers();

  const [selectedUserId, setSelectedUserId] = useState("");
  const [associationType, setAssociationType] = useState<LotAssociationType>(
    LotAssociationType.PROPRIETARIO
  );
  const [isPrimary, setIsPrimary] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      setError(t("lots.selectUser"));
      return;
    }

    try {
      setError(null);
      await onSubmit({
        user_id: selectedUserId,
        association_type: associationType,
        is_primary: isPrimary,
        start_date: startDate ? new Date(startDate).toISOString() : null,
        end_date: endDate ? new Date(endDate).toISOString() : null,
      });
      setSelectedUserId("");
      setIsPrimary(false);
      setStartDate("");
      setEndDate("");
      onClose();
    } catch (err: unknown) {
      if (typeof err === "object" && err !== null && "response" in err) {
        const apiError = err as { response?: { data?: { detail?: string } } };
        setError(apiError.response?.data?.detail || "Erro ao vincular usuário");
      } else {
        setError("Erro ao vincular usuário");
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            {t("lots.linkUser")} (Q: {lotBlock}, L: {lotNumber})
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

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("lots.selectUser")} *
            </label>
            {isLoadingUsers ? (
              <div className="text-sm text-slate-500">Carregando usuários...</div>
            ) : (
              <select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                required
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              >
                <option value="">{t("lots.selectUser")}...</option>
                {users?.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.email})
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("lots.associationType")}
            </label>
            <select
              value={associationType}
              onChange={(e) => setAssociationType(e.target.value as LotAssociationType)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            >
              <option value={LotAssociationType.PROPRIETARIO}>
                {t("lots.assocProprietario")}
              </option>
              <option value={LotAssociationType.INQUILINO}>
                {t("lots.assocInquilino")}
              </option>
              <option value={LotAssociationType.RESPONSAVEL_FINANCEIRO}>
                {t("lots.assocRespFinanceiro")}
              </option>
              <option value={LotAssociationType.OUTRO}>
                {t("lots.assocOutro")}
              </option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="is_primary"
              checked={isPrimary}
              onChange={(e) => setIsPrimary(e.target.checked)}
              className="size-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800"
            />
            <label
              htmlFor="is_primary"
              className="text-sm font-medium text-slate-700 dark:text-slate-300 cursor-pointer"
            >
              {t("lots.isPrimary")}
            </label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("lots.startDate")}
              </label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("lots.endDate")}
              </label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center justify-end space-x-3 border-t border-slate-100 pt-4 dark:border-slate-800">
            <Button type="button" variant="outline" onClick={onClose}>
              {t("lots.cancel")}
            </Button>
            <Button type="submit" disabled={isLoading || !selectedUserId}>
              {isLoading ? "Vinculando..." : t("lots.linkUser")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
