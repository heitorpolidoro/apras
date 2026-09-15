import apiClient from "./client";

/**
 * The condominium profile surface (APRAS-61).
 *
 * The paths are written **exactly** as FastAPI mounts them —
 * `/tenant-profile` and `/tenant-profile/logo`, neither with a trailing
 * slash — because a mismatch costs a 307 redirect, and a 307 drops
 * `X-Tenant-Id`. None of them carries a `{tenant_id}`: the subject is the
 * acting tenant, which the interceptor in `api/client.ts` attaches.
 *
 * The four constants below are **one half of a two-sided pin**, the shape
 * `src/api/uploads.ts` established: neither side can import the other, so each
 * states the constant and names the other. The backend half is
 * `backend/tests/test_tenant_profile.py::test_the_profile_contract_matches_the_frontend_client`,
 * which reads `TenantService` and `ROUTE_PERMISSIONS` and fails with this
 * file's name in the message.
 */

export interface TenantProfile {
  id: string;
  name: string;
  is_active: boolean;
  logo_url: string | null;
}

/** `TenantService.LOGO_MAX_FILE_SIZE` — 2 MiB, deliberately below the 5 MiB
 *  photo cap: the logo is embedded in every printed document. */
export const TENANT_LOGO_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024;

/**
 * `TenantService.LOGO_ALLOWED_MIME_TYPES`.
 *
 * `image/svg+xml` is **absent on purpose** (D2): an SVG is active content
 * served same-origin from `/static/uploads/` and embedded in a printable
 * report a browser renders, so accepting it without a sanitiser is a
 * stored-XSS surface.
 */
export const TENANT_LOGO_ALLOWED_MIME_TYPES = [
  "image/png",
  "image/jpeg",
  "image/webp",
] as const;

/** The `accept=` of the file input, derived from the set above — never retyped. */
export const TENANT_LOGO_ACCEPT = TENANT_LOGO_ALLOWED_MIME_TYPES.join(",");

/**
 * The permission the three writes demand
 * (`core/permissions.py` ↔ `require_permission` in
 * `endpoints/tenant_profile.py`). It is what `ROUTE_ACCESS` gates the screen
 * on, so the menu and the API agree by construction.
 */
export const TENANT_PROFILE_PERMISSION = "tenants:profile_update";

/** The acting condominium's name, id, active flag and logo. */
export const getTenantProfile = async (): Promise<TenantProfile> => {
  const response = await apiClient.get<TenantProfile>("/tenant-profile");
  return response.data;
};

/** Rename the acting condominium. 409 when another tenant holds the name. */
export const patchTenantProfile = async (
  name: string,
): Promise<TenantProfile> => {
  const response = await apiClient.patch<TenantProfile>("/tenant-profile", {
    name,
  });
  return response.data;
};

/** Replace the logo. The response body *is* the new profile. */
export const putTenantLogo = async (logo: File): Promise<TenantProfile> => {
  const formData = new FormData();
  formData.append("file", logo, logo.name);
  const response = await apiClient.put<TenantProfile>(
    "/tenant-profile/logo",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data;
};

/** Remove the logo. Idempotent: an already-empty profile is still a 200. */
export const deleteTenantLogo = async (): Promise<TenantProfile> => {
  const response = await apiClient.delete<TenantProfile>("/tenant-profile/logo");
  return response.data;
};
