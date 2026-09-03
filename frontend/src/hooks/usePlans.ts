import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createPlan,
  getTenantSubscription,
  listPlans,
  putTenantCourtesy,
  putTenantSubscription,
  updatePlan,
} from "../api/plans";
import type {
  CourtesyPayload,
  PlanPayload,
  TenantSubscriptionPayload,
} from "../types/subscription";

/**
 * The superuser surfaces (APRAS-40 §8.2).
 *
 * `["tenants", id, "subscription"]` starts with `"tenants"`, so
 * `setActingTenant`'s eviction sweep (`queryKey[0] !== "tenants"`) **preserves**
 * it — correct, it is keyed by an explicit tenant id and does not depend on
 * the acting tenant. `["plans"]` is install-wide and would be reset on a
 * tenant switch, which is harmless (it is refetched) and is the safe default.
 */

/** The whole catalogue, including inactive plans. */
export const usePlans = () =>
  useQuery({ queryKey: ["plans"], queryFn: listPlans });

export const useCreatePlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PlanPayload) => createPlan(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
  });
};

export const useUpdatePlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, payload }: { planId: string; payload: PlanPayload }) =>
      updatePlan(planId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
  });
};

/** One tenant's subscription. Idle until a tenant is chosen. */
export const useTenantSubscription = (tenantId: string | null) =>
  useQuery({
    queryKey: ["tenants", tenantId, "subscription"],
    enabled: !!tenantId,
    queryFn: () => getTenantSubscription(tenantId as string),
  });

/**
 * Assign or change a tenant's plan.
 *
 * Invalidates `["me","permissions"]`: this changes `tenant.disabled_modules`,
 * and the operator may be a member of the tenant they just changed.
 */
export const useSetTenantPlan = (tenantId: string | null) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TenantSubscriptionPayload) =>
      putTenantSubscription(tenantId as string, payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["tenants", tenantId, "subscription"], data);
      void queryClient.invalidateQueries({
        queryKey: ["tenants", tenantId, "modules"],
      });
      void queryClient.invalidateQueries({ queryKey: ["me", "permissions"] });
    },
  });
};

/** Grant or revoke courtesy modules. Same invalidation, same reason. */
export const useSetTenantCourtesy = (tenantId: string | null) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CourtesyPayload) =>
      putTenantCourtesy(tenantId as string, payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["tenants", tenantId, "subscription"], data);
      void queryClient.invalidateQueries({
        queryKey: ["tenants", tenantId, "modules"],
      });
      void queryClient.invalidateQueries({ queryKey: ["me", "permissions"] });
    },
  });
};
