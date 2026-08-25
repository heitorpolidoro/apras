import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, Search, Users } from "lucide-react";
import { Button } from "../../../components/ui/button";
import {
  useCreateResident,
  useDeactivateResident,
  useLinkResidentUser,
  useLotResidents,
  useUnlinkResidentUser,
  useUpdateResident,
} from "../hooks/useResidents";
import {
  ResidentCreatePayload,
  ResidentDetail,
  ResidentUpdatePayload,
} from "../../../types/resident";
import { ResidentTable } from "./ResidentTable";
import { ResidentFormModal } from "./ResidentFormModal";
import { LinkUserAccountModal } from "./LinkUserAccountModal";

interface ResidentsTabProps {
  lotId: string;
  canManage: boolean;
}

export const ResidentsTab: React.FC<ResidentsTabProps> = ({ lotId, canManage }) => {
  const { t } = useTranslation();
  const { data: residentsData, isLoading, isError } = useLotResidents(lotId);

  const createMutation = useCreateResident();
  const updateMutation = useUpdateResident();
  const deactivateMutation = useDeactivateResident();
  const linkMutation = useLinkResidentUser();
  const unlinkMutation = useUnlinkResidentUser();

  const [searchTerm, setSearchTerm] = useState("");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingResident, setEditingResident] = useState<ResidentDetail | null>(null);

  const [linkingResident, setLinkingResident] = useState<ResidentDetail | null>(null);
  const [deactivatingResident, setDeactivatingResident] = useState<ResidentDetail | null>(null);
  const [unlinkingResident, setUnlinkingResident] = useState<ResidentDetail | null>(null);

  const residents = residentsData?.items || [];
  const filteredResidents = residents.filter(
    (r) =>
      r.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.cpf.includes(searchTerm) ||
      (r.email && r.email.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleOpenCreate = () => {
    setEditingResident(null);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (resident: ResidentDetail) => {
    setEditingResident(resident);
    setIsFormOpen(true);
  };

  const handleFormSubmit = async (data: ResidentCreatePayload | ResidentUpdatePayload) => {
    if (editingResident) {
      await updateMutation.mutateAsync({
        residentId: editingResident.id,
        lotId,
        data: data as ResidentUpdatePayload,
      });
    } else {
      await createMutation.mutateAsync({
        lotId,
        data: data as ResidentCreatePayload,
      });
    }
  };

  const handleConfirmDeactivate = async () => {
    if (deactivatingResident) {
      await deactivateMutation.mutateAsync({
        residentId: deactivatingResident.id,
        lotId,
      });
      setDeactivatingResident(null);
    }
  };

  const handleConfirmUnlink = async () => {
    if (unlinkingResident) {
      await unlinkMutation.mutateAsync({
        residentId: unlinkingResident.id,
        lotId,
      });
      setUnlinkingResident(null);
    }
  };

  const handleLinkUser = async (residentId: string, userId: string) => {
    await linkMutation.mutateAsync({
      residentId,
      userId,
      lotId,
    });
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-500">
        {t("residents.loading")}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 text-center text-red-500">
        {t("residents.loadError")}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 size-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={t("residents.searchPlaceholder")}
            className="w-full rounded-md border border-slate-300 pl-9 pr-3 py-2 text-sm bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
        </div>

        {canManage && (
          <Button onClick={handleOpenCreate} className="gap-2">
            <Plus className="size-4" />
            {t("residents.newResident")}
          </Button>
        )}
      </div>

      {filteredResidents.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <Users className="mx-auto size-10 text-slate-400 mb-2" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
            {t("residents.noResidentsFound")}
          </p>
        </div>
      ) : (
        <ResidentTable
          residents={filteredResidents}
          canManage={canManage}
          onEdit={handleOpenEdit}
          onLinkUser={(r) => setLinkingResident(r)}
          onUnlinkUser={(r) => setUnlinkingResident(r)}
          onDeactivate={(r) => setDeactivatingResident(r)}
        />
      )}

      {/* Form Modal */}
      <ResidentFormModal
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        onSubmit={handleFormSubmit}
        initialData={editingResident}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      {/* Link User Modal */}
      <LinkUserAccountModal
        isOpen={!!linkingResident}
        onClose={() => setLinkingResident(null)}
        resident={linkingResident}
        onLink={handleLinkUser}
        isLoading={linkMutation.isPending}
      />

      {/* Deactivate Confirmation Modal */}
      {deactivatingResident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-sm rounded-xl border border-red-200 bg-white p-6 shadow-xl dark:border-red-900/50 dark:bg-slate-900">
            <h3 className="text-base font-semibold text-red-600 dark:text-red-400">
              {t("residents.deactivateTitle")}
            </h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {t("residents.confirmDeactivate", { name: deactivatingResident.full_name })}
            </p>
            <div className="mt-5 flex justify-end space-x-3">
              <Button variant="outline" size="sm" onClick={() => setDeactivatingResident(null)}>
                {t("residents.cancel")}
              </Button>
              <Button variant="destructive" size="sm" onClick={handleConfirmDeactivate}>
                {t("residents.deactivate")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Unlink Confirmation Modal */}
      {unlinkingResident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-sm rounded-xl border border-amber-200 bg-white p-6 shadow-xl dark:border-amber-900/50 dark:bg-slate-900">
            <h3 className="text-base font-semibold text-amber-600 dark:text-amber-400">
              {t("residents.unlinkTitle")}
            </h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {t("residents.confirmUnlink", { name: unlinkingResident.full_name })}
            </p>
            <div className="mt-5 flex justify-end space-x-3">
              <Button variant="outline" size="sm" onClick={() => setUnlinkingResident(null)}>
                {t("residents.cancel")}
              </Button>
              <Button variant="destructive" size="sm" onClick={handleConfirmUnlink}>
                {t("residents.unlinkAccount")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
