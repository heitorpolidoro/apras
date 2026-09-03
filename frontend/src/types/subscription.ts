/**
 * The subscription area (APRAS-40 §8.1), mirroring `app/schemas/*.py` field
 * for field.
 *
 * **Every price field is inert.** `base_price`, `module_prices`,
 * `monthly_price`, `estimated_monthly_total` and `currency` are stored,
 * returned and summed for display only: no payment provider exists for this
 * project, so nothing here charges anything.
 */

/** Why a module is active, in §4.7's priority order. */
export type SubscriptionSource =
  | "CORE"
  | "UNMANAGED"
  | "PLAN"
  | "COURTESY"
  | "OVERRIDE";

/** What produced one history row (§3.4). */
export type SubscriptionChangeKind =
  | "CONTRACTED"
  | "PLAN_CHANGE"
  | "COURTESY_GRANT"
  | "COURTESY_REVOKE"
  | "OVERRIDE";

export type SubscriptionStatus = "ACTIVE" | "SUSPENDED" | "CANCELED";

/** One plan in the install-wide, superuser-managed catalogue. */
export interface Plan {
  id: string;
  name: string;
  description: string | null;
  included_modules: string[];
  base_price: number;
  module_prices: Record<string, number>;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** One catalogue module, seen from the subscription area. */
export interface ModuleEntitlement {
  module: string;
  is_core: boolean;
  /** From `tenant.disabled_modules` — APRAS-39's truth. */
  is_active: boolean;
  in_plan: boolean;
  courtesy: boolean;
  /** Exactly "the contracting PUT would accept this module", never looser:
   *  it is false for every module of a tenant with no subscription, whose
   *  PUT is a 404. */
  can_contract: boolean;
  monthly_price: number | null;
  source: SubscriptionSource | null;
}

export interface Subscription {
  tenant_id: string;
  plan: Plan | null;
  status: SubscriptionStatus | null;
  started_at: string | null;
  notes: string | null;
  /** One per catalogue module, sorted by `module`. */
  modules: ModuleEntitlement[];
  estimated_monthly_total: number | null;
  currency: string | null;
}

export interface SubscriptionChange {
  id: string;
  kind: SubscriptionChangeKind;
  modules_added: string[];
  modules_removed: string[];
  from_plan_name: string | null;
  to_plan_name: string | null;
  reason: string | null;
  changed_by_id: string;
  changed_by_name: string | null;
  changed_at: string;
}

/** `POST /plans/` and, with every field optional, `PATCH /plans/{id}`. */
export interface PlanPayload {
  name?: string;
  description?: string | null;
  included_modules?: string[];
  base_price?: number;
  module_prices?: Record<string, number>;
  currency?: string;
  is_active?: boolean;
}

export interface TenantSubscriptionPayload {
  plan_id: string;
  status?: SubscriptionStatus;
  notes?: string | null;
}

export interface CourtesyPayload {
  courtesy_modules: string[];
  reason?: string | null;
}
