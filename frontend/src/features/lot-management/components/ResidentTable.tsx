import React from "react";
import { useTranslation } from "react-i18next";
import { Edit2, Link as LinkIcon, Mail, Phone, Trash2, Unlink, User as UserIcon } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { type ResidentDetail, ResidentRelationship } from "../../../types/resident";

interface ResidentTableProps {
  residents: ResidentDetail[];
  canManage: boolean;
  onEdit: (resident: ResidentDetail) => void;
  onLinkUser: (resident: ResidentDetail) => void;
  onUnlinkUser: (resident: ResidentDetail) => void;
  onDeactivate: (resident: ResidentDetail) => void;
}

export const ResidentTable: React.FC<ResidentTableProps> = ({
  residents,
  canManage,
  onEdit,
  onLinkUser,
  onUnlinkUser,
  onDeactivate,
}) => {
  const { t } = useTranslation();

  const getRelationshipBadge = (rel: ResidentRelationship) => {
    switch (rel) {
      case ResidentRelationship.TITULAR:
        return (
          <span className="inline-flex items-center rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-700/10 dark:bg-purple-900/30 dark:text-purple-300">
            {t("residents.relTitular")}
          </span>
        );
      case ResidentRelationship.CONJUGE:
        return (
          <span className="inline-flex items-center rounded-md bg-pink-50 px-2 py-1 text-xs font-medium text-pink-700 ring-1 ring-inset ring-pink-700/10 dark:bg-pink-900/30 dark:text-pink-300">
            {t("residents.relConjuge")}
          </span>
        );
      case ResidentRelationship.FILHO_DEPENDENTE:
        return (
          <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10 dark:bg-blue-900/30 dark:text-blue-300">
            {t("residents.relFilho")}
          </span>
        );
      case ResidentRelationship.INQUILINO:
        return (
          <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-300">
            {t("residents.relInquilino")}
          </span>
        );
      case ResidentRelationship.PARENTE:
        return (
          <span className="inline-flex items-center rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-300">
            {t("residents.relParente")}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-md bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-500/10 dark:bg-slate-800 dark:text-slate-400">
            {t("residents.relOutro")}
          </span>
        );
    }
  };

  const formatCpf = (cpf: string) => {
    if (!cpf || cpf.length !== 11) return cpf;
    return `${cpf.slice(0, 3)}.${cpf.slice(3, 6)}.${cpf.slice(6, 9)}-${cpf.slice(9)}`;
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase font-semibold text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
          <tr>
            <th scope="col" className="px-4 py-3">
              {t("residents.name")}
            </th>
            <th scope="col" className="px-4 py-3">
              CPF / RG
            </th>
            <th scope="col" className="px-4 py-3">
              {t("residents.relationship")}
            </th>
            <th scope="col" className="px-4 py-3">
              {t("residents.userAccount")}
            </th>
            <th scope="col" className="px-4 py-3">
              {t("residents.contact")}
            </th>
            <th scope="col" className="px-4 py-3">
              Status
            </th>
            {canManage && (
              <th scope="col" className="px-4 py-3 text-right">
                {t("residents.actions")}
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {residents.map((resident) => (
            <tr key={resident.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
              <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">
                <div className="flex items-center space-x-2">
                  <div className="flex size-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 font-bold text-xs">
                    {resident.full_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <span>{resident.full_name}</span>
                    {resident.notes && (
                      <p className="text-xs text-slate-400 font-normal">{resident.notes}</p>
                    )}
                  </div>
                </div>
              </td>
              <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                <div>{formatCpf(resident.cpf)}</div>
                {resident.rg && <div className="text-[11px]">RG: {resident.rg}</div>}
              </td>
              <td className="px-4 py-3">{getRelationshipBadge(resident.relationship_type)}</td>
              <td className="px-4 py-3">
                {resident.user ? (
                  <div className="flex items-center space-x-1 text-xs text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-1 rounded border border-emerald-200 dark:border-emerald-800/50 w-fit">
                    <UserIcon className="size-3" />
                    <span className="font-medium">{resident.user.full_name}</span>
                  </div>
                ) : (
                  <span className="inline-flex items-center text-xs text-slate-400 italic">
                    {t("residents.unlinked")}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 space-y-0.5">
                {resident.phone && (
                  <div className="flex items-center space-x-1">
                    <Phone className="size-3 text-slate-400" />
                    <span>{resident.phone}</span>
                  </div>
                )}
                {resident.email && (
                  <div className="flex items-center space-x-1">
                    <Mail className="size-3 text-slate-400" />
                    <span>{resident.email}</span>
                  </div>
                )}
                {!resident.phone && !resident.email && <span>-</span>}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                    resident.is_active
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                      : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                  }`}
                >
                  {resident.is_active ? t("residents.active") : t("residents.inactive")}
                </span>
              </td>
              {canManage && (
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit(resident)}
                      title={t("residents.edit")}
                      aria-label={t("residents.edit")}
                    >
                      <Edit2 className="size-4 text-slate-600 dark:text-slate-300" />
                    </Button>
                    {resident.user ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onUnlinkUser(resident)}
                        title={t("residents.unlinkUser")}
                        aria-label={t("residents.unlinkUser")}
                      >
                        <Unlink className="size-4 text-amber-600 dark:text-amber-400" />
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onLinkUser(resident)}
                        title={t("residents.linkUser")}
                        aria-label={t("residents.linkUser")}
                      >
                        <LinkIcon className="size-4 text-emerald-600 dark:text-emerald-400" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDeactivate(resident)}
                      title={t("residents.deactivate")}
                      aria-label={t("residents.deactivate")}
                    >
                      <Trash2 className="size-4 text-red-600 dark:text-red-400" />
                    </Button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
