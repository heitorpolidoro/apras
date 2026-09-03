import apiClient from "./client";
import type { Subscription, SubscriptionChange } from "../types/subscription";

/**
 * The tenant-side subscription area (APRAS-40 §5.1).
 *
 * The paths are written **exactly** as FastAPI mounts them — `/subscription`,
 * `/subscription/modules` and `/subscription/history`, none with a trailing
 * slash — because a mismatch costs a 307 redirect, and a 307 drops
 * `X-Tenant-Id`. These three routes have no `{tenant_id}`: the subject is the
 * acting tenant, which the interceptor in `api/client.ts` attaches.
 */

/** The acting tenant's plan, entitlements and inert estimate. */
export const getSubscription = async (): Promise<Subscription> => {
  const response = await apiClient.get<Subscription>("/subscription");
  return response.data;
};

/**
 * Contract or cancel modules within the plan.
 *
 * The body is the **contracted set** — the plan-covered checkboxes and
 * nothing else. Courtesy and override activations are never sent and are
 * never dropped: the server's merge preserves what the tenant does not
 * govern.
 */
export const putSubscriptionModules = async (
  activeModules: string[],
): Promise<Subscription> => {
  const response = await apiClient.put<Subscription>("/subscription/modules", {
    active_modules: activeModules,
  });
  return response.data;
};

/** The acting tenant's change history, newest first. */
export const getSubscriptionHistory = async (): Promise<
  SubscriptionChange[]
> => {
  const response = await apiClient.get<SubscriptionChange[]>(
    "/subscription/history",
  );
  return response.data;
};
