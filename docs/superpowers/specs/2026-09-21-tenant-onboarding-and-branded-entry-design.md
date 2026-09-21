# Tenant onboarding and branded entry — design

Date: 2026-09-21
Status: approved in conversation, pending written review

## Problem

APRAS has no public face and no way to bring a new condominium on board.

`/` is behind `ProtectedRoute`; the only unauthenticated screens are login,
signup, forgot-password and reset-password. A visitor who has never logged in
sees a login box and nothing else.

There is no tenant onboarding at all. `POST /tenants` exists but
`tenants:create` sits in `SUPERUSER_ONLY_PERMISSIONS` and no screen calls it.
The `/signup` endpoint does something different from what its name suggests: it
attaches a new user to the **default** tenant (`use_default_tenant_scope`),
inactive and with zero roles, waiting for an administrator. It joins a
condominium; it does not create one.

A tenant is also not addressable. `Tenant` carries `id`, `name`, `is_active`,
`disabled_modules` and `logo_url` — **no slug** — and the acting tenant is
resolved from the `X-Tenant-Id` header, a UUID. Nothing about a condominium can
be reached by URL.

## What we are building

Four deliverables, in dependency order. Each is its own Meridian task.

1. **Tenant slug** — the addressable name.
2. **Tenant onboarding** — superuser creates a condominium and invites its
   administrator.
3. **Landing page and `/c/<slug>`** — a public front door and a per-tenant
   entry point.
4. **White-label theming** — logo and colours from the tenant profile.

## Decisions

Each records what the operator chose and why, so a later reader does not
relitigate it.

### D1 — Superuser creates the tenant; there is no public self-service

Anyone-can-create-a-condominium was rejected. It is the full SaaS shape and
drags quota, abuse handling, email verification and billing in with it, none of
which the product needs while condominiums are sold one at a time.

The superuser creates the tenant and invites the person who will administer it
in the system. **That person is a `tenant_admin`, not necessarily the síndico** —
`is_tenant_admin` is a system role; síndico is an office of the condominium.
The two are frequently confused and must not be conflated in code, UI or copy.

### D2 — `/c/<slug>`, not `/<slug>`

The bare root form the operator first asked for collides with the 39 existing
top-level routes (`/tasks`, `/lots`, `/gate`, `/documents`, …). It would need a
reserved-word list maintained forever: every new screen checked against every
existing slug, and a condominium that already took a name would block a future
route. The `/c/` prefix removes the problem entirely at the cost of four
characters.

**Subdomains (`altos-da-serra.apras.app`) are recorded as a future study**, not
as scope. They are the endgame for a multi-tenant SaaS and would change CORS,
DNS, certificates and local development.

### D3 — A tenant's existence is not a secret

Resolved after the operator initially asked for both no-leakage and a branded
login, which cannot hold together: if a real condominium renders with identity
and an invented slug renders generic, the difference between the two screens
*is* the existence oracle.

The operator accepted public branding, in the Slack and Linear tradition, after
being shown the cost:

- **Enumeration.** A script requesting the branding endpoint against thousands
  of candidate slugs recovers the client list; every 200 is a customer.
- **Phishing.** Name, logo and colours served publicly make a per-condominium
  clone of the login screen trivial, and a targeted email to residents
  convincing. The branding is precisely what makes the forgery work.

**Mitigation: the public branding endpoint is rate-limited per IP** (the
project already has `slowapi`). This raises the cost of mass scanning. It does
**not** reduce the phishing risk for a condominium whose name is already known;
that risk is accepted.

Because existence is not secret, a signed-in user who opens the URL of a
condominium they do not belong to gets a clear "you do not have access to this
condominium" — not a 404. A 404 would protect nothing the branding endpoint
does not already publish.

### D4 — White-label uses the theme layer that already exists

The frontend already carries 80 CSS custom properties in the shadcn shape
(`--primary`, `--primary-foreground`, `--background`, `--card`, `--border`, …)
with Tailwind v4 mapping `--color-*` onto them, plus a `.dark` block. Colours
are authored in **OKLCH**.

