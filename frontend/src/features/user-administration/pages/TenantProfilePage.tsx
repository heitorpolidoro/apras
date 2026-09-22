import React, { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  Image as ImageIcon,
  Landmark,
  Link2,
  Trash2,
  Upload,
  Wand2,
  XCircle,
} from "lucide-react";
import {
  TENANT_LOGO_ACCEPT,
  TENANT_LOGO_ALLOWED_MIME_TYPES,
  TENANT_LOGO_MAX_FILE_SIZE_BYTES,
  isValidSlug,
  slugifyName,
} from "../../../api/tenantProfile";
import {
  useClearTenantLogo,
  useSetTenantLogo,
  useTenantProfile,
  useUpdateTenantProfile,
} from "../../../hooks/useTenantProfile";
import { Spinner } from "../../../components/ui/spinner";
import TenantBrandColors from "../components/TenantBrandColors";

/**
 * "Perfil do condomínio" — the screen behind `/admin/tenant-profile`
 * (APRAS-61).
 *
 * The condominium's name and the **logo** every document the system renders
 * puts in its masthead. Before this screen, `tenant.logo_url` was a column an
 * operator wrote with SQL.
 *
 * **A refused file never reaches the network.** Type and size are checked here
 * first, which is not a duplicate of the server's check but the point of D2:
 * the accepted set exists so that certain bytes are never served from our own
 * origin, and the cheapest place to keep them out is before the request. The
 * server checks again — and adds a Pillow decode the browser cannot do — so a
 * client that skips this is still refused, with a 422 this page translates.
 *
 * The permission gate is the **route's**, not a second one here:
 * `ProtectedRoute` reads `ROUTE_ACCESS["/admin/tenant-profile"]` and renders
 * `RestrictedAccessMessage` in place, so a caller without
 * `tenants:profile_update` never mounts this component and never sees an
 * upload control.
 */

/** In MB, for the hint and the two refusal messages. Derived from the pinned
 *  byte constant so the copy cannot drift from the cap. */
const MAX_MB = TENANT_LOGO_MAX_FILE_SIZE_BYTES / (1024 * 1024);

/** The status a failed write reports, mapped to the key that explains it.
 *  `null` for anything unexpected, which falls back to the generic message. */
const errorKeyOf = (error: unknown): string => {
  const status = (error as { response?: { status?: number } })?.response
    ?.status;
  if (status === 409) return "tenantProfile.errors.conflict";
  if (status === 422) return "tenantProfile.errors.rejected";
  if (status === 403) return "tenantProfile.errors.forbidden";
  return "tenantProfile.errors.generic";
};

/** The same mapping for a write that carried a **slug**: the two statuses
 *  mean something else there — taken, and malformed — and the message belongs
 *  beside the field rather than in the page-level banner. */
const slugErrorKeyOf = (error: unknown): string => {
  const status = (error as { response?: { status?: number } })?.response
    ?.status;
  if (status === 409) return "tenantProfile.errors.slugTaken";
  if (status === 422) return "tenantProfile.errors.slugInvalid";
  return errorKeyOf(error);
};

