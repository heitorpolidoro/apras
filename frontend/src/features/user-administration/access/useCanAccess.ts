import { useMemo } from "react";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { useRoles } from "../../../hooks/useRoles";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
import type { AccessRule, PermissionKey } from "../../../types/permissions";

/**
 * The permission decision hooks (APRAS-48 §4.3).
 *
 * There are **two** permission sets, not one, and each consumer is named:
 *
 * | Set | Hook | While simulating | Consumer |
 * |---|---|---|---|
 * | real | `usePermissionSet` | the real user's payload, unchanged | `useCanAccess` → `ProtectedRoute` |
 * | effective | `useEffectivePermissionSet` | the simulated roles' union | `useCanShowMenu` → `Navbar` |
 *
 * That mapping is one-to-one with what the code did before APRAS-48: what
 * `requiredRoles`/`requiredCapability` did with the real identity,
 * `useCanAccess` does with the real permission set; what `requiredMenu` did
 * with `useEffectiveIdentity`, `useCanShowMenu` does with the effective one.
 * APRAS-35's invariant — an administrator can never be locked out of ending a
 * simulation — is therefore preserved rather than reimplemented.
 */
export interface PermissionSet {
  has(permission: PermissionKey): boolean;
  hasModule(module: string): boolean;
  /** Pending and not errored. An errored query fails closed with no spinner. */
  isLoading: boolean;
  all: ReadonlySet<PermissionKey>;
}

const buildSet = (
  permissions: readonly PermissionKey[],
  isLoading: boolean,
): PermissionSet => {
  const all = new Set(permissions);
  return {
    all,
    isLoading,
    has: (permission) => all.has(permission),
    // The permission-string prefix **is** the module key (§2.2): there is no
    // second vocabulary and no menu-key-to-module mapping table.
    hasModule: (module) => {
      const prefix = `${module}:`;
      for (const permission of all) {
        if (permission.startsWith(prefix)) return true;
      }
      return false;
    },
  };
};

/**
 * The REAL user's permissions. Never simulated — the absence of any
 * `useSimulation`/`useEffectiveIdentity` import on this path *is* the
 * guarantee. Authorization reads this.
 */
export const usePermissionSet = (): PermissionSet => {
  const { data, isPending, isError } = useMyPermissions();
  const permissions = data?.permissions;
  return useMemo(
    () => buildSet(permissions ?? [], isPending && !isError),
    [permissions, isPending, isError],
  );
};

/**
 * The simulated set while simulating, otherwise identical to
 * `usePermissionSet()`. Display reads this.
 *
 * While simulating, the set is the union of the `permissions` arrays of the
 * simulated `roleIds`, read from `useRoles()` (IAM F2 put `permissions` on
 * `RoleRead`). Since IAM F5 there is nothing else it could be: the backend's
 * legacy fallback is gone, so a role's set really is whatever its bundle
 * grants, and the preview is exact rather than approximate.
 */
export const useEffectivePermissionSet = (): PermissionSet => {
  const real = usePermissionSet();
  const { isSimulating, roleIds } = useEffectiveIdentity();
  const { data: roles } = useRoles();
  return useMemo(() => {
    if (!isSimulating) return real;
    const union = (roles ?? [])
      .filter((role) => roleIds.includes(role.id))
      .flatMap((role) => role.permissions ?? []);
    return buildSet(union, real.isLoading);
  }, [isSimulating, roleIds, roles, real]);
};

/**
 * The one evaluator both decision hooks share, so a rule can never be
 * interpreted two ways.
 *
 * IAM F5 (APRAS-49 §4.1) removed the `menuAllowed` conjunct: the
 * menu gate is gone from the 12 backend handlers it guarded, so a
 * rule is now exactly its permission predicate. The one behaviour delta that
 * causes is §4.2's, enumerated there and pinned by
 * `tests/test_menu_gate_removal.py`.
 */
const evaluate = (rule: AccessRule | undefined, set: PermissionSet): boolean => {
  if (!rule) return true;
  return "module" in rule
    ? set.hasModule(rule.module)
    : rule.anyOf.some((permission) => set.has(permission));
};

/** Authorization. Consumed by `ProtectedRoute`. Reads the NON-SIMULATED set. */
export const useCanAccess = (
  rule?: AccessRule,
): { allowed: boolean; isLoading: boolean } => {
  const set = usePermissionSet();
  return { allowed: evaluate(rule, set), isLoading: set.isLoading };
};

/** Display. Consumed by `Navbar`. Reads the effective (simulated) set. */
export const useCanShowMenu = (
  rule?: AccessRule,
): { allowed: boolean; isLoading: boolean } => {
  const set = useEffectivePermissionSet();
  return { allowed: evaluate(rule, set), isLoading: set.isLoading };
};
