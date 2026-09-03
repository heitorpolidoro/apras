import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  usePlans,
  useSetTenantCourtesy,
  useSetTenantPlan,
  useTenantSubscription,
} from "../../../hooks/usePlans";
import { useAllTenants } from "../../../hooks/useTenantModules";
import type { SubscriptionStatus } from "../../../types/subscription";

/**
 * The superuser screen behind `/admin/subscriptions` (APRAS-40 §8.4).
 *
 * One condominium `<select>`, the tenant's current subscription, a plan
 * `<select>` with status and notes, and a courtesy checklist with a required
 * reason.
 *
 * **The two levers do different things, and the screen says so.** Assigning a
 * plan applies the ceiling *shrink-only*: modules leaving the entitlement are
 * deactivated, modules newly entering it are **not** auto-activated, because
 * contracting them is the tenant's explicit act. A courtesy grant *does*
 * activate, because it names one specific module as a deliberate per-module
 * operator act — "turn this on for them".
 *
 * **APRAS-39's `/admin/modules` page is not touched.** That is the raw switch;
 * this is the commercial surface. Both are reachable, they write the same
 * column, and `/admin/modules` remains the repair tool.
 *
 * The change history lives on the tenant-side `/subscription` page: the three
 * operator routes are read, plan and courtesy, and this task deliberately adds
 * no fourth (a per-tenant history route would be an eighth superuser route and
 * is out of the declared accounting).
 */

const STATUSES: readonly SubscriptionStatus[] = [
  "ACTIVE",
  "SUSPENDED",
  "CANCELED",
];