const TenantProfilePage: React.FC = () => {
  const { t } = useTranslation();
  const { data, isPending } = useTenantProfile();
  const update = useUpdateTenantProfile();
  const setLogo = useSetTenantLogo();
  const clearLogo = useClearTenantLogo();

  // Only the operator's *edit*, never a copy of the server's answer: the
  // rendered value falls back to `data.name`, so there is no effect
  // synchronising two sources of truth and no window in which they disagree.
  //
  // The tenant id is carried **with** the draft rather than watched by an
  // effect that clears it: a tenant switch replaces the payload under the
  // same query key, and a draft typed against the previous condominium must
  // not survive it. Comparing ids makes that a render-time derivation instead
  // of a state write inside `useEffect`.
  const [draft, setDraft] = useState<{
    id: string;
    name: string;
    slug: string;
  } | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [slugErrorKey, setSlugErrorKey] = useState<string | null>(null);
  // D-G: the confirmation is a **client-side** guard. The API has no
  // confirmation parameter, so this is state and not a request field.
  const [confirming, setConfirming] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  if (isPending || !data) return <Spinner />;

  const current = draft?.id === data.id ? draft : { ...data };
  const name = current.name;
  const slug = current.slug;
  const slugChanged = slug !== data.slug;
  const slugMalformed = !isValidSlug(slug);

  const announce = (key: string) => {
    setErrorKey(null);
    setSavedKey(key);
  };

  const fail = (error: unknown) => {
    setSavedKey(null);
    setErrorKey(errorKeyOf(error));
  };

  const onPick = (event: React.ChangeEvent<HTMLInputElement>) => {
    const picked = event.target.files?.[0];
    event.target.value = "";
    if (!picked) return;

    setSavedKey(null);
    if (
      !(TENANT_LOGO_ALLOWED_MIME_TYPES as readonly string[]).includes(
        picked.type,
      )
    ) {
      setErrorKey("tenantProfile.errors.type");
      return;
    }
    if (picked.size > TENANT_LOGO_MAX_FILE_SIZE_BYTES) {
      setErrorKey("tenantProfile.errors.size");
      return;
    }
    setErrorKey(null);
    setLogo.mutate(picked, {
      onSuccess: () => announce("tenantProfile.logoSaved"),
      onError: fail,
    });
  };

  const edit = (patch: { name?: string; slug?: string }) => {
    setSlugErrorKey(null);
    setDraft({ id: data.id, name, slug, ...patch });
  };

  /** The write itself. `slug` rides along **only** when it changed, so a
   *  rename can never carry one — the server's D-C.2 rule, mirrored. */
  const submit = () => {
    setConfirming(false);
    update.mutate(
      slugChanged ? { name: name.trim(), slug } : { name: name.trim() },
      {
        onSuccess: () => {
          setDraft(null);
          setSlugErrorKey(null);
          announce("tenantProfile.saved");
        },
        onError: (error) => {
          if (!slugChanged) {
            fail(error);
            return;
          }
          setSavedKey(null);
          setErrorKey(null);
          setSlugErrorKey(slugErrorKeyOf(error));
        },
      },
    );
  };

  const onSave = () => {
    if (slugChanged) {
      setConfirming(true);
      return;
    }
    submit();
  };

  const onRemove = () => {
    clearLogo.mutate(undefined as never, {
      onSuccess: () => announce("tenantProfile.logoRemoved"),
      onError: fail,
    });
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center gap-3 border-b border-border px-6 py-4">
          <Landmark className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              {t("tenantProfile.title")}
            </h1>
            <p className="text-xs text-muted-foreground">
              {t("tenantProfile.subtitle")}
            </p>
          </div>
        </div>

        {errorKey && (
          <div
            role="alert"
            className="mx-6 mt-6 flex items-start gap-3 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3"
          >
            <AlertTriangle className="mt-0.5 h-5 w-5 text-destructive" aria-hidden="true" />
            <div className="text-sm text-destructive">
              <p className="font-medium">{t("tenantProfile.errors.title")}</p>
              <p className="mt-0.5">{t(errorKey)}</p>
            </div>
          </div>
        )}

        {savedKey && (
          <p
            role="status"
            className="mx-6 mt-6 rounded-md bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700"
          >
            {t(savedKey)}
          </p>
        )}

        <div className="grid gap-8 px-6 py-6 md:grid-cols-[220px_1fr]">
          <div className="space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("tenantProfile.logoLabel")}
            </span>
            {data.logo_url ? (
              <div className="flex h-36 w-full items-center justify-center overflow-hidden rounded-lg border border-border bg-muted">
                <img
                  src={data.logo_url}
                  alt={t("tenantProfile.logoAlt")}
                  className="max-h-32 max-w-[180px] object-contain"
                />
              </div>
            ) : (
              <div className="flex h-36 w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border bg-muted text-muted-foreground">
                <ImageIcon className="h-7 w-7" aria-hidden="true" />
                <span className="text-xs">{t("tenantProfile.logoEmpty")}</span>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              {t("tenantProfile.hint", { size: MAX_MB })}
            </p>

            <label className="sr-only" htmlFor="tenant-logo-input">
              {t("tenantProfile.fileInputLabel")}
            </label>
            <input
              id="tenant-logo-input"
              ref={inputRef}
              type="file"
              className="hidden"
              accept={TENANT_LOGO_ACCEPT}
              onChange={onPick}
            />
            <div className="flex flex-col gap-2">
              <button
                type="button"
                disabled={setLogo.isPending}
                onClick={() => inputRef.current?.click()}
                className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
              >
                <Upload className="h-4 w-4" aria-hidden="true" />
                {t(data.logo_url ? "tenantProfile.replace" : "tenantProfile.upload")}
              </button>
              {data.logo_url && (
                <button
                  type="button"
                  disabled={clearLogo.isPending}
                  onClick={onRemove}
                  className="inline-flex items-center justify-center gap-2 rounded-md border border-destructive/30 px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 disabled:opacity-60"
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  {t("tenantProfile.remove")}
                </button>
              )}
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <label
                className="block text-sm font-medium text-foreground"
                htmlFor="tenant-name-input"
              >
                {t("tenantProfile.nameLabel")}
              </label>
              <input
                id="tenant-name-input"
                value={name}
                onChange={(event) => edit({ name: event.target.value })}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                {t("tenantProfile.nameHint")}
              </p>
            </div>

            <div
              className={`rounded-lg border p-4 ${
                slugMalformed || slugErrorKey
                  ? "border-destructive/40 bg-destructive/5"
                  : "border-border bg-muted/40"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <label
                  className="flex items-center gap-2 text-sm font-medium text-foreground"
                  htmlFor="tenant-slug-input"
                >
                  <Link2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  {t("tenantProfile.slugLabel")}
                </label>
                <button
                  type="button"
                  onClick={() => edit({ slug: slugifyName(name) })}
                  className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                >
                  <Wand2 className="h-3.5 w-3.5" aria-hidden="true" />
                  {t("tenantProfile.slugSuggest")}
                </button>
              </div>

              <div className="mt-2 flex items-stretch">
                <span
                  className="inline-flex items-center rounded-l-md border border-r-0 border-input bg-muted px-3 font-mono text-sm text-muted-foreground"
                  aria-hidden="true"
                >
                  /c/
                </span>
                <input
                  id="tenant-slug-input"
                  value={slug}
                  onChange={(event) => edit({ slug: event.target.value })}
                  className="w-full rounded-r-md border border-input bg-background px-3 py-2 font-mono text-sm"
                />
              </div>

              {slugMalformed || slugErrorKey ? (
                <p
                  role="alert"
                  className="mt-2 flex items-start gap-1.5 text-xs font-medium text-destructive"
                >
                  <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <span>
                    {t(slugMalformed ? "tenantProfile.errors.slugInvalid" : slugErrorKey!)}
                  </span>
                </p>
              ) : (
                <p className="mt-2 text-xs text-muted-foreground">
                  {t("tenantProfile.slugHint")}
                </p>
              )}

              <p className="mt-2 flex items-start gap-1.5 rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span>{t("tenantProfile.slugWarning")}</span>
              </p>
            </div>

            <div>
              <label
                className="block text-sm font-medium text-foreground"
                htmlFor="tenant-id-input"
              >
                {t("tenantProfile.idLabel")}
              </label>
              <input
                id="tenant-id-input"
                readOnly
                value={data.id}
                className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 font-mono text-xs text-muted-foreground"
              />
            </div>

            <button
              type="button"
              onClick={onSave}
              disabled={
                update.isPending || name.trim().length === 0 || slugMalformed
              }
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
            >
              {t("tenantProfile.save")}
            </button>

            {!data.logo_url && (
              <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
                {t("tenantProfile.noLogoWarning")}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* The condominium's brand colours (APRAS-68). Under the same
          `tenants:profile_update` the route already gates on — there is no
          second permission — and reading the same profile payload, so a save
          here re-themes the running app through `TenantBrandTheme` with no
          extra wiring. */}
      <TenantBrandColors profile={data} />

      {confirming && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="tenant-slug-confirm-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        >
          <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl">
            <div className="flex items-start gap-3">
              <AlertTriangle
                className="mt-0.5 h-6 w-6 shrink-0 text-destructive"
                aria-hidden="true"
              />
              <div>
                <h2
                  id="tenant-slug-confirm-title"
                  className="text-base font-semibold text-foreground"
                >
                  {t("tenantProfile.slugConfirmTitle")}
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  {t("tenantProfile.slugConfirmBody", {
                    from: data.slug,
                    to: slug,
                  })}
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className="rounded-md border border-input px-4 py-2 text-sm font-medium text-foreground"
              >
                {t("tenantProfile.slugConfirmCancel")}
              </button>
              <button
                type="button"
                onClick={submit}
                className="rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground"
              >
                {t("tenantProfile.slugConfirmCta")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TenantProfilePage;
