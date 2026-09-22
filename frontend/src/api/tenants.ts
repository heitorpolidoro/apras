import apiClient from "./client";
import type { Tenant } from "../types/auth";
import type { TenantModules } from "../types/permissions";

/**
 * The tenant reads and the per-tenant module switch (APRAS-39 §10.3).
 *
 * The paths are written **exactly** as FastAPI mounts them — `/tenants` and
 * `/tenants/{id}/modules`, neither with a trailing slash — because a mismatch
 * costs a 307 redirect that drops the `Authorization` header on some proxies.
 * `api/client.ts` and `TenantContext` already carry the same warning.
 */

/** Every tenant. `GET /tenants` returns all of them to a superuser. */
export const listTenants = async (): Promise<Tenant[]> => {
  const response = await apiClient.get<Tenant[]>("/tenants");
  return response.data;
};

/**
 * Create one condominium. Superuser only (APRAS-70).
 *
 * The body is `{ name }` and nothing else: `TenantCreate` has no `slug`
 * field — `app/core/slug.py` plus `TenantService.generated_slug` are the
 * single derivation authority, including the `-2` collision suffix — and
 * `is_active` is omitted so the backend's `true` default applies. The
 * authoritative slug is read from the `201` body.
 */
export const createTenant = async (payload: {
  name: string;
}): Promise<Tenant> => {
  const response = await apiClient.post<Tenant>("/tenants", payload);
  return response.data;
};

/** Every module and its state in one tenant. Superuser only. */
export const getTenantModules = async (
  tenantId: string,
): Promise<TenantModules> => {
  const response = await apiClient.get<TenantModules>(
    `/tenants/${tenantId}/modules`,
  );
  return response.data;
};

/**
 * Replace the tenant's disabled-module set. Superuser only.
 *
 * `PUT` of the *complete* desired state, so the call is idempotent and the
 * response body is the new state — which is why the caller re-renders from
 * the answer instead of updating optimistically.
 */
export const putTenantModules = async (
  tenantId: string,
  disabledModules: string[],
): Promise<TenantModules> => {
  const response = await apiClient.put<TenantModules>(
    `/tenants/${tenantId}/modules`,
    { disabled_modules: disabledModules },
  );
  return response.data;
};
