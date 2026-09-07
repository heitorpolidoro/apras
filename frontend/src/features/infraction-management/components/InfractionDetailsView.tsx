import React from "react";
import { Link } from "react-router-dom";
import { Button } from "../../../components/ui/button";
import { useTranslation } from "react-i18next";
import type { Infraction, InfractionStepAction, NextStep } from "../../../types/infraction";
import { InfractionStageTimeline } from "./InfractionStageTimeline";
import { NextStepPanel } from "./NextStepPanel";

/**
 * One process: header, evidence, the merged timeline and the next-step panel.
 *
 * The origin occurrence is a **link**, not a label: ER-6 makes the promotion
 * navigable in both directions, and `source_occurrence_protocol` is carried on
 * the payload precisely so this renders without a second fetch.
 */
export const InfractionDetailsView: React.FC<{
  infraction: Infraction;
  nextStep?: NextStep;
  onApplyStage?: (action: InfractionStepAction | null, note: string) => void;
  /** Opens the cycle close for **this** infraction's (rule, responsible). */
  onCloseCycle?: () => void;
  isSubmitting?: boolean;
}> = ({ infraction, nextStep, onApplyStage, onCloseCycle, isSubmitting }) => {
  const { t } = useTranslation();

  return (
    <div className="space-y-4" data-testid="infraction-details">
      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <h2 className="text-lg font-bold text-gray-900">
          {infraction.rule.article}
        </h2>
        <p className="text-sm text-gray-500">
          {t(`infractions.origins.${infraction.rule.origin}`)}
        </p>

        <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
          <dt className="text-gray-500">{t("infractions.fields.lot")}</dt>
          <dd>
            {infraction.lot.block} / {infraction.lot.lot_number}
          </dd>
          <dt className="text-gray-500">
            {t("infractions.fields.responsible")}
          </dt>
          <dd data-testid="responsible-name">
            {infraction.responsible.full_name}
          </dd>
          <dt className="text-gray-500">
            {t("infractions.fields.occurredOn")}
          </dt>
          <dd>{infraction.occurred_on}</dd>
          <dt className="text-gray-500">
            {t("infractions.fields.currentStage")}
          </dt>
          <dd data-testid="current-stage">
            {infraction.current_stage
              ? t(`infractions.actions.${infraction.current_stage}`)
              : t("infractions.stageFilter.NONE")}
          </dd>
        </dl>

        <p className="mt-3 text-sm text-gray-700">{infraction.description}</p>

        {infraction.source_occurrence_id && (
          <p className="mt-3 text-sm">
            <Link
              className="text-indigo-600 underline"
              data-testid="source-occurrence-link"
              to={`/occurrences?occurrence=${infraction.source_occurrence_id}`}
            >
              {t("infractions.fields.sourceOccurrence")}:{" "}
              {infraction.source_occurrence_protocol}
            </Link>
          </p>
        )}

        {/* Reading is never gated on `uploads:photo_create`: whoever may see
            the infraction may see its proof, and a permission to create does
            not govern display. */}
        {infraction.evidence_urls.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm" data-testid="evidence-list">
            {infraction.evidence_urls.map((url, index) => (
              <li key={url} className="flex items-center gap-2">
                <img
                  src={url}
                  alt={t("infractions.attachments.imageAlt", {
                    index: index + 1,
                  })}
                  className="h-10 w-10 rounded object-cover"
                />
                <a className="text-indigo-600 underline" href={url}>
                  {url}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <h3 className="mb-3 text-base font-bold text-gray-900">
          {t("infractions.timeline.title")}
        </h3>
        <InfractionStageTimeline entries={infraction.timeline} />
      </div>

      {nextStep && onApplyStage && (
        <NextStepPanel
          nextStep={nextStep}
          onApply={onApplyStage}
          isSubmitting={isSubmitting}
        />
      )}

      {/* ER-9's manual close, offered where the síndico is already looking at
          the (rule, responsible) whose ladder they want to restart. The count
          is personal and resets by construction on a change of responsible
          (§6.2); this covers the one case the legal addendum names -- a
          resident change not reflected in the cadastre in time. */}
      {onCloseCycle && (
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <h3 className="text-base font-bold text-gray-900">
            {t("infractions.cycleClose.title")}
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            {t("infractions.cycleClose.explanation", {
              article: infraction.rule.article,
              name: infraction.responsible.full_name,
            })}
          </p>
          <Button
            className="mt-3"
            variant="outline"
            data-testid="open-cycle-close"
            onClick={onCloseCycle}
          >
            {t("infractions.cycleClose.submit")}
          </Button>
        </div>
      )}
    </div>
  );
};

export default InfractionDetailsView;
