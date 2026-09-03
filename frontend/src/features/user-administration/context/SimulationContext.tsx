import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
} from "react";
import { setSimulationState, registerSimulationReset,  } from "./simulationState";

const STORAGE_USER_TYPE_IDS_KEY = "simulation.roleIds";

/**
 * IAM F5 (APRAS-49 §10.3) deleted `simulatedRole`: there is no enum left to
 * simulate, and a simulation is now exactly a set of roles. `isSimulating`
 * is therefore "at least one role is selected" rather than "a role value has
 * been picked", which is the same statement in the model that exists.
 */
interface SimulationContextType {
  /** The role ids currently selected for the simulation. */
  simulatedRoleIds: string[];
  /** `true` once at least one role has been selected. */
  isSimulating: boolean;
  /** Sets the simulated role id selection. */
  setSimulatedRoleIds: (ids: string[]) => void;
  /** Clears the simulated role selection. */
  stopSimulation: () => void;
}

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined,
);

/** Reads the persisted simulated Role id selection. */
function readStoredRoleIds(): string[] {
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
  const [simulatedRoleIds, setSimulatedRoleIdsState] = useState<
    string[]
  >(readStoredRoleIds);

  const isSimulating = simulatedRoleIds.length > 0;

  useEffect(() => {
    setSimulationState({ isSimulating });
  }, [isSimulating]);

  const setSimulatedRoleIds = useCallback((ids: string[]) => {
    setSimulatedRoleIdsState(ids);
    sessionStorage.setItem(STORAGE_USER_TYPE_IDS_KEY, JSON.stringify(ids));
  }, []);

  const stopSimulation = useCallback(() => {
    setSimulatedRoleIdsState([]);
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
      simulatedRoleIds,
      isSimulating,
      setSimulatedRoleIds,
      stopSimulation,
    }),
    [simulatedRoleIds, isSimulating, setSimulatedRoleIds, stopSimulation],
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
