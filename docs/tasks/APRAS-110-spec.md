# APRAS-110 — Show the acting condominium's logo in the header

Mock: [`docs/tasks/APRAS-110-mock.html`](APRAS-110-mock.html) — every state below
on the real header strip (the broken-bytes card fails and then recovers for real,
on a 3 s stand-in for the app's 60 s retry), plus the two questions the operator
has now answered, each still drawn as its A and B options with the chosen one
marked.

**Both questions are settled; neither is open.**

1. **Does the logo show on a desktop screen, or only on the phone?** Answered
   **A** — every screen size. This is what the spec already recommended; it is
   recorded here as decided rather than proposed, and §Behavior state 1 and the
   three-way `md:hidden` rule are unchanged.
2. **In the dark colour scheme, does a dark logo get a white card behind it?**
   Answered **B** — **yes, it does.** This **reverses** the spec's own
   recommendation of A. The operator read the tradeoff the mock stated (a white
   patch in an otherwise dark bar, for every logo, including the ones that did
   not need it) and chose the card, so that a condominium's black-ink logo is
   readable in the dark scheme instead of nearly vanishing. §"Theming and
   contrast" now specifies the card; A is not re-argued anywhere below.
3. A third question asked whether to file a backend follow-up for the logo
   route's missing validator. Answered yes, and it exists as **APRAS-124**,
   "Cache the public tenant logo route so repeat page loads do not re-fetch the
   bytes". Nothing in it lands here — the expected result forbidding any file under
   `backend/` in `git diff --name-only` still stands.

## Scope

The app's banner header is the `<header>` (implicitly `role="banner"`; the file
carries **no** literal `role` attribute, so do not grep for one) inside
`frontend/src/features/user-administration/components/Navbar.tsx:65`. It is the
only `<header>` rendered as the application chrome. Of the other four `<header>`
elements in `src`, three are page-section headings (`TenantsAdminPage.tsx:237`,
`AssemblyVotingPage.tsx:176`, `AnnouncementCard.tsx:40`); the fourth,
`LandingPage.tsx:29`, *is* a banner landmark, but it sits on a public route
outside `AppChrome` and never co-renders with `Navbar`. Today the banner's left
group carries a hamburger (mobile only) and a **generic APRAS mark** — a
`bg-primary` dot inside
a `bg-primary/10` rounded square, wrapped in a `Link to="/"` labelled
`common.appName`, hidden at `md` and above because the Sidebar already shows the
app brand there. Nothing in the header identifies the condominium the user is
acting in, and with a single membership the tenant switcher does not render
either, so a one-condominium user sees no identity at all.

This task makes that slot show the **acting condominium's own logo** when it has
one, keeps today's generic mark when it does not, and defines every other state
of the slot.

**No backend work, no schema change, no migration, no new i18n key.** Every
piece of data and every URL this needs already exists (see Approach). The
condominium/tenant distinction does not arise here: in APRAS a tenant *is* a
condominium — `TenantProfileRead` is documented as "the acting condominium's own
profile" and its `slug` is the `<slug>` of `/c/<slug>`. The acting condominium is
`X-Tenant-Id`, i.e. exactly what `TenantContext` calls `actingTenant`; a
`síndico` or a `tenant_admin` sees the same header, since nothing here is
permission-gated.

## Approach

### Where the logo comes from (decided, not open)

The asset already exists end to end and this task displays it; it does not
create it.

- **Storage truth / "has a logo" flag:** the `logo_url` column on the `Tenant`
  model, written by the three `/tenant-profile/logo` routes behind
  `TenantProfilePage`. It is **never** a display source (APRAS-105 §D): it is
  relative for a disk-stored logo and unfetchable for a Blob-stored one, because
  the Blob store has private access.
- **Display source:** `tenantLogoUrl(slug)` from
  `frontend/src/api/publicBranding.ts`, which builds the absolute URL of
  `GET /api/v1/public/tenants/{slug}/logo` — the route that reads the object with
  the application's own credential and answers the bytes. Both existing logo
  renderers (`TenantProfilePage`, `BrandedEntryPage`) already use it; this is the
  third caller and introduces no new URL construction.
- **Flag and slug reach the header** from `useTenantProfile()`
  (`frontend/src/hooks/useTenantProfile.ts`, key `["tenantProfile"]`), which
  reads `GET /tenant-profile` — authenticated, unguarded, self-scoped to the
  acting tenant. The query is **already mounted app-wide** by
  `components/TenantBrandTheme.tsx`, so the header adds **no new JSON request**
  (it does add a request for the image bytes — see "The cost of the logo bytes"
  below), and because the key deliberately does not start with `"tenants"`,
  `setActingTenant`'s `resetQueries` resets it on a switch: the header re-themes
  and re-logos on a tenant switch with no extra wiring.

