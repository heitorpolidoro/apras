import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useSetSubscriptionModules,
  useSubscription,
  useSubscriptionHistory,
} from "../../../hooks/useSubscription";
import { groupsCovering } from "../access/moduleGroups";
import type { ModuleEntitlement } from "../../../types/subscription";

/**
 * The tenant-side subscription area behind `/subscription` (APRAS-40 §8.4).
 *
 * The current plan card, the toggleable modules grouped by APRAS-39 §2.3's
 * clusters, a Save button, and the append-only change history.
 *
 * **Prices are inert.** Every amount on this screen is display metadata: no
 * payment provider exists for this project, so nothing here charges anything.
 * The screen says so, in both languages.
 *
 * No optimistic update — the `PUT` response body is the new state.
 */

/**
 * The four mutually exclusive row states of §8.4, resolved by a **stated
 * precedence**: `OVERRIDE > COURTESY > PLAN > out-of-plan`, first match wins.
 *
 * Rules 1 and 2 are already disjoint by §4.7 (`OVERRIDE` means active and in
 * neither set), and rule 2 is written on `courtesy && !in_plan` rather than
 * `source === "COURTESY"` so that a courtesy module which is *inactive*
 * (source `null`) still renders as a courtesy row instead of falling through
 * to rule 4. Stating the order anyway is what makes the mapping a function
 * rather than four competing predicates.
 */
type RowState = "override" | "courtesy" | "inPlan" | "outOfPlan";

/** Module-private on purpose: the page's only export is the component, so
 *  Fast Refresh keeps working (`react-refresh/only-export-components`), and
 *  the four states are asserted through the DOM in `SubscriptionPage.test.tsx`
 *  rather than by calling this directly. */
const rowStateOf = (row: ModuleEntitlement): RowState => {
  if (row.source === "OVERRIDE") return "override";
  if (row.courtesy && !row.in_plan) return "courtesy";
  if (row.in_plan) return "inPlan";
  return "outOfPlan";
};

