import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, X } from "lucide-react";
import { useIssueInvitation, useTenantInvitations } from "../../../hooks/useInvitations";
import { invitationStatus } from "../../../types/invitations";
import type { Invitation, InvitationStatus } from "../../../types/invitations";
import type { Tenant } from "../../../types/auth";

/**
 * One condominium's invitations (APRAS-72 D2–D4).
 *
 * A side panel and not a second table on the screen:
 * `GET /api/v1/invitations?tenant_id=<id>` is the only list APRAS-71 offers,
 * and rendering every condominium's invitations inline would multiply the
 * requests by the row count for information that is one badge wide.
 *
 * **No revoke control is drawn**, deliberately (D4): there is no `revoked_at`
 * column and no route to call, so a control here would need a backend change
 * this task must not make. Re-issuing supersedes instead.
 */

const BADGE_CLASSES: Record<InvitationStatus, string> = {
  pending:
    "inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700",
  accepted:
    "inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700",
  expired:
    "inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground",
};

/** The three states of D3, each with its own colour so they never read alike. */
export const InvitationStatusBadge: React.FC<{ status: InvitationStatus }> = ({
  status,
}) => {
  const { t } = useTranslation();
  return (
    <span className={BADGE_CLASSES[status]}>
      {t(`invitations.status.${status}`)}
    </span>
  );
};

interface Props {
  tenant: Tenant;
  onClose: () => void;
}

const TenantInvitationsPanel: React.FC<Props> = ({ tenant, onClose }) => {
  const { t, i18n } = useTranslation();
  const { data, isPending, isError } = useTenantInvitations(tenant.id);
  const issue = useIssueInvitation();
  // Which row is being re-issued. `issue.isPending` alone would put the
  // pending label on every resendable row at once.
  const [resendingId, setResendingId] = useState<string | null>(null);

  const formatDate = (isoString: string) =>
    new Date(isoString).toLocaleDateString(i18n.language);

  /**
   * D4: resend is the *same* issuance call with the same pair. The backend
   * supersedes the previous row, so after the invalidation the panel shows it
   * as expired next to a fresh pending one.
   */
  const resend = (invitation: Invitation) => {
    setResendingId(invitation.id);
    issue.mutate(
      { tenant_id: invitation.tenant_id, email: invitation.email },
      { onSettled: () => setResendingId(null) },
    );
  };

  return (
    <aside
      data-testid="invitation-panel"
      className="flex flex-col gap-4 rounded-xl border border-border p-5"
    >
      <div className="flex items-start gap-3">
        <h2 className="mr-auto text-lg font-semibold text-foreground">
          {t("invitations.panel.title", { tenant: tenant.name })}
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("invitations.panel.close")}
          className="rounded-md border border-border p-1 text-muted-foreground"
        >
          <X className="size-4" />
        </button>
      </div>

      {isPending && <p>{t("invitations.panel.loading")}</p>}
      {isError && <p role="alert">{t("invitations.panel.loadError")}</p>}
      {data && data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          {t("invitations.panel.empty")}
        </p>
      )}

      {data && data.length > 0 && (
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-2">{t("invitations.panel.columns.email")}</th>
              <th className="px-3 py-2">
                {t("invitations.panel.columns.status")}
              </th>
              <th className="px-3 py-2">
                {t("invitations.panel.columns.sentAt")}
              </th>
              <th className="px-3 py-2">
                {t("invitations.panel.columns.expiresAt")}
              </th>
              <th className="px-3 py-2 text-right">
                {t("invitations.panel.columns.actions")}
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((invitation) => {
              const status = invitationStatus(invitation);
              return (
                <tr
                  key={invitation.id}
                  data-testid={`invitation-row-${invitation.id}`}
                >
                  <td className="px-3 py-2 font-medium">{invitation.email}</td>
                  <td className="px-3 py-2">
                    <InvitationStatusBadge status={status} />
                    {invitation.accepted_at && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {t("invitations.panel.acceptedOn", {
                          date: formatDate(invitation.accepted_at),
                        })}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {formatDate(invitation.created_at)}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {formatDate(invitation.expires_at)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {status === "accepted" ? (
                      <span className="text-xs text-muted-foreground">
                        {t("invitations.panel.noAction")}
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => resend(invitation)}
                        disabled={issue.isPending}
                        data-testid={`resend-${invitation.id}`}
                        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium disabled:opacity-50"
                      >
                        <RefreshCw className="size-3.5" />
                        {resendingId === invitation.id
                          ? t("invitations.panel.resending")
                          : t("invitations.panel.resend")}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </aside>
  );
};

export default TenantInvitationsPanel;
