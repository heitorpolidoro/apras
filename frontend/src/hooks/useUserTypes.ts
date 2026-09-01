import { useQuery } from "@tanstack/react-query";
import apiClient from "../api/client";
import { useActingTenantReady } from "../features/user-administration/context/useTenant";
import type { UserType } from "../types/auth";

/**
 * The tenant-scoped `GET /user-types/` list.
 *
 * `enabled` is the one gate that keeps a tenant-scoped request from leaving
 * before the acting tenant is resolved (APRAS-38 §4.10). This hook is the only
 * scoped query in the app that can subscribe *above* an auth guard —
 * `Navbar` and `ProtectedRoute` both call `useMenuAccess` above their
 * `isAuthenticated` / `isLoading` early returns, as the rules of hooks
 * require, and returning `null` from a component does not cancel a query that
 * has already subscribed. Without the gate a multi-membership user's first
 * request is a headerless `/user-types/`, which the backend answers
 * `400 X-Tenant-Id header is required`; the query is then *errored*, not
 * stale, so nothing refetches it after `setUser` and the whole menu
 * disappears. Every other scoped hook mounts inside a `ProtectedRoute` child,
 * i.e. after the spinner clears, so it needs no gate.
 */
export const useUserTypes = () => {
  const isReady = useActingTenantReady();
  return useQuery({
    queryKey: ["user-types"],
    enabled: isReady,
    queryFn: async () => {
      const response = await apiClient.get<UserType[]>("/user-types/");
      return response.data;
    },
  });
};
