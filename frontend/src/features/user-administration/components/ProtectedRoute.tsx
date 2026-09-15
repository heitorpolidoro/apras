import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { useCanAccess } from "../access/useCanAccess";
import { Spinner } from "../../../components/ui/spinner";
import type { AccessRule } from "../../../types/permissions";

interface ProtectedRouteProps {
  children: React.ReactElement;
  /** The route's rule, taken from `ROUTE_ACCESS` (APRAS-48 §5.2). */
  requiredAccess?: AccessRule;
}

/**
 * The module a rule is *about*, or null.
 *
 * `{ module }` states it; `{ anyOf }` carries it in the prefix of its first
 * permission, which is the same `<module>:<action>` convention the whole
 * catalogue uses (there is no second vocabulary). `{ superuser: true }` names
 * no module by construction.
 */
const moduleOfRule = (rule?: AccessRule): string | null => {
  if (!rule) return null;
  if ("module" in rule) return rule.module;
  if ("anyOf" in rule) return rule.anyOf[0]?.split(":", 1)[0] ?? null;
  return null;
};

/**
 * The denial copy. **Presentational only** (APRAS-39 §10.4): the refusal
 * itself is produced by the backend strip — a disabled module's permissions
 * are simply absent from `/permissions/me` — so this branch changes two
 * strings and nothing else. Same component, same zero network calls.
 */
const RestrictedAccessMessage: React.FC<{ moduleDisabled?: boolean }> = ({
  moduleDisabled = false,
}) => {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center gap-2 min-h-[50vh] p-8 text-center">
      <p className="text-lg font-semibold text-foreground">
        {t(moduleDisabled ? "common.moduleUnavailable" : "common.restrictedAccess")}
      </p>
      <p className="text-sm text-muted-foreground max-w-md">
        {t(
          moduleDisabled
            ? "common.moduleUnavailableMessage"
            : "common.restrictedAccessMessage",
        )}
      </p>
    </div>
  );
};

/**
 * Authorization is decided by `useCanAccess`, i.e. on the **real**
 * (non-simulated) permission set: an administrator must always be able to
 * reach the control that ends a simulation (APRAS-35, restated in §2.7).
 * `Navbar` is the mirror image and uses `useCanShowMenu`.
 *
 * Denial is **in place**, never a redirect. Bouncing a denied user to
 * `/dashboard` — what `requiredRoles` did before this slice — is a real
 * redirect-loop hazard the moment `/dashboard` denies them too, and it made
 * two routes' denials assertable by two different queries. Now every route's
 * denial is `getByText("Acesso restrito")`.
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredAccess,
}) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const { allowed, isLoading: isAccessLoading } = useCanAccess(requiredAccess);
  // Read for `disabled_modules` alone: it decides which of the two denial
  // copies the restricted message shows. Nothing on this payload gates.
  const { data: myPermissions } = useMyPermissions();

  if (isLoading) return <Spinner />;

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Without this the page would flash "Acesso restrito" on every cold load,
  // which is exactly the regression `TenantBootstrapOrder.test.tsx` catches.
  if (isAccessLoading) return <Spinner />;

  if (!allowed) {
    const module = moduleOfRule(requiredAccess);
    // Optional-chained on both hops on purpose. `MyPermissions` now *types*
    // `disabled_modules` as required, but this is a denial path: a payload
    // without it (a frontend deployed ahead of its backend) must degrade to
    // "no module disabled" and render the generic copy, never throw and blank
    // the page. The type expresses the contract; this expresses what happens
    // when the contract is broken.
    const moduleDisabled =
      module !== null &&
      (myPermissions?.disabled_modules?.includes(module) ?? false);
    return <RestrictedAccessMessage moduleDisabled={moduleDisabled} />;
  }

  return children;
};

export default ProtectedRoute;
