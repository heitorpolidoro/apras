import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { Button } from "../../../components/ui/button";
import { InfractionDetailsView } from "../components/InfractionDetailsView";
import { NewInfractionModal } from "../components/NewInfractionModal";
import { CycleCloseModal } from "../components/CycleCloseModal";
import {
  useAddInfractionStage,
  useCloseCycle,
  useCreateInfraction,
  useCycleCloses,
  useInfraction,
  useInfractions,
  useNextStep,
  usePromoteOccurrence,
} from "../hooks/useInfractions";
import { useInfractionRules } from "../hooks/useInfractionRules";
import { useOccurrenceDetail } from "../../occurrence-management/hooks/useOccurrences";
import { parseApiError } from "../../../api/errors";
import type {
  InfractionListFilters,
  InfractionStageFilter,
} from "../../../types/infraction";

const STAGE_OPTIONS: InfractionStageFilter[] = [
  "NONE",
  "AVISO",
  "NOTIFICACAO",
  "MULTA",
];

const PAGE_SIZE = 20;

/**
 * The management list plus the detail (§10.1).
 *
 * All five filters of §4.5 are here, `stage` included, and `stage` is the one
 * worth noticing: it reads the **derived** current stage server-side through a
 * correlated subquery, so the option list carries `NONE` — "no stage applied
 * yet" — which is not a step action and could not live in the action enum.
 *
 * **This page is also the landing point of the occurrence bridge (ER-6).**
 * `OccurrenceDetailsView` links here rather than promoting inline, because a
 * promotion needs a rule and a responsible resident that only this screen's
 * forms can offer. Two query parameters are the whole protocol:
 *
 * * `?occurrence=<id>` — open the create modal in **promote mode**, its lot
 *   resolved by §7.4's effective-lot rule and its defaults taken from the
 *   occurrence. Submitting calls `POST /infractions/from-occurrence/{id}`.
 * * `?infraction=<id>` — select that infraction, so the "already promoted"
 *   links on the occurrence detail land on the process itself rather than on
 *   an unfiltered list.
 *
 * **The URL is the state**, not a message the page copies into `useState` on
 * mount. Which infraction is selected and which occurrence is being promoted
 * are both read straight from the query string, and closing either surface
 * writes the query string back. That removes the "consume the parameter once"
 * bookkeeping entirely — there is nothing to consume — and it is what makes
 * the browser's back button, a reload and a pasted link all behave the way a
 * reader would expect. The five *filters* stay local: they are not addressable
 * and nobody links to them.
 */
