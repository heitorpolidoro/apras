import React from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";

/**
 * Persistent, always-visible indicator shown on every page while an
 * administrator is simulating a set of roles, so the simulated view is never
 * mistaken for the real one.
 *
 * IAM F5 (APRAS-49 §10.3): the label lost its `{{role}}` interpolation with
 * the enum; a simulation is now exactly the role names it selects.
 */
const SimulationBanner: React.FC = () => {
  const { t } = useTranslation();
  const { simulatedRoleIds, isSimulating, stopSimulation } = useSimulation();
  const { data: roles } = useRoles();

  if (!isSimulating) return null;

  const selectedNames = (roles ?? [])
    .filter((role) => simulatedRoleIds.includes(role.id))
    .map((role) => role.name);

  const rolesLabel =
    selectedNames.length > 0
      ? selectedNames.join(", ")
      : t("simulation.noRoles");

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-8 py-2.5 bg-amber-400 text-amber-950 text-sm font-semibold sticky top-0 z-30 shadow-sm">
      <span>
        {t("simulation.bannerLabel", { roles: rolesLabel })}{" "}
        {/* §2.7: the preview shows the simulated roles' menus, while the
            administrator's own route access stays on their real permission
            set — so a menu and its route can disagree here, by design. */}
        <span className="font-normal">
          {t("simulation.permissionsPreviewNote")}
        </span>
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