`GET /tenants` (`TenantRead`) is **not** the source: it carries `slug` but no
`logo_url`, and widening it is not needed when a per-acting-tenant read already
carries both.

### The cost of the logo bytes (decided: accept, bounded, degrade)

The `<img src>` **is** a second network request, and unlike the profile JSON it is
not already in flight. It is recorded here rather than left implied, because the
route it hits is the one whose own docstring names this exact amplification.

`backend/app/api/v1/endpoints/public_branding.py:98-135`
(`GET /api/v1/public/tenants/{slug}/logo`) carries `@limiter.limit("30/minute")`
**per IP**, sets **no `Cache-Control` and no `ETag`** (deliberately, per
APRAS-92 D3: a browser-held copy cannot be invalidated, and a logo replaced on
the admin screen must not stay stale at a slug-stable URL), and performs an
outbound fetch buffering up to 2 MiB on every hit. With no validator of any
kind a browser's heuristic freshness lifetime is zero, so every full document
load refetches. Until now the only callers were two low-traffic screens; this
task puts the asset in the chrome of every authenticated screen.

**What the volume actually is.** `Navbar` is mounted by `AppChrome` *above* the
`<Outlet/>` (`App.tsx:130-137`), so the `<img>` mounts once per full document
load and survives every soft navigation. The cost is therefore **one logo
request per full document load per user**, plus **at most one retry per
document load** (see state 5), and zero per in-app navigation. It is not per
screen and not per render.

**Decision: accept it in this task, unmitigated, and degrade gracefully.**
Reasons, in order: the per-load cost is bounded at one request and cannot grow
with navigation; a rate-limited or otherwise failed response never breaks the
header, it shows the fallback mark; the single retry is scheduled further out
than the limiter's own window, so the most likely 429 self-heals; and the only
real remedy is a validator on that route, which is a change under `backend/`
and is foreclosed by the expected result that forbids any file under `backend/`
in `git diff --name-only`. The follow-up backend task that owns it
is **APRAS-124**, "Cache the public tenant logo route so repeat page loads do not
re-fetch the bytes" — already filed, so the remedy is tracked elsewhere rather
than hypothetical here. See §Out of Scope.

### Behavior

A new component
`frontend/src/features/user-administration/components/TenantHeaderLogo.tsx` owns
the whole slot, including the `Link to="/"` that wraps it, so that the
accessible-name rule below lives in one place. `Navbar.tsx` renders
`<TenantHeaderLogo />` where the inline mark is today and keeps the hamburger
untouched. The component calls `useTenantProfile()` with no `enabled` argument:
it is only ever mounted inside Navbar's authenticated branch, so the query
cannot fire on the login screen, and `TenantBrandTheme`'s `enabled` guard stays
the single place that concern is expressed.

Six states, each tested separately. Three of them — 2, 3 and 4 — render
*identically* by design, and the per-state cases exist to pin that they are
intentionally the same rather than accidentally so; the mock draws them as one
card for the same reason.

1. **Logo configured and shown** — `data.logo_url` is non-null: an `<img>` with
   `src={tenantLogoUrl(data.slug)}`, visible at **every** breakpoint (question 1,
   answered A), inside the card wrapper §"Theming and contrast" specifies.
2. **Loading** — the profile query is pending: the fallback mark, no spinner and
   no skeleton. The slot's height is fixed, so nothing shifts when the answer
   arrives.
3. **No logo configured** — `data.logo_url` is `null`: the fallback mark.
4. **Profile read failed** — query error, no data: the fallback mark. The header
   must never be the thing that breaks because a logo could not be resolved.
5. **Logo bytes unavailable** — the `<img>` fires `onError`. This is one state
   with four causes, all handled identically: a 404 (unknown slug, inactive
   condominium, disallowed suffix, empty or refused store read), a **429 from
   the route's `30/minute` per-IP limit**, a dropped connection, and a cold or
   failing Blob read. The component suppresses the image and renders the
   fallback mark; see "The latch and its recovery" below for the key and the
   two ways it clears. A logo that *loads* but is transparent or blank is
   **accepted and undetectable**: no `onError` fires and distinguishing it
   would mean sampling pixels. The visible result is an empty slot, which looks
   like a bug but is not one this task can see.
6. **Dark scheme** — the image itself is untouched (no `dark:` utility, no
   `filter`, no `invert`); the card behind it paints, and paints only here (see
   Theming). The card is part of state 1's markup, so it exists exactly when the
   image does and never behind the fallback mark.

Neither existing renderer handles `onError` at all (`TenantProfilePage.tsx:239`,
`BrandedEntryPage.tsx:195`), so a broken logo shows the browser's broken-image
icon on both today. State 5 is a deliberate improvement on the two precedents
this spec otherwise follows, not an inconsistency with them.

