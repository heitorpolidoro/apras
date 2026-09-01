import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth, UserRole } from "../context/AuthContext";
import { useEffectiveIdentity } from "../context/useEffectiveIdentity";
import { useMenuAccess, type MenuKey } from "../context/useMenuAccess";
import { useAdminCapability } from "../context/useAdminCapability";

interface ProtectedRouteProps {
  children: React.ReactElement;
  requiredRole?: UserRole;
  requiredRoles?: UserRole[];
  requiredMenu?: MenuKey;
  /** Gate on the APRAS-43 admin *capability* rather than on a role: a global
   *  ADMINISTRATOR anywhere, or a tenant_admin in the acting tenant. When it
   *  is combined with `requiredRoles` the two are OR'd, never AND'd. */
  requiredCapability?: "admin";
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

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredRoles,
  requiredMenu,
  requiredCapability,
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();
  // Always called (rules of hooks): when requiredMenu is undefined,
  // useMenuAccess is effectively a no-op below.
  const hasMenuAccess = useMenuAccess(requiredMenu ?? "tasks");
  // Real identity, never the simulated one: an administrator must always be
  // able to reach the control that ends a simulation (APRAS-35).
  const hasAdminCapability = useAdminCapability();
  const { role: effectiveRole } = useEffectiveIdentity();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to="/dashboard" replace />;
  }

  // The capability check is deliberately an OR with `requiredRoles`, so the
  // `requiredRoles`-only branch is skipped whenever `requiredCapability` is
  // also present — otherwise the two would AND together and a tenant_admin
  // who is not a MANAGER would be turned away from a route they may use.
  if (requiredCapability) {
    const allowedByRole = Boolean(
      requiredRoles && user && requiredRoles.includes(user.role),
    );
    if (!hasAdminCapability && !allowedByRole) {
      return <Navigate to="/dashboard" replace />;
    }
  } else if (requiredRoles && (!user || !requiredRoles.includes(user.role))) {
    return <Navigate to="/dashboard" replace />;
  }

  if (requiredMenu && effectiveRole === UserRole.GUEST) {
    return <Navigate to="/welcome" replace />;
  }

  if (requiredMenu && effectiveRole === UserRole.PORTEIRO) {
    return <Navigate to="/gate" replace />;
  }

  if (requiredMenu && !hasMenuAccess) {
    return <RestrictedAccessMessage />;
  }

  return children;
};

export default ProtectedRoute;
