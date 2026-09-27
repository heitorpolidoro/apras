import apiClient from "./client";

/**
 * The public obras report (APRAS-92, D1/D2/D3).
 *
 * `GET /api/v1/public/tenants/{slug}/projects/report` is the second
 * unauthenticated read in this client, beside `publicBranding.ts`, and the
 * first that answers with a whole rendered document rather than JSON. It is
 * what `/c/<slug>/obras` shows a resident who was handed a link and is not
 * signed in.
 *
 * Documented the same way as `publicBranding.ts`, and for the same reasons:
 * the path is written exactly as FastAPI mounts it, with no trailing slash (a
 * mismatch costs a 307 that drops headers on some proxies), and it goes through
 * the ordinary `apiClient` interceptor and all — the header the interceptor may
 * attach is inert, because the route is mounted `GLOBAL_SCOPED` on the backend
 * and reads no acting tenant. Routing around the shared client to avoid an
 * inert header would be a second HTTP path to keep in step with the first.
 *
 * Nothing here caches: the backend sets no `Cache-Control` and no `ETag` by
 * decision (D3), so the document is fetched fresh and is never held.
 */

/** The report's path on the API, without the client's `baseURL`. */
export const publicReportPath = (slug: string): string =>
  `/public/tenants/${encodeURIComponent(slug)}/projects/report`;

/**
 * The same document as an **absolute** URL, for a plain `<a target="_blank">`.
 *
 * Because the route is unauthenticated, a direct link genuinely works, and the
 * report's own print CSS then applies to a real top-level document — which is
 * precisely the constraint that forced `ConstructionTrackerPage` into its
 * object-URL workaround for the authenticated report and that does not apply
 * here. The base is read off the shared client rather than from
 * `import.meta.env`, so this file does not become a second definition of where
 * the API lives.
 */
export const publicReportUrl = (slug: string): string =>
  `${apiClient.defaults.baseURL ?? ""}${publicReportPath(slug)}`;

/**
 * The rendered report, as text.
 *
 * `responseType: "text"` because the body is HTML and Axios would otherwise
 * try to parse it. Rejects with the ordinary Axios error on 404 — an unknown
 * *and* an inactive condominium both answer 404, indistinguishably and
 * deliberately. The caller renders a short "unavailable" panel, never a blank
 * screen and never a redirect to `/login`.
 */
export const fetchPublicProjectsReport = async (
  slug: string,
): Promise<string> => {
  const response = await apiClient.get<string>(publicReportPath(slug), {
    responseType: "text",
    transformResponse: [(data: string) => data],
  });
  return response.data;
};
