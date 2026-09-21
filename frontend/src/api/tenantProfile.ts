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
  /** The condominium's address, the `<slug>` of `/c/<slug>` (APRAS-66). */
  slug: string;
  is_active: boolean;
  logo_url: string | null;
}

/** The writable half of the profile. A field left out is a field left alone —
 *  which is what keeps a rename from ever touching the slug (D-C.2). */
export interface TenantProfileUpdate {
  name?: string;
  slug?: string;
}

/**
 * The slug rule, mirrored from `backend/app/core/slug.py` (APRAS-66 D-C.4).
 *
 * A **mirror**, not a second authority: the server is the enforcer and
 * answers 422 on anything outside this set. These exist so the field can say
 * why it is refusing before a round trip, and so "suggest from name" can fill
 * something the server will accept. Pinned from the backend side by
 * `backend/tests/test_tenant_profile.py::test_the_profile_contract_matches_the_frontend_client`.
 */
export const SLUG_MIN_LENGTH = 3;
export const SLUG_MAX_LENGTH = 64;
export const SLUG_PATTERN = /^[a-z0-9]+(-[a-z0-9]+)*$/;
/** `slugify`'s fallback base whenever a derivation is shorter than the floor. */
export const SLUG_FALLBACK_BASE = "condominio";
/** How much of a derived slug survives, leaving room for a `-<n>` suffix. */
const SLUG_MAX_BASE_LENGTH = 60;

/** Whether the server would store this value as typed. */
export const isValidSlug = (value: string): boolean =>
  value.length >= SLUG_MIN_LENGTH &&
  value.length <= SLUG_MAX_LENGTH &&
  SLUG_PATTERN.test(value);

/**
 * `slugify(name)`, for the "suggest from name" affordance only.
 *
 * It fills the field; the person still submits it. The server never folds a
 * typed value itself — what someone sees accepted must be what is stored.
 */
export const slugifyName = (name: string): string => {
  const ascii = name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\x20-\x7e]/g, "");
  const hyphenated = ascii
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  const truncated = hyphenated
    .slice(0, SLUG_MAX_BASE_LENGTH)
    .replace(/^-+|-+$/g, "");
  return truncated.length < SLUG_MIN_LENGTH ? SLUG_FALLBACK_BASE : truncated;
};

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

/** The acting condominium's name, id, slug, active flag and logo. */
export const getTenantProfile = async (): Promise<TenantProfile> => {
  const response = await apiClient.get<TenantProfile>("/tenant-profile");
  return response.data;
};

/**
 * Rename the acting condominium and/or move its address.
 *
 * 409 when another tenant holds the name **or** the slug — the slug is never
 * suffixed to resolve a typed collision (D-C.3). 422 when the slug is
 * malformed. `slug` is sent **only** when it changed, so a rename can never
 * carry one (D-C.2).
 */
export const patchTenantProfile = async (
  update: TenantProfileUpdate,
): Promise<TenantProfile> => {
  const response = await apiClient.patch<TenantProfile>(
    "/tenant-profile",
    update,
  );
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
