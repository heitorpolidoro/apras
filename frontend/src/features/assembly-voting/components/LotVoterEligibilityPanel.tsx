import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import {
  useAddLotVoterEligibility,
  useLotVoterEligibility,
  useRemoveLotVoterEligibility,
} from "../hooks/useVoting";

interface LotVoterEligibilityPanelProps {
  lotId: string;
}

interface ApiError extends Error {
  response?: { data?: { detail?: string } };
}

/**
 * Extra assembly voters of a lot.
 *
 * Owners are eligible automatically; this list covers whoever represents
 * the unit without being recorded as an owner (a spouse, typically), which
 * depends on paperwork APRAS does not verify — hence the manual curation
 * by ADMINISTRATOR/DIRECTOR/MANAGER.
 */
const LotVoterEligibilityPanel: React.FC<LotVoterEligibilityPanelProps> = ({
  lotId,
}) => {
  const { t } = useTranslation();
  const { data: entries } = useLotVoterEligibility(lotId);
  const addMutation = useAddLotVoterEligibility();
  const removeMutation = useRemoveLotVoterEligibility();
  const [userId, setUserId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleAdd = (event: React.FormEvent) => {
    event.preventDefault();
    if (!userId.trim()) return;
    setError(null);
    addMutation.mutate(
      { lotId, userId: userId.trim() },
      {
        onSuccess: () => setUserId(""),
        onError: (err: ApiError) =>
          setError(
            err.response?.data?.detail || t("voting.eligibility.errorAdding"),
          ),
      },
    );
  };

  const handleRemove = (targetUserId: string) => {
    setError(null);
    removeMutation.mutate(
      { lotId, userId: targetUserId },
      {
        onError: (err: ApiError) =>
          setError(
            err.response?.data?.detail || t("voting.eligibility.errorRemoving"),
          ),
      },
    );
  };

  return (
    <section className="rounded-lg border border-border/60 p-4 space-y-3">
      <h3 className="text-base font-semibold">{t("voting.eligibility.title")}</h3>
      <p className="text-xs text-muted-foreground">
        {t("voting.eligibility.hint")}
      </p>

      {entries && entries.length > 0 ? (
        <ul className="space-y-1">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="flex items-center justify-between text-sm"
            >
              <span>{entry.user_name ?? entry.user_id}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleRemove(entry.user_id)}
              >
                {t("voting.eligibility.remove")}
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          {t("voting.eligibility.empty")}
        </p>
      )}

      <form onSubmit={handleAdd} className="flex gap-2">
        <Input
          value={userId}
          onChange={(event) => setUserId(event.target.value)}
          placeholder={t("voting.eligibility.userIdPlaceholder")}
          aria-label={t("voting.eligibility.userIdPlaceholder")}
        />
        <Button type="submit" size="sm" disabled={addMutation.isPending}>
          {t("voting.eligibility.add")}
        </Button>
      </form>

      {error && <p className="text-sm text-destructive">{error}</p>}
    </section>
  );
};

export default LotVoterEligibilityPanel;