### The latch and its recovery

The failure state is held as **the logo URL that failed, plus how many times it
has failed** — nothing else. Three rules, and all three are load-bearing:

- **The stored URL is the one the current render computed** (`tenantLogoUrl(data.slug)`),
  captured in that render's closure. The handler **must not** read
  `event.currentTarget.src`. The two differ when the slug changes while a
  request is in flight: mutating a live `<img>`'s `src` aborts the old load and
  can fire `error` on an element that already carries the **new** URL, which
  would latch the condominium the user just switched *to*.
- **The `<img>` carries a React `key` derived from the logo URL and the attempt
  count.** A slug change therefore *replaces* the element instead of mutating
  its `src`, so the aborted load fires on a detached node that no longer reaches
  a React handler, and nothing is latched. This is what actually closes the
  in-flight hole; the closure rule alone does not, because a late `error` would
  otherwise be delivered to the new render's handler.
- **Recovery, two conditions, the first of which needs no user action:**
  1. **One automatic retry, 60 seconds after the first failure.** The slot shows
     the fallback for that interval, then the image is re-mounted once (fresh
     `key`, same `src`) and the request is re-issued. 60 s is chosen to exceed
     the limiter's one-minute window, so the 429 introduced by this task heals
     itself. If that retry also fails the slot keeps the fallback for the rest
     of the document's life — bounded at two requests per load, deliberately, so
     the recovery cannot become the amplification §"The cost of the logo bytes"
     accepts. The timer is cleared on unmount and whenever the URL changes.
  2. **The acting condominium's logo URL changes** (a tenant switch, which
     `resetQueries` already drives). Attempt count resets with it.

  **Rejected as a recovery condition: "clear the latch when the profile query
  refetches"** (e.g. on `dataUpdatedAt` advancing). It is unreachable in this
  app. `src/main.tsx:8-16` sets `refetchOnWindowFocus: false` and
  `staleTime: 5 min` on the global `QueryClient`, and `Navbar` never unmounts, so
  no refetch of `["tenantProfile"]` occurs for a user who stays on the app. Also
  note React Query's structural sharing keeps `data`'s identity across a refetch
  that returns equal rows, so keying on `data` identity would not fire either.
  Both would wedge exactly the single-condominium user this task exists for.

**Breakpoints when the latch is engaged.** The fallback is `md:hidden` in the
states where the condominium simply has no logo to show (3, and the pending and
error states 2 and 4), which reproduces today's desktop left group exactly. When
the condominium **does** have a logo and only its bytes failed, the fallback is
rendered **without** `md:hidden`, so the desktop slot is not blank where a logo
was promised. Three-way, and asserted three ways.

The **fallback mark is today's markup** — the `Link to="/"` with
`aria-label={t("common.appName")}` wrapping `size-7 rounded-lg bg-primary/10` >
`size-3.5 rounded-full bg-primary` — with exactly one addition and one
conditional. The addition: **that `Link` gains
`data-testid="tenant-header-fallback"`**, because the mark itself is a
decorative `div` with no role, no accessible name, no text and no test id, and
"the fallback mark is present" must not degrade into
`querySelector(".size-3.5")` — a bare presence assertion on a styling class,
which is the defect `docs/audits/APRAS-111-test-suite-audit.md` exists to
eliminate. `data-testid` is this project's established hook (180 occurrences
under `frontend/src`). **Throughout this spec, "the fallback mark" means
exactly the element carrying `data-testid="tenant-header-fallback"`** — one
noun, one selector, in every criterion. The conditional is `md:hidden`, per the
three-way rule above: on desktop the Sidebar already shows the app brand, so a
second generic APRAS dot would be noise where no logo exists, but a blank slot
where one does exist is a bug. The rule therefore reads: *desktop shows the
condominium's logo, or the generic mark if its bytes failed, or nothing if there
is no logo; mobile shows the condominium's logo or today's mark.* Deliberately
**not** chosen as a fallback: the condominium's initials as text. That would be
brand text on a brand tint (`bg-primary/10`), which is the subject of the open
APRAS-80/90 chain, and this task does not reopen it.

### Accessible name

The `<img>`'s `alt` is **`data.name` — the condominium's name as the API returns
it** (e.g. `alt="Residencial Vila Nova"`). This is `BrandedEntryPage`'s existing
choice (`alt={branding.name}`) and not `TenantProfilePage`'s generic
`tenantProfile.logoAlt`, which is acceptable there only because the image sits
next to a visible "Logo" label. No new i18n key: the name is data, not copy, and
is identical in both locales.

