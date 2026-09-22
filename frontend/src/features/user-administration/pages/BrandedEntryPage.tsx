import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { useTenant } from "../context/useTenant";
import LoginForm from "../components/LoginForm";
import { Button } from "../../../components/ui/button";
import { Spinner } from "../../../components/ui/spinner";
import {
  PUBLIC_BRAND_STYLE_ID,
  themeStylesheet,
} from "../../../lib/brandStylesheet";
import {
  fetchPublicBranding,
  type PublicTenantBranding,
} from "../../../api/publicBranding";

/**
 * `/c/<slug>` — the condominium's own front door (APRAS-74, D2/D3/D5/D6).
 *
 * Three visitors, one route:
 *
 * * **Anonymous** → the branded login: the condominium's name and logo above
 *   the *shared* `LoginForm`, themed with the colours the public endpoint
 *   returned. Never a redirect.
 * * **Signed in and a member** → `setActingTenant(id)` and `/`.
 * * **Signed in and not a member — or a slug no condominium carries** → the
 *   same no-access panel, byte for byte. Never a 404, never a redirect.
 *
 * ## The readiness gate
 *
 * A branded link is normally opened by direct navigation, so on mount
 * `useAuth().isLoading` is `true`, `isAuthenticated` is `false` and the
 * membership list is `[]` — for a member and a stranger alike. Resolving then
 * would show a legitimate resident the anonymous login, then the no-access
 * panel, and only then switch them. So nothing but the spinner renders while
 *
 *     isLoading || (isAuthenticated && tenants are still loading)
 *
 * and the resolution is driven by the **current context values on every
 * render**, never by a one-shot mount effect — a membership list that arrives
 * late still resolves. The same expression covers the post-login path:
 * `AuthContext.login` flips `isAuthenticated`, which enables the `["tenants"]`
 * query, which puts `useTenant().isLoading` back to `true`.
 *
 * The gate is deliberately **symmetric**: the same spinner precedes the
 * unknown-slug panel and the not-a-member panel, and the branding read runs
 * underneath it identically in both. Gating one branch and not the other
 * would reinstate exactly the timing oracle D6 forbids.
 *
 * ## No timing oracle (D6)
 *
 * `slug → id` is a pure array lookup over `useTenant().tenants` — the very
 * list the condominium switcher offers. **No request is issued to decide**,
 * in either branch, so an unknown slug and a known slug the visitor does not
 * belong to execute the same code and render the same component; there is
 * nothing to time because there is no I/O. Reading the switcher's own option
 * list is also what makes "`/c/<slug>` opens" and "appears in the dropdown"
 * structurally unable to disagree, superusers included.
 *
 * The branding read is issued in every case, its failure degrades the screen
 * rather than blanking it, and its result never feeds the decision. The slug
 * feeds `X-Tenant-Id` through `setActingTenant`; it never replaces it (D5).
 */
