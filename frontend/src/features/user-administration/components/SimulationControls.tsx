import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Select } from "../../../components/ui/select";
import { Label } from "../../../components/ui/label";
import { useSimulation } from "../context/SimulationContext";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { UserRole } from "../../../types/auth";
import UserTypeMultiSelect from "./UserTypeMultiSelect";

const SIMULATABLE_ROLES = [
  UserRole.DIRECTOR,
  UserRole.MANAGER,
  UserRole.GUEST,
] as const;

/**
 * Navbar control that lets a real Administrator activate a "view-as"
 * simulation of another role + UserType combination. Only rendered for the
 * real Administrator (see Navbar.tsx) — it must stay visible regardless of
 * the simulated role so the admin can always reach "Encerrar simulação".
 */
const SimulationControls: React.FC = () => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const {
    simulatedRole,
    simulatedUserTypeIds,
    isSimulating,
    setSimulatedRole,
    setSimulatedUserTypeIds,
    stopSimulation,
  } = useSimulation();
  const { data: userTypes } = useUserTypes();

  const handleRoleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setSimulatedRole(value ? (value as UserRole) : null);
  };

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
            <Label htmlFor="simulation-role">
              {t("simulation.roleLabel")}
            </Label>
            <Select
              id="simulation-role"
              value={simulatedRole ?? ""}
              onChange={handleRoleChange}
            >
              <option value="">{t("simulation.roleSelectPlaceholder")}</option>
              {SIMULATABLE_ROLES.map((role) => (
                <option key={role} value={role}>
                  {t(`roles.${role}`)}
                </option>
              ))}
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>{t("simulation.userTypesLabel")}</Label>
            <UserTypeMultiSelect
              userTypes={userTypes ?? []}
              selectedIds={simulatedUserTypeIds}
              onChange={setSimulatedUserTypeIds}
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