const SubscriptionPage: React.FC = () => {
  const { t } = useTranslation();
  // Only the tenant's *edits*, never a copy of the server's answer. The
  // checkbox state is derived below, so there is no effect synchronising two
  // sources of truth and no window in which they can disagree.
  const [edits, setEdits] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState(false);

  const { data, isPending, isError } = useSubscription();
  const { data: history } = useSubscriptionHistory();
  const mutation = useSetSubscriptionModules();

  const rows = useMemo(() => data?.modules ?? [], [data]);
  const known = useMemo(
    () => new Map(rows.map((row) => [row.module, row])),
    [rows],
  );

  // `groupsCovering` appends an `"other"` group for any module the clusters do
  // not name: the backend derives `MODULES` from the catalogue precisely so a
  // module a future task adds is toggleable the day its first permission
  // exists, while the clusters are hand-written presentation.
  const groups = useMemo(
    () => groupsCovering(rows.map((row) => row.module)),
    [rows],
  );

  /** The server's answer, with the tenant's unsaved edits on top. */
  const isChecked = (row: ModuleEntitlement): boolean =>
    edits[row.module] ?? row.is_active;

  const toggle = (row: ModuleEntitlement) => {
    setSaved(false);
    setEdits((previous) => ({ ...previous, [row.module]: !isChecked(row) }));
  };

  /**
   * The payload is **the contracted set only**: the plan-covered checkboxes
   * and nothing else.
   *
   * Courtesy and override modules are display-only rows, are never sent, and
   * are never dropped — §4.4 (a)'s `preserved` term keeps them active on the
   * server. This is what stops Save from being a permanent 400 (an
   * out-of-entitlement module is never in the payload) and from silently
   * killing an operator override (omission does not deactivate anything the
   * tenant does not govern).
   */
  const save = () => {
    const activeModules = rows
      .filter((row) => !row.is_core && row.in_plan && row.source !== "OVERRIDE")
      .filter((row) => isChecked(row))
      .map((row) => row.module);
    setSaved(false);
    mutation.mutate(activeModules, {
      onSuccess: () => {
        // The response body is written into the cache by the hook, so the
        // edits have served their purpose and are dropped here rather than
        // reconciled — the server's answer is the state from now on.
        setEdits({});
        setSaved(true);
      },
    });
  };

  const unmanaged = data !== undefined && data.plan === null;

  const renderRow = (row: ModuleEntitlement) => {
    const label = t(`modules.names.${row.module}`);
    const state = rowStateOf(row);

    // The `!unmanaged` term is **not** the mirror of a dead branch: an
    // unmanaged tenant's rows all come back `in_plan: false`, so `rowStateOf`
    // cannot return `"inPlan"` here — but if it ever did, this term is what
    // decides the failure is a read-only row rather than a checkbox whose
    // Save is a guaranteed 404 (§4.6). It fails safe; the same condition on
    // the hint below only chose a label, so it was deleted rather than kept.
    if (state === "inPlan" && !unmanaged) {
      return (
        <label
          key={row.module}
          className="flex items-center gap-2 text-sm"
          htmlFor={`subscription-${row.module}`}
        >
          <input
            id={`subscription-${row.module}`}
            type="checkbox"
            aria-label={label}
            checked={isChecked(row)}
            disabled={!row.can_contract}
            onChange={() => toggle(row)}
          />
          {label}
          {row.monthly_price !== null && (
            <span className="text-xs text-muted-foreground">
              {row.monthly_price} {data?.currency}
            </span>
          )}
        </label>
      );
    }

    return (
      <div
        key={row.module}
        data-testid={`subscription-row-${row.module}`}
        className="flex items-center gap-2 text-sm text-muted-foreground"
      >
        {label}
        {state === "override" && (
          <span className="text-xs uppercase border border-border rounded px-1">
            {t("subscription.operatorBadge")}
          </span>
        )}
        {state === "courtesy" && (
          <>
            <span className="text-xs uppercase border border-border rounded px-1">
              {t("subscription.courtesyBadge")}
            </span>
            <span className="text-xs">{t("subscription.free")}</span>
          </>
        )}
        {state === "outOfPlan" && (
          <span className="text-xs">{t("subscription.outOfPlan")}</span>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-8 flex flex-col gap-6">
      <h1 className="text-2xl font-black text-foreground">
        {t("subscription.title")}
      </h1>

      {isPending && <p>{t("subscription.loading")}</p>}
      {isError && <p role="alert">{t("subscription.loadError")}</p>}

      {data && (
        <>
          <section className="border border-border rounded-md p-4 flex flex-col gap-1">
            <h2 className="text-lg font-bold">{t("subscription.currentPlan")}</h2>
            {data.plan === null ? (
              <p>{t("subscription.noPlan")}</p>
            ) : (
              <>
                <p className="font-semibold">{data.plan.name}</p>
                {data.plan.description && <p>{data.plan.description}</p>}
                {data.status && (
                  <p>{t(`subscription.status.${data.status}`)}</p>
                )}
                {data.started_at && (
                  <p>
                    {t("subscription.startedAt")}: {data.started_at}
                  </p>
                )}
                <p>
                  {t("subscription.estimatedTotal")}:{" "}
                  {data.estimated_monthly_total} {data.currency}
                </p>
              </>
            )}
            <p className="text-xs text-muted-foreground">
              {t("subscription.inertPriceNotice")}
            </p>
          </section>

          <section className="flex flex-col gap-6">
            <h2 className="text-lg font-bold">
              {t("subscription.modulesTitle")}
            </h2>
            {groups.map((group) => (
              <fieldset key={group.key} className="flex flex-col gap-2">
                <legend className="text-sm font-bold text-foreground">
                  {t(`modules.groups.${group.key}`)}
                </legend>
                {group.modules
                  .map((module) => known.get(module))
                  .filter((row): row is ModuleEntitlement => row !== undefined)
                  .map(renderRow)}
              </fieldset>
            ))}
          </section>

          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={save}
              disabled={unmanaged || mutation.isPending}
              className="bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {mutation.isPending
                ? t("subscription.saving")
                : t("subscription.save")}
            </button>
            {saved && <span>{t("subscription.saved")}</span>}
            {mutation.isError && (
              <span role="alert">{t("subscription.notEntitled")}</span>
            )}
          </div>

          <section className="flex flex-col gap-2">
            <h2 className="text-lg font-bold">
              {t("subscription.historyTitle")}
            </h2>
            {history && history.length === 0 && <p>{t("subscription.empty")}</p>}
            {history && history.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>{t("subscription.historyTitle")}</th>
                    <th>{t("subscription.added")}</th>
                    <th>{t("subscription.removed")}</th>
                    <th>{t("subscription.author")}</th>
                    <th>{t("subscription.when")}</th>
                    <th>{t("subscription.reason")}</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((row) => (
                    <tr key={row.id}>
                      <td>{t(`subscription.kind.${row.kind}`)}</td>
                      <td>{row.modules_added.join(", ")}</td>
                      <td>{row.modules_removed.join(", ")}</td>
                      <td>{row.changed_by_name}</td>
                      <td>{row.changed_at}</td>
                      <td>{row.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
};

export default SubscriptionPage;