On the logo branch the wrapping `Link` **must not** carry
`aria-label={t("common.appName")}`: an `aria-label` on the link overrides the
image's `alt` for assistive technology, which would make the condominium's name
unreachable and leave "APRAS" as the accessible name of its logo. On the
fallback branch the `aria-label` stays exactly as it is today, and the mark stays
`aria-hidden`-equivalent (a decorative `div`, no text). The link's `href` stays
`/` in both branches, and the banner still exposes **exactly one** link.

Decided rather than left open: the fallback branch keeps `common.appName` as its
accessible name in **every** fallback state, including the latched one, even
though the condominium's name is known there. The alternative — naming the
latched fallback after the condominium — would make the accessible name of one
visually identical element depend on why it is showing, and `Navbar.test.tsx`'s
existing case requires `APRAS` on the no-logo branch anyway. A failure state
promises nothing about the condominium's name.

### Aspect ratio and layout

The image's class list is **exactly these four tokens**, in any order and with
no others: `h-7 w-auto max-w-32 object-contain`. The literals are fixed here,
not left to the implementer, so the asserted tokens and the drawn tokens (the
mock's `logoLink` helper — find it by that name, not by line number, which moved
when the card was added) cannot drift.

Height is pinned at 1.75rem — the same `size-7` the mark it replaces uses, so the
header's own height is byte-identical between a tenant with a logo and one
without. `w-auto` lets a wide logo ask for its natural width; `max-w-32` clamps
that at 8rem; `object-contain` then fits the content inside the resulting
128×28 box. A square logo fills the box's height; a 4:1 banner letterboxes; a
10:1 extreme is scaled down rather than overflowing or stretching. No track in
either `flex items-center` ancestor is sized by the image, so nothing it
contains can move the header.

Two honesty notes for whoever verifies this. `w-auto` is already the `<img>`
default, so asserting it documents intent and guards nothing — it is kept for
that reason only. And a class-token assertion proves four strings are present,
not that a 10:1 banner letterboxes: jsdom has no layout engine, so token
assertions are the only instrument available in Vitest, and **the mock's
extreme-aspect-ratio card is where that behaviour is actually demonstrated**
(a real 400×40 SVG in a real browser). The token list must not be read as proof
of the layout.

### Theming and contrast

The surround uses the existing semantic tokens only (`bg-primary/10`,
`bg-primary`, `border-border/40`, `bg-background/80`), which are already
scheme-aware, so dark mode needs no second rule for it.

**The card, decided by the operator (question 2, answered B).** In the dark
colour scheme a logo gets a small light card behind it. The reason the operator
was given, and chose on: many condominium logos are drawn in black ink for
printing, and on the dark bar they nearly disappear. The cost they accepted
explicitly is that the card shows for *every* logo in the dark scheme, including
the ones that did not need it.

**Where it lives, and its exact class list.** The card is a **wrapper element
around the `<img>`** — a `<span>` the component renders between the `Link` and
the image, on the logo branch only, carrying
`data-testid="tenant-header-logo-plate"`. The `<img>` is its only child, so
`img.parentElement` *is* the card. Its class list is **exactly these five
tokens**, in any order and with no others:

`inline-flex items-center px-1 rounded-md dark:bg-foreground`

Each is deliberate:

- `dark:bg-foreground` is the **only** paint token and the **only** `dark:`
  token. `--foreground` is the semantic token the theme layer already defines as
  the near-white of the dark scheme (`frontend/src/index.css`, `.dark` block),
  and `bg-foreground` is a published target of the token mapping
  (`docs/frontend/theme-token-mapping.md`, the `bg-slate-900`/`bg-slate-950`
  rows), so it is a token and not a raw palette class. A literal `bg-white` is
  the obvious reach here and is exactly what `themeTokenMigration.test.ts`
  exists to reject. The token's role is inverted on purpose — a colour normally
  used for marks is used here as a surface — and that is why the `dark:` prefix
  is load-bearing twice over: unprefixed, `bg-foreground` would paint a
  near-black patch in the light scheme.
- `inline-flex items-center` keep the wrapper's box exactly the image's box
  rather than an inline box with line-height leading, so inserting it changes no
  geometry.
- `px-1` is a 4 px cushion on each side so the ink does not touch the card's
  edge. It is **unprefixed on purpose**: the layout is then identical in both
  schemes and only the paint differs, which is also what makes the single
  sorted-token-set assertion below decide the whole rule. There is deliberately
  **no vertical padding**: the card is exactly `h-7` tall, so it cannot move the
  header's height in either scheme, which is the invariant §"Aspect ratio and
  layout" protects.
- `rounded-md` is the radius token (`--radius-md`); with no background it paints
  nothing in the light scheme.

