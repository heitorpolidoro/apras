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

/**
 * The 13 colours advanced mode asks for, per scheme (APRAS-68 (b)).
 *
 * Mirrored from `backend/app/core/branding.AUTHORED_KEYS`, in the same order,
 * so the form lists them in the order the server validates them. The other
 * four of the 17 emitted properties — `popover`, `popover-foreground`,
 * `input`, `ring` — are derived *inside* a scheme and never asked for.
 * `--destructive*`, the 10 status tokens, the 8 priority tokens and
 * `--radius` are semantic and are never overridden at all.
 */
export const BRAND_AUTHORED_KEYS = [
  "background",
  "foreground",
  "card",
  "card-foreground",
  "primary",
  "primary-foreground",
  "secondary",
  "secondary-foreground",
  "accent",
  "accent-foreground",
  "muted",
  "muted-foreground",
  "border",
] as const;

export type BrandPaletteKey = (typeof BRAND_AUTHORED_KEYS)[number];

/** Exactly the 13 keys above, each an sRGB `#rrggbb`. */
export type BrandPalette = Record<BrandPaletteKey, string>;

/** Two colours in; the whole palette and the whole `.dark` counterpart are
 *  derived in OKLCH by `app/core/branding.py` and by nothing else. */
export interface SimpleBrandTheme {
  mode: "simple";
  primary: string;
  accent: string;
}

/** The palette authored by hand. `dark: null` — the default the screen
 *  offers — means the dark scheme is the simple-mode derivation of the
 *  authored `primary` and `accent`, because no per-variable inversion of a
 *  hand-authored light palette preserves either intent or contrast. */
export interface AdvancedBrandTheme {
  mode: "advanced";
  light: BrandPalette;
  dark: BrandPalette | null;
}

export type BrandTheme = SimpleBrandTheme | AdvancedBrandTheme;

/** One emitted scheme: CSS custom-property names without the leading `--`,
 *  mapped to `oklch(L C H)` strings at 2dp. */
export type ThemeScheme = Record<string, string>;

/** What `build_theme` returns — derived on read, never stored. */
export interface DerivedTheme {
  light: ThemeScheme;
  dark: ThemeScheme;
}

/** One pair the API refused, as `InsufficientContrastError` reports it. */
export interface BrandContrastFailure {
  pair: string;
  ratio: number;
  minimum: number;
  scheme: string;
}

export interface TenantProfile {
  id: string;
  name: string;
  /** The condominium's address, the `<slug>` of `/c/<slug>` (APRAS-66). */
  slug: string;
  is_active: boolean;
  logo_url: string | null;
  /** What the condominium chose, normalised to lowercase by the server;
   *  `null` means no branding, and then the app renders today's `index.css`
   *  byte for byte (APRAS-68 (e)). */
  brand_theme: BrandTheme | null;
  /** What `app/core/branding.build_theme` derived from it. `null` whenever
   *  `brand_theme` is, and then `TenantBrandTheme` injects no element at all. */
  theme: DerivedTheme | null;
}

/** The writable half of the profile. A field left out is a field left alone —
 *  which is what keeps a rename from ever touching the slug (D-C.2), and what
 *  keeps a rename from touching the colours. An explicit `null` on
 *  `brand_theme` is the "voltar ao padrão" action. */
export interface TenantProfileUpdate {
  name?: string;
  slug?: string;
  brand_theme?: BrandTheme | null;
}

/**
 * The hex rule, mirrored from `backend/app/core/branding.HEX_COLOR_PATTERN`.
 *
 * **Case-insensitive and it never lowercases.** Brand guides conventionally
 * write hex uppercase, so `#FFE680` is accepted; the server is the single
 * normalisation point and is what stores `#ffe680`. This pre-validates only,
 * so a field can say why it is refusing before a round trip.
 */
export const HEX_COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/;

/** Whether the server would accept this value as a colour. */
export const isValidHexColor = (value: string): boolean =>
  HEX_COLOR_PATTERN.test(value);

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
