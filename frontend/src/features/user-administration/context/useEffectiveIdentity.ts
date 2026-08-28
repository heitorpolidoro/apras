import { useAuth } from "./AuthContext";
import { useSimulation } from "./SimulationContext";
import { useUserTypes } from "../../../hooks/useUserTypes";
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
 * Since APRAS-9, `userTypeIds` also folds in the id of the UserType
 * implicitly linked to the effective role (real or simulated), mirroring
 * the backend's `get_effective_user_type_ids`: a user/simulation with zero
 * explicitly-assigned UserTypes still gets their role-type id here. This is
 * the single fold-in point — `useMenuAccess`, `useTaskFiltering`,
 * `TaskList`, `TaskBoard`, and `simulatedPermissions` all consume
 * `userTypeIds` from this hook (directly or via `useEffectiveIdentity()`),
 * so none of them need any code change to inherit the role-type fallback.
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
  const { data: userTypes } = useUserTypes();

  const roleTypeId = (role: UserRole | undefined): string | undefined =>
    userTypes?.find((userType) => userType.role === role)?.id;

  if (isSimulating && simulatedRole) {
    const simulatedRoleTypeId = roleTypeId(simulatedRole);
    return {
      role: simulatedRole,
      userTypeIds: simulatedRoleTypeId
        ? [...new Set([...simulatedUserTypeIds, simulatedRoleTypeId])]
        : simulatedUserTypeIds,
      isSimulating: true,
    };
  }

  const explicitUserTypeIds =
    user?.user_types?.map((userType) => userType.id) ?? [];
  const realRoleTypeId = roleTypeId(user?.role);

  return {
    role: user?.role,
    userTypeIds: realRoleTypeId
      ? [...new Set([...explicitUserTypeIds, realRoleTypeId])]
      : explicitUserTypeIds,
    isSimulating: false,
  };
};
