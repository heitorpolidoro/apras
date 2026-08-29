import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, ShieldCheck } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { useLots } from "../../lot-management/hooks/useLots";
import {
  useCreateAuthorization,
  useLotAuthorizations,
  useRevokeAuthorization,
} from "../hooks/useVisitors";
import { VisitorTable } from "./VisitorTable";
import { AuthorizationFormModal } from "./AuthorizationFormModal";
import { AuthorizationQrModal } from "./AuthorizationQrModal";
import type { VisitorAuthorization, VisitorAuthorizationCreate } from "../../../types/visitor";

export const VisitorAuthPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: lotsData } = useLots();
  const lots = lotsData?.items || [];

  const [selectedLotId, setSelectedLotId] = useState<string>(lots[0]?.id || "");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [revokingAuth, setRevokingAuth] = useState<VisitorAuthorization | null>(null);
  const [qrAuth, setQrAuth] = useState<VisitorAuthorization | null>(null);

  // Auto select first lot if available
  const effectiveLotId = selectedLotId || (lots.length > 0 ? lots[0].id : "");

  const { data: authsData, isLoading } = useLotAuthorizations(
    effectiveLotId,
    statusFilter || undefined
  );
  const createAuthMutation = useCreateAuthorization();
  const revokeAuthMutation = useRevokeAuthorization();

  const handleCreateSubmit = async (data: VisitorAuthorizationCreate) => {
    if (effectiveLotId) {
      await createAuthMutation.mutateAsync({
        lotId: effectiveLotId,
        data,
      });
    }
  };

  const handleConfirmRevoke = async () => {
    if (revokingAuth) {
      await revokeAuthMutation.mutateAsync({
        authId: revokingAuth.id,
        lotId: effectiveLotId,
      });
      setRevokingAuth(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="size-7 text-indigo-600 dark:text-indigo-400" />
            {t("authorizations.title")}
          </h1>
        </div>

        {effectiveLotId && (
          <Button onClick={() => setIsModalOpen(true)} className="gap-2">
            <Plus className="size-4" />
            {t("authorizations.newAuth")}
          </Button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
            {t("authorizations.lotSelect")}
          </label>
          <select
            value={effectiveLotId}
            onChange={(e) => setSelectedLotId(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
          >
            {lots.map((lot) => (
              <option key={lot.id} value={lot.id}>
                {t("lots.block")} {lot.block}, {t("lots.lotNumber")} {lot.lot_number}
              </option>
            ))}
          </select>
        </div>

        <div className="w-full sm:w-48">
          <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
            {t("authorizations.status")}
          </label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white dark:border-slate-700 dark:bg-slate-800 text-slate-900 dark:text-white"
          >
            <option value="">{t("admin.filterAll")}</option>
            <option value="ACTIVE">{t("authorizations.statusActive")}</option>
            <option value="EXPIRED">{t("authorizations.statusExpired")}</option>
            <option value="REVOKED">{t("authorizations.statusRevoked")}</option>
          </select>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="p-8 text-center text-slate-500">{t("authorizations.loading")}</div>
      ) : !authsData || authsData.items.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <ShieldCheck className="mx-auto size-10 text-slate-400 mb-2" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
            {t("authorizations.empty")}
          </p>
        </div>
      ) : (
        <VisitorTable
          authorizations={authsData.items}
          onRevoke={(auth) => setRevokingAuth(auth)}
          onShowQr={(auth) => setQrAuth(auth)}
        />
      )}

      {/* QR Code Modal */}
      <AuthorizationQrModal
        key={qrAuth?.id ?? "none"}
        authorization={qrAuth}
        onClose={() => setQrAuth(null)}
      />

      {/* Creation Modal */}
      <AuthorizationFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateSubmit}
        lotId={effectiveLotId}
        isLoading={createAuthMutation.isPending}
      />

      {/* Revoke Confirmation Modal */}
      {revokingAuth && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-sm rounded-xl border border-red-200 bg-white p-6 shadow-xl dark:border-red-900/50 dark:bg-slate-900">
            <h3 className="text-base font-semibold text-red-600 dark:text-red-400">
              {t("authorizations.revoke")}
            </h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {t("authorizations.confirmRevoke", {
                name: revokingAuth.visitor?.full_name || "Visitante",
              })}
            </p>
            <div className="mt-5 flex justify-end space-x-3">
              <Button variant="outline" size="sm" onClick={() => setRevokingAuth(null)}>
                {t("authorizations.cancel")}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleConfirmRevoke}
                disabled={revokeAuthMutation.isPending}
              >
                {revokeAuthMutation.isPending ? t("residents.saving") : t("authorizations.revoke")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
