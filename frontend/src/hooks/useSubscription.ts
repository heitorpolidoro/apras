import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getSubscription,
  getSubscriptionHistory,
  putSubscriptionModules,
} from "../api/subscription";

/**
 * The tenant-side subscription area (APRAS-40 §8.2).
 *
 * **Cache-key discipline, and why it matters here.** `["subscription"]` starts
 * with `"subscription"`, so `setActingTenant`'s `resetQueries` predicate
 * (`queryKey[0] !== "tenants"`, APRAS-38/39) **resets** it on a tenant
 * switch — correct, it is acting-tenant data, read through `X-Tenant-Id` with
 * no tenant id anywhere in the path. The superuser hooks in `usePlans.ts` key
 * on `["tenants", id, ...]` for the opposite reason.
 */

/** The acting tenant's subscription. */
export const useSubscription = () =>
  useQuery({ queryKey: ["subscription"], queryFn: getSubscription });

/** The acting tenant's change history, newest first. */
export const useSubscriptionHistory = () =>
  useQuery({
    queryKey: ["subscription", "history"],
    queryFn: getSubscriptionHistory,
  });

/**
 * Contract or cancel modules within the plan.
 *
 * Invalidates `["me","permissions"]` as well as its own keys: this mutation
 * changes `tenant.disabled_modules`, and without the invalidation the navbar
 * would keep showing a menu the API has just started refusing.
 */
export const useSetSubscriptionModules = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (activeModules: string[]) =>
      putSubscriptionModules(activeModules),
    onSuccess: (data) => {
      // The response body *is* the new state, so it is written straight in
      // rather than refetched; no optimistic update to roll back.
      queryClient.setQueryData(["subscription"], data);
      void queryClient.invalidateQueries({ queryKey: ["subscription", "history"] });
      void queryClient.invalidateQueries({ queryKey: ["me", "permissions"] });
    },
  });
};