const BrandedEntryPage: React.FC = () => {
  const { slug = "" } = useParams<{ slug: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: isAuthLoading, logout } = useAuth();
  const {
    tenants,
    actingTenantId,
    isLoading: isTenantsLoading,
    setActingTenant,
  } = useTenant();

  const [branding, setBranding] = useState<PublicTenantBranding | null>(null);
  const [isBrandingPending, setIsBrandingPending] = useState(true);
  // The slug the fetch below was issued for, so React 19's double-invoked
  // effects in development do not issue it twice.
  const requestedSlug = useRef<string | null>(null);

  useEffect(() => {
    if (requestedSlug.current === slug) return;
    requestedSlug.current = slug;
    setIsBrandingPending(true);
    void fetchPublicBranding(slug)
      .then((payload) => {
        setBranding(payload);
      })
      .catch(() => {
        // A 404 (unknown *or* inactive condominium) and a transport failure
        // are the same fact here: there are no colours to show. The screen
        // degrades to the unbranded form rather than going blank — an
        // unknown slug must still be able to sign somebody in.
        setBranding(null);
      })
      .finally(() => {
        setIsBrandingPending(false);
      });
  }, [slug]);

  /**
   * Whether the identity and its memberships have settled. Recomputed every
   * render from the context values themselves, which is what lets a list that
   * arrives late still resolve.
   */
  const isSettling = isAuthLoading || (isAuthenticated && isTenantsLoading);

  /** The array lookup, and the whole of the signed-in decision. */
  const matchedId =
    !isSettling && isAuthenticated
      ? (tenants.find((tenant) => tenant.slug === slug)?.id ?? null)
      : null;

  useEffect(() => {
    if (matchedId === null) return;
    // Already acting in it: navigate without touching switcher state, so the
    // cache eviction a real switch performs is not paid for nothing.
    if (matchedId !== actingTenantId) {
      setActingTenant(matchedId);
    }
    navigate("/", { replace: true });
  }, [matchedId, actingTenantId, setActingTenant, navigate]);

  /**
   * The colours, injected **only while the visitor is anonymous**.
   *
   * `TenantBrandTheme` themes a signed-in session from the acting tenant's
   * profile; a signed-in visitor here is either redirected out at once or
   * shown the no-access panel, neither of which needs the branding. Keeping
   * this injector off that path is what stops the two from ever fighting over
   * the same custom properties. `theme: null` and a failed read both mean:
   * inject nothing, render the default palette.
   */
  const publicTheme = isAuthenticated ? null : (branding?.theme ?? null);

  useEffect(() => {
    if (publicTheme === null) {
      document.getElementById(PUBLIC_BRAND_STYLE_ID)?.remove();
      return;
    }

    const element =
      document.getElementById(PUBLIC_BRAND_STYLE_ID) ??
      document.createElement("style");
    element.id = PUBLIC_BRAND_STYLE_ID;
    element.textContent = themeStylesheet(publicTheme);
    document.head.appendChild(element);

    return () => {
      document.getElementById(PUBLIC_BRAND_STYLE_ID)?.remove();
    };
  }, [publicTheme]);

  if (isSettling) return <Spinner />;

  if (isAuthenticated) {
    // The switch and the navigation are the effect's business; holding the
    // spinner keeps the panel below from flashing during the commit in which
    // they run.
    if (matchedId !== null) return <Spinner />;

    return (
      <div className="flex flex-col items-center justify-center gap-2 min-h-[50vh] p-8 text-center">
        <p className="text-lg font-semibold text-foreground">
          {t("publicEntry.noAccess")}
        </p>
        <p className="text-sm text-muted-foreground max-w-md">
          {t("publicEntry.noAccessMessage")}
        </p>
        <div className="flex flex-wrap justify-center gap-2 mt-4">
          {/* Both affordances read the visitor's **own** membership list and
              never the slug, so they are identical between the unknown-slug
              and the not-a-member branch. */}
          {tenants.length > 0 && (
            <Button variant="outline" onClick={() => navigate("/")}>
              {t("publicEntry.myCondominiums")}
            </Button>
          )}
          <Button onClick={logout}>{t("publicEntry.signOut")}</Button>
        </div>
      </div>
    );
  }

  if (isBrandingPending) return <Spinner />;

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center text-center mb-8 gap-3">
          {branding?.logo_url && (
            <img
              src={branding.logo_url}
              alt={branding.name}
              className="h-14 w-14 rounded-xl object-contain"
            />
          )}
          <div>
            <h1 className="text-2xl font-bold text-primary tracking-tight">
              {branding?.name ?? t("common.appName")}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {branding
                ? t("publicEntry.subtitle")
                : t("common.appSubtitle")}
            </p>
          </div>
        </div>

        <div className="rounded-xl border bg-card shadow-sm p-6">
          <h2 className="text-lg font-semibold text-foreground mb-5">
            {t("login.heading")}
          </h2>
          {/* No `onSuccess`: flipping `isAuthenticated` puts this page back
              into the readiness gate above, and the slug is resolved once the
              memberships have actually arrived. Navigating from here would
              race that. */}
          <LoginForm />
        </div>
      </div>
    </div>
  );
};

export default BrandedEntryPage;
