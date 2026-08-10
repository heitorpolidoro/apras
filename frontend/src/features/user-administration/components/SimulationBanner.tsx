import React from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { useSimulation } from "../context/SimulationContext";
import { useUserTypes } from "../../../hooks/useUserTypes";

/**
 * Persistent, always-visible indicator shown on every page while an
 * Administrator is simulating another role, so the simulated view is never
 * mistaken for the real one.
 */
const SimulationBanner: React.FC = () => {
  const { t } = useTranslation();
  const { simulatedRole, simulatedUserTypeIds, isSimulating, stopSimulation } =
    useSimulation();
  const { data: userTypes } = useUserTypes();

  if (!isSimulating || !simulatedRole) return null;

  const selectedNames = (userTypes ?? [])
    .filter((userType) => simulatedUserTypeIds.includes(userType.id))
    .map((userType) => userType.name);

  const userTypesLabel =
    selectedNames.length > 0
      ? selectedNames.join(", ")
      : t("simulation.noUserTypes");

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-8 py-2.5 bg-amber-400 text-amber-950 text-sm font-semibold sticky top-0 z-30 shadow-sm">
      <span>
        {t("simulation.bannerLabel", {
          role: t(`roles.${simulatedRole}`),
          userTypes: userTypesLabel,
        })}
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="border-amber-950/30 bg-amber-400/40 hover:bg-amber-400/70"
        onClick={stopSimulation}
      >
        {t("simulation.stopButton")}
      </Button>
    </div>
  );
};

export default SimulationBanner;
