import apiClient from "./client";
import type { DerivedTheme } from "./tenantProfile";

/**
 * The one unauthenticated read in this client (APRAS-74 D3).
 *
 * `GET /api/v1/public/tenants/{slug}/branding` is what lets `/c/<slug>` show
 * a condominium's own name, logo and colours to somebody who has not signed
 * in yet. The path is written exactly as FastAPI mounts it, with no trailing
 * slash: a mismatch costs a 307 that drops headers on some proxies.
 *
 * It goes through the ordinary `apiClient`, interceptor and all. The header
 * the interceptor may attach is inert here — the route is mounted
 * `GLOBAL_SCOPED` on the backend and reads no acting tenant — and routing
 * around the shared client to avoid an inert header would be a second HTTP
 * path to keep in step with the first.
 */

/** Exactly the four keys `PublicTenantBrandingRead` serialises. */
export interface PublicTenantBranding {
  /** Echoed back, so a client that followed a normalisation knows what it
   *  actually resolved. */
  slug: string;
  name: string;
  logo_url: string | null;
  /** What `app/core/branding.build_theme` derived (APRAS-68), or `null` for a
   *  condominium with no colours. Never derived here: this client owns no
   *  colour arithmetic and the type is the backend's, imported not restated. */
  theme: DerivedTheme | null;
}

/**
 * One condominium's public identity.
 *
 * Rejects with the ordinary Axios error on 404 — an unknown *and* an inactive
 * condominium both answer 404, indistinguishably and deliberately. The caller
 * is expected to degrade to the unbranded screen rather than to blank it: an
 * unknown slug must still be able to sign somebody in.
 */
export const fetchPublicBranding = async (
  slug: string,
): Promise<PublicTenantBranding> => {
  const response = await apiClient.get<PublicTenantBranding>(
    `/public/tenants/${encodeURIComponent(slug)}/branding`,
  );
  return response.data;
};

/** The public logo route's path on the API, without the client's `baseURL`. */
export const tenantLogoPath = (slug: string): string =>
  `/public/tenants/${encodeURIComponent(slug)}/logo`;

/**
 * One condominium's logo, as an **absolute** URL (APRAS-105 §D).
 *
 * `logo_url` is storage truth and the "has a logo" flag; it is not a display
 * source. Rendering it verbatim is what `TenantProfilePage` and
 * `BrandedEntryPage` both did, and it silently loads nothing whenever the
 * stored value is relative — the frontend and the backend are served from
 * different hosts, so `/static/uploads/...` resolves against the wrong origin.
 * Since the Blob store is configured with private access, the stored value is
 * not fetchable by a browser at all: the bytes come from the route this helper
 * names, which reads the object with the application's own credential.
 *
 * The base is read off the shared client, exactly as `publicReportUrl` does,
 * so this file does not become a second definition of where the API lives.
 */
export const tenantLogoUrl = (slug: string): string =>
  `${apiClient.defaults.baseURL ?? ""}${tenantLogoPath(slug)}`;
