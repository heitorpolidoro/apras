import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Button } from "../../../components/ui/button";
import { useLots } from "../../lot-management/hooks/useLots";
import { useLotResidents } from "../../lot-management/hooks/useResidents";
import type {
  InfractionCreate,
  InfractionPromote,
  InfractionRule,
} from "../../../types/infraction";

/**
 * The page size the lot select asks for, and it is **the route's own ceiling**:
 * `GET /api/v1/lots/` declares `limit: int = Query(default=100, ge=1, le=100)`,
 * so anything above 100 is a FastAPI **422** before the handler runs — which is
 * exactly how round 2 shipped an empty select and an unregisterable infraction.
 *
 * Exported so `lotSelectContract.test.tsx` can assert it against that bound
 * without mocking the API module away. A number here is a contract with a
 * route, not a preference, and the two must be checked against each other by
 * something other than a reader's memory.
 */
export const LOT_SELECT_LIMIT = 100;

/** Just enough of an occurrence to promote it (APRAS-44 §7.4). */
export interface PromotionSource {
  id: string;
  protocol_number: string;
  lot_id?: string | null;
  description: string;
  created_at: string;
}

/**
 * Register an infraction directly (ER-3), **or** promote an occurrence (ER-6).
 *
 * One modal and not two, because the two differ in exactly three ways — where
 * the lot comes from, where the defaults come from, and which endpoint is
 * called — and a second component would have duplicated the rule select, the
 * responsible select and §7.7's whole client-side half.
 *
 * **The effective-lot rule (§7.4) is what promote mode encodes.**
 * `occurrence.lot_id` is nullable and `infraction.lot_id` is not, so:
 *
 * * the occurrence **has** a lot → it is shown, locked, and sent as nothing at
 *   all: the body omits `lot_id` and the server resolves it from the
 *   occurrence. That is the ordinary case, and §7.4's own words are "the
 *   caller types nothing".
 * * the occurrence has **no** lot (a common-area report) → the caller must
 *   attribute one, and the modal says why. That is the only case in which this
 *   form sends `lot_id` on a promotion, which is exactly the row of §7.4's
 *   table that permits it.
 *
 * It never sends a `lot_id` that contradicts the occurrence, so the 422 the
 * server owes a mismatched body is unreachable from here — enforced there
 * regardless, because a form is a convenience and never a guarantee.
 */
