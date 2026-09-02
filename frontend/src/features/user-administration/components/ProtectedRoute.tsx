import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth, UserRole } from "../context/AuthContext";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
import { useCanAccess } from "../access/useCanAccess";
import type { AccessRule } from "../../../types/permissions";

interface ProtectedRouteProps {
  children: React.ReactElement;
  /** The route's rule, taken from `ROUTE_ACCESS` (APRAS-48 §5.2). */
  requiredAccess?: AccessRule;
}

const RestrictedAccessMessage: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center gap-2 min-h-[50vh] p-8 text-center">
      <p className="text-lg font-semibold text-foreground">
        {t("common.restrictedAccess")}
      </p>
      <p className="text-sm text-muted-foreground max-w-md">
        {t("common.restrictedAccessMessage")}
      </p>
    </div>
  );
};

const Spinner: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

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
  // TRANSITIONAL (IAM F4 -> F5): the GUEST/PORTEIRO landing redirects are not
  // authorization — a PORTEIRO genuinely holds `tasks:read` — so they keep
  // reading the effective role, on exactly the two routes that carry
  // `landingRedirect` (§2.4).
  const { role: effectiveRole } = useEffectiveIdentity();

  if (isLoading) return <Spinner />;

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredAccess?.landingRedirect && effectiveRole === UserRole.GUEST) {
    return <Navigate to="/welcome" replace />;
  }

  if (requiredAccess?.landingRedirect && effectiveRole === UserRole.PORTEIRO) {
    return <Navigate to="/gate" replace />;
  }

  // Without this the page would flash "Acesso restrito" on every cold load,
  // which is exactly the regression `TenantBootstrapOrder.test.tsx` catches.
  if (isAccessLoading) return <Spinner />;

  if (!allowed) return <RestrictedAccessMessage />;

  return children;
};

export default ProtectedRoute;
