import React from "react";
import { useTranslation } from "react-i18next";
import { Eye, Pencil, Trash2, UserPlus } from "lucide-react";
import type { Lot } from "../../../types/lot";
import { LotStatus } from "../../../types/lot";
import { Button } from "../../../components/ui/button";

interface LotTableProps {
  lots: Lot[];
  onViewDetails: (lot: Lot) => void;
  onEdit: (lot: Lot) => void;
  onLinkUser: (lot: Lot) => void;
  onDelete: (lot: Lot) => void;
  canManage: boolean;
  canDelete: boolean;
}

export const LotTable: React.FC<LotTableProps> = ({
  lots,
  onViewDetails,
  onEdit,
  onLinkUser,
  onDelete,
  canManage,
  canDelete,
}) => {
  const { t } = useTranslation();

  const getStatusBadge = (status: LotStatus) => {
    switch (status) {
      case LotStatus.VACANT:
        return (
          <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
            {t("lots.statusVacant")}
          </span>
        );
      case LotStatus.OCCUPIED:
        return (
          <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
            {t("lots.statusOccupied")}
          </span>
        );
      case LotStatus.UNDER_CONSTRUCTION:
        return (
          <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
            {t("lots.statusUnderConstruction")}
          </span>
        );
      default:
        return status;
    }
  };

  if (lots.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground">
        {t("lots.empty")}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
      <table className="w-full text-left text-sm text-muted-foreground">
        <thead className="border-b border-border bg-muted text-xs uppercase font-semibold text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-3">
              {t("lots.block")}
            </th>
            <th scope="col" className="px-4 py-3">
              {t("lots.lotNumber")}
            </th>
            <th scope="col" className="px-4 py-3">
              {t("lots.address")}
            </th>
            <th scope="col" className="px-4 py-3">
              {t("lots.postalCode")}
            </th>
            <th scope="col" className="px-4 py-3">
              {t("lots.areaSqm")}
            </th>
            <th scope="col" className="px-4 py-3">
              {t("lots.fractionIdeal")}
            </th>
            <th scope="col" className="px-4 py-3">
              {t("lots.status")}
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              {t("lots.actions")}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {lots.map((lot) => (
            <tr
              key={lot.id}
              className="hover:bg-accent transition-colors"
            >
              <td className="px-4 py-3 font-semibold text-foreground">
                {lot.block}
              </td>
              <td className="px-4 py-3 font-medium text-foreground">
                {lot.lot_number}
              </td>
              <td className="px-4 py-3 text-muted-foreground max-w-xs truncate">
                {lot.address || "-"}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {lot.postal_code || "-"}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {lot.area_sqm !== null && lot.area_sqm !== undefined
                  ? `${lot.area_sqm} m²`
                  : "-"}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {lot.fraction_ideal !== null && lot.fraction_ideal !== undefined
                  ? lot.fraction_ideal
                  : "-"}
              </td>
              <td className="px-4 py-3">{getStatusBadge(lot.status)}</td>
              <td className="px-4 py-3 text-right">
                <div className="flex items-center justify-end space-x-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onViewDetails(lot)}
                    title={t("lots.lotDetails")}
                    aria-label={t("lots.lotDetails")}
                  >
                    <Eye className="size-4 text-muted-foreground" />
                  </Button>

                  {canManage && (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onLinkUser(lot)}
                        title={t("lots.linkUser")}
                        aria-label={t("lots.linkUser")}
                      >
                        <UserPlus className="size-4 text-blue-600 dark:text-blue-400" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onEdit(lot)}
                        title={t("lots.editLot")}
                        aria-label={t("lots.editLot")}
                      >
                        <Pencil className="size-4 text-amber-600 dark:text-amber-400" />
                      </Button>
                    </>
                  )}

                  {canDelete && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(lot)}
                      title={t("lots.delete")}
                      aria-label={t("lots.delete")}
                    >
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
