import React from "react";
import { useTranslation } from "react-i18next";
import { ContestationForm } from "../components/ContestationForm";
import { InfractionStageTimeline } from "../components/InfractionStageTimeline";
import { useAddContestation, useMyInfractions } from "../hooks/useInfractions";

/**
 * The resident's own view (ER-7, ER-8).
 *
 * It lists nothing but the infractions of the lots the caller is linked to —
 * the backend narrows, so this page never filters — and it is the *only*
 * surface that renders `ContestationForm`, which is what makes §7.5's 403
 * unreachable from the UI.
 *
 * A caller with no linked lot gets an empty list and a sentence, never a
 * refusal: `infractions:my_lots_read` is a filter, not an inverted gate.
 */
export const MyInfractionsPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: infractions, isLoading } = useMyInfractions();
  const contest = useAddContestation();

  return (
    <div className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {t("infractions.mine.pageTitle")}
        </h1>
        <p className="text-sm text-gray-500">
          {t("infractions.mine.pageSubtitle")}
        </p>
      </div>

      {isLoading && (
        <p className="text-sm text-gray-500">{t("infractions.ui.loading")}</p>
      )}

      {!isLoading && (infractions?.length ?? 0) === 0 && (
        <p
          className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500"
          data-testid="my-infractions-empty"
        >
          {t("infractions.mine.empty")}
        </p>
      )}

      {(infractions ?? []).map((infraction) => (
        <div
          key={infraction.id}
          data-testid={`my-infraction-${infraction.id}`}
          className="space-y-3 rounded-xl border border-gray-200 bg-white p-6"
        >
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900">
              {infraction.rule.article}
            </h2>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
              {infraction.current_stage
                ? t(`infractions.actions.${infraction.current_stage}`)
                : t("infractions.stageFilter.NONE")}
            </span>
          </div>
          <p className="text-sm text-gray-700">{infraction.description}</p>

          {infraction.defense_due_on && (
            <p
              className="rounded-lg bg-amber-50 p-2 text-sm text-amber-800"
              data-testid={`deadline-${infraction.id}`}
            >
              {t("infractions.mine.deadline", {
                date: infraction.defense_due_on,
              })}
            </p>
          )}

          <InfractionStageTimeline entries={infraction.timeline} />

          <ContestationForm
            defenseDueOn={infraction.defense_due_on}
            isSubmitting={contest.isPending}
            onSubmit={(body) =>
              contest.mutate({ id: infraction.id, data: { body } })
            }
          />
        </div>
      ))}
    </div>
  );
};

export default MyInfractionsPage;
