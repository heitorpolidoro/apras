import React from "react";
import { useTranslation } from "react-i18next";
import { Car, Building, ShieldAlert, ShieldCheck, Clock, QrCode } from "lucide-react";
import { Button } from "../../../components/ui/button";
import type { VisitorAuthorization } from "../../../types/visitor";

interface VisitorTableProps {
  authorizations: VisitorAuthorization[];
  onRevoke?: (auth: VisitorAuthorization) => void;
  onShowQr?: (auth: VisitorAuthorization) => void;
  canRevoke?: boolean;
}

export const VisitorTable: React.FC<VisitorTableProps> = ({
  authorizations,
  onRevoke,
  onShowQr,
  canRevoke = true,
}) => {
  const { t } = useTranslation();

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400">
            <ShieldCheck className="size-3.5" />
            {t("authorizations.statusActive")}
          </span>
        );
      case "EXPIRED":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-950/50 dark:text-amber-400">
            <Clock className="size-3.5" />
            {t("authorizations.statusExpired")}
          </span>
        );
      case "REVOKED":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 dark:bg-red-950/50 dark:text-red-400">
            <ShieldAlert className="size-3.5" />
            {t("authorizations.statusRevoked")}
          </span>
        );
      default:
        return status;
    }
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-sm">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-muted text-xs font-semibold text-muted-foreground uppercase">
          <tr>
            <th className="px-4 py-3">{t("visitors.fullName")}</th>
            <th className="px-4 py-3">{t("visitors.companyName")}</th>
            <th className="px-4 py-3">{t("visitors.vehiclePlate")}</th>
            <th className="px-4 py-3">{t("authorizations.authType")}</th>
            <th className="px-4 py-3">{t("authorizations.status")}</th>
            <th className="px-4 py-3 text-right">{t("lots.actions")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {authorizations.map((auth) => {
            const visitorName = auth.visitor?.full_name || "N/A";
            const company = auth.visitor?.company_name || "-";
            const plate = auth.visitor?.vehicle_plate || "-";

            return (
              <tr
                key={auth.id}
                className="hover:bg-accent/50 transition-colors"
              >
                <td className="px-4 py-3.5 font-medium text-foreground">
                  <div>{visitorName}</div>
                  {auth.visitor?.cpf && (
                    <div className="text-xs text-muted-foreground">
                      CPF: {auth.visitor.cpf}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3.5 text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Building className="size-3.5 text-muted-foreground" />
                    {company}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-muted-foreground">
                  <span className="inline-flex items-center gap-1 font-mono text-xs">
                    <Car className="size-3.5 text-muted-foreground" />
                    {plate}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-muted-foreground">
                  <span className="text-xs font-semibold uppercase tracking-wider">
                    {auth.auth_type === "SINGLE"
                      ? t("authorizations.single")
                      : t("authorizations.permanent")}
                  </span>
                </td>
                <td className="px-4 py-3.5">{getStatusBadge(auth.status)}</td>
                <td className="px-4 py-3.5 text-right space-x-2 whitespace-nowrap">
                  {onShowQr && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onShowQr(auth)}
                      className="gap-1"
                    >
                      <QrCode className="size-3.5" />
                      {t("authorizations.viewQr")}
                    </Button>
                  )}
                  {canRevoke && auth.status === "ACTIVE" && onRevoke && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onRevoke(auth)}
                      className="text-red-600 border-red-200 hover:bg-red-50 dark:text-red-400 dark:border-red-900/50 dark:hover:bg-red-950/50"
                    >
                      {t("authorizations.revoke")}
                    </Button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
