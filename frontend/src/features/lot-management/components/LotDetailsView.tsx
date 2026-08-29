import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeft, UserPlus, Trash2, Mail } from "lucide-react";
import { useLotDetail, useUnlinkUserLot } from "../hooks/useLots";
import { LotAssociationType, LotStatus } from "../../../types/lot";
import { Button } from "../../../components/ui/button";
import { ResidentsTab } from "./ResidentsTab";

interface LotDetailsViewProps {
  lotId: string;
  onBack: () => void;
  onLinkUser: () => void;
  canManage: boolean;
}

export const LotDetailsView: React.FC<LotDetailsViewProps> = ({
  lotId,
  onBack,
  onLinkUser,
  canManage,
}) => {
  const { t } = useTranslation();
  const { data: lot, isLoading, isError } = useLotDetail(lotId);
  const unlinkMutation = useUnlinkUserLot();

  const [activeTab, setActiveTab] = useState<"users" | "residents">("users");
  const [userToUnlink, setUserToUnlink] = useState<{ id: string; name: string } | null>(null);


  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-500">
        {t("lots.loading")}
      </div>
    );
  }

  if (isError || !lot) {
    return (
      <div className="p-8 text-center text-red-500">
        Erro ao carregar detalhes do lote.
      </div>
    );
  }

  const handleConfirmUnlink = async () => {
    if (userToUnlink) {
      await unlinkMutation.mutateAsync({ id: lotId, userId: userToUnlink.id });
      setUserToUnlink(null);
    }
  };

  const getAssocBadge = (type: LotAssociationType) => {
    switch (type) {
      case LotAssociationType.PROPRIETARIO:
        return (
          <span className="inline-flex items-center rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-600/20 dark:bg-purple-900/30 dark:text-purple-300">
            {t("lots.assocProprietario")}
          </span>
        );
      case LotAssociationType.INQUILINO:
        return (
          <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10 dark:bg-blue-900/30 dark:text-blue-300">
            {t("lots.assocInquilino")}
          </span>
        );
      case LotAssociationType.RESPONSAVEL_FINANCEIRO:
        return (
          <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-300">
            {t("lots.assocRespFinanceiro")}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-md bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-500/10 dark:bg-slate-800 dark:text-slate-400">
            {t("lots.assocOutro")}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={onBack} className="gap-2">
          <ArrowLeft className="size-4" />
          {t("lots.backToList")}
        </Button>
        {canManage && (
          <Button onClick={onLinkUser} className="gap-2">
            <UserPlus className="size-4" />
            {t("lots.linkUser")}
          </Button>
        )}
      </div>

      {/* Lot Info Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              {t("lots.block")} {lot.block} — {t("lots.lotNumber")} {lot.lot_number}
            </h2>
            {lot.address && (
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                {lot.address} {lot.postal_code ? `(${lot.postal_code})` : ""}
              </p>
            )}
          </div>
          <div>
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                lot.status === LotStatus.VACANT
                  ? "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300"
                  : lot.status === LotStatus.OCCUPIED
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                  : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
              }`}
            >
              {lot.status === LotStatus.VACANT
                ? t("lots.statusVacant")
                : lot.status === LotStatus.OCCUPIED
                ? t("lots.statusOccupied")
                : t("lots.statusUnderConstruction")}
            </span>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <span className="block text-xs font-medium text-slate-500 dark:text-slate-400">
              {t("lots.areaSqm")}
            </span>
            <span className="font-medium text-slate-900 dark:text-white">
              {lot.area_sqm ? `${lot.area_sqm} m²` : "-"}
            </span>
          </div>
          <div>
            <span className="block text-xs font-medium text-slate-500 dark:text-slate-400">
              {t("lots.fractionIdeal")}
            </span>
            <span className="font-medium text-slate-900 dark:text-white">
              {lot.fraction_ideal ?? "-"}
            </span>
          </div>
          <div className="col-span-2">
            <span className="block text-xs font-medium text-slate-500 dark:text-slate-400">
              {t("lots.notes")}
            </span>
            <span className="font-medium text-slate-900 dark:text-white">
              {lot.notes || "-"}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav className="-mb-px flex space-x-6" aria-label="Tabs">
          <button
            type="button"
            onClick={() => setActiveTab("users")}
            className={`whitespace-nowrap pb-4 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === "users"
                ? "border-emerald-600 text-emerald-600 dark:border-emerald-400 dark:text-emerald-400"
                : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
            }`}
          >
            {t("lots.linkedUsersTab")} ({lot.users.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("residents")}
            className={`whitespace-nowrap pb-4 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === "residents"
                ? "border-emerald-600 text-emerald-600 dark:border-emerald-400 dark:text-emerald-400"
                : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
            }`}
          >
            {t("residents.residentsTab")}
          </button>
        </nav>
      </div>

      {activeTab === "residents" ? (
        <ResidentsTab lotId={lotId} canManage={canManage} />
      ) : (
        /* Linked Users Table */
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            {t("lots.linkedUsers")} ({lot.users.length})
          </h3>

          {lot.users.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t("lots.noLinkedUsers")}
            </p>
          ) : (

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase font-semibold text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                <tr>
                  <th scope="col" className="px-4 py-3">
                    Usuário
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Associação
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Papel no Sistema
                  </th>
                  {canManage && (
                    <th scope="col" className="px-4 py-3 text-right">
                      {t("lots.actions")}
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {lot.users.map((link) => (
                  <tr key={link.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center space-x-3">
                        <div className="flex size-8 items-center justify-center rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 font-semibold text-xs">
                          {link.user.full_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold text-slate-900 dark:text-white">
                              {link.user.full_name}
                            </span>
                            {link.is_primary && (
                              <span className="inline-flex items-center rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-amber-800 dark:bg-amber-900/50 dark:text-amber-300">
                                {t("lots.primaryTag")}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center text-xs text-slate-500 space-x-1">
                            <Mail className="size-3" />
                            <span>{link.user.email}</span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">{getAssocBadge(link.association_type)}</td>
                    <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                      {link.user.role}
                    </td>
                    {canManage && (
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setUserToUnlink({ id: link.user.id, name: link.user.full_name })
                          }
                          title={t("lots.unlinkUser")}
                          aria-label={t("lots.unlinkUser")}
                        >
                          <Trash2 className="size-4 text-red-600 dark:text-red-400" />
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      )}

      {userToUnlink && (

        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-sm rounded-xl border border-red-200 bg-white p-6 shadow-xl dark:border-red-900/50 dark:bg-slate-900">
            <h3 className="text-base font-semibold text-red-600 dark:text-red-400">
              {t("lots.unlinkUser")}
            </h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {t("lots.confirmUnlink", { name: userToUnlink.name })}
            </p>
            <div className="mt-5 flex justify-end space-x-3">
              <Button variant="outline" size="sm" onClick={() => setUserToUnlink(null)}>
                {t("lots.cancel")}
              </Button>
              <Button variant="destructive" size="sm" onClick={handleConfirmUnlink}>
                {t("lots.unlinkUser")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
