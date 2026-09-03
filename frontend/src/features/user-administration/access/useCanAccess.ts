import { useMemo } from "react";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { useRoles } from "../../../hooks/useRoles";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
import { useAuth } from "../context/AuthContext";
import { ROUTE_ACCESS } from "./routeAccess";
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
  const { data: myPermissions } = useMyPermissions();
  const disabledModules = myPermissions?.disabled_modules;
  return useMemo(() => {
    if (!isSimulating) return real;
    const union = (roles ?? [])
      .filter((role) => roleIds.includes(role.id))
      .flatMap((role) => role.permissions ?? []);
    // APRAS-39 §10.2: the union comes from the role *rows*, which the
    // backend never strips, so the preview has to intersect with the
    // tenant's active modules itself. Without this, simulating a role in a
    // tenant with `finance` off would preview a menu the real user cannot
    // have. `usePermissionSet` needs no equivalent: its payload is already
    // stripped by the backend.
    const disabled = new Set(disabledModules);
    return buildSet(
      union.filter((permission) => !disabled.has(permission.split(":", 1)[0])),
      real.isLoading,
    );
  }, [isSimulating, roleIds, roles, real, disabledModules]);
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
export const evaluate = (
  rule: AccessRule | undefined,
  set: PermissionSet,
  // APRAS-39 §10.1: passed **in**, never read here. `evaluate` is specified
  // as a pure function, and calling `useAuth()` from it would make it a hook
  // and break every direct unit test. Defaulted so no call site breaks.
  isSuperuser = false,
): boolean => {
  if (!rule) return true;
  if ("superuser" in rule) return isSuperuser;
  return "module" in rule
    ? set.hasModule(rule.module)
    : rule.anyOf.some((permission) => set.has(permission));
};

/**
 * The caller's **real** superuser flag (F5 puts `is_superuser` on
 * `UserMeRead`). Deliberately not simulated in either hook below: "view-as"
 * previews a role, and a role can never carry the global flag, so simulating
 * one must not open — or close — an operator screen.
 */
const useIsSuperuser = (): boolean => useAuth().user?.is_superuser === true;

/** Authorization. Consumed by `ProtectedRoute`. Reads the NON-SIMULATED set. */
export const useCanAccess = (
  rule?: AccessRule,
): { allowed: boolean; isLoading: boolean } => {
  const set = usePermissionSet();
  const isSuperuser = useIsSuperuser();
  return { allowed: evaluate(rule, set, isSuperuser), isLoading: set.isLoading };
};

/** Display. Consumed by `Navbar`. Reads the effective (simulated) set. */
export const useCanShowMenu = (
  rule?: AccessRule,
): { allowed: boolean; isLoading: boolean } => {
  const set = useEffectivePermissionSet();
  const isSuperuser = useIsSuperuser();
  return { allowed: evaluate(rule, set, isSuperuser), isLoading: set.isLoading };
};

/**
 * "Could the caller open this path?", for the two consumers that must agree
 * about it (APRAS-39 §10.4, code review round 1 finding 2).
 *
 * `RootRedirect` uses it to *choose* a landing; `ProtectedRoute` uses it to
 * decide whether the `landingRedirect` bounce may fire. They have to share one
 * evaluation, because the failure mode of two is precisely round 1's bug: the
 * chain rejects `/gate` and picks `/dashboard`, and `/dashboard`'s
 * `landingRedirect` sends the caller straight back to the `/gate` the chain
 * just rejected.
 *
 * A predicate rather than a boolean, so a caller can ask about several paths
 * without calling a hook in a loop. It reads the **real** set — the same one
 * `useCanAccess` authorizes with — so a path it approves is a path
 * `ProtectedRoute` will actually render. A path with no `ROUTE_ACCESS` entry
 * (`/welcome`) has no rule and is therefore open to any authenticated caller,
 * which is what makes it a safe terminal for the chain.
 */
export const useCanOpenPath = (): ((
  path: string | null | undefined,
) => boolean) => {
  const set = usePermissionSet();
  const isSuperuser = useIsSuperuser();
  return (path) =>
    !!path && evaluate(ROUTE_ACCESS[path], set, isSuperuser);
};