So white-label is not building a theming system; it is feeding the one that is
there. The tenant stores its brand colour(s), the API returns them, and the
frontend overrides the variables at runtime. No screen-by-screen revision.

Two costs remain and are in scope:

- **Contrast.** A tenant that picks pale yellow as its primary makes white
  text on it unreadable. The implementation derives `--primary-foreground`
  from the chosen colour rather than trusting input, and validates the pair
  against a stated contrast ratio. OKLCH's perceptual lightness makes this
  calculable rather than a hand-maintained table.
- **Dark mode.** The `.dark` block needs its own derivation from the same brand
  colour, or the tenant supplies two.

### D5 — The slug feeds `X-Tenant-Id`; it does not replace it

The frontend resolves slug to tenant id and keeps sending the header. The
backend contract does not change, and the URL becomes one more tenant selector
alongside the existing switcher, rather than a second, competing resolution
mechanism inside the API.

### D6 — Timing must not undo the messaging

Where two cases are meant to be indistinguishable, the code path must take a
comparable route in both. A lookup that returns fast for an unknown slug and
slow for a known one reinstates the oracle the copy was written to avoid. This
applies to anything the design declares uniform.

## Deliverable 1 — Tenant slug

A new unique column on `tenant`, generated from the name (lowercased,
accent-stripped, hyphenated) and unique across the installation.

**This needs a new Alembic revision.** The standing rule of the past week —
new columns declared inside `0001_initial_schema.py` — **expired** when
production applied `0001` on 2026-09-19. Editing `0001` now causes schema drift
and would need another production reset.

**Open question for the operator:** is the slug editable after creation?
Changing it breaks every saved link — residents will have `/c/altos-da-serra`
bookmarked. The usual answer is to allow the change and keep the old slug
redirecting, which means a table of historical slugs. Recommendation: start
immutable, generated from the name, and revisit when someone actually asks.

## Deliverable 2 — Tenant onboarding

A superuser screen that creates the condominium and invites its administrator.

The creation half is thin: `POST /tenants` exists. The invitation is the new
work — minting a user with `is_tenant_admin`, sending mail, and an acceptance
flow that sets the password. The project has no invitation mechanism today;
`forgot-password` is the closest existing shape and should be examined for
reuse before inventing a second token flow.

## Deliverable 3 — Landing page and `/c/<slug>`

`/` stops being protected. An anonymous visitor gets the landing page; an
authenticated one keeps today's `RootRedirect` behaviour into the dashboard
(APRAS-56). This is the only change to existing routing.

`/c/<slug>` renders a login screen carrying the condominium's name, logo and
colours, fetched from a new public, rate-limited endpoint that returns **only**
those fields — never user counts, active modules, or anything describing the
condominium internally.

Behaviour by visitor:

| Visitor | Result |
|---|---|
| Anonymous | Branded login; on success, straight into that tenant |
| Signed in, belongs to the tenant | Switches to it and continues |
| Signed in, does not belong | "You do not have access to this condominium" |
| Unknown slug | Same shape as "does not belong" (see D6) |

**Landing page content is not specified here and blocks implementation of this
deliverable only.** What APRAS does, for whom, and the selling argument are the
operator's to supply — as a draft or as bullets to be turned into a page.
Inventing marketing copy would produce text that ages badly and gets rewritten.

## Deliverable 4 — White-label theming

Brand colours on the tenant profile (the screen APRAS-61 built), returned by
the branding endpoint and applied by overriding the CSS variables at runtime,
with the contrast derivation and dark-mode handling of D4.

## Risks

- **Phishing is made easier by design** (D3). Accepted, mitigated only against
  mass enumeration. Worth revisiting if the product ever handles payments.
- **The logo file is already world-readable.** `/static/uploads/…` is served by
  an unauthenticated mount; APRAS-65 hardened the served *type*, not access.
  This is not a slug oracle — nobody guesses the file UUID — but a leaked logo
  URL opens to anyone. Out of scope here; worth its own task if it matters.
- **Two tenant-resolution paths** (URL and header) can disagree. D5 keeps the
  header authoritative to bound this.

## Out of scope

Subdomain routing, public self-service tenant creation, billing, slug history
and redirects, and hardening the static mount's access control.
