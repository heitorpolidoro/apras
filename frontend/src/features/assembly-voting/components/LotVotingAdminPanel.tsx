import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { UserRole } from "../../../types/auth";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import { useLots } from "../../lot-management/hooks/useLots";
import { useUpdateLotDelinquency } from "../hooks/useVoting";
import LotVoterEligibilityPanel from "./LotVoterEligibilityPanel";

interface ApiError extends Error {
  response?: { data?: { detail?: string } };
}

/**
 * Per-lot voting administration: the manual delinquency flag (board only,
 * it is what suspends the unit's voting right) and the extra eligible
 * voters of the lot (board and manager).
 */
const LotVotingAdminPanel: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();
  const isBoard = role === UserRole.ADMINISTRATOR || role === UserRole.DIRECTOR;

  const { data: lots } = useLots();
  const delinquencyMutation = useUpdateLotDelinquency();
  const [selectedLotId, setSelectedLotId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const items = lots?.items ?? [];
  const selectedLot = items.find((lot) => lot.id === selectedLotId) ?? null;

  const handleToggleDelinquency = () => {
    if (!selectedLot) return;
    setError(null);
    delinquencyMutation.mutate(
      { lotId: selectedLot.id, isDelinquent: !selectedLot.is_delinquent },
      {
        onError: (err: ApiError) =>
          setError(
            err.response?.data?.detail || t("voting.delinquency.errorUpdating"),
          ),
      },
    );
  };

  return (
    <section className="rounded-lg border border-border/60 p-4 space-y-3">
      <h2 className="text-lg font-bold">{t("voting.lotAdmin.title")}</h2>

      <label className="block text-sm">
        {t("voting.lotAdmin.selectLot")}
        <select
          className="ml-2 rounded-md border border-border/60 px-2 py-1 text-sm"
          value={selectedLotId ?? ""}
          onChange={(event) => setSelectedLotId(event.target.value || null)}
        >
          <option value="">—</option>
          {items.map((lot) => (
            <option key={lot.id} value={lot.id}>
              {lot.block}/{lot.lot_number}
            </option>
          ))}
        </select>
      </label>

      {selectedLot && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <p className="text-sm" data-testid="delinquency-state">
              {selectedLot.is_delinquent
                ? t("voting.delinquency.delinquent")
                : t("voting.delinquency.settled")}
            </p>
            {isBoard && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleToggleDelinquency}
                disabled={delinquencyMutation.isPending}
              >
                {selectedLot.is_delinquent
                  ? t("voting.delinquency.markSettled")
                  : t("voting.delinquency.markDelinquent")}
              </Button>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {t("voting.delinquency.hint")}
          </p>

          <LotVoterEligibilityPanel lotId={selectedLot.id} />
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
    </section>
  );
};

export default LotVotingAdminPanel;