export const InfractionsPage: React.FC = () => {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<InfractionListFilters>({
    skip: 0,
    limit: PAGE_SIZE,
  });
  const [isCreating, setIsCreating] = useState(false);
  const [isClosingCycle, setIsClosingCycle] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  // Read, never copied into state (see the note above).
  const selectedId = searchParams.get("infraction");
  const promotingId = searchParams.get("occurrence");
  const select = (infractionId: string | null) =>
    setSearchParams(infractionId ? { infraction: infractionId } : {});

  const { data: page, isLoading } = useInfractions(filters);
  const { data: rules } = useInfractionRules();
  const { data: selected } = useInfraction(selectedId);
  const { data: nextStep } = useNextStep(selectedId);
  const { data: promotionSource } = useOccurrenceDetail(promotingId);
  const { data: cycles } = useCycleCloses();
  const createInfraction = useCreateInfraction();
  const promoteOccurrence = usePromoteOccurrence();
  const addStage = useAddInfractionStage();
  const closeCycle = useCloseCycle();

  // This module refuses more requests than any of its neighbours -- §7.7's two
  // 422s and §6.3's and §6.5's 409s are all *expected* answers a síndico needs
  // to read, not bugs. Firing the mutation and closing the modal in the same
  // tick, as round 2 did, showed them a modal closing and no infraction
  // appearing, with the reason discarded.
  const refusal = (mutation: { error: unknown }) =>
    mutation.error
      ? parseApiError(mutation.error, t, {
          validationError: "infractions.errors.validation",
          genericError: "infractions.errors.generic",
        })
      : null;

  const setFilter = (key: keyof InfractionListFilters, value: string) =>
    setFilters((previous) => ({
      ...previous,
      skip: 0,
      [key]: value === "" ? undefined : value,
    }));

  // The *filter* options are derived from the current page on purpose: a
  // filter can only usefully narrow what is already there. The **forms** must
  // not be — `NewInfractionModal` fetches lots (searchable by block) and the
  // residents of the chosen lot through lot-management's own `useLots` /
  // `useLotResidents`, or the first infraction on a lot would be
  // unregisterable.
  const lots = Array.from(
    new Map(
      (page?.items ?? []).map((item) => [
        item.lot.id,
        { id: item.lot.id, label: `${item.lot.block} / ${item.lot.lot_number}` },
      ]),
    ).values(),
  );
  const residents = Array.from(
    new Map(
      (page?.items ?? []).map((item) => [item.responsible.id, item.responsible]),
    ).values(),
  );

  return (
    <div className="container mx-auto space-y-6 px-4 py-8">
      <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {t("infractions.pageTitle")}
          </h1>
          <p className="text-sm text-gray-500">
            {t("infractions.pageSubtitle")}
          </p>
        </div>
        <Button
          data-testid="open-new-infraction"
          onClick={() => setIsCreating(true)}
        >
          {t("infractions.new.title")}
        </Button>
      </div>

      <div
        className="grid gap-3 rounded-xl border border-gray-200 bg-white p-4 md:grid-cols-3"
        data-testid="infraction-filters"
      >
        <label className="block text-sm">
          <span className="text-gray-500">{t("infractions.fields.rule")}</span>
          <select
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.filters.rule")}
            value={filters.rule_id ?? ""}
            onChange={(event) => setFilter("rule_id", event.target.value)}
          >
            <option value="">{t("infractions.ui.all")}</option>
            {(rules ?? []).map((rule) => (
              <option key={rule.id} value={rule.id}>
                {rule.article}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-gray-500">{t("infractions.fields.lot")}</span>
          <select
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.filters.lot")}
            value={filters.lot_id ?? ""}
            onChange={(event) => setFilter("lot_id", event.target.value)}
          >
            <option value="">{t("infractions.ui.all")}</option>
            {lots.map((lot) => (
              <option key={lot.id} value={lot.id}>
                {lot.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-gray-500">
            {t("infractions.fields.responsible")}
          </span>
          <select
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.filters.responsible")}
            value={filters.responsible_id ?? ""}
            onChange={(event) => setFilter("responsible_id", event.target.value)}
          >
            <option value="">{t("infractions.ui.all")}</option>
            {residents.map((resident) => (
              <option key={resident.id} value={resident.id}>
                {resident.full_name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-gray-500">
            {t("infractions.fields.currentStage")}
          </span>
          <select
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.filters.stage")}
            value={filters.stage ?? ""}
            onChange={(event) => setFilter("stage", event.target.value)}
          >
            <option value="">{t("infractions.ui.all")}</option>
            {STAGE_OPTIONS.map((stage) => (
              <option key={stage} value={stage}>
                {t(`infractions.stageFilter.${stage}`)}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-gray-500">{t("infractions.filters.from")}</span>
          <input
            type="date"
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.filters.from")}
            value={filters.date_from ?? ""}
            onChange={(event) => setFilter("date_from", event.target.value)}
          />
        </label>

        <label className="block text-sm">
          <span className="text-gray-500">{t("infractions.filters.to")}</span>
          <input
            type="date"
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.filters.to")}
            value={filters.date_to ?? ""}
            onChange={(event) => setFilter("date_to", event.target.value)}
          />
        </label>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4">
        {isLoading && <p className="text-sm text-gray-500">{t("infractions.ui.loading")}</p>}
        {!isLoading && (page?.items.length ?? 0) === 0 && (
          <p className="text-sm text-gray-500" data-testid="infractions-empty">
            {t("infractions.empty")}
          </p>
        )}
        <ul className="space-y-2">
          {(page?.items ?? []).map((infraction) => (
            <li key={infraction.id}>
              <button
                type="button"
                data-testid={`infraction-row-${infraction.id}`}
                className="w-full rounded-lg border border-gray-100 p-3 text-left hover:bg-gray-50"
                onClick={() => select(infraction.id)}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900">
                    {infraction.rule.article}
                  </span>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                    {infraction.current_stage
                      ? t(`infractions.actions.${infraction.current_stage}`)
                      : t("infractions.stageFilter.NONE")}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  {infraction.lot.block} / {infraction.lot.lot_number} ·{" "}
                  {infraction.responsible.full_name} · {infraction.occurred_on}
                </div>
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-3 flex items-center justify-between text-sm">
          <span data-testid="infractions-total">
            {t("infractions.total", { count: page?.total ?? 0 })}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              data-testid="page-previous"
              disabled={(filters.skip ?? 0) === 0}
              onClick={() =>
                setFilters((previous) => ({
                  ...previous,
                  skip: Math.max(0, (previous.skip ?? 0) - PAGE_SIZE),
                }))
              }
            >
              {t("infractions.ui.previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              data-testid="page-next"
              disabled={
                (filters.skip ?? 0) + PAGE_SIZE >= (page?.total ?? 0)
              }
              onClick={() =>
                setFilters((previous) => ({
                  ...previous,
                  skip: (previous.skip ?? 0) + PAGE_SIZE,
                }))
              }
            >
              {t("infractions.ui.next")}
            </Button>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <h2 className="text-base font-bold text-gray-900">
          {t("infractions.cycleClose.listTitle")}
        </h2>
        {(cycles?.length ?? 0) === 0 ? (
          <p className="mt-2 text-sm text-gray-500" data-testid="cycles-empty">
            {t("infractions.cycleClose.listEmpty")}
          </p>
        ) : (
          <ul className="mt-2 space-y-2" data-testid="cycle-close-list">
            {(cycles ?? []).map((cycle) => (
              <li
                key={cycle.id}
                data-testid={`cycle-close-${cycle.id}`}
                className="rounded-lg border border-gray-100 p-3 text-sm"
              >
                <div className="font-semibold text-gray-900">
                  {cycle.rule.article} · {cycle.responsible.full_name}
                </div>
                <div className="text-xs text-gray-500">
                  {cycle.closed_by.full_name} ·{" "}
                  {new Date(cycle.closed_at).toLocaleString()}
                </div>
                <p className="mt-1 text-gray-700">{cycle.justification}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      {addStage.error && (
        <p
          className="rounded-lg bg-red-50 p-3 text-sm text-red-700"
          role="alert"
          data-testid="stage-error"
        >
          {refusal(addStage)}
        </p>
      )}

      {selected && (
        <InfractionDetailsView
          infraction={selected}
          nextStep={nextStep}
          isSubmitting={addStage.isPending}
          onApplyStage={(action, note) =>
            addStage.mutate({ id: selected.id, data: { action, note } })
          }
          onCloseCycle={() => setIsClosingCycle(true)}
        />
      )}

      {isClosingCycle && selected && (
        <CycleCloseModal
          rule={selected.rule}
          responsible={selected.responsible}
          lotId={selected.lot.id}
          isSubmitting={closeCycle.isPending}
          error={refusal(closeCycle)}
          onClose={() => {
            closeCycle.reset();
            setIsClosingCycle(false);
          }}
          onSubmit={(data) =>
            // Closed on success only: an empty justification is a 422 the
            // síndico has to be able to read and correct in place.
            closeCycle.mutate(data, {
              onSuccess: () => setIsClosingCycle(false),
            })
          }
        />
      )}

      {isCreating && (
        <NewInfractionModal
          rules={rules ?? []}
          isSubmitting={createInfraction.isPending}
          error={refusal(createInfraction)}
          onClose={() => {
            createInfraction.reset();
            setIsCreating(false);
          }}
          onSubmit={(data) =>
            // Closed on *success*, not on submit: a 422 has to leave the form
            // open with the values still in it.
            createInfraction.mutate(data, {
              onSuccess: () => setIsCreating(false),
            })
          }
        />
      )}

      {promotingId && promotionSource && (
        <NewInfractionModal
          rules={rules ?? []}
          occurrence={{
            id: promotionSource.id,
            protocol_number: promotionSource.protocol_number,
            lot_id: promotionSource.lot_id,
            description: promotionSource.description,
            created_at: promotionSource.created_at,
          }}
          isSubmitting={promoteOccurrence.isPending}
          error={refusal(promoteOccurrence)}
          onClose={() => {
            promoteOccurrence.reset();
            select(null);
          }}
          onPromote={(data) => {
            promoteOccurrence.mutate(
              { occurrenceId: promotingId, data },
              // Land on the process that was just created, which is also what
              // clears `?occurrence=` from the URL.
              { onSuccess: (created) => select(created.id) },
            );
          }}
        />
      )}
    </div>
  );
};

export default InfractionsPage;
