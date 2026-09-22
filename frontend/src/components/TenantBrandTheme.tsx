import { useEffect } from "react";
import { useAuth } from "../features/user-administration/context/AuthContext";
import { useTenantProfile } from "../hooks/useTenantProfile";
import { TENANT_BRAND_STYLE_ID, themeStylesheet } from "../lib/brandStylesheet";

/**
 * The condominium's colours, applied to the running app (APRAS-68).
 *
 * It renders nothing. Its whole job is one `<style>` element appended to
 * `document.head` after the bundled stylesheet, overriding the CSS custom
 * properties `src/index.css` already declares. No screen is revised
 * individually, and the mechanism reaches exactly the components that consume
 * the semantic tokens — which is a minority of this UI today, because 108
 * files hard-code Tailwind palette classes no custom property can reach.
 * Migrating those is APRAS-77, deliberately not this task.
 *
 * **A tenant with no branding gets no element at all** (D-F), not an empty
 * one: `theme` is `null`, nothing is injected, and the app renders today's
 * `index.css` byte for byte.
 *
 * Because `["tenantProfile"]` is reset on a tenant switch (it deliberately
 * does not key under `"tenants"`), switching condominium re-themes with no
 * extra wiring.
 *
 * The id and the stylesheet text live in `lib/brandStylesheet.ts`: a module
 * that exports both a component and a plain function breaks Fast Refresh.
 */
const TenantBrandTheme = () => {
  const { isAuthenticated } = useAuth();
  // `enabled` keeps this off the login screen, where there is no token and
  // the `GET` could only 401.
  const { data } = useTenantProfile({ enabled: isAuthenticated });
  const theme = data?.theme ?? null;

  useEffect(() => {
    if (theme === null) {
      document.getElementById(TENANT_BRAND_STYLE_ID)?.remove();
      return;
    }

    const element =
      document.getElementById(TENANT_BRAND_STYLE_ID) ??
      document.createElement("style");
    element.id = TENANT_BRAND_STYLE_ID;
    element.textContent = themeStylesheet(theme);
    // `appendChild` on an element already in the head *moves* it, which is
    // what keeps it the last child after an HMR re-injection.
    document.head.appendChild(element);

    return () => {
      document.getElementById(TENANT_BRAND_STYLE_ID)?.remove();
    };
  }, [theme]);

  return null;
};

export default TenantBrandTheme;
