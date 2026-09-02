import { useMemo } from "react";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
import { useMenuAccess } from "../context/useMenuAccess";
import type { AccessRule, PermissionKey } from "../../../types/permissions";

/**
 * The permission decision hooks (APRAS-48 §4.3).
 *
 * There are **two** permission sets, not one, and each consumer is named:
 *
 * | Set | Hook | While simulating | Consumer |
 * |---|---|---|---|
 * | real | `usePermissionSet` | the real user's payload, unchanged | `useCanAccess` → `ProtectedRoute` |
 * | effective | `useEffectivePermissionSet` | the simulated groups' union | `useCanShowMenu` → `Navbar` |
 *
 * That mapping is one-to-one with what the code did before this slice: what
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
 * simulated `userTypeIds`, read from `useUserTypes()` (IAM F2 put
 * `permissions` on `UserTypeRead`). `LEGACY_ROLE_PERMISSIONS` is deliberately
 * *not* simulatable: it lives only in the backend, so a simulated role's set
 * is whatever that role's **groups** grant — which is exactly the preview an
 * operator wants of the new model.
 */
export const useEffectivePermissionSet = (): PermissionSet => {
  const real = usePermissionSet();
  const { isSimulating, userTypeIds } = useEffectiveIdentity();
  const { data: userTypes } = useUserTypes();
  return useMemo(() => {
    if (!isSimulating) return real;
    const union = (userTypes ?? [])
      .filter((userType) => userTypeIds.includes(userType.id))
      .flatMap((userType) => userType.permissions ?? []);
    return buildSet(union, real.isLoading);
  }, [isSimulating, userTypeIds, userTypes, real]);
};

/**
 * The one evaluator both decision hooks share, so a rule can never be
 * interpreted two ways. `menuAllowed` is only consulted for the two entries
 * that carry `legacyMenu` (§2.3).
 */
const evaluate = (
  rule: AccessRule | undefined,
  set: PermissionSet,
  menuAllowed: boolean,
): boolean => {
  if (!rule) return true;
  const base =
    "module" in rule
      ? set.hasModule(rule.module)
      : rule.anyOf.some((permission) => set.has(permission));
  if ("legacyMenu" in rule && rule.legacyMenu) return base && menuAllowed;
  return base;
};

const legacyMenuOf = (rule?: AccessRule) =>
  rule && "legacyMenu" in rule ? rule.legacyMenu : undefined;

/** Authorization. Consumed by `ProtectedRoute`. Reads the NON-SIMULATED set. */
export const useCanAccess = (
  rule?: AccessRule,
): { allowed: boolean; isLoading: boolean } => {
  const set = usePermissionSet();
  // Always called (rules of hooks), exactly as `ProtectedRoute` called it
  // before this slice: with no `legacyMenu` the result is discarded by
  // `evaluate`. TRANSITIONAL (IAM F4 -> F5), and simulation-aware in both
  // hooks by design — that is APRAS-35's documented `requiredMenu`
  // exception, carried over untouched.
  const menuAllowed = useMenuAccess(legacyMenuOf(rule) ?? "tasks");
  return {
    allowed: evaluate(rule, set, menuAllowed),
    isLoading: set.isLoading,
  };
};

/** Display. Consumed by `Navbar`. Reads the effective (simulated) set. */
export const useCanShowMenu = (
  rule?: AccessRule,
): { allowed: boolean; isLoading: boolean } => {
  const set = useEffectivePermissionSet();
  const menuAllowed = useMenuAccess(legacyMenuOf(rule) ?? "tasks");
  return {
    allowed: evaluate(rule, set, menuAllowed),
    isLoading: set.isLoading,
  };
};
