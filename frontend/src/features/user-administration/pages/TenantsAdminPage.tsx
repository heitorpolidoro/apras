import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Copy, MailPlus, Plus, Search } from "lucide-react";
import { useCreateTenant, useTenants } from "../../../hooks/useTenants";
import { parseApiError } from "../../../api/errors";
import type { Tenant } from "../../../types/auth";

/**
 * The superuser screen behind `/admin/tenants` (APRAS-70).
 *
 * It lists every condominium and creates one through the **existing**
 * `POST /api/v1/tenants`. No backend line belongs to this screen.
 *
 * **The form asks for the name and nothing else** (D1). `TenantCreate` has no
 * `slug` field, and there is deliberately no client-side slug preview (D2):
 * `app/core/slug.py` plus `TenantService.generated_slug` are the single
 * derivation authority, collision suffix included, so a JS reimplementation
 * would be a second authority that can silently disagree. The slug shown
 * after saving is the one in the `201` body.
 *
 * **`is_active` is read-only here** (D5): the badge and the status filter read
 * it, and nothing writes it — deactivation is `PATCH /tenants/{id}`, an
 * operator act that belongs to a screen for editing an existing condominium.
 *
 * **No pagination** (D4): `GET /tenants` accepts no `skip`/`limit` and returns
 * every tenant ordered by name, so a pager would be a fiction over an
 * already-complete payload. The filters below are therefore client-side.
 *
 * The **Administrator** column, the per-row **actions** cell and the success
 * panel's secondary slot are APRAS-72's attachment points (D7) and render as
 * disabled placeholders here, so the layout is not redesigned then.
 */

type StatusFilter = "all" | "active" | "inactive";

/** `TenantService.create_tenant` refuses an existing name with a 409 (D6). */
const isDuplicateName = (error: unknown): boolean =>
  (error as { response?: { status?: number } })?.response?.status === 409;

const StatusBadge: React.FC<{ isActive: boolean }> = ({ isActive }) => {
  const { t } = useTranslation();
  return (
    <span
      className={
        isActive
          ? "inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700"
          : "inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
      }
    >
      {t(isActive ? "tenantsAdmin.activeBadge" : "tenantsAdmin.inactiveBadge")}
    </span>
  );
};

const TenantsAdminPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { data: tenants, isPending, isError } = useTenants();
  const createTenant = useCreateTenant();

  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [created, setCreated] = useState<Tenant | null>(null);
  const [copied, setCopied] = useState(false);

  const all = useMemo(() => tenants ?? [], [tenants]);

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return all.filter((tenant) => {
      const matchesText =
        needle === "" ||
        tenant.name.toLowerCase().includes(needle) ||
        tenant.slug.toLowerCase().includes(needle);
      if (!matchesText) return false;
      if (status === "active") return tenant.is_active;
      if (status === "inactive") return !tenant.is_active;
      return true;
    });
  }, [all, query, status]);

  const openForm = () => {
    setCreated(null);
    setFormError(null);
    setName("");
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
    setFormError(null);
    setName("");
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    createTenant.mutate(
      { name: name.trim() },
      {
        onSuccess: (tenant) => {
          setCreated(tenant);
          setCopied(false);
          setIsFormOpen(false);
          setName("");
        },
        onError: (error) => {
          // A duplicate name gets the **translated** message, not the
          // backend's English `detail` string (D6); everything else — a 422
          // on an empty or over-long name included — falls back to
          // `parseApiError` with this page's generic keys.
          setFormError(
            isDuplicateName(error)
              ? t("tenantsAdmin.duplicateName")
              : parseApiError(error, t, {
                  validationError: "tenantsAdmin.validationError",
                  genericError: "tenantsAdmin.genericError",
                }),
          );
        },
      },
    );
  };

  const copySlug = () => {
    if (!created) return;
    void navigator.clipboard?.writeText(created.slug);
    setCopied(true);
  };

  const formatDate = (isoString: string) =>
    new Date(isoString).toLocaleDateString(i18n.language);

  return (
    <div className="max-w-6xl mx-auto p-8 flex flex-col gap-6">
      <header className="flex flex-wrap items-start gap-4">
        <div className="mr-auto flex flex-col gap-1">
          <h1 className="text-2xl font-black text-foreground">
            {t("tenantsAdmin.title")}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t("tenantsAdmin.subtitle")}
          </p>
        </div>
        <button
          type="button"
          onClick={openForm}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground"
        >
          <Plus className="size-4" />
          {t("tenantsAdmin.new")}
        </button>
      </header>

      {created && (
        <div className="flex flex-col gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-5">
          <p className="text-sm font-semibold text-emerald-900">
            {t("tenantsAdmin.createdTitle")}
          </p>
          <p className="text-sm text-emerald-900">{created.name}</p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-emerald-800">
              {t("tenantsAdmin.createdSlugLabel")}
            </span>
            <code className="rounded bg-background px-2 py-1 font-mono text-xs">
              {created.slug}
            </code>
            <button
              type="button"
              onClick={copySlug}
              className="inline-flex items-center gap-1 rounded border border-emerald-300 px-2 py-1 text-xs text-emerald-800"
            >
              <Copy className="size-3" />
              {t("tenantsAdmin.copy")}
            </button>
            {copied && (
              <span className="text-xs text-emerald-800">
                {t("tenantsAdmin.copied")}
              </span>
            )}
          </div>
          <p className="text-xs text-emerald-800">
            {t("tenantsAdmin.createdSlugHint")}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setCreated(null)}
              className="rounded-md bg-emerald-700 px-3 py-2 text-xs font-semibold text-white"
            >
              {t("tenantsAdmin.backToList")}
            </button>
            {/* APRAS-72's third attachment point (D7). */}
            <button
              type="button"
              disabled
              className="inline-flex cursor-not-allowed items-center gap-2 rounded-md border border-dashed border-border px-3 py-2 text-xs font-medium text-muted-foreground"
            >
              <MailPlus className="size-3.5" />
              {t("tenantsAdmin.inviteAdministratorSoon")}
            </button>
          </div>
        </div>
      )}

      {isFormOpen && (
        <form
          onSubmit={submit}
          className="flex max-w-xl flex-col gap-4 rounded-xl border border-border p-5"
        >
          <h2 className="text-lg font-semibold text-foreground">
            {t("tenantsAdmin.formTitle")}
          </h2>
          <label className="flex flex-col gap-1" htmlFor="tenant-name">
            <span className="text-sm font-medium text-foreground">
              {t("tenantsAdmin.nameLabel")}
            </span>
            <input
              id="tenant-name"
              value={name}
              maxLength={120}
              onChange={(event) => {
                setFormError(null);
                setName(event.target.value);
              }}
              className="rounded-md border border-border px-3 py-2 text-sm"
            />
          </label>
          <p className="text-xs text-muted-foreground">
            {t("tenantsAdmin.nameHint")}
          </p>
          <p className="rounded-md border border-border bg-muted px-3 py-3 text-xs text-muted-foreground">
            {t("tenantsAdmin.slugDerivedHint")}
          </p>
          {formError && (
            <p role="alert" className="text-xs font-medium text-destructive">
              {formError}
            </p>
          )}
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={closeForm}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium"
            >
              {t("tenantsAdmin.cancel")}
            </button>
            <button
              type="submit"
              disabled={name.trim() === "" || createTenant.isPending}
              className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
            >
              {createTenant.isPending
                ? t("tenantsAdmin.submitting")
                : t("tenantsAdmin.submit")}
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2" htmlFor="tenant-filter">
          <Search className="size-4 text-muted-foreground" />
          <span className="sr-only">{t("tenantsAdmin.filterLabel")}</span>
          <input
            id="tenant-filter"
            value={query}
            placeholder={t("tenantsAdmin.filterLabel")}
            onChange={(event) => setQuery(event.target.value)}
            className="w-72 rounded-md border border-border px-3 py-2 text-sm"
          />
        </label>
        <label className="flex items-center gap-2" htmlFor="tenant-status">
          <span className="sr-only">{t("tenantsAdmin.statusLabel")}</span>
          <select
            id="tenant-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as StatusFilter)}
            className="rounded-md border border-border px-3 py-2 text-sm"
          >
            <option value="all">{t("tenantsAdmin.statusAll")}</option>
            <option value="active">{t("tenantsAdmin.statusActive")}</option>
            <option value="inactive">{t("tenantsAdmin.statusInactive")}</option>
          </select>
        </label>
        <span className="ml-auto text-xs text-muted-foreground">
          {t("tenantsAdmin.count", { shown: rows.length, total: all.length })}
        </span>
      </div>

      {isPending && <p>{t("tenantsAdmin.loading")}</p>}
      {isError && <p role="alert">{t("tenantsAdmin.loadError")}</p>}

      {tenants && all.length === 0 && <p>{t("tenantsAdmin.empty")}</p>}

      {all.length > 0 && (
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-3">{t("tenantsAdmin.columns.name")}</th>
              <th className="px-4 py-3">{t("tenantsAdmin.columns.slug")}</th>
              <th className="px-4 py-3">{t("tenantsAdmin.columns.status")}</th>
              <th className="px-4 py-3">
                {t("tenantsAdmin.columns.createdAt")}
              </th>
              <th className="px-4 py-3">
                {t("tenantsAdmin.columns.administrator")}
              </th>
              <th className="px-4 py-3 text-right">
                {t("tenantsAdmin.columns.actions")}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((tenant) => (
              <tr key={tenant.id} data-testid={`tenant-row-${tenant.id}`}>
                <td className="px-4 py-3 font-medium">{tenant.name}</td>
                <td className="px-4 py-3">
                  <code className="rounded bg-muted px-2 py-0.5 font-mono text-xs">
                    {tenant.slug}
                  </code>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge isActive={tenant.is_active} />
                </td>
                <td
                  className="px-4 py-3 text-muted-foreground"
                  data-testid={`tenant-created-${tenant.id}`}
                >
                  {formatDate(tenant.created_at)}
                </td>
                {/* APRAS-72's first attachment point: the invitation state. */}
                <td className="px-4 py-3 text-xs italic text-muted-foreground">
                  {t("tenantsAdmin.administratorPlaceholder")}
                </td>
                {/* APRAS-72's second: "Invite administrator". */}
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    disabled
                    className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-md border border-dashed border-border px-2.5 py-1 text-xs text-muted-foreground"
                  >
                    <MailPlus className="size-3.5" />
                    {t("tenantsAdmin.inviteSoon")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {all.length > 0 && rows.length === 0 && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          {t("tenantsAdmin.noResults")}
        </p>
      )}

      <p className="text-xs text-muted-foreground">
        {t("tenantsAdmin.slugEditHint")}
      </p>
    </div>
  );
};

export default TenantsAdminPage;
