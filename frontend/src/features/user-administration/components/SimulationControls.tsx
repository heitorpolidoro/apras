import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Label } from "../../../components/ui/label";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import RoleMultiSelect from "./RoleMultiSelect";

/**
 * Navbar control that lets a real administrator activate a "view-as"
 * simulation of a set of roles. Rendered only for a caller holding
 * `roles:update` (see Navbar.tsx) — it must stay visible regardless of what
 * is being simulated so the admin can always reach "Encerrar simulação".
 *
 * IAM F5 (APRAS-49 §10.2) removed the hard-coded three-value role dropdown:
 * every role in the tenant is now simulatable, which is strictly more than
 * the enum allowed and needs no second vocabulary.
 */
const SimulationControls: React.FC = () => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const { simulatedRoleIds, isSimulating, setSimulatedRoleIds, stopSimulation } =
    useSimulation();
  const { data: roles } = useRoles();

  const handleStop = () => {
    stopSimulation();
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <Button
        type="button"
        variant={isSimulating ? "secondary" : "outline"}
        size="sm"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
      >
        {t("simulation.toggleButton")}
      </Button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 rounded-lg border border-border bg-popover p-4 shadow-lg z-50 flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>{t("simulation.rolesLabel")}</Label>
            <RoleMultiSelect
              roles={roles ?? []}
              selectedIds={simulatedRoleIds}
              onChange={setSimulatedRoleIds}
            />
          </div>

          {isSimulating && (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={handleStop}
            >
              {t("simulation.stopButton")}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default SimulationControls;
