import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { MailPlus, X } from "lucide-react";
import { useIssueInvitation } from "../../../hooks/useInvitations";
import { parseApiError } from "../../../api/errors";
import type { Tenant } from "../../../types/auth";

/**
 * "Invite administrator" (APRAS-72 D1b).
 *
 * One required email, one optional full name, `POST /api/v1/invitations`.
 * The invited person becomes that condominium's **administrator in the
 * system** (`is_tenant_admin`) — a system role, not one of the condominium's
 * elected offices, which this flow never grants.
 *
 * The dialog is opened from two places with the same props: a table row, and
 * the post-create success panel with the freshly created condominium already
 * chosen. It therefore takes the tenant as a prop and offers no picker.
 *
 * `full_name` is the mail's courtesy greeting only and is not stored
 * (`InvitationCreate`), so an empty box is **omitted from the body** rather
 * than sent as `""`.
 */

/** `EmailStr` refuses a malformed address with a 422. */
const isInvalidEmail = (error: unknown): boolean =>
  (error as { response?: { status?: number } })?.response?.status === 422;

interface Props {
  tenant: Tenant;
  onClose: () => void;
}

const InviteAdministratorDialog: React.FC<Props> = ({ tenant, onClose }) => {
  const { t } = useTranslation();
  const issue = useIssueInvitation();

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    const address = email.trim();
    const name = fullName.trim();
    issue.mutate(
      {
        tenant_id: tenant.id,
        email: address,
        ...(name === "" ? {} : { full_name: name }),
      },
      {
        onSuccess: () => setSentTo(address),
        onError: (cause) => {
          setError(
            isInvalidEmail(cause)
              ? t("invitations.dialog.invalidEmail")
              : parseApiError(cause, t, {
                  validationError: "invitations.dialog.validationError",
                  genericError: "invitations.dialog.genericError",
                }),
          );
        },
      },
    );
  };

  return (
    <div
      data-testid="invite-administrator-dialog"
      className="flex max-w-xl flex-col gap-4 rounded-xl border border-border p-5"
    >
      <div className="flex items-start gap-3">
        <h2 className="mr-auto text-lg font-semibold text-foreground">
          {t("invitations.dialog.title")}
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("invitations.dialog.close")}
          className="rounded-md border border-border p-1 text-muted-foreground"
        >
          <X className="size-4" />
        </button>
      </div>

      <p className="text-sm text-muted-foreground">
        {t("invitations.dialog.tenantLabel")}{" "}
        <strong data-testid="invite-dialog-tenant" className="text-foreground">
          {tenant.name}
        </strong>
      </p>

      {sentTo ? (
        <div
          data-testid="invitation-sent"
          className="flex flex-col gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4"
        >
          <p className="text-sm font-semibold text-emerald-900">
            {t("invitations.dialog.successTitle")}
          </p>
          <p className="text-sm text-emerald-900">
            {t("invitations.dialog.successBody", {
              email: sentTo,
              tenant: tenant.name,
            })}
          </p>
          <div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground"
            >
              {t("invitations.dialog.done")}
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1" htmlFor="invitation-email">
            <span className="text-sm font-medium text-foreground">
              {t("invitations.dialog.emailLabel")}
            </span>
            <input
              id="invitation-email"
              type="email"
              value={email}
              onChange={(event) => {
                setError(null);
                setEmail(event.target.value);
              }}
              className="rounded-md border border-border px-3 py-2 text-sm"
            />
          </label>
          {error && (
            <p role="alert" className="text-xs font-medium text-destructive">
              {error}
            </p>
          )}
          <label className="flex flex-col gap-1" htmlFor="invitation-full-name">
            <span className="text-sm font-medium text-foreground">
              {t("invitations.dialog.fullNameLabel")}
            </span>
            <input
              id="invitation-full-name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              className="rounded-md border border-border px-3 py-2 text-sm"
            />
          </label>
          <p className="text-xs text-muted-foreground">
            {t("invitations.dialog.hint")}
          </p>
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium"
            >
              {t("invitations.dialog.cancel")}
            </button>
            <button
              type="submit"
              disabled={email.trim() === "" || issue.isPending}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
            >
              <MailPlus className="size-4" />
              {issue.isPending
                ? t("invitations.dialog.submitting")
                : t("invitations.dialog.submit")}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default InviteAdministratorDialog;