**What the card is not.** The image still gets **no `dark:` variant, no `filter`
and no `invert`** — the `classTokens(…img).sort()` expected result is unchanged,
and the part of the old reasoning that survives the reversal is the part that
matters: a logo is a logotype, which WCAG 1.4.11 exempts from the contrast requirement, and
re-colouring an arbitrary tenant asset changes a colour the condominium chose.
A surface placed *behind* the artwork is not the same act as re-colouring the
artwork: every pixel the condominium drew is still painted exactly as they drew
it. That distinction is the whole reason the card is a wrapper rather than a
filter on the image.

**Two negatives the card must satisfy, and both are asserted.** It must not
paint in the light scheme (which is what "`dark:` is the only paint token" buys),
and it must not appear behind the **fallback mark** in any of the four fallback
states — no logo, loading, profile error, latched bytes. The generic APRAS mark
already sits on its own `bg-primary/10` tint and needs nothing behind it; a
light card there would be a white patch with no artwork in it.

**This spec states no colour figure and no ratio, deliberately.** It names the
token the card uses and leaves the arithmetic out. Nothing here introduces a
text/surface pair for `frontend/src/lib/contrast.ts` to measure — a logotype is
not text — so there is no ratio to publish, and `docsColourProvenance.test.ts`
(landed at `ab54bf8`) is the reason not to approximate one: the only legitimate
way to write a colour figure into this repository is to let `contrast.ts`
produce it, and no figure here has been produced that way because none is
needed. The card's painted value lives in one place, `index.css`, and is not
copied here.

Note for the reviewer, unchanged and now more load-bearing: no code in `src`
applies the `.dark` class to any element today, so the dark scheme is reachable
only by adding the class by hand — which is how the test reaches it. The project
declares `@custom-variant dark (&:is(.dark *))`, so the hand-added class must be
on an **ancestor** of the component, not on the component's own root.

### Files touched

- `frontend/src/features/user-administration/components/TenantHeaderLogo.tsx`
  (new) — the slot: the `Link`, the six states, the card wrapper on the logo
  branch, the `onError` latch, its 60 s retry timer and the `key` on the `<img>`.
- `frontend/src/features/user-administration/components/Navbar.tsx` — the inline
  mobile mark is replaced by `<TenantHeaderLogo />`; nothing else changes.
- `frontend/src/features/user-administration/__tests__/TenantHeaderLogo.test.tsx`
  (new) — the state matrix below.
- `frontend/src/features/user-administration/__tests__/Navbar.test.tsx`,
  `Navbar.tenantAdmin.test.tsx`, `Navbar.modules.test.tsx`,
  `Navbar.permissions.test.tsx` — each gains a `vi.mock` of
  `../../../hooks/useTenantProfile`. Required, not cosmetic: `Navbar.test.tsx`
  and `Navbar.tenantAdmin.test.tsx` render `Navbar` with **no**
  `QueryClientProvider`, so an unmocked `useQuery` throws and every case in both
  files fails. Default the mock to the no-logo answer so
  `Navbar.test.tsx`'s "exactly one link in the banner, the appName logo" case
  keeps passing unchanged. **Write that default inside the factory**
  (`useTenantProfile: vi.fn(() => NO_LOGO)`), not via a later `mockReturnValue`:
  `Navbar.tenantAdmin.test.tsx:89` calls `vi.restoreAllMocks()` in `beforeEach`
  and `vitest.config.ts` sets neither `restoreMocks` nor `clearMocks`
  (documented at `Navbar.test.tsx:52-56`), and an implementation passed to
  `vi.fn(impl)` survives the restore while one installed afterwards does not.
- `docs/tasks/APRAS-110-mock.html` — kept in step with this spec; its
  broken-bytes card now drives the latch and its one retry rather than only the
  latch.

### Test criteria

All in Vitest, all rendering the real component (no snapshot, no prose):

- the six states above, each by the element and attribute that distinguishes it —
  `getByRole("img")` / `queryByRole("img")`, `alt`, `src`, and
  `classTokens(...)` from `src/test/classTokens.ts` for the class assertions
  (never `className.toContain`, which is a vacuous substring match);
- the broken-asset state driven by `fireEvent.error(img)` on the rendered image,
  then asserting the image is **gone** and the fallback mark
  (`getByTestId("tenant-header-fallback")`) is present — the mutation and its
  effect, not merely the handler's existence;
- the recovery, under `vi.useFakeTimers()`, as a **four-step sequence in one
  case** so that neither an implementation that never latches nor one that never
  recovers can pass: error → no image; advance 59 s → still no image; advance
  past 60 s → the image is back with the same `src`; error again, advance 120 s →
  no image, and the retry does not repeat;
