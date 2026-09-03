import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useAllTenants,
  useSetTenantModules,
  useTenantModules,
} from "../../../hooks/useTenantModules";
import { groupsCovering } from "../access/moduleGroups";

/**
 * The superuser screen behind `/admin/modules` (APRAS-39 §10.3).
 *
 * One condominium `<select>` and one checkbox list of the 27 modules,
 * grouped by the companion clusters of §2.3. The grouping is **presentation,
 * not machinery**: the modules toggle independently, and turning one
 * companion off without the other is legal and safe — every endpoint of a
 * disabled module refuses, and it is reversible in one click. Modelling
 * `requires` edges would be a second authorization concept for an operator
 * error that costs one checkbox to fix.
 *
 * Core modules render checked and `disabled`: the API refuses to disable
 * them, because a tenant without `tenants`/`users`/`roles` could not
 * administer itself back into existence.
 *
 * No optimistic update — the `PUT` response body is the new state.
 */

const TenantModulesPage: React.FC = () => {
  const { t } = useTranslation();
  const [chosenTenantId, setChosenTenantId] = useState<string | null>(null);
  // Only the operator's *edits*, never a copy of the server's answer. The
  // checkbox state is derived below, so there is no effect synchronising two
  // sources of truth and no window in which they can disagree.
  const [edits, setEdits] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState(false);

  const { data: tenants } = useAllTenants();
  // The first tenant is pre-selected, derived rather than written by an
  // effect, so the screen is never an empty shell.
  const tenantId = chosenTenantId ?? tenants?.[0]?.id ?? null;
  const { data, isPending, isError } = useTenantModules(tenantId);
  const mutation = useSetTenantModules(tenantId);

  const coreModules = useMemo(
    () =>
      new Set(
        (data?.modules ?? []).filter((row) => row.is_core).map((r) => r.module),
      ),
    [data],
  );

  const known = useMemo(
    () => new Set((data?.modules ?? []).map((row) => row.module)),
    [data],
  );

  // `groupsCovering` appends an `"other"` group for any module the clusters do
  // not name, so a module a future task adds is visible to the operator rather
  // than silently dropped. (`test_the_catalogue_modules_are_the_ones_the_ui_labels`
  // is the other half of that guard: it fails at the catalogue end, naming the
  // shared constant.)
  const groups = useMemo(
    () => groupsCovering((data?.modules ?? []).map((row) => row.module)),
    [data],
  );

  /** The server's answer, with the operator's unsaved edits on top. */
  const isActive = (module: string): boolean =>
    edits[module] ??
    (data?.modules.find((row) => row.module === module)?.is_active ?? false);

  const toggle = (module: string) => {
    setSaved(false);
    setEdits((previous) => ({ ...previous, [module]: !isActive(module) }));
  };

  const save = () => {
    // Derived from the **toggleable** set only: a core module can never
    // enter the payload, even if a hand-edited row claimed it was inactive.
    const disabled = (data?.modules ?? [])
      .filter((row) => !row.is_core && !isActive(row.module))
      .map((row) => row.module)
      .sort();
    setSaved(false);
    mutation.mutate(disabled, {
      onSuccess: () => {
        // The response body is written into the cache by the hook, so the
        // edits have served their purpose and are dropped here rather than
        // reconciled — the server's answer is the state from now on.
        setEdits({});
        setSaved(true);
      },
    });
  };

  return (
    <div className="max-w-4xl mx-auto p-8 flex flex-col gap-6">
      <h1 className="text-2xl font-black text-foreground">
        {t("modules.title")}
      </h1>

      <div className="flex flex-col gap-2 max-w-sm">
        <label
          htmlFor="tenant-modules-select"
          className="text-sm font-semibold text-foreground"
        >
          {t("modules.tenantLabel")}
        </label>
        <select
          id="tenant-modules-select"
          className="border border-border rounded-md px-3 py-2 text-sm bg-background"
          value={tenantId ?? ""}
          onChange={(event) => {
            setSaved(false);
            // Unsaved edits belong to the tenant they were made in.
            setEdits({});
            setChosenTenantId(event.target.value || null);
          }}
        >
          <option value="">{t("modules.tenantPlaceholder")}</option>
          {(tenants ?? []).map((tenant) => (
            <option key={tenant.id} value={tenant.id}>
              {tenant.name}
            </option>
          ))}
        </select>
        {tenants && tenants.length === 0 && <p>{t("modules.empty")}</p>}
      </div>

      <p className="text-sm text-muted-foreground">{t("modules.coreHint")}</p>

      {tenantId && isPending && <p>{t("modules.loading")}</p>}
      {tenantId && isError && <p role="alert">{t("modules.loadError")}</p>}

      {data && (
        <>
          <div className="flex flex-col gap-6">
            {groups.map((group) => (
              <fieldset key={group.key} className="flex flex-col gap-2">
                <legend className="text-sm font-bold text-foreground">
                  {t(`modules.groups.${group.key}`)}
                </legend>
                {group.modules
                  .filter((module) => known.has(module))
                  .map((module) => (
                    <label
                      key={module}
                      className="flex items-center gap-2 text-sm"
                      htmlFor={`module-${module}`}
                    >
                      <input
                        id={`module-${module}`}
                        type="checkbox"
                        // The visible label carries the "core" badge as well,
                        // so the accessible name is stated explicitly here:
                        // a checkbox called "Papéis essencial" would be a
                        // worse announcement, not a better one.
                        aria-label={t(`modules.names.${module}`)}
                        checked={isActive(module)}
                        disabled={coreModules.has(module)}
                        onChange={() => toggle(module)}
                      />
                      {t(`modules.names.${module}`)}
                      {coreModules.has(module) && (
                        <span className="text-xs uppercase text-muted-foreground border border-border rounded px-1">
                          {t("modules.coreBadge")}
                        </span>
                      )}
                    </label>
                  ))}
              </fieldset>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={save}
              disabled={mutation.isPending}
              className="bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {mutation.isPending ? t("modules.saving") : t("modules.save")}
            </button>
            {saved && <span>{t("modules.saved")}</span>}
            {mutation.isError && <span role="alert">{t("modules.saveError")}</span>}
          </div>
        </>
      )}
    </div>
  );
};

export default TenantModulesPage;
