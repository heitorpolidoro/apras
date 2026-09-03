import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useCreatePlan,
  usePlans,
  useUpdatePlan,
} from "../../../hooks/usePlans";
import { useSubscription } from "../../../hooks/useSubscription";
import type { Plan } from "../../../types/subscription";

/**
 * The superuser screen behind `/admin/plans` (APRAS-40 §8.4).
 *
 * The plan table plus one create/edit form: the module checklist, the base
 * price, the per-module prices, the currency and `is_active`.
 *
 * **There is no delete.** `tenant_subscription.plan_id` is
 * `ON DELETE RESTRICT` and a plan a tenant is on must not vanish, so the
 * deactivation checkbox *is* the removal operation — exactly as for `Tenant`.
 *
 * **Prices are inert**: display metadata only, never charged.
 *
 * The module checklist excludes core modules, because a plan cannot "include"
 * what is always on — the API answers 400 for one, and offering the checkbox
 * would be offering a guaranteed error.
 */

const emptyDraft = () => ({
  name: "",
  description: "",
  included_modules: [] as string[],
  base_price: 0,
  module_prices: {} as Record<string, number>,
  currency: "BRL",
  is_active: true,
});

const PlansAdminPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: plans, isPending, isError } = usePlans();
  // The catalogue vocabulary comes from the acting tenant's own subscription
  // read, which lists one row per catalogue module with `is_core` on it. There
  // is deliberately no second endpoint and no hardcoded module list: this is
  // the same derivation the backend does, crossed once.
  const { data: subscription } = useSubscription();
  const createPlan = useCreatePlan();
  const updatePlan = useUpdatePlan();

  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [saved, setSaved] = useState(false);

  const toggleable = useMemo(
    () =>
      (subscription?.modules ?? [])
        .filter((row) => !row.is_core)
        .map((row) => row.module),
    [subscription],
  );

  const startNew = () => {
    setEditing(null);
    setDraft(emptyDraft());
    setSaved(false);
  };

  const startEdit = (plan: Plan) => {
    setEditing(plan.id);
    setDraft({
      name: plan.name,
      description: plan.description ?? "",
      included_modules: [...plan.included_modules],
      base_price: plan.base_price,
      module_prices: { ...plan.module_prices },
      currency: plan.currency,
      is_active: plan.is_active,
    });
    setSaved(false);
  };

  const toggleModule = (module: string) => {
    setSaved(false);
    setDraft((previous) => {
      const included = previous.included_modules.includes(module)
        ? previous.included_modules.filter((name) => name !== module)
        : [...previous.included_modules, module];
      // Dropping a module drops its price with it: the API refuses a price
      // for an uncovered module (400), so leaving the entry behind would make
      // Save a guaranteed error the operator cannot see the cause of.
      const prices = { ...previous.module_prices };
      if (!included.includes(module)) delete prices[module];
      return { ...previous, included_modules: included, module_prices: prices };
    });
  };

  const setPrice = (module: string, value: string) => {
    setSaved(false);
    setDraft((previous) => ({
      ...previous,
      module_prices: { ...previous.module_prices, [module]: Number(value) },
    }));
  };

  const mutation = editing === null ? createPlan : updatePlan;

  const save = () => {
    setSaved(false);
    const payload = {
      name: draft.name,
      description: draft.description || null,
      included_modules: draft.included_modules,
      base_price: draft.base_price,
      module_prices: draft.module_prices,
      currency: draft.currency,
      is_active: draft.is_active,
    };
    const done = {
      onSuccess: () => {
        setSaved(true);
        setEditing(null);
        setDraft(emptyDraft());
      },
    };
    if (editing === null) {
      createPlan.mutate(payload, done);
    } else {
      updatePlan.mutate({ planId: editing, payload }, done);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8 flex flex-col gap-6">
      <h1 className="text-2xl font-black text-foreground">{t("plans.title")}</h1>
      <p className="text-xs text-muted-foreground">
        {t("plans.inertPriceNotice")}
      </p>

      {isPending && <p>{t("plans.loading")}</p>}
      {isError && <p role="alert">{t("plans.loadError")}</p>}

      {plans && plans.length === 0 && <p>{t("plans.empty")}</p>}
      {plans && plans.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>{t("plans.name")}</th>
              <th>{t("plans.includedModules")}</th>
              <th>{t("plans.basePrice")}</th>
              <th>{t("plans.isActive")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {plans.map((plan) => (
              <tr key={plan.id}>
                <td>{plan.name}</td>
                <td>{plan.included_modules.length}</td>
                <td>
                  {plan.base_price} {plan.currency}
                </td>
                <td>{plan.is_active ? "" : t("plans.inactiveBadge")}</td>
                <td>
                  <button type="button" onClick={() => startEdit(plan)}>
                    {t("plans.edit")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <button type="button" onClick={startNew}>
        {t("plans.new")}
      </button>

      <form
        className="flex flex-col gap-3 border border-border rounded-md p-4"
        onSubmit={(event) => {
          event.preventDefault();
          save();
        }}
      >
        <label className="flex flex-col gap-1" htmlFor="plan-name">
          {t("plans.name")}
          <input
            id="plan-name"
            value={draft.name}
            onChange={(event) =>
              setDraft({ ...draft, name: event.target.value })
            }
          />
        </label>

        <label className="flex flex-col gap-1" htmlFor="plan-description">
          {t("plans.description")}
          <input
            id="plan-description"
            value={draft.description}
            onChange={(event) =>
              setDraft({ ...draft, description: event.target.value })
            }
          />
        </label>

        <label className="flex flex-col gap-1" htmlFor="plan-base-price">
          {t("plans.basePrice")}
          <input
            id="plan-base-price"
            type="number"
            value={draft.base_price}
            onChange={(event) =>
              setDraft({ ...draft, base_price: Number(event.target.value) })
            }
          />
        </label>

        <label className="flex flex-col gap-1" htmlFor="plan-currency">
          {t("plans.currency")}
          <input
            id="plan-currency"
            value={draft.currency}
            onChange={(event) =>
              setDraft({ ...draft, currency: event.target.value })
            }
          />
        </label>

        <label htmlFor="plan-is-active">
          <input
            id="plan-is-active"
            type="checkbox"
            checked={draft.is_active}
            onChange={(event) =>
              setDraft({ ...draft, is_active: event.target.checked })
            }
          />
          {t("plans.isActive")}
        </label>

        <fieldset className="flex flex-col gap-2">
          <legend>{t("plans.includedModules")}</legend>
          {toggleable.map((module) => (
            <div key={module} className="flex items-center gap-2 text-sm">
              <label htmlFor={`plan-module-${module}`}>
                <input
                  id={`plan-module-${module}`}
                  type="checkbox"
                  aria-label={t(`modules.names.${module}`)}
                  checked={draft.included_modules.includes(module)}
                  onChange={() => toggleModule(module)}
                />
                {t(`modules.names.${module}`)}
              </label>
              {draft.included_modules.includes(module) && (
                <input
                  type="number"
                  aria-label={`${t("plans.modulePrices")} ${t(
                    `modules.names.${module}`,
                  )}`}
                  value={draft.module_prices[module] ?? 0}
                  onChange={(event) => setPrice(module, event.target.value)}
                />
              )}
            </div>
          ))}
        </fieldset>

        <div className="flex items-center gap-4">
          <button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t("plans.saving") : t("plans.save")}
          </button>
          {saved && <span>{t("plans.saved")}</span>}
          {mutation.isError && <span role="alert">{t("plans.saveError")}</span>}
        </div>
      </form>
    </div>
  );
};

export default PlansAdminPage;