- the in-flight property: capture the `<img>` node, re-render with a different
  slug, assert the node is a **different element** (the `key` replaced it rather
  than mutating `src`), then `fireEvent.error` on the **old, detached** node and
  assert the new slug's image is still rendered and the fallback is absent;
- the accessible-name property asserted from the **link**
  (`getByRole("link", { name: <condominium name> })`), which is what proves the
  `aria-label` is not shadowing the `alt`;
- the URL asserted as the full absolute value `tenantLogoUrl(slug)` returns, so a
  regression to raw `logo_url` fails;
- the `md:hidden` rule asserted three ways (absent on the logo link, present on
  the fallback when there is no logo, absent on the fallback when a logo's bytes
  failed), always selecting the fallback by
  `getByTestId("tenant-header-fallback")` and never by a styling class;
- the dark scheme asserted by rendering inside a `.dark` **ancestor** and checking
  the image's token list is exactly the four tokens §"Aspect ratio and layout"
  names — unchanged by the card, because the card is a different element;
- the card asserted as the image's parent, by its sorted token list, **in both
  schemes in one case** (no `.dark` ancestor, then inside one, same array both
  times), which is what proves the paint is `dark:`-gated rather than
  unconditional or branched in JavaScript;
- the card's absence in all four fallback states, by
  `queryByTestId("tenant-header-logo-plate")`, which is the pair without which
  the presence assertion above is worthless.

## Expected Results

- [ ] `frontend/src/features/user-administration/components/TenantHeaderLogo.tsx`
      exists and is rendered by
      `frontend/src/features/user-administration/components/Navbar.tsx`; the
      inline `size-3.5 rounded-full bg-primary` mark no longer appears in
      `Navbar.tsx` — `grep -c "size-3.5" frontend/src/features/user-administration/components/Navbar.tsx`
      **prints** `0` (judge the printed number, not the exit status: `grep -c`
      exits 1 when there is no match).
- [ ] With a profile fixture whose `logo_url` is non-null, `slug` is `vila-nova`
      and `name` is `Residencial Vila Nova`,
      `within(screen.getByRole("banner")).getByRole("img")` has `src` exactly
      equal to `tenantLogoUrl("vila-nova")` and `alt` exactly equal to
      `Residencial Vila Nova`.
- [ ] With that same fixture,
      `screen.getByRole("link", { name: "Residencial Vila Nova" })` resolves and
      has `href="/"`, and the banner still exposes exactly one link
      (`within(screen.getByRole("banner")).getAllByRole("link")` has length 1 —
      the query **must** be scoped to the banner, because `Navbar` renders
      `Sidebar` as a sibling and an unscoped `getAllByRole("link")` would count
      its links too and fail a correct implementation).
- [ ] With `logo_url: null`: inside the banner `queryByRole("img")` is `null`,
      `screen.getByTestId("tenant-header-fallback")` resolves, **and**
      `within(screen.getByRole("banner")).getByRole("link", { name: "APRAS" })`
      resolves — **scoped to the banner, which is not optional**: `Sidebar`
      renders its own appName-named link as a sibling, so the unscoped query
      matches two elements and Testing Library throws `Found multiple elements`.
      No implementation can satisfy the unscoped form; the existing case this
      result points at is itself banner-scoped. That is — i.e.
      `Navbar.test.tsx`'s existing "exposes exactly one link in the banner,
      the appName logo pointing at /" case passes unmodified — find it by that
      title, not by line number, which moved when `2cb0d48` and `1f0079b` added
      cases to the file. All three
      assertions are required: the pair is what fails both when the fallback is
      absent and when the wrong branch renders.
- [ ] With `useTenantProfile` mocked as `{ data: undefined, isPending: true }`:
      inside the banner `queryByRole("img")` is `null`,
      `screen.getByTestId("tenant-header-fallback")` resolves, and
      `queryByRole("status")` and `queryByRole("progressbar")` are both `null`
      (no spinner, no skeleton).
- [ ] With `useTenantProfile` mocked as `{ data: undefined, isError: true }`:
      inside the banner `queryByRole("img")` is `null` and
      `screen.getByTestId("tenant-header-fallback")` resolves.
- [ ] **The latch engages.** On the logo branch, after
      `fireEvent.error(within(screen.getByRole("banner")).getByRole("img"))`,
      `queryByRole("img")` inside the banner is `null` and
      `screen.getByTestId("tenant-header-fallback")` resolves.
