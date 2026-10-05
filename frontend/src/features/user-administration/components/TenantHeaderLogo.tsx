import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { tenantLogoUrl } from "../../../api/publicBranding";
import { useTenantProfile } from "../../../hooks/useTenantProfile";
import { cn } from "../../../lib/utils";

/**
 * The banner header's left slot: the acting condominium's logo (APRAS-110).
 *
 * It owns the `Link to="/"` as well as what goes inside it, so the
 * accessible-name rule lives in one place — on the logo branch the link must
 * carry **no** `aria-label`, because an `aria-label` overrides the image's
 * `alt` and would leave the app's name as the accessible name of the
 * condominium's logo.
 *
 * `useTenantProfile()` is called with no `enabled` argument: this component is
 * only ever mounted inside `Navbar`'s authenticated branch, so the query
 * cannot fire on the login screen, and `TenantBrandTheme`'s own `enabled`
 * guard stays the single place that concern is expressed. The query is already
 * mounted app-wide under `["tenantProfile"]`, so the header adds no new JSON
 * request — only the image bytes.
 */

/**
 * How long the slot waits before re-mounting the image once, after its bytes
 * failed.
 *
 * Longer than the public logo route's one-minute rate-limit window, so the
 * 429 this task's traffic can provoke heals itself.
 */
const RETRY_DELAY_MS = 60_000;

/**
 * The failure the slot is holding, if any.
 *
 * The URL is the one the *render that mounted the image* computed, never
 * `event.currentTarget.src`: the two differ when the slug changes while a
 * request is in flight, and reading the element would latch the condominium
 * the user just switched to.
 */
interface LogoFailure {
  url: string;
  /** How many times `url` has failed. The retry fires only after the first. */
  failures: number;
  /** Whether the image is currently withheld. */
  suppressed: boolean;
}

const TenantHeaderLogo: React.FC = () => {
  const { t } = useTranslation();
  const { data } = useTenantProfile();
  const [failure, setFailure] = useState<LogoFailure | null>(null);

  // The display source is always the public logo route, never the stored
  // `logo_url` — which is relative for a disk-stored logo and unfetchable for
  // a Blob-stored one. `logo_url` is only the "has a logo" flag.
  const logoUrl = data?.logo_url ? tenantLogoUrl(data.slug) : null;

  // A failure recorded against another URL is not this URL's failure. This is
  // what makes a tenant switch reset the attempt count with no extra wiring.
  const current = failure?.url === logoUrl ? failure : null;

  const shouldRetry = current?.suppressed === true && current.failures === 1;

  useEffect(() => {
    if (!shouldRetry || logoUrl === null) return;
    const timer = setTimeout(() => {
      setFailure({ url: logoUrl, failures: 1, suppressed: false });
    }, RETRY_DELAY_MS);
    // Cleared on unmount and whenever the URL changes, so a slot that was
    // latched for a condominium the user left cannot fire later.
    return () => clearTimeout(timer);
  }, [shouldRetry, logoUrl]);

  if (logoUrl !== null && data && current?.suppressed !== true) {
    const attempt = current?.failures ?? 0;
    return (
      <Link
        to="/"
        className="flex items-center hover:opacity-80 transition-opacity"
      >
        {/* The card the operator chose: a surface *behind* the artwork, so
            every pixel the condominium drew is still painted as they drew it.
            `dark:bg-foreground` is the only paint token and the only `dark:`
            one — unprefixed it would paint in the light scheme too, where the
            token's value is the opposite end of the scale. The element itself
            exists in both schemes; only its paint is gated. */}
        <span
          data-testid="tenant-header-logo-plate"
          className="inline-flex items-center px-1 rounded-md dark:bg-foreground"
        >
          <img
            // The key is derived from the URL and the attempt count, so a slug
            // change *replaces* the element instead of mutating its `src`: the
            // aborted load then fires on a detached node that no longer
            // reaches a React handler, and nothing is latched.
            key={`${logoUrl}#${attempt}`}
            src={logoUrl}
            alt={data.name}
            onError={() => {
              setFailure({
                url: logoUrl,
                failures: attempt + 1,
                suppressed: true,
              });
            }}
            className="h-7 w-auto max-w-32 object-contain"
          />
        </span>
      </Link>
    );
  }

  return (
    <Link
      to="/"
      data-testid="tenant-header-fallback"
      aria-label={t("common.appName")}
      className={cn(
        "flex items-center gap-2 hover:opacity-80 transition-opacity",
        // Three-way. Where the condominium has no logo to show, the desktop
        // slot stays as it is today: the Sidebar already carries the app
        // brand there. Where a logo was promised and only its bytes failed,
        // the mark shows at every breakpoint rather than leaving a blank slot.
        logoUrl === null && "md:hidden",
      )}
    >
      <div className="size-7 rounded-lg bg-primary/10 flex items-center justify-center">
        <div className="size-3.5 rounded-full bg-primary" />
      </div>
    </Link>
  );
};

export default TenantHeaderLogo;
