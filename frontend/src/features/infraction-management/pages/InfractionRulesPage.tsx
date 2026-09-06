import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import {
  useCreateInfractionRule,
  useDeactivateInfractionRule,
  useInfractionRules,
  useInfractionSettings,
  useWriteInfractionPolicy,
  useWriteInfractionSettings,
} from "../hooks/useInfractionRules";
import type {
  InfractionFineMode,
  InfractionPolicyStep,
  InfractionRuleOrigin,
  InfractionStepAction,
} from "../../../types/infraction";

const ORIGINS: InfractionRuleOrigin[] = [
  "ESTATUTO",
  "REGIMENTO_INTERNO",
  "CONVENCAO",
];
const ACTIONS: InfractionStepAction[] = ["AVISO", "NOTIFICACAO", "MULTA"];
const FINE_MODES: InfractionFineMode[] = ["FIXED", "MULTIPLE"];

/** The ladder is written whole, so the editor is a list, not a per-row form. */
const renumber = (steps: InfractionPolicyStep[]): InfractionPolicyStep[] =>
  steps.map((step, index) => ({ ...step, step_order: index + 1 }));

/**
 * The catalogue and the per-rule escalation ladder (§10.1).
 *
 * `step_order` is never typed by hand: it is derived from the list position on
 * every add, remove and reorder, which is what makes "contiguous from 1"
 * unbreakable from this screen — the API validates it anyway, and the two
 * agreeing is the point.
 */