- [ ] **The latch recovers by itself, once, and then stops** — one case, under
      `vi.useFakeTimers()`, with **no re-render and no prop change at any step**,
      so it cannot be satisfied either by an implementation that never latches or
      by one that never recovers: (a) after the error of the previous result,
      `vi.advanceTimersByTime(59_000)` leaves `queryByRole("img")` still `null`;
      (b) a further `vi.advanceTimersByTime(2_000)` makes `getByRole("img")`
      resolve again with `src` exactly equal to `tenantLogoUrl("vila-nova")` and
      `queryByTestId("tenant-header-fallback")` `null`; (c) `fireEvent.error` on
      that retried image followed by `vi.advanceTimersByTime(120_000)` leaves
      `queryByRole("img")` `null` and the fallback present — the retry is bounded
      at one.

      Each advance **must** be wrapped as
      `act(() => { vi.advanceTimersByTime(…) })`. `fireEvent` wraps its own
      dispatch but `advanceTimersByTime` does not, and under React 19 the
      timer's `setState` is scheduled rather than flushed — so an unwrapped
      advance makes a *correct* implementation fail step (b). This is a
      mechanical hazard, not a loosening of the criterion: the bounds above
      still pin the interval to `(59 s, 61 s]`.
- [ ] **A slug change replaces the element rather than mutating its `src`.** With
      the `vila-nova` fixture, capture `const first = getByRole("img")`; re-render
      with a fixture whose `slug` is `parque-azul`; then
      `const second = getByRole("img")` satisfies `second !== first` and has `src`
      exactly `tenantLogoUrl("parque-azul")`; and after `fireEvent.error(first)`
      on that now-detached node, `getByRole("img")` still resolves with `src`
      exactly `tenantLogoUrl("parque-azul")` and
      `queryByTestId("tenant-header-fallback")` is `null`. (Under the
      `event.currentTarget.src` implementation, or without the React `key`,
      `first === second` and this error latches the condominium just switched to.)
- [ ] `classTokens(within(screen.getByRole("banner")).getByRole("img")).sort()`
      equals exactly `["h-7", "max-w-32", "object-contain", "w-auto"]` — the same
      four tokens the mock draws, no others, so there is in particular no token
      starting with `dark:`, no `invert` and no token starting with `filter`. The
      operator's light card is a **wrapper element**, never a token on the image:
      this result is unchanged by it, and the next two are what assert the card.
- [ ] **The card is the image's parent, and its only paint token is
      `dark:`-gated.** One case, with the `vila-nova` fixture, rendered twice:
      once with **no** `.dark` ancestor and once inside a `<div className="dark">`
      ancestor (no code in `src` applies that class, and the project's
      `@custom-variant dark (&:is(.dark *))` matches descendants, so the class
      must be on an ancestor). In **both** renders:
      `const plate = screen.getByTestId("tenant-header-logo-plate")` resolves,
      `within(screen.getByRole("banner")).getByRole("img").parentElement === plate`,
      and `classTokens(plate).sort()` equals exactly
      `["dark:bg-foreground", "inline-flex", "items-center", "px-1", "rounded-md"]`
      — the same array in both renders, no other token. The equality is what
      decides the rule in both directions: an implementation that paints the card
      unconditionally carries an unprefixed `bg-*` token and fails it; one that
      branches on the scheme in JavaScript produces two different arrays and fails
      it; one that reaches the effect with `bg-white`, `invert` or a `filter` fails
      it or the previous result; and one that renders no card at all fails
      `getByTestId`.
- [ ] **The card never sits behind the fallback mark** — asserted in all four
      fallback states, which is the pair that makes the result above mean
      something (an unconditionally rendered card passes presence and fails here):
      `screen.queryByTestId("tenant-header-logo-plate")` is `null` with
      `logo_url: null`, with `{ data: undefined, isPending: true }`, with
      `{ data: undefined, isError: true }`, and on the logo branch after
      `fireEvent.error(within(screen.getByRole("banner")).getByRole("img"))`. The
      latched case is additionally asserted inside a `.dark` ancestor, so the card
      cannot reappear in the one scheme that paints it.
- [ ] The `md:hidden` rule asserted **three ways**: with `logo_url` non-null,
      `classTokens` of the logo's wrapping link does not contain `md:hidden`;
      with `logo_url: null`, `classTokens(screen.getByTestId("tenant-header-fallback"))`
      does contain it; and after `fireEvent.error` on the logo branch,
      `classTokens(screen.getByTestId("tenant-header-fallback"))` does **not**
      contain it — the desktop slot is not blank where a logo was promised.
- [ ] `frontend/src/features/user-administration/__tests__/TenantHeaderLogo.test.tsx`
      exists and `npx vitest run src/features/user-administration/__tests__/TenantHeaderLogo.test.tsx`
      passes with at least one case per state above.
- [ ] `npx vitest run src/features/user-administration/__tests__/Navbar.test.tsx src/features/user-administration/__tests__/Navbar.tenantAdmin.test.tsx src/features/user-administration/__tests__/Navbar.modules.test.tsx src/features/user-administration/__tests__/Navbar.permissions.test.tsx`
      passes, with no case deleted or skipped (case count is no lower than
      before the change).
