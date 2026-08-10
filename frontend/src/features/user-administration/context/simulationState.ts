/**
 * Module-level mirror of the current simulation flag.
 *
 * `SimulationContext` is a React context and can't be read from
 * non-component code such as the Axios client (`api/client.ts`). This tiny
 * singleton mirrors the pattern already used for reading `accessToken` from
 * storage inside the Axios interceptor, applied to the simulation flag
 * instead of a token: `SimulationContext` writes every state change here,
 * and the interceptor reads it synchronously on every request.
 */
export interface SimulationStateMirror {
  isSimulating: boolean;
}

let current: SimulationStateMirror = { isSimulating: false };

/** Updates the mirrored simulation state. Called by `SimulationContext` on every change. */
export const setSimulationState = (state: SimulationStateMirror): void => {
  current = state;
};

/** Reads the mirrored simulation state. Called by the Axios request interceptor. */
export const getSimulationState = (): SimulationStateMirror => current;

type ResetHandler = (() => void) | null;

let resetHandler: ResetHandler = null;

/**
 * Registers the function that fully resets the simulation (state + storage).
 * `SimulationProvider` registers its `stopSimulation` callback here on mount
 * so that `AuthContext.logout` — which has no access to React context — can
 * clear an in-progress simulation when the real user signs out.
 */
export const registerSimulationReset = (fn: ResetHandler): void => {
  resetHandler = fn;
};

/** Invokes the registered reset function, if any. Called by `AuthContext.logout`. */
export const triggerSimulationReset = (): void => {
  resetHandler?.();
};
