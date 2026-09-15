import React, { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Image as ImageIcon, Landmark, Trash2, Upload } from "lucide-react";
import {
  TENANT_LOGO_ACCEPT,
  TENANT_LOGO_ALLOWED_MIME_TYPES,
  TENANT_LOGO_MAX_FILE_SIZE_BYTES,
} from "../../../api/tenantProfile";
import {
  useClearTenantLogo,
  useRenameTenant,
  useSetTenantLogo,
  useTenantProfile,
} from "../../../hooks/useTenantProfile";
import { Spinner } from "../../../components/ui/spinner";

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

const TenantProfilePage: React.FC = () => {
  const { t } = useTranslation();
  const { data, isPending } = useTenantProfile();
  const rename = useRenameTenant();
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
  const [draft, setDraft] = useState<{ id: string; name: string } | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  if (isPending || !data) return <Spinner />;

  const name = draft?.id === data.id ? draft.name : data.name;

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

  const onSave = () => {
    rename.mutate(name.trim(), {
      onSuccess: () => {
        setDraft(null);
        announce("tenantProfile.saved");
      },
      onError: fail,
    });
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
                onChange={(event) =>
                  setDraft({ id: data.id, name: event.target.value })
                }
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                {t("tenantProfile.nameHint")}
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
              disabled={rename.isPending || name.trim().length === 0}
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
    </div>
  );
};

export default TenantProfilePage;
