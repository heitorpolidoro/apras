import { useAuth } from "./AuthContext";
import { useSimulation } from "./SimulationContext";

export interface EffectiveIdentity {
  /** The role ids to use for display decisions: simulated when simulating. */
  roleIds: string[];
  /** `true` when a real administrator is currently simulating. */
  isSimulating: boolean;
}

/**
 * The role ids UI *display* decisions should use: the simulated selection
 * while an administrator is "viewing as" other roles, or the real user's own
 * memberships otherwise.
 *
 * IAM F5 (APRAS-49 §10.3) deleted the `role` field. There is no enum left,
 * and the role-implicit membership it used to fold in became a real
 * `user_role_link` row at migration time, so `user.roles` is now the whole
 * answer and this hook has no query of its own.
 *
 * **This hook is display-only.** Route guards read the *real* permission set
 * through `useCanAccess`, which imports neither this hook nor
 * `useSimulation` — the absence of those imports on that path is the
 * mechanical guarantee that an administrator can never be locked out of
 * ending a simulation (APRAS-35, re-pinned by
 * `ProtectedRoute.permissions.test.tsx`). The one exception is
 * `landing_path`, which follows the effective identity on purpose: landing
 * is a preference, not authorization (§10.4).
 */
export const useEffectiveIdentity = (): EffectiveIdentity => {
  const { user } = useAuth();
  const { simulatedRoleIds, isSimulating } = useSimulation();

  if (isSimulating) {
    return { roleIds: simulatedRoleIds, isSimulating: true };
  }

  return {
    roleIds: user?.roles?.map((role) => role.id) ?? [],
    isSimulating: false,
  };
};
