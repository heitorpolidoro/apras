import apiClient from "./client";
import type { MyPermissions, PermissionDescriptor } from "../types/permissions";

/**
 * The two `/permissions` reads (APRAS-48 §3).
 *
 * The paths are written **exactly** as FastAPI mounts them — `/permissions/`
 * with the trailing slash (like `/user-types/`) and `/permissions/me`
 * without — because a mismatch costs a 307 redirect that drops the
 * `Authorization` header on some proxies. `TenantContext` already carries the
 * same warning for `/tenants`.
 */

/** The whole static catalogue, sorted, identical for every caller. */
export const fetchPermissionCatalogue = async (): Promise<
  PermissionDescriptor[]
> => {
  const response = await apiClient.get<PermissionDescriptor[]>("/permissions/");
  return response.data;
};

/** My effective permissions in the tenant the interceptor is sending. */
export const fetchMyPermissions = async (): Promise<MyPermissions> => {
  const response = await apiClient.get<MyPermissions>("/permissions/me");
  return response.data;
};