export const NewInfractionModal: React.FC<{
  rules: InfractionRule[];
  /** Present ⇒ promote mode. */
  occurrence?: PromotionSource | null;
  onClose: () => void;
  /** Required in create mode; absent in promote mode, which uses `onPromote`. */
  onSubmit?: (data: InfractionCreate) => void;
  onPromote?: (data: InfractionPromote) => void;
  isSubmitting?: boolean;
  /** A refusal from the server, rendered above the actions. */
  error?: string | null;
}> = ({
  rules,
  occurrence = null,
  onClose,
  onSubmit,
  onPromote,
  isSubmitting = false,
  error = null,
}) => {
  const { t } = useTranslation();
  const isPromotion = occurrence !== null;
  // The occurrence's own lot, when it has one, is not a choice: it is the
  // effective lot, and offering a select there would invite the mismatch 422.
  const lotIsFixed = isPromotion && !!occurrence?.lot_id;

  // `GET /api/v1/lots/` already accepts `block`, and `useLots` already
  // forwards it. Without this, a condominium past the route's 100-lot ceiling
  // simply cannot register an infraction against lot 101 onward -- the
  // truncation hint said so honestly and offered no way out.
  const [blockFilter, setBlockFilter] = useState("");

  const activeRules = rules.filter((rule) => rule.is_active);
  // Lot-management's own hooks, not a second pair: a private copy would be a
  // second cache key for the same server state, so deactivating a resident
  // over there would leave this form's list stale for the whole `staleTime`.
  const { data: lotPage } = useLots({
    block: blockFilter.trim() || undefined,
    limit: LOT_SELECT_LIMIT,
  });
  const lots = lotPage?.items ?? [];
  // The route is paginated and this select is not, so say so rather than
  // silently offering the first hundred as if they were all of them.
  const truncated = (lotPage?.total ?? 0) > lots.length;

  // The rule and lot selects are **derived**, not synchronised: their options
  // arrive asynchronously, and an effect that wrote the first one into state
  // would be a cascading render for a value that is a pure function of the
  // data plus the user's choice. State holds only the *choice*; the fallback
  // is computed.
  const [ruleChoice, setRuleChoice] = useState("");
  const [lotChoice, setLotChoice] = useState("");
  const [residentId, setResidentId] = useState("");
  const [occurredOn, setOccurredOn] = useState(
    occurrence ? occurrence.created_at.slice(0, 10) : "",
  );
  const [description, setDescription] = useState(occurrence?.description ?? "");

  const ruleId = ruleChoice || activeRules[0]?.id || "";
  // A lotless promotion deliberately has **no** default: attributing a
  // common-area report to a unit is a decision the síndico makes.
  const lotId =
    lotChoice ||
    (isPromotion ? (occurrence?.lot_id ?? "") : (lots[0]?.id ?? ""));

  const { data: residentPage } = useLotResidents(lotId || undefined);
  const residents = (residentPage?.items ?? []).filter(
    (resident) => resident.is_active,
  );

  const canSubmit =
    !!ruleId &&
    !!residentId &&
    !!occurredOn &&
    !!description.trim() &&
    (isPromotion ? lotIsFixed || !!lotId : !!lotId) &&
    !isSubmitting;

  const submit = () => {
    if (isPromotion && onPromote) {
      onPromote({
        rule_id: ruleId,
        responsible_resident_id: residentId,
        // Omitted when the occurrence already carries the lot: §7.4's
        // ordinary case, resolved server-side.
        lot_id: lotIsFixed ? null : lotId,
        description,
        occurred_on: occurredOn,
      });
      return;
    }
    onSubmit?.({
      rule_id: ruleId,
      lot_id: lotId,
      responsible_resident_id: residentId,
      occurred_on: occurredOn,
      description,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      data-testid="new-infraction-modal"
    >
      <div className="w-full max-w-lg space-y-3 rounded-xl bg-white p-6">
        <h2 className="text-lg font-bold text-gray-900">
          {isPromotion
            ? t("infractions.promote.title")
            : t("infractions.new.title")}
        </h2>

        {isPromotion && occurrence && (
          <p className="text-sm text-gray-500" data-testid="promotion-source">
            <Link
              className="text-indigo-600 underline"
              to={`/occurrences?occurrence=${occurrence.id}`}
            >
              {t("infractions.fields.sourceOccurrence")}:{" "}
              {occurrence.protocol_number}
            </Link>
          </p>
        )}

        <label className="block text-sm">
          <span className="text-gray-500">{t("infractions.fields.rule")}</span>
          <select
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.fields.rule")}
            value={ruleId}
            onChange={(event) => setRuleChoice(event.target.value)}
          >
            {activeRules.map((rule) => (
              <option key={rule.id} value={rule.id}>
                {rule.article}
              </option>
            ))}
          </select>
        </label>

        {lotIsFixed ? (
          <div className="block text-sm" data-testid="locked-lot">
            <span className="text-gray-500">{t("infractions.fields.lot")}</span>
            <p className="mt-1 rounded-lg bg-gray-50 p-2 text-sm text-gray-900">
              {(() => {
                const lot = lots.find((item) => item.id === occurrence?.lot_id);
                return lot
                  ? `${lot.block} / ${lot.lot_number}`
                  : t("infractions.promote.lotFromOccurrence");
              })()}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {t("infractions.promote.lotIsTheOccurrences")}
            </p>
          </div>
        ) : (
          <>
          {/* Its own label, not nested inside the lot's: a filter and the
              thing it filters are two controls, and sharing one label makes
              both unaddressable by name. */}
          <label className="block text-sm">
            <span className="text-gray-500">
              {t("infractions.new.blockFilter")}
            </span>
            <input
              className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
              aria-label={t("infractions.new.blockFilter")}
              placeholder={t("infractions.new.blockFilterPlaceholder")}
              value={blockFilter}
              onChange={(event) => {
                setBlockFilter(event.target.value);
                setLotChoice("");
                setResidentId("");
              }}
            />
          </label>

          <label className="block text-sm">
            <span className="text-gray-500">{t("infractions.fields.lot")}</span>
            <select
              className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
              aria-label={t("infractions.fields.lot")}
              value={lotId}
              onChange={(event) => {
                setLotChoice(event.target.value);
                setResidentId("");
              }}
            >
              <option value="">{t("infractions.ui.select")}</option>
              {lots.map((lot) => (
                <option key={lot.id} value={lot.id}>
                  {lot.block} / {lot.lot_number}
                </option>
              ))}
            </select>
            {isPromotion && (
              <p className="mt-1 text-xs text-amber-700" data-testid="lotless-hint">
                {t("infractions.promote.occurrenceHasNoLot")}
              </p>
            )}
            {truncated && (
              <p className="mt-1 text-xs text-gray-500" data-testid="lots-truncated">
                {t("infractions.new.lotsTruncated", {
                  shown: lots.length,
                  total: lotPage?.total ?? 0,
                })}
              </p>
            )}
          </label>
          </>
        )}

        <label className="block text-sm">
          <span className="text-gray-500">
            {t("infractions.fields.responsible")}
          </span>
          <select
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.fields.responsible")}
            value={residentId}
            onChange={(event) => setResidentId(event.target.value)}
          >
            <option value="">{t("infractions.ui.select")}</option>
            {residents.map((resident) => (
              <option key={resident.id} value={resident.id}>
                {resident.full_name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-gray-500">
            {t("infractions.fields.occurredOn")}
          </span>
          <input
            type="date"
            className="mt-1 w-full rounded-lg border border-gray-200 p-2 text-sm"
            aria-label={t("infractions.fields.occurredOn")}
            value={occurredOn}
            onChange={(event) => setOccurredOn(event.target.value)}
          />
        </label>

        <label className="block text-sm">
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

        {error && (
          <p
            className="rounded-lg bg-red-50 p-2 text-sm text-red-700"
            role="alert"
            data-testid="modal-error"
          >
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t("infractions.ui.cancel")}
          </Button>
          <Button
            data-testid="submit-new-infraction"
            disabled={!canSubmit}
            onClick={submit}
          >
            {isPromotion
              ? t("infractions.promote.submit")
              : t("infractions.new.submit")}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default NewInfractionModal;
