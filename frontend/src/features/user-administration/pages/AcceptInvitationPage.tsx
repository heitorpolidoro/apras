import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { acceptInvitation, previewInvitation } from "../../../api/invitations";
import { parseApiError } from "../../../api/errors";
import { useAuth } from "../context/AuthContext";
import type {
  InvitationAccept,
  InvitationPreview,
  InvitationToken,
} from "../../../types/invitations";

/**
 * The public acceptance page at `/invite?token=…` (APRAS-72 D5–D7).
 *
 * The route is not a choice this page gets to make: APRAS-71 already prints
 * and mails `<origin>/invite?token=…`. It sits **outside** `ProtectedRoute`,
 * beside `/login` and `/reset-password`, and therefore has no `ROUTE_ACCESS`
 * entry and no navigation entry — `Navbar` returns `null` when
 * unauthenticated, so the page renders chrome-free.
 *
 * **The rule this file is organised around:** the preview's `account_exists`
 * decides only **which form is rendered**; what happens after a successful
 * accept is decided **solely by the accept response status** (D6). The two
 * calls happen at different moments and can legitimately disagree — the
 * invitee can sign up between them — so branching on `account_exists` after
 * the accept would be wrong even where it appears to work. Concretely,
 * `login(undefined, false)` is not a no-op: it writes the literal string
 * `"undefined"` into `sessionStorage`, `/auth/me` then fails, and the person
 * lands back on `/login` with no explanation.
 */

/**
 * The terminal states, each rendering a message and no form at all.
 *
 * `missingLink` and `invalid` are kept apart on purpose. `invalid` is the
 * backend's `404` — no such invitation. `missingLink` is "this page was
 * opened without the token in the URL", which since the scrub below is
 * mostly a **reload of a perfectly good invitation**, so its copy must send
 * the person back to their mailbox and must never ask them to request a new
 * invitation: re-issuing supersedes the valid token they still hold
 * (APRAS-71 D4 sets the old row's `expires_at` to now).
 */
type Terminal =
  | "missingLink"
  | "invalid"
  | "expired"
  | "used"
  | "linked"
  | "error";

const statusOf = (error: unknown): number | undefined =>
  (error as { response?: { status?: number } })?.response?.status;

/** D7: the preview's three failures map one-to-one onto terminal states. */
const terminalForStatus = (status: number | undefined): Terminal => {
  if (status === 404) return "invalid";
  if (status === 410) return "expired";
  if (status === 409) return "used";
  return "error";
};

const AcceptInvitationPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [searchParams] = useSearchParams();
  /**
   * The token, normalised **once** so the whole file has a single predicate
   * for "there is no token": `token === null`.
   *
   * `?token=` — the parameter present and empty — is the same fact as no
   * parameter at all, and folding it here is what keeps the effect's guard
   * and the terminal-state derivation below from disagreeing. When they
   * disagreed (`!token` in one, `=== null` in the other) an empty value made
   * the effect correctly decline to call while the render waited forever for
   * a call that would never come. Two predicates for one concept is the
   * defect; there is now one value and one predicate.
   */
  const token = searchParams.get("token") || null;

  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [terminal, setTerminal] = useState<Terminal | null>(null);
  const [linkedTenant, setLinkedTenant] = useState("");

  const [fullName, setFullName] = useState("");
  const [cpf, setCpf] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [cpfError, setCpfError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // One preview per mount. The ref is what keeps StrictMode's double effect
  // from spending two of the five requests a minute the route allows.
  const previewed = useRef(false);

  useEffect(() => {
    // No token, no request: there is nothing to ask about, and the invalid
    // state is *derived* below rather than stored, so the effect has no
    // synchronous state write at all.
    if (token === null || previewed.current) return;
    previewed.current = true;

    // The token arrives in the URL because that is the shape APRAS-71 mails,
    // and it mints a condominium administrator. Replacing the entry keeps it
    // out of browser history and out of the `Referer` of anything this page
    // loads afterwards. It is already captured in a local, and the router's
    // own location is untouched, so the page keeps working.
    window.history.replaceState(window.history.state, "", "/invite");

    previewInvitation(token)
      .then(setPreview)
      .catch((cause: unknown) =>
        setTerminal(terminalForStatus(statusOf(cause))),
      );
  }, [token]);

  /**
   * D7: a `409` on accept is either a duplicate CPF or a token consumed
   * meanwhile. It is told apart by re-issuing the **preview** rather than by
   * reading the backend's English `detail`. Only this rare path pays for the
   * extra request.
   */
  const disambiguateConflict = useCallback(async () => {
    try {
      await previewInvitation(token as string);
      // The token is alive, so the conflict was the CPF — which only the
      // new-account form can cause: the existing-account branch sends no
      // `cpf` at all, and `InvitationCpfConflictError` is raised from
      // `_create_user` alone. The CPF field is therefore always on screen
      // when this line runs.
      setCpfError(t("acceptInvitation.newAccount.cpfConflict"));
    } catch (cause: unknown) {
      setTerminal(terminalForStatus(statusOf(cause)));
    }
  }, [t, token]);

  const submitAccept = useCallback(
    async (payload: InvitationAccept) => {
      setFormError(null);
      setCpfError(null);
      setIsSubmitting(true);
      try {
        const { status, data } = await acceptInvitation(payload);
        if (status === 201) {
          // The only branch that carries a credential.
          await login((data as InvitationToken).access_token, false);
          navigate("/", { replace: true });
          return;
        }
        // 200: an `InvitationPreview` body, no credential, nothing stored.
        setLinkedTenant((data as InvitationPreview).tenant_name);
        setTerminal("linked");
      } catch (cause: unknown) {
        const status = statusOf(cause);
        if (status === 410) {
          setTerminal("expired");
        } else if (status === 409) {
          await disambiguateConflict();
        } else {
          setFormError(
            parseApiError(cause, t, {
              validationError: "acceptInvitation.validationError",
              genericError: "acceptInvitation.genericError",
            }),
          );
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [disambiguateConflict, login, navigate, t],
  );

  const submitNewAccount = (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setFormError(t("acceptInvitation.newAccount.passwordMismatch"));
      return;
    }
    void submitAccept({
      token: token as string,
      full_name: fullName.trim(),
      cpf,
      password,
    });
  };

  const submitExistingAccount = (event: React.FormEvent) => {
    event.preventDefault();
    // The token alone: `full_name`, `cpf` and `password` are ignored by the
    // existing-account branch, so none is rendered and none is sent.
    void submitAccept({ token: token as string });
  };

  const loginLink = (
    <Link
      to="/login"
      className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
    >
      {t("acceptInvitation.goToLogin")}
    </Link>
  );

  const shell = (children: React.ReactNode) => (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary-text tracking-tight">
            {t("common.appName")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("acceptInvitation.title")}
          </p>
        </div>
        <div className="flex flex-col gap-5 rounded-xl border bg-card p-6 shadow-sm">
          {children}
        </div>
      </div>
    </div>
  );

  // Derived, not stored: a missing token is a property of the URL, and the
  // two could otherwise drift for one render.
  const state: Terminal | null = token === null ? "missingLink" : terminal;

  if (state === "linked") {
    return shell(
      <div data-testid="invitation-linked" className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-foreground">
          {t("acceptInvitation.linked.title")}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t("acceptInvitation.linked.body", { tenant: linkedTenant })}
        </p>
        {loginLink}
      </div>,
    );
  }

  if (state !== null) {
    return shell(
      <div
        data-testid={`invitation-${state}`}
        role="alert"
        className="flex flex-col gap-4"
      >
        <h2 className="text-lg font-semibold text-foreground">
          {t(`acceptInvitation.${state}.title`)}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t(`acceptInvitation.${state}.body`)}
        </p>
        {state === "used" && loginLink}
      </div>,
    );
  }

  // Neither decided yet: the preview is still in flight. There is no
  // separate `isLoading` flag, so no state can contradict this one.
  if (preview === null) return shell(<p>{t("acceptInvitation.loading")}</p>);

  const details = (
    <dl
      data-testid="invitation-preview"
      className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm"
    >
      <dt className="text-muted-foreground">
        {t("acceptInvitation.tenantLabel")}
      </dt>
      <dd className="font-semibold text-foreground">{preview.tenant_name}</dd>
      <dt className="text-muted-foreground">
        {t("acceptInvitation.slugLabel")}
      </dt>
      <dd>
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
          {preview.tenant_slug}
        </code>
      </dd>
      <dt className="text-muted-foreground">
        {t("acceptInvitation.inviterLabel")}
      </dt>
      <dd className="text-foreground">{preview.invited_by_name}</dd>
      <dt className="text-muted-foreground">
        {t("acceptInvitation.emailLabel")}
      </dt>
      <dd className="text-foreground">{preview.email}</dd>
      <dt className="text-muted-foreground">
        {t("acceptInvitation.expiresLabel")}
      </dt>
      <dd className="text-foreground">
        {new Date(preview.expires_at).toLocaleDateString(i18n.language)}
      </dd>
    </dl>
  );

  if (preview.account_exists) {
    return shell(
      <>
        {details}
        <p className="text-sm text-foreground">
          {t("acceptInvitation.existingAccount.intro", {
            tenant: preview.tenant_name,
          })}
        </p>
        <p className="rounded-md border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
          {t("acceptInvitation.existingAccount.notice")}
        </p>
        {formError && (
          <p role="alert" className="text-xs font-medium text-destructive">
            {formError}
          </p>
        )}
        <form onSubmit={submitExistingAccount}>
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
          >
            {isSubmitting
              ? t("acceptInvitation.existingAccount.submitting")
              : t("acceptInvitation.existingAccount.submit")}
          </button>
        </form>
      </>,
    );
  }

  const incomplete =
    fullName.trim() === "" ||
    cpf.trim() === "" ||
    password === "" ||
    confirmPassword === "";

  return shell(
    <>
      {details}
      <p className="text-sm text-foreground">
        {t("acceptInvitation.newAccount.intro")}
      </p>
      <form onSubmit={submitNewAccount} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1" htmlFor="invite-full-name">
          <span className="text-sm font-medium text-foreground">
            {t("acceptInvitation.newAccount.fullNameLabel")}
          </span>
          <input
            id="invite-full-name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1" htmlFor="invite-cpf">
          <span className="text-sm font-medium text-foreground">
            {t("acceptInvitation.newAccount.cpfLabel")}
          </span>
          <input
            id="invite-cpf"
            value={cpf}
            onChange={(event) => {
              setCpfError(null);
              setCpf(event.target.value);
            }}
            className="rounded-md border border-border px-3 py-2 text-sm"
          />
        </label>
        {cpfError && (
          <p role="alert" className="text-xs font-medium text-destructive">
            {cpfError}
          </p>
        )}
        <label className="flex flex-col gap-1" htmlFor="invite-password">
          <span className="text-sm font-medium text-foreground">
            {t("acceptInvitation.newAccount.passwordLabel")}
          </span>
          <input
            id="invite-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1" htmlFor="invite-confirm">
          <span className="text-sm font-medium text-foreground">
            {t("acceptInvitation.newAccount.confirmPasswordLabel")}
          </span>
          <input
            id="invite-confirm"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
          />
        </label>
        {formError && (
          <p role="alert" className="text-xs font-medium text-destructive">
            {formError}
          </p>
        )}
        <button
          type="submit"
          disabled={incomplete || isSubmitting}
          className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
        >
          {isSubmitting
            ? t("acceptInvitation.newAccount.submitting")
            : t("acceptInvitation.newAccount.submit")}
        </button>
      </form>
    </>,
  );
};

export default AcceptInvitationPage;
