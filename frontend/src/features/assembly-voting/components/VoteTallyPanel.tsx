import React from "react";
import { useTranslation } from "react-i18next";
import { useTally } from "../hooks/useVoting";
import type { VoteRead } from "../../../types/voting";

interface VoteTallyPanelProps {
  vote: VoteRead;
}

/**
 * Tally panel.
 *
 * The window gate is enforced server-side — while the vote is open the API
 * simply does not send `results`/`attributions`. This component renders
 * whatever it is given and never reconstructs a partial result, so hiding
 * here is a display decision, not the security boundary.
 */
const VoteTallyPanel: React.FC<VoteTallyPanelProps> = ({ vote }) => {
  const { t } = useTranslation();
  const { data: tally, isLoading } = useTally(vote.id);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">{t("voting.tally.loading")}</p>;
  }
  if (!tally) return null;

  const isClosed = tally.status === "CLOSED";
  const hasDenominator =
    tally.total_lots !== undefined && tally.total_lots !== null;

  return (
    <section className="rounded-lg border border-border/60 p-4 space-y-3">
      <h3 className="text-base font-semibold">{t("voting.tally.title")}</h3>

      <div className="flex flex-wrap items-baseline gap-2">
        <p className="text-sm font-medium" data-testid="tally-voters-count">
          {t("voting.tally.votersCount", { count: tally.voters_count })}
        </p>
        {hasDenominator && (
          <p className="text-sm text-muted-foreground" data-testid="tally-denominator">
            {t("voting.tally.denominator", { total: tally.total_lots })}
          </p>
        )}
      </div>

      {!isClosed && (
        <p className="text-sm text-muted-foreground">
          {t("voting.tally.resultsAfterClose")}
        </p>
      )}

      {tally.is_anonymous && (
        <p className="text-sm text-muted-foreground">
          {t("voting.tally.anonymousAggregateOnly")}
        </p>
      )}

      {isClosed && tally.results && (
        <div data-testid="tally-results">
          <h4 className="text-sm font-semibold mb-1">{t("voting.tally.results")}</h4>
          <ul className="space-y-1">
            {tally.results.map((result) => (
              <li key={result.option_id} className="text-sm flex justify-between">
                <span>{result.label}</span>
                <span className="font-semibold">{result.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {isClosed && tally.attributions && (
        <div data-testid="tally-attributions">
          <h4 className="text-sm font-semibold mb-1">
            {t("voting.tally.attributions")}
          </h4>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th>
                  {tally.kind === "ASSEMBLEIA"
                    ? t("voting.tally.lot")
                    : t("voting.tally.voter")}
                </th>
                <th>{t("voting.tally.choice")}</th>
                <th>{t("voting.tally.castAt")}</th>
              </tr>
            </thead>
            <tbody>
              {tally.attributions.map((entry, index) => (
                <tr key={`${entry.lot_id ?? entry.voter_user_id ?? index}`}>
                  <td>{entry.lot_label ?? entry.voter_name ?? "—"}</td>
                  <td>{entry.selected_labels.join(", ")}</td>
                  <td>{new Date(entry.cast_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

export default VoteTallyPanel;
