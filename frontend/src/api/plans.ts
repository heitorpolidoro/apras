import apiClient from "./client";
import type {
  CourtesyPayload,
  Plan,
  PlanPayload,
  Subscription,
  TenantSubscriptionPayload,
} from "../types/subscription";

/**
 * The superuser surfaces: the install-wide plan catalogue and the per-tenant
 * subscription (APRAS-40 §5.2, §5.3).
 *
 * `/plans/` carries a trailing slash and `/tenants/{id}/subscription` does
 * not, because that is exactly how FastAPI mounts them — a mismatch is a 307
 * and a 307 drops headers.
 *
 * There is **no `deletePlan`**: `tenant_subscription.plan_id` is
 * `ON DELETE RESTRICT` and a plan a tenant is on must not vanish.
 * Deactivation (`updatePlan(id, { is_active: false })`) is the operation.
 */

export const listPlans = async (): Promise<Plan[]> => {
  const response = await apiClient.get<Plan[]>("/plans/");
  return response.data;
};

export const createPlan = async (payload: PlanPayload): Promise<Plan> => {
  const response = await apiClient.post<Plan>("/plans/", payload);
  return response.data;
};

export const updatePlan = async (
  planId: string,
  payload: PlanPayload,
): Promise<Plan> => {
  const response = await apiClient.patch<Plan>(`/plans/${planId}`, payload);
  return response.data;
};

/** One tenant's commercial state, named by path. Superuser only. */
export const getTenantSubscription = async (
  tenantId: string,
): Promise<Subscription> => {
  const response = await apiClient.get<Subscription>(
    `/tenants/${tenantId}/subscription`,
  );
  return response.data;
};

/**
 * Assign or change the tenant's plan. Applies the ceiling shrink-only:
 * modules leaving the entitlement are deactivated, modules newly entering it
 * are not auto-activated — contracting them is the tenant's explicit act.
 */
export const putTenantSubscription = async (
  tenantId: string,
  payload: TenantSubscriptionPayload,
): Promise<Subscription> => {
  const response = await apiClient.put<Subscription>(
    `/tenants/${tenantId}/subscription`,
    payload,
  );
  return response.data;
};

/**
 * Grant or revoke modules outside the plan, and activate them in one call.
 * Courtesy is free: it never enters `estimated_monthly_total`.
 */
export const putTenantCourtesy = async (
  tenantId: string,
  payload: CourtesyPayload,
): Promise<Subscription> => {
  const response = await apiClient.put<Subscription>(
    `/tenants/${tenantId}/subscription/courtesy`,
    payload,
  );
  return response.data;
};
