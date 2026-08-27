import { useAuth } from "./AuthContext";
import { useSimulation } from "./SimulationContext";
import type { UserRole } from "../../../types/auth";

export interface EffectiveIdentity {
  /** The role to use for permission decisions: simulated when simulating, real otherwise. */
  role: UserRole | undefined;
  /** The UserType ids to use for permission decisions: simulated when simulating, real otherwise. */
  userTypeIds: string[];
  /** `true` when the real Administrator is currently simulating another role. */
  isSimulating: boolean;
}

/**
 * Returns the identity (role + UserType ids) that UI permission decisions
 * should use: the simulated role/UserTypes while an Administrator is
 * "viewing as" another role, or the real authenticated user's own
 * role/UserTypes otherwise.
 *
 * Route guards (`ProtectedRoute`) intentionally do NOT use this hook for
 * requiredRole/requiredRoles checks — those must always reflect the real
 * user's access so the admin can never get locked out of ending a
 * simulation. The one exception is `requiredMenu` checks (via
 * `useMenuAccess`), which intentionally DO use simulated identity so
 * admin-role-simulation can preview menu-gated pages; this is safe because
 * the exit-simulation control (`SimulationBanner`) is rendered outside
 * `ProtectedRoute`/`<Routes>` in App.tsx and is always reachable.
 */
export const useEffectiveIdentity = (): EffectiveIdentity => {
  const { user } = useAuth();
  const { simulatedRole, simulatedUserTypeIds, isSimulating } =
    useSimulation();

  if (isSimulating && simulatedRole) {
    return {
      role: simulatedRole,
      userTypeIds: simulatedUserTypeIds,
      isSimulating: true,
    };
  }

  return {
    role: user?.role,
    userTypeIds: user?.user_types?.map((userType) => userType.id) ?? [],
    isSimulating: false,
  };
};
