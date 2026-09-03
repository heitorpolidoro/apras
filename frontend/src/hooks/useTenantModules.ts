import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getTenantModules,
  listTenants,
  putTenantModules,
} from "../api/tenants";

/**
 * The per-tenant module switch, from the operator's side (APRAS-39 §10.3).
 *
 * Every key here starts with `"tenants"`, which is deliberate:
 * `TenantContext.setActingTenant`'s eviction sweep keeps exactly those
 * (`query.queryKey[0] !== "tenants"`). This data is keyed by an **explicit**
 * tenant id and does not depend on the acting tenant, so switching tenants
 * must not throw it away.
 */

/** Every tenant, for the screen's `<select>`. */
export const useAllTenants = () =>
  useQuery({ queryKey: ["tenants"], queryFn: listTenants });

/** One tenant's module states. Idle until a tenant is chosen. */
export const useTenantModules = (tenantId: string | null) =>
  useQuery({
    queryKey: ["tenants", tenantId, "modules"],
    enabled: !!tenantId,
    queryFn: () => getTenantModules(tenantId as string),
  });

/**
 * Save the complete desired state.
 *
 * Invalidates the tenant's own key **and** `["me","permissions"]`: the
 * operator may be a member of the tenant they just changed, and
 * `/permissions/me` carries both the stripped set and `disabled_modules`.
 */
export const useSetTenantModules = (tenantId: string | null) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (disabledModules: string[]) =>
      putTenantModules(tenantId as string, disabledModules),
    onSuccess: (data) => {
      // The response body *is* the new state, so it is written straight in
      // rather than refetched; no optimistic update to roll back.
      queryClient.setQueryData(["tenants", tenantId, "modules"], data);
      void queryClient.invalidateQueries({ queryKey: ["me", "permissions"] });
    },
  });
};