const TenantSubscriptionsPage: React.FC = () => {
  const { t } = useTranslation();
  const [chosenTenantId, setChosenTenantId] = useState<string | null>(null);
  const [planId, setPlanId] = useState<string>("");
  const [status, setStatus] = useState<SubscriptionStatus>("ACTIVE");
  const [notes, setNotes] = useState("");
  const [courtesyEdits, setCourtesyEdits] = useState<Record<string, boolean>>(
    {},
  );
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState(false);
  const [saved, setSaved] = useState(false);

  const { data: tenants } = useAllTenants();
  const { data: plans } = usePlans();
  // The first tenant is pre-selected, derived rather than written by an
  // effect, so the screen is never an empty shell.
  const tenantId = chosenTenantId ?? tenants?.[0]?.id ?? null;
  const { data, isPending, isError } = useTenantSubscription(tenantId);
  const planMutation = useSetTenantPlan(tenantId);
  const courtesyMutation = useSetTenantCourtesy(tenantId);

  const toggleable = useMemo(
    () => (data?.modules ?? []).filter((row) => !row.is_core),
    [data],
  );

  const isCourtesy = (module: string): boolean =>
    courtesyEdits[module] ??
    (data?.modules.find((row) => row.module === module)?.courtesy ?? false);

  const savePlan = () => {
    setSaved(false);
    planMutation.mutate(
      { plan_id: planId, status, notes: notes || null },
      { onSuccess: () => setSaved(true) },
    );
  };

  const saveCourtesy = () => {
    if (!reason.trim()) {
      // Required on purpose: a courtesy grant is a commercial decision, and
      // the history row is where it has to be explainable afterwards.
      setReasonError(true);
      return;
    }
    setReasonError(false);
    setSaved(false);
    courtesyMutation.mutate(
      {
        courtesy_modules: toggleable
          .filter((row) => isCourtesy(row.module))
          .map((row) => row.module),
        reason,
      },
      {
        onSuccess: () => {
          setCourtesyEdits({});
          setSaved(true);
        },
      },
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-8 flex flex-col gap-6">
      <h1 className="text-2xl font-black text-foreground">
        {t("tenantSubscriptions.title")}
      </h1>
      <p className="text-xs text-muted-foreground">
        {t("tenantSubscriptions.inertPriceNotice")}
      </p>

      <div className="flex flex-col gap-2 max-w-sm">
        <label
          htmlFor="tenant-subscription-select"
          className="text-sm font-semibold"
        >
          {t("tenantSubscriptions.tenantLabel")}
        </label>
        <select
          id="tenant-subscription-select"
          value={tenantId ?? ""}
          onChange={(event) => {
            setSaved(false);
            // Unsaved edits belong to the tenant they were made in.
            setCourtesyEdits({});
            setReason("");
            setChosenTenantId(event.target.value || null);
          }}
        >
          <option value="">
            {t("tenantSubscriptions.tenantPlaceholder")}
          </option>
          {(tenants ?? []).map((tenant) => (
            <option key={tenant.id} value={tenant.id}>
              {tenant.name}
            </option>
          ))}
        </select>
      </div>

      {tenantId && isPending && <p>{t("tenantSubscriptions.loading")}</p>}
      {tenantId && isError && (
        <p role="alert">{t("tenantSubscriptions.loadError")}</p>
      )}

      {data && (
        <>
          <section className="border border-border rounded-md p-4 flex flex-col gap-1">
            {data.plan === null ? (
              <p>{t("tenantSubscriptions.noSubscription")}</p>
            ) : (
              <>
                <p className="font-semibold">{data.plan.name}</p>
                {data.status && (
                  <p>{t(`subscription.status.${data.status}`)}</p>
                )}
                <p>
                  {t("subscription.estimatedTotal")}:{" "}
                  {data.estimated_monthly_total} {data.currency}
                </p>
              </>
            )}
          </section>

          <section className="flex flex-col gap-3">
            <label className="flex flex-col gap-1" htmlFor="subscription-plan">
              {t("tenantSubscriptions.plan")}
              <select
                id="subscription-plan"
                value={planId}
                onChange={(event) => {
                  setSaved(false);
                  setPlanId(event.target.value);
                }}
              >
                <option value="">
                  {t("tenantSubscriptions.planPlaceholder")}
                </option>
                {(plans ?? []).map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name}
                    {plan.is_active ? "" : ` (${t("plans.inactiveBadge")})`}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1" htmlFor="subscription-status">
              {t("tenantSubscriptions.status")}
              <select
                id="subscription-status"
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as SubscriptionStatus)
                }
              >
                {STATUSES.map((value) => (
                  <option key={value} value={value}>
                    {t(`subscription.status.${value}`)}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1" htmlFor="subscription-notes">
              {t("tenantSubscriptions.notes")}
              <input
                id="subscription-notes"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
            </label>

            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={savePlan}
                disabled={!planId || planMutation.isPending}
              >
                {planMutation.isPending
                  ? t("tenantSubscriptions.saving")
                  : t("tenantSubscriptions.save")}
              </button>
              {planMutation.isError && (
                <span role="alert">{t("tenantSubscriptions.saveError")}</span>
              )}
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-lg font-bold">
              {t("tenantSubscriptions.courtesyTitle")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("tenantSubscriptions.courtesyHint")}
            </p>
            {toggleable.map((row) => (
              <label
                key={row.module}
                className="flex items-center gap-2 text-sm"
                htmlFor={`courtesy-${row.module}`}
              >
                <input
                  id={`courtesy-${row.module}`}
                  type="checkbox"
                  aria-label={t(`modules.names.${row.module}`)}
                  checked={isCourtesy(row.module)}
                  onChange={() => {
                    setSaved(false);
                    setCourtesyEdits((previous) => ({
                      ...previous,
                      [row.module]: !isCourtesy(row.module),
                    }));
                  }}
                />
                {t(`modules.names.${row.module}`)}
              </label>
            ))}

            <label className="flex flex-col gap-1" htmlFor="courtesy-reason">
              {t("tenantSubscriptions.reason")}
              <input
                id="courtesy-reason"
                value={reason}
                onChange={(event) => {
                  setReasonError(false);
                  setReason(event.target.value);
                }}
              />
            </label>
            {reasonError && (
              <span role="alert">{t("tenantSubscriptions.reasonRequired")}</span>
            )}

            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={saveCourtesy}
                disabled={courtesyMutation.isPending}
              >
                {t("tenantSubscriptions.grantCourtesy")}
              </button>
              {saved && <span>{t("tenantSubscriptions.saved")}</span>}
              {courtesyMutation.isError && (
                <span role="alert">{t("tenantSubscriptions.saveError")}</span>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
};

export default TenantSubscriptionsPage;
