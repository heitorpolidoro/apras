import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createTenant, listTenants } from "../api/tenants";
import type { Tenant } from "../types/auth";

/**
 * The install-wide condominium list and its one write (APRAS-70).
 *
 * The key is `["tenants"]` — **the same key `TenantContext` already uses**,
 * with the same fetcher — so the screen and the tenant switcher share one
 * cache entry and a create refreshes both. A second key would let the two
 * disagree about which condominiums exist.
 */
export const useTenants = () =>
  useQuery({ queryKey: ["tenants"], queryFn: listTenants });

/**
 * Create a condominium and refresh the shared list.
 *
 * The invalidation is the whole point of reusing `["tenants"]`: the tenant
 * switcher gains the new condominium with no reload. It runs on success only,
 * so a refused create (a 409 duplicate name) leaves the list untouched.
 */
export const useCreateTenant = () => {
  const queryClient = useQueryClient();
  return useMutation<Tenant, unknown, { name: string }>({
    mutationFn: (payload) => createTenant(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
    },
  });
};
