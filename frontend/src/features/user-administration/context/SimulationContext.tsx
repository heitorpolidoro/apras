import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
} from "react";
import { UserRole, type UserRole as UserRoleType } from "../../../types/auth";
import {
  setSimulationState,
  registerSimulationReset,
} from "./simulationState";

const STORAGE_ROLE_KEY = "simulation.role";
const STORAGE_USER_TYPE_IDS_KEY = "simulation.userTypeIds";

const VALID_ROLES: ReadonlySet<string> = new Set(Object.values(UserRole));

interface SimulationContextType {
  /** The role currently being simulated, or `null` when not simulating. */
  simulatedRole: UserRoleType | null;
  /** The UserType ids currently selected for the simulation. */
  simulatedUserTypeIds: string[];
  /** `true` once a role has been picked. */
  isSimulating: boolean;
  /** Sets the simulated role. Passing `null` deactivates the simulation. */
  setSimulatedRole: (role: UserRoleType | null) => void;
  /** Sets the simulated UserType id selection. */
  setSimulatedUserTypeIds: (ids: string[]) => void;
  /** Clears the simulated role and UserType selection. */
  stopSimulation: () => void;
}

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined,
);

/** Reads the persisted simulated role, discarding stale/invalid values. */
function readStoredRole(): UserRoleType | null {
  const stored = sessionStorage.getItem(STORAGE_ROLE_KEY);
  if (stored && VALID_ROLES.has(stored)) {
    return stored as UserRoleType;
  }
  return null;
}

/** Reads the persisted simulated UserType id selection. */
function readStoredUserTypeIds(): string[] {
  const stored = sessionStorage.getItem(STORAGE_USER_TYPE_IDS_KEY);
  if (!stored) return [];
  try {
    const parsed: unknown = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((value): value is string => typeof value === "string");
  } catch {
    return [];
  }
}

export const SimulationProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [simulatedRole, setSimulatedRoleState] = useState<UserRoleType | null>(
    readStoredRole,
  );
  const [simulatedUserTypeIds, setSimulatedUserTypeIdsState] = useState<
    string[]
  >(readStoredUserTypeIds);

  const isSimulating = simulatedRole !== null;

  useEffect(() => {
    setSimulationState({ isSimulating });
  }, [isSimulating]);

  const setSimulatedRole = useCallback((role: UserRoleType | null) => {
    setSimulatedRoleState(role);
    if (role === null) {
      sessionStorage.removeItem(STORAGE_ROLE_KEY);
    } else {
      sessionStorage.setItem(STORAGE_ROLE_KEY, role);
    }
  }, []);

  const setSimulatedUserTypeIds = useCallback((ids: string[]) => {
    setSimulatedUserTypeIdsState(ids);
    sessionStorage.setItem(STORAGE_USER_TYPE_IDS_KEY, JSON.stringify(ids));
  }, []);

  const stopSimulation = useCallback(() => {
    setSimulatedRoleState(null);
    setSimulatedUserTypeIdsState([]);
    sessionStorage.removeItem(STORAGE_ROLE_KEY);
    sessionStorage.removeItem(STORAGE_USER_TYPE_IDS_KEY);
  }, []);

  // Let AuthContext.logout clear an in-progress simulation without needing
  // access to this context (see simulationState.ts).
  useEffect(() => {
    registerSimulationReset(stopSimulation);
    return () => registerSimulationReset(null);
  }, [stopSimulation]);

  const value = useMemo(
    () => ({
      simulatedRole,
      simulatedUserTypeIds,
      isSimulating,
      setSimulatedRole,
      setSimulatedUserTypeIds,
      stopSimulation,
    }),
    [
      simulatedRole,
      simulatedUserTypeIds,
      isSimulating,
      setSimulatedRole,
      setSimulatedUserTypeIds,
      stopSimulation,
    ],
  );

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = (): SimulationContextType => {
  const context = useContext(SimulationContext);
  if (context === undefined) {
    throw new Error("useSimulation must be used within a SimulationProvider");
  }
  return context;
};
