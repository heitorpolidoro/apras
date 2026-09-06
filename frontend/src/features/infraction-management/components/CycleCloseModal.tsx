import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import type {
  CycleCloseCreate,
  InfractionRuleSummary,
  ResidentSummary,
} from "../../../types/infraction";

/**
 * Close a `(rule, responsible)` recidivism cycle (ER-9).
 *
 * **The pair is pinned, not chosen.** A cycle *is* `(rule, responsible)`
 * (§6.2), and this modal is reached from an infraction of that exact pair, so
 * both are shown read-only. An earlier draft offered a rule select, which
 * quietly invited closing a cycle other than the one the síndico was looking
 * at — the two are one click apart and the mistake is silent, because a close
 * against the wrong rule is a perfectly valid row.
 *
 * The justification is **required** and the confirmation says, in as many
 * words, that nothing is deleted: the close is a cutoff going forward, an
 * already-registered infraction keeps its count, and both facts are easy to
 * assume the other way round when the button says "encerrar".
 *
 * The lot is **optional** and labelled as audit context, because it is not
 * part of the recidivism predicate (§6.2 property 5) — a modal that made it
 * look like a filter would teach the síndico the wrong model.
 */
export const CycleCloseModal: React.FC<{
  rule: InfractionRuleSummary;
  responsible: ResidentSummary;
  lotId?: string | null;
  onClose: () => void;
  onSubmit: (data: CycleCloseCreate) => void;
  isSubmitting?: boolean;
  error?: string | null;
}> = ({
  rule,
  responsible,
  lotId,
  onClose,
  onSubmit,
  isSubmitting = false,
  error = null,
}) => {
  const { t } = useTranslation();
  const [justification, setJustification] = useState("");
  const [includeLot, setIncludeLot] = useState(false);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      data-testid="cycle-close-modal"
    >
      <div className="w-full max-w-lg space-y-4 rounded-xl bg-white p-6">
        <h2 className="text-lg font-bold text-gray-900">
          {t("infractions.cycleClose.title")}
        </h2>

        <dl
          className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm"
          data-testid="cycle-close-pair"
        >
          <dt className="text-gray-500">{t("infractions.fields.rule")}</dt>
          <dd className="text-gray-900">{rule.article}</dd>
          <dt className="text-gray-500">
            {t("infractions.fields.responsible")}
          </dt>
          <dd className="text-gray-900">{responsible.full_name}</dd>
        </dl>

        <p className="text-sm text-gray-600" data-testid="cycle-close-warning">
          {t("infractions.cycleClose.nothingIsDeleted")}
        </p>

        {lotId && (
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeLot}
              onChange={(event) => setIncludeLot(event.target.checked)}
              aria-label={t("infractions.cycleClose.includeLot")}
            />
            <span className="text-gray-500">
              {t("infractions.cycleClose.includeLot")}
            </span>
          </label>
        )}

        <label className="block text-sm">
          <span className="text-gray-500">
            {t("infractions.cycleClose.justification")}
          </span>
          <textarea
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.cycleClose.justification")}
            value={justification}
            onChange={(event) => setJustification(event.target.value)}
          />
        </label>

        {error && (
          <p
            className="rounded-lg bg-red-50 p-2 text-sm text-red-700"
            role="alert"
            data-testid="cycle-close-error"
          >
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t("infractions.ui.cancel")}
          </Button>
          <Button
            data-testid="submit-cycle-close"
            disabled={!justification.trim() || isSubmitting}
            onClick={() =>
              onSubmit({
                rule_id: rule.id,
                responsible_resident_id: responsible.id,
                lot_id: includeLot ? lotId : null,
                justification,
              })
            }
          >
            {t("infractions.cycleClose.submit")}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default CycleCloseModal;