export const InfractionRulesPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: rules, isLoading } = useInfractionRules();
  const { data: settings } = useInfractionSettings();
  const createRule = useCreateInfractionRule();
  const deactivateRule = useDeactivateInfractionRule();
  const writePolicy = useWriteInfractionPolicy();
  const writeSettings = useWriteInfractionSettings();

  const [article, setArticle] = useState("");
  const [origin, setOrigin] = useState<InfractionRuleOrigin>("REGIMENTO_INTERNO");
  const [description, setDescription] = useState("");
  const [windowDays, setWindowDays] = useState("365");

  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const [draftSteps, setDraftSteps] = useState<InfractionPolicyStep[]>([]);
  const [fee, setFee] = useState("");

  const startEditing = (ruleId: string, steps: InfractionPolicyStep[]) => {
    setEditingRuleId(ruleId);
    setDraftSteps(steps.map((step) => ({ ...step })));
  };

  const updateStep = (index: number, patch: Partial<InfractionPolicyStep>) =>
    setDraftSteps((previous) =>
      previous.map((step, position) =>
        position === index ? { ...step, ...patch } : step,
      ),
    );

  const move = (index: number, delta: number) =>
    setDraftSteps((previous) => {
      const target = index + delta;
      if (target < 0 || target >= previous.length) return previous;
      const next = [...previous];
      [next[index], next[target]] = [next[target], next[index]];
      return renumber(next);
    });

  return (
    <div className="container mx-auto space-y-6 px-4 py-8">
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {t("infractions.rules.pageTitle")}
        </h1>
        <p className="text-sm text-gray-500">
          {t("infractions.rules.pageSubtitle")}
        </p>
      </div>

      <div
        className="space-y-2 rounded-xl border border-gray-200 bg-white p-4"
        data-testid="settings-panel"
      >
        <h2 className="text-base font-bold text-gray-900">
          {t("infractions.settings.title")}
        </h2>
        <p className="text-sm text-gray-500">
          {t("infractions.settings.explanation")}
        </p>
        <div className="flex items-end gap-2">
          <label className="block text-sm">
            <span className="text-gray-500">
              {t("infractions.settings.condoFee")}
            </span>
            <input
              type="number"
              className="mt-1 w-40 rounded-lg border border-gray-200 p-2 text-sm"
              aria-label={t("infractions.settings.condoFee")}
              value={fee !== "" ? fee : (settings?.condo_fee_amount ?? "")}
              onChange={(event) => setFee(event.target.value)}
            />
          </label>
          <Button
            data-testid="save-settings"
            onClick={() => writeSettings.mutate(fee === "" ? null : Number(fee))}
          >
            {t("infractions.ui.save")}
          </Button>
        </div>
      </div>

      <div
        className="space-y-3 rounded-xl border border-gray-200 bg-white p-4"
        data-testid="new-rule-form"
      >
        <h2 className="text-base font-bold text-gray-900">
          {t("infractions.rules.newTitle")}
        </h2>
        <div className="grid gap-2 md:grid-cols-2">
          <label className="block text-sm">
            <span className="text-gray-500">
              {t("infractions.fields.article")}
            </span>
            <input
              className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
              aria-label={t("infractions.fields.article")}
              value={article}
              onChange={(event) => setArticle(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="text-gray-500">
              {t("infractions.fields.origin")}
            </span>
            <select
              className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
              aria-label={t("infractions.fields.origin")}
              value={origin}
              onChange={(event) =>
                setOrigin(event.target.value as InfractionRuleOrigin)
              }
            >
              {ORIGINS.map((value) => (
                <option key={value} value={value}>
                  {t(`infractions.origins.${value}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm md:col-span-2">
            <span className="text-gray-500">
              {t("infractions.fields.description")}
            </span>
            <textarea
              className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
              aria-label={t("infractions.fields.description")}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="text-gray-500">
              {t("infractions.fields.recidivismWindow")}
            </span>
            <input
              type="number"
              className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
              aria-label={t("infractions.fields.recidivismWindow")}
              value={windowDays}
              onChange={(event) => setWindowDays(event.target.value)}
            />
          </label>
        </div>
        <Button
          data-testid="submit-new-rule"
          disabled={!article.trim() || !description.trim()}
          onClick={() => {
            createRule.mutate({
              article,
              origin,
              description,
              recidivism_window_days: Number(windowDays),
            });
            setArticle("");
            setDescription("");
          }}
        >
          {t("infractions.rules.create")}
        </Button>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4">
        {isLoading && (
          <p className="text-sm text-gray-500">{t("infractions.ui.loading")}</p>
        )}
        {!isLoading && (rules?.length ?? 0) === 0 && (
          <p className="text-sm text-gray-500" data-testid="rules-empty">
            {t("infractions.rules.empty")}
          </p>
        )}

        <ul className="space-y-4">
          {(rules ?? []).map((rule) => (
            <li
              key={rule.id}
              className="rounded-lg border border-gray-100 p-3"
              data-testid={`rule-row-${rule.id}`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-900">
                    {rule.article}
                  </div>
                  <div className="text-xs text-gray-500">
                    {t(`infractions.origins.${rule.origin}`)} ·{" "}
                    {t("infractions.fields.recidivismWindow")}:{" "}
                    {rule.recidivism_window_days}
                  </div>
                  <p className="mt-1 text-sm text-gray-700">
                    {rule.description}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {!rule.is_active && (
                    <span
                      className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                      data-testid={`rule-inactive-${rule.id}`}
                    >
                      {t("infractions.rules.inactive")}
                    </span>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    data-testid={`edit-policy-${rule.id}`}
                    onClick={() => startEditing(rule.id, rule.steps)}
                  >
                    {t("infractions.rules.editPolicy")}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    data-testid={`deactivate-${rule.id}`}
                    disabled={!rule.is_active}
                    onClick={() => deactivateRule.mutate(rule.id)}
                  >
                    {t("infractions.rules.deactivate")}
                  </Button>
                </div>
              </div>

              {editingRuleId === rule.id && (
                <div className="mt-3 space-y-2" data-testid="policy-editor">
                  {draftSteps.map((step, index) => (
                    <div
                      key={`step-${step.step_order}-${index}`}
                      className="flex flex-wrap items-end gap-2 rounded-lg border border-gray-100 p-2"
                      data-testid={`policy-step-${index}`}
                    >
                      <span className="text-sm font-semibold">
                        {step.step_order}
                      </span>
                      <select
                        className="rounded-lg border border-gray-200 p-1 text-sm"
                        aria-label={t("infractions.fields.action")}
                        value={step.action}
                        onChange={(event) =>
                          updateStep(index, {
                            action: event.target.value as InfractionStepAction,
                            defense_deadline_days: null,
                            fine_mode: null,
                            fine_fixed_amount: null,
                            fine_fee_multiplier: null,
                          })
                        }
                      >
                        {ACTIONS.map((action) => (
                          <option key={action} value={action}>
                            {t(`infractions.actions.${action}`)}
                          </option>
                        ))}
                      </select>

                      {step.action === "NOTIFICACAO" && (
                        <input
                          type="number"
                          className="w-28 rounded-lg border border-gray-200 p-1 text-sm"
                          aria-label={t("infractions.fields.deadlineDays")}
                          value={step.defense_deadline_days ?? ""}
                          onChange={(event) =>
                            updateStep(index, {
                              defense_deadline_days: Number(event.target.value),
                            })
                          }
                        />
                      )}

                      {step.action === "MULTA" && (
                        <>
                          <select
                            className="rounded-lg border border-gray-200 p-1 text-sm"
                            aria-label={t("infractions.fields.fineMode")}
                            value={step.fine_mode ?? ""}
                            onChange={(event) =>
                              updateStep(index, {
                                fine_mode: event.target
                                  .value as InfractionFineMode,
                                fine_fixed_amount: null,
                                fine_fee_multiplier: null,
                              })
                            }
                          >
                            <option value="">{t("infractions.ui.select")}</option>
                            {FINE_MODES.map((mode) => (
                              <option key={mode} value={mode}>
                                {t(`infractions.fineModes.${mode}`)}
                              </option>
                            ))}
                          </select>
                          {step.fine_mode === "FIXED" && (
                            <input
                              type="number"
                              className="w-28 rounded-lg border border-gray-200 p-1 text-sm"
                              aria-label={t("infractions.fields.fineAmount")}
                              value={step.fine_fixed_amount ?? ""}
                              onChange={(event) =>
                                updateStep(index, {
                                  fine_fixed_amount: Number(event.target.value),
                                })
                              }
                            />
                          )}
                          {step.fine_mode === "MULTIPLE" && (
                            <input
                              type="number"
                              className="w-28 rounded-lg border border-gray-200 p-1 text-sm"
                              aria-label={t("infractions.fields.fineMultiplier")}
                              value={step.fine_fee_multiplier ?? ""}
                              onChange={(event) =>
                                updateStep(index, {
                                  fine_fee_multiplier: Number(
                                    event.target.value,
                                  ),
                                })
                              }
                            />
                          )}
                        </>
                      )}

                      <Button
                        size="sm"
                        variant="outline"
                        data-testid={`move-up-${index}`}
                        onClick={() => move(index, -1)}
                      >
                        ↑
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        data-testid={`move-down-${index}`}
                        onClick={() => move(index, 1)}
                      >
                        ↓
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        data-testid={`remove-step-${index}`}
                        onClick={() =>
                          setDraftSteps((previous) =>
                            renumber(
                              previous.filter(
                                (_step, position) => position !== index,
                              ),
                            ),
                          )
                        }
                      >
                        {t("infractions.ui.remove")}
                      </Button>
                    </div>
                  ))}

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      data-testid="add-step"
                      onClick={() =>
                        setDraftSteps((previous) =>
                          renumber([
                            ...previous,
                            { step_order: previous.length + 1, action: "AVISO" },
                          ]),
                        )
                      }
                    >
                      {t("infractions.rules.addStep")}
                    </Button>
                    <Button
                      size="sm"
                      data-testid="save-policy"
                      disabled={draftSteps.length === 0}
                      onClick={() => {
                        writePolicy.mutate({
                          id: rule.id,
                          steps: renumber(draftSteps),
                        });
                        setEditingRuleId(null);
                      }}
                    >
                      {t("infractions.ui.save")}
                    </Button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default InfractionRulesPage;
