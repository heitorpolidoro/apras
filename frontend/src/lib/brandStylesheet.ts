import type { DerivedTheme } from "../api/tenantProfile";

/**
 * The stylesheet text the tenant's theme becomes (APRAS-68).
 *
 * A module of its own rather than two more exports beside
 * `components/TenantBrandTheme.tsx`: a file that exports both a component and
 * a plain function breaks Fast Refresh (`react-refresh/only-export-components`),
 * and the text is worth testing without mounting anything.
 */

/** The single element the injector owns, by id, so a second mount can never
 *  leave two rule sets behind. */
export const TENANT_BRAND_STYLE_ID = "tenant-brand-theme";

const declarations = (scheme: Readonly<Record<string, string>>): string =>
  Object.entries(scheme)
    .map(([name, value]) => `  --${name}: ${value};`)
    .join("\n");

/**
 * The `:root` and dark rule sets for one derived theme.
 *
 * Two selector decisions, both about **specificity**, not taste:
 *
 * * `:root:root` rather than `:root`. The injected rule and `index.css`'s
 *   `:root` would otherwise have equal specificity and document order would
 *   decide — which is fine at runtime, but Vite's dev HMR can re-inject the
 *   bundled stylesheet *after* an element appended at mount. Doubling the
 *   pseudo-class wins regardless of order.
 * * `:root:root.dark` rather than a bare `.dark`. A bare `.dark` is (0,1,0)
 *   and `:root:root` is (0,2,0), so the light override would beat the dark
 *   one **from inside this very stylesheet** and a dark-mode tenant would
 *   silently get the light palette. Carrying the same doubled `:root` puts
 *   the dark rule at (0,3,0), one step above the light one — the same
 *   relationship `index.css` has between its own `:root` and `.dark`.
 *
 * Only the 17 keys `build_theme` emitted are written, so `--destructive*`,
 * the status and priority tokens and `--radius` are never touched.
 */
export const themeStylesheet = (theme: DerivedTheme): string =>
  [
    `:root:root {\n${declarations(theme.light)}\n}`,
    `:root:root.dark {\n${declarations(theme.dark)}\n}`,
  ].join("\n\n");
