import { UserRole } from "../../../types/auth";
import { useAuth } from "./AuthContext";
import { useTenant } from "./useTenant";
import { useEffectiveIdentity } from "./useEffectiveIdentity";

/**
 * Real-identity admin capability, mirroring the backend's
 * `deps.has_admin_capability`: a global `ADMINISTRATOR` anywhere, or a
 * `tenant_admin` **in the acting tenant only**.
 *
 * Used by `ProtectedRoute`, because route gating must never follow a
 * simulated role (APRAS-35) — an administrator has to be able to end a
 * simulation from any page. `isActingTenantAdmin` comes from `useTenant()`,
 * whose acting tenant is a `useSyncExternalStore` snapshot of the
 * `tenantState` mirror, so the tenant this is judged against is exactly the
 * one the Axios interceptor would put on the wire at that instant.
 */
export const useAdminCapability = (): boolean => {
  const { user } = useAuth();
  const { isActingTenantAdmin } = useTenant();
  return user?.role === UserRole.ADMINISTRATOR || isActingTenantAdmin;
};

/**
 * Simulation-aware admin capability, for menu visibility only.
 *
 * The `!isSimulating` guard keeps today's behaviour exactly: a real
 * administrator simulating `DIRECTOR` sees no admin link.
 */
export const useEffectiveAdminCapability = (): boolean => {
  const { role, isSimulating } = useEffectiveIdentity();
  const { isActingTenantAdmin } = useTenant();
  return (
    role === UserRole.ADMINISTRATOR || (!isSimulating && isActingTenantAdmin)
  );
};