- [ ] `npx vitest run` in `frontend/` shows no newly failing file, and
      `npm run build` (which runs `tsc`) exits 0.
- [ ] `npm run lint` in `frontend/` reports no more errors than the baseline
      measured **with the eslint the lockfile pins** — `372 problems (370 errors,
      2 warnings)` on `ea37e9a` — so the check is "not worse", not "zero".

      Measure it with the project's own install, not a global or stale one. The
      earlier figure recorded here, `370 problems (368 errors, 2 warnings)`, was
      taken by eslint **9.39.4** from a stale `node_modules`; the lockfile pins
      **10.11.0**, which reports two more errors in two more files on the same
      tree. Same `package.json`, same `package-lock.json`, different linter — that
      alone accounted for a figure this project quoted inconsistently all week.
- [ ] `git diff --name-only` contains no file under `backend/` (which includes
      `backend/alembic/`): this task ships no API, schema or migration change.
- [ ] `docs/tasks/APRAS-110-spec.md` contains a section headed "The cost of the
      logo bytes" that names the route's `30/minute` per-IP limit, its absent
      `Cache-Control` and `ETag`, the resulting volume (one logo request per full
      document load, at most one retry, zero per in-app navigation) and the
      explicit accept decision, and points at **APRAS-124** by id as the task that
      owns the remedy; and §Behavior state 5 names `429` among the causes it
      handles. The recorded decision is the deliverable, since no `backend/` file
      may change.
- [ ] `docs/tasks/APRAS-110-mock.html` exists and opens with no build step
      (Tailwind and Lucide load from CDNs, so it renders unstyled offline —
      "standalone" here means no bundler and no server). It draws **five** cards
      for the six states, because no-logo, loading and profile-error render
      identically and share one card: logo configured; extreme aspect ratio
      (10:1 banner); no-logo/loading/profile-error; logo bytes unavailable, with
      the latch and its 60 s retry; dark scheme, **with the light card painted
      behind the logo**, which is what the operator chose. Plus the two question
      sections, each still drawn with its A and B card and each labelling the
      option the operator chose (question 1: A; question 2: B) rather than the one
      the spec had recommended.

## Out of Scope

- Uploading, replacing or removing a logo — that is `TenantProfilePage` and the
  `/tenant-profile/logo` routes, which already exist and are not touched.
- The Sidebar's app brand mark, and the login screen's logo
  (`BrandedEntryPage`), both of which already render what they should.
- Adding `logo_url` to `TenantRead` / `GET /tenants`.
- Showing the condominium's **name** as text in the header. The switcher already
  does so whenever there are two or more memberships, and the logo's `alt`
  carries it for assistive technology; adding visible text would duplicate the
  switcher for multi-tenant users.
- Logo cache invalidation — *staleness*. The public logo route sets no
  `Cache-Control` and the URL is slug-stable, so a browser may briefly keep a
  replaced logo. That is today's behaviour on `TenantProfilePage` and
  `BrandedEntryPage` alike, and it is not a regression introduced here.
- Adding a `Cache-Control` or `ETag` to
  `GET /api/v1/public/tenants/{slug}/logo` — *volume*, which is a different
  concern from the staleness above and the one this task actually changes. It is
  out of scope only because it is a change under `backend/`, which the expected
  result on `git diff --name-only` forbids; the decision to accept the volume
  meanwhile is recorded in §"The cost of the logo bytes". The operator asked for a follow-up and it now
  exists: **APRAS-124**, "Cache the public tenant logo route so repeat page loads
  do not re-fetch the bytes". Its `ETag` work stays entirely there — the shape it
  takes is an `ETag` plus `Cache-Control: no-cache`, which revalidates on every
  load and answers `304` when the logo is unchanged, removing the 2 MiB outbound
  fetch without weakening the freshness guarantee APRAS-92 D3 chose. Nothing in
  APRAS-124 may land in this task's diff.
- **Painting** the card in the light colour scheme, and any filtering, inverting
  or re-colouring of the logo artwork in either scheme. The operator's decision is
  scoped to the dark scheme and to a surface behind the artwork; the artwork
  itself is never altered.

  Read this as being about the paint only. The card **element** is present on the
  logo branch in *both* schemes — the expected results require exactly that, and
  assert the same five-token class list in a light render and a dark one. What is
  out of scope is giving it a visible background outside the dark scheme: the
  single paint token stays `dark:`-prefixed, so in the light scheme the element is
  there and paints nothing. An implementation that omits the element when no
  `.dark` ancestor is present fails those results.
- Any change to dark-mode activation; no code applies the `.dark` class today.
