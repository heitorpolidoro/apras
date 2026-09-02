import { useQuery } from "@tanstack/react-query";
import {
  fetchMyPermissions,
  fetchPermissionCatalogue,
} from "../api/permissions";
import { useActingTenantReady } from "../features/user-administration/context/useTenant";

/**
 * The two TanStack queries behind the permission model (APRAS-48 §4.2).
 *
 * Named `usePermissionQueries.ts` and **not** `usePermissions.ts` so it can
 * never be confused with the decision hooks in
 * `features/user-administration/access/useCanAccess.ts`: two modules with the
 * same basename would make every `vi.mock("…/usePermissions")` ambiguous by
 * sight.
 *
 * `enabled` mirrors `useUserTypes` for the reason that hook's docstring
 * already gives: `Navbar` and `ProtectedRoute` both subscribe **above** their
 * own auth guards, as the rules of hooks require, and a headerless scoped
 * request is answered `400 X-Tenant-Id header is required` — an *errored*
 * query, which nothing refetches after `setUser`.
 *
 * Neither key starts with `"tenants"`, so `TenantContext.setActingTenant`'s
 * `resetQueries`/`removeQueries` sweep evicts both on a tenant switch and the
 * menus re-evaluate with no page reload (ER-3).
 */

/** My effective permissions in the acting tenant. */
export const useMyPermissions = () => {
  const isReady = useActingTenantReady();
  return useQuery({
    queryKey: ["me", "permissions"],
    enabled: isReady,
    queryFn: fetchMyPermissions,
  });
};

/**
 * The static catalogue. Fetched only where it is needed (the group editor),
 * so an ordinary user's page load gains exactly one request, not two.
 */
export const usePermissionCatalogue = () => {
  const isReady = useActingTenantReady();
  return useQuery({
    queryKey: ["permissions", "catalogue"],
    enabled: isReady,
    queryFn: fetchPermissionCatalogue,
  });
};
