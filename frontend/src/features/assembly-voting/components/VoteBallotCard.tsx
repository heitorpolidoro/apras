import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import {
  useCastBallot,
  useMyBallot,
  useRetractBallot,
} from "../hooks/useVoting";
import type { MyBallotRead, VoteRead } from "../../../types/voting";

interface EligibleLot {
  id: string;
  label: string;
}

interface VoteBallotCardProps {
  vote: VoteRead;
  eligibleLots?: EligibleLot[];
}

interface ApiError extends Error {
  response?: { data?: { detail?: string } };
}

const isWindowOpen = (vote: VoteRead): boolean =>
  vote.status === "OPEN" && new Date(vote.closes_at).getTime() > Date.now();

/**
 * Ballot card.
 *
 * Exactly one ballot is active per lot (assembly) or per person (poll).
 * Whoever cast it is its holder and is the only one who may change or
 * retract it — everyone else eligible sees it read-only, which is the
 * "who lives together" transparency rule of the spec.
 */
const VoteBallotCard: React.FC<VoteBallotCardProps> = ({
  vote,
  eligibleLots = [],
}) => {
  const { t } = useTranslation();
  const isAssembly = vote.kind === "ASSEMBLEIA";
  const windowOpen = isWindowOpen(vote);

  const { data: ballots } = useMyBallot(vote.id);
  const castMutation = useCastBallot();
  const retractMutation = useRetractBallot();

  const [selectedLotId, setSelectedLotId] = useState<string | null>(
    eligibleLots[0]?.id ?? null,
  );
  const [selectedOptionIds, setSelectedOptionIds] = useState<string[]>([]);
  const [isChanging, setIsChanging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const myBallots = useMemo(() => ballots ?? [], [ballots]);
  const targetBallot = useMemo(() => {
    if (isAssembly) {
      return myBallots.find((ballot) => ballot.lot_id === selectedLotId) ?? null;
    }
    return myBallots.find((ballot) => ballot.can_edit) ?? null;
  }, [isAssembly, myBallots, selectedLotId]);

  const otherBallots = myBallots.filter((ballot) => ballot !== targetBallot);

  const optionLabel = (optionId: string) =>
    vote.options.find((option) => option.id === optionId)?.label ?? optionId;

  const toggleOption = (optionId: string) => {
    setSelectedOptionIds((current) => {
      if (vote.vote_type === "SINGLE_CHOICE") return [optionId];
      return current.includes(optionId)
        ? current.filter((id) => id !== optionId)
        : [...current, optionId];
    });
  };

  const handleCast = () => {
    if (selectedOptionIds.length === 0) return;
    setError(null);
    castMutation.mutate(
      {
        voteId: vote.id,
        data: {
          lot_id: isAssembly ? selectedLotId : null,
          selected_option_ids: selectedOptionIds,
        },
      },
      {
        onSuccess: () => {
          setIsChanging(false);
          setSelectedOptionIds([]);
        },
        onError: (err: ApiError) => {
          setError(err.response?.data?.detail || t("voting.ballot.errorCasting"));
        },
      },
    );
  };

  const handleRetract = (ballot: MyBallotRead) => {
    setError(null);
    retractMutation.mutate(
      {
        voteId: vote.id,
        data: { lot_id: isAssembly ? ballot.lot_id ?? null : null },
      },
      {
        onError: (err: ApiError) => {
          setError(
            err.response?.data?.detail || t("voting.ballot.errorRetracting"),
          );
        },
      },
    );
  };

  const renderBallotSummary = (ballot: MyBallotRead) => (
    <div
      key={ballot.id}
      className="rounded-md border border-border/50 p-3 space-y-1"
    >
      {ballot.lot_label && (
        <p className="text-xs font-semibold text-muted-foreground">
          {ballot.lot_label}
        </p>
      )}
      <p className="text-sm">
        {ballot.selected_option_ids.map(optionLabel).join(", ")}
      </p>
      {ballot.can_edit ? (
        windowOpen && (
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setIsChanging(true);
                setSelectedOptionIds(ballot.selected_option_ids);
                if (ballot.lot_id) setSelectedLotId(ballot.lot_id);
              }}
            >
              {t("voting.ballot.change")}
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={() => handleRetract(ballot)}
            >
              {t("voting.ballot.retract")}
            </Button>
          </div>
        )
      ) : (
        <p className="text-xs text-muted-foreground">
          {t("voting.ballot.readOnlyHint", {
            name: ballot.voter_name ?? "—",
          })}
        </p>
      )}
    </div>
  );

  const showForm = windowOpen && (!targetBallot || isChanging);

  return (
    <section className="rounded-lg border border-border/60 p-4 space-y-3">
      <h3 className="text-base font-semibold">{t("voting.ballot.title")}</h3>

      {!windowOpen && (
        <p className="text-sm text-muted-foreground">
          {t("voting.ballot.windowClosed")}
        </p>
      )}

      {vote.is_anonymous && (
        <p className="text-xs text-muted-foreground">
          {t("voting.anonymityNotice")}
        </p>
      )}

      {targetBallot && renderBallotSummary(targetBallot)}
      {otherBallots.map(renderBallotSummary)}

      {showForm && (
        <div className="space-y-2">
          {isAssembly && eligibleLots.length > 1 && (
            <label className="block text-sm">
              {t("voting.ballot.chooseLot")}
              <select
                className="ml-2 rounded-md border border-border/60 px-2 py-1 text-sm"
                value={selectedLotId ?? ""}
                onChange={(event) => setSelectedLotId(event.target.value)}
              >
                {eligibleLots.map((lot) => (
                  <option key={lot.id} value={lot.id}>
                    {lot.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          <fieldset className="space-y-1">
            {vote.options.map((option) => (
              <label
                key={option.id}
                className="flex items-center gap-2 text-sm"
                htmlFor={`option-${option.id}`}
              >
                <input
                  id={`option-${option.id}`}
                  type={
                    vote.vote_type === "SINGLE_CHOICE" ? "radio" : "checkbox"
                  }
                  name={`vote-${vote.id}`}
                  checked={selectedOptionIds.includes(option.id)}
                  onChange={() => toggleOption(option.id)}
                />
                {option.label}
              </label>
            ))}
          </fieldset>

          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              onClick={handleCast}
              disabled={selectedOptionIds.length === 0}
            >
              {isChanging ? t("voting.ballot.confirmChange") : t("voting.ballot.cast")}
            </Button>
            {isChanging && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setIsChanging(false);
                  setSelectedOptionIds([]);
                }}
              >
                {t("voting.ballot.cancelChange")}
              </Button>
            )}
          </div>
        </div>
      )}

      {!targetBallot && !showForm && (
        <p className="text-sm text-muted-foreground">
          {t("voting.ballot.noBallot")}
        </p>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
    </section>
  );
};

export default VoteBallotCard;
