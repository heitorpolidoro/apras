import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import type {
  InfractionStepAction,
  NextStep,
} from "../../../types/infraction";

const ACTIONS: InfractionStepAction[] = ["AVISO", "NOTIFICACAO", "MULTA"];

/**
 * `NextStepRead`, rendered (§10.1).
 *
 * Two states are easy to collapse and must not be:
 *
 * - `reason === "NO_POLICY"` disables **"Aplicar sugestão"** and says why,
 *   because there is nothing to apply — the API answers 409. The override
 *   select stays enabled, because an explicit action is always accepted: the
 *   ladder is a suggestion engine, not a gate on staff judgement.
 * - `is_saturated` and `reason === "CLAMPED"` disagree at the last rung. The
 *   panel says "a política se esgotou" only when the ladder was actually
 *   truncated, or it would say it on the first application of the last step.
 */
export const NextStepPanel: React.FC<{
  nextStep: NextStep;
  onApply: (action: InfractionStepAction | null, note: string) => void;
  isSubmitting?: boolean;
}> = ({ nextStep, onApply, isSubmitting = false }) => {
  const { t } = useTranslation();
  const [override, setOverride] = useState<InfractionStepAction | "">("");
  const [note, setNote] = useState("");

  const noPolicy = nextStep.reason === "NO_POLICY";

  return (
    <div
      className="space-y-3 rounded-xl border border-gray-200 bg-white p-4"
      data-testid="next-step-panel"
    >
      <h3 className="text-base font-bold text-gray-900">
        {t("infractions.nextStep.title")}
      </h3>

      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-gray-500">
          {t("infractions.nextStep.recidivismCount")}
        </dt>
        <dd data-testid="recidivism-count">{nextStep.recidivism_count}</dd>
        <dt className="text-gray-500">{t("infractions.nextStep.window")}</dt>
        <dd data-testid="window-start">{nextStep.window_start}</dd>
        <dt className="text-gray-500">
          {t("infractions.nextStep.stagesApplied")}
        </dt>
        <dd>{nextStep.stages_applied}</dd>
        <dt className="text-gray-500">
          {t("infractions.nextStep.ladderIndex")}
        </dt>
        <dd>{nextStep.ladder_index}</dd>
      </dl>

      {noPolicy ? (
        <p className="text-sm text-amber-700" data-testid="no-policy-message">
          {t("infractions.nextStep.noPolicy")}
        </p>
      ) : (
        <p className="text-sm text-gray-900" data-testid="suggested-action">
          {t("infractions.nextStep.suggestion", {
            action: t(`infractions.actions.${nextStep.suggested_action}`),
            step: nextStep.suggested_step_order,
          })}
        </p>
      )}

      {nextStep.fine_amount !== null && (
        <p className="text-sm text-gray-900" data-testid="suggested-fine">
          {t("infractions.nextStep.fineAmount")}:{" "}
          {nextStep.fine_amount.toFixed(2)}
        </p>
      )}

      {nextStep.fine_amount_unavailable_reason === "CONDO_FEE_NOT_SET" && (
        <p className="text-sm text-red-700" data-testid="fee-not-set">
          {t("infractions.nextStep.feeNotSet")}
        </p>
      )}

      {nextStep.reason === "CLAMPED" && (
        <p className="text-xs text-gray-500" data-testid="clamped-message">
          {t("infractions.nextStep.clamped")}
        </p>
      )}

      <label className="block text-sm">
        <span className="text-gray-500">{t("infractions.nextStep.note")}</span>
        <textarea
          className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          aria-label={t("infractions.nextStep.note")}
        />
      </label>

      <label className="block text-sm">
        <span className="text-gray-500">
          {t("infractions.nextStep.override")}
        </span>
        <select
          className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
          data-testid="override-select"
          aria-label={t("infractions.nextStep.override")}
          value={override}
          onChange={(event) =>
            setOverride(event.target.value as InfractionStepAction | "")
          }
        >
          <option value="">{t("infractions.nextStep.followSuggestion")}</option>
          {ACTIONS.map((action) => (
            <option key={action} value={action}>
              {t(`infractions.actions.${action}`)}
            </option>
          ))}
        </select>
      </label>

      <div className="flex gap-2">
        <Button
          data-testid="apply-suggestion"
          disabled={noPolicy || !note.trim() || isSubmitting}
          onClick={() => onApply(null, note)}
        >
          {t("infractions.nextStep.apply")}
        </Button>
        <Button
          variant="outline"
          data-testid="apply-override"
          disabled={!override || !note.trim() || isSubmitting}
          onClick={() => onApply(override as InfractionStepAction, note)}
        >
          {t("infractions.nextStep.applyOverride")}
        </Button>
      </div>
    </div>
  );
};

export default NextStepPanel;
