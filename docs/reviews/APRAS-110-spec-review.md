# APRAS-110 spec review — "Show the acting condominium's logo in the header"

Reviewed: `docs/tasks/APRAS-110-spec.md`, `docs/tasks/APRAS-110-mock.html`.
Round 1, full review. No implementation exists; nothing in the working tree was
modified. Field contract read from
`/Users/heitor/workspace/meridian/plugin/plugins/meridian/references/schema.md`.

The spec is in English, is one PR's worth of work (two production files, one new
test file, four test files touched, no backend), and is unusually careful about
its own factual grounding. Almost every claim it makes about existing code
checks out. It is rejected on five findings, four of which are wording in the
acceptance criteria and one of which is a real operational consequence the spec
does not record.

---

## 1. Verification of the spec's factual claims

Every claim below was checked against the repository, not read.

| Claim | Verdict | Evidence |
|---|---|---|
| The banner is the `<header>` in `features/user-administration/components/Navbar.tsx` | **true, with one imprecision** | `Navbar.tsx:65`. It carries **no** literal `role="banner"` — `grep -rn 'role="banner"' src/` returns nothing. The role is implicit, so `getByRole("banner")` works, but the spec's `<header role="banner">` is not what the file says. |
| The other four `<header>` elements in `src` are page-section headings | **three of four** | `TenantsAdminPage.tsx:237`, `AssemblyVotingPage.tsx:176`, `AnnouncementCard.tsx:40` — the first two render inside `AppLayoutContent`'s `<main className="flex-1">` (`App.tsx:108`), the third inside an `<article>`, so none is a landmark. `LandingPage.tsx:29` is **not**: it is a direct child of a `div` on a public route outside `AppChrome`, so it *is* a `banner` landmark. Harmless — `LandingPage` never co-renders with `Navbar` — but the sentence is wrong. |
| Left group today: hamburger (`md:hidden`) + `Link to="/" aria-label={t("common.appName")} className="md:hidden …"` wrapping `size-7 rounded-lg bg-primary/10` > `size-3.5 rounded-full bg-primary` | **true, verbatim** | `Navbar.tsx:70-91`. `grep -c "size-3.5" Navbar.tsx` = 1. |
| The switcher does not render below two memberships | **true** | `Navbar.tsx` `{tenants.length >= 2 && (<select …>)}`, with a comment giving the same reason the spec gives. A one-condominium user genuinely sees no condominium identity in the header today. |
| `Tenant.logo_url` is a nullable relative/unfetchable path, never a display source | **true** | `backend/app/models/tenant.py:147`; `api/publicBranding.ts` docblock states the relative-path and private-Blob reasons; `TenantProfilePage.tsx:239-244` and `BrandedEntryPage.tsx:195-197` both carry the same APRAS-105 §D comment. |
| `GET /api/v1/public/tenants/{slug}/logo` + `tenantLogoUrl(slug)` are the serving path, and both existing renderers use it | **true** | `backend/app/api/v1/endpoints/public_branding.py:99-150`; `publicBranding.ts:68`; `TenantProfilePage.tsx:245`, `BrandedEntryPage.tsx:199`. This would be the third caller. |
| `useTenantProfile()` carries `logo_url`, `slug` **and** `name`; key is `["tenantProfile"]`; deliberately not under `"tenants"`, so `setActingTenant`'s `resetQueries` resets it | **true** | `TenantProfileRead` (`backend/app/schemas/tenant.py:113-120`) has `name`, `slug`, `logo_url`. `src/hooks/useTenantProfile.ts:22-34`, whose own docblock states the cache-key discipline and names the `queryKey[0] !== "tenants"` predicate. |
| The query is already mounted app-wide by `components/TenantBrandTheme.tsx` | **true** | `TenantBrandTheme.tsx:32` calls `useTenantProfile({ enabled: isAuthenticated })`; mounted at `App.tsx:151`, inside `TenantProvider`, outside `BrowserRouter`. The header therefore adds **no new JSON request** — the claim holds for `/tenant-profile`. It does **not** hold for the logo bytes; see finding 1. |
| `GET /tenants` / `TenantRead` carries `slug` but no `logo_url` | **true** | `backend/app/schemas/tenant.py:36-51`. |
| `Navbar.test.tsx` and `Navbar.tenantAdmin.test.tsx` render `Navbar` with no `QueryClientProvider` | **true — this is the spec's most consequential claim and it is correct** | `Navbar.test.tsx:103-109` renders `MemoryRouter > SidebarProvider > Navbar`; `Navbar.tenantAdmin.test.tsx:81-86` renders `MemoryRouter > Navbar`. Neither imports `QueryClient`. Both mock `../../../hooks/usePermissionQueries` for exactly this reason. `Navbar.modules.test.tsx:92-100` and `Navbar.permissions.test.tsx:70-78` **do** wrap in `QueryClientProvider`. So an unmocked `useQuery` would throw "No QueryClient set" and fail every case in the first two files. |
| The `vi.mock` remedy is sufficient for all four files | **sufficient, with a caveat worth stating** | The relative specifier `../../../hooks/useTenantProfile` resolves to the same module from all four files (they all sit in `__tests__/`), and no other component in the Navbar/Sidebar tree imports that module, so a factory exporting only `useTenantProfile` is safe. Caveat: `Navbar.tenantAdmin.test.tsx:89` calls `vi.restoreAllMocks()` in `beforeEach`, and `Navbar.test.tsx:52-56` documents that `vitest.config.ts` sets neither `restoreMocks` nor `clearMocks`. On the installed Vitest 4.1.11, `mockReset`/`mockRestore` restore the implementation passed to `vi.fn(impl)`, so a default written **inside** the factory survives; a default installed later via `mockReturnValue` would not. See Suggestions. |
| `Navbar.test.tsx:912` is "exposes exactly one link in the banner, the appName logo pointing at /" | **true, exactly at that line**, and the fallback design keeps it passing unmodified | The case asserts `getAllByRole("link")` length 1, `href="/"`, and `getByRole("link", { name: "APRAS" })`. With the mock defaulted to no-logo the fallback branch keeps today's `aria-label` and renders one link. The only change the file needs is the `vi.mock`, not the case. |
| No code in `src` applies the `.dark` class today | **true** | `.dark` appears only as a declaration in `src/index.css:3,90`; no `classList.add("dark")` and no `className="dark"` anywhere in `src`. |
| `src/test/classTokens.ts` splits on whitespace, so negative assertions mean something | **true** | `classTokens.ts:19`. The spec's insistence on it over `className.toContain` is right and matches that file's own docblock. |
| Lint baseline "roughly 375 errors across 64 files" | **close, not exact** | Measured on this checkout: `✖ 370 problems (368 errors, 2 warnings)`. |

Nothing in the spec's factual section was left unverified.

---

## 2. Judgements on the five design decisions

**1. `alt = data.name`, and the prohibition on keeping `aria-label` on the logo
branch — correct, and the reasoning is sound.** The shadowing claim is right:
accessible-name computation takes `aria-label` at step 2C, before it ever
descends into the element's contents, so an `aria-label` on the `<a>` means the
`<img>`'s `alt` is never consulted. Keeping it would publish "APRAS" as the
accessible name of a condominium's logo and make the condominium's name
unreachable. The resulting name — the condominium's name, on a link to `/` — is
the right one; it matches `BrandedEntryPage.tsx:199-200` (`alt={branding.name}`)
and correctly declines `TenantProfilePage`'s generic `tenantProfile.logoAlt`,
which is only adequate there because the image sits beside a visible label.
Asserting the name from the **link** rather than the image (test criteria,
bullet 4) is the right instrument: it is the only assertion that can fail if the
`aria-label` is left behind.

**2. Six states.** They collapse to three distinct renderings (logo; fallback;
fallback), which the spec says plainly rather than pretending otherwise — that
is honest and the per-state cases are still worth having, since they pin that
pending/null/error are *intentionally* identical. On the three cases asked
about:

- *A logo that loads but is transparent or blank*: not a state the spec can
  handle, and not a defect — no `onError` fires, and detecting it would mean
  sampling pixels. Worth one sentence of explicit acceptance rather than
  silence (Suggestions), since the visible result is an empty slot that looks
  exactly like a bug.
- *A slug that changes while a request is in flight*: the spec's latch rule is
  ambiguous here. See finding 5.
- *Can the latch wedge permanently*: **yes.** See finding 2. This is the one
  state-model defect.

**3. Today's generic mark as the fallback, keeping `md:hidden` — right, and the
asymmetry is coherent, not a latent layout bug.** Declining to render initials
on `bg-primary/10` is correct: that is brand text on a brand tint, which is
precisely the open APRAS-80/90 chain, and a task whose whole point is to display
an asset should not acquire a contrast decision on the way. The asymmetry is
safe because it *reproduces today's desktop state exactly*: the hamburger and
the mark are both already `md:hidden`, so a no-logo tenant's desktop left group
is empty today and stays empty, with `justify-between` holding the right-hand
group in place. The only new desktop case is "a logo appears where nothing was",
which is additive. No layout bug.

**4. No contrast claim, no `dark:`, no plate, no filter — verified and
correct.** The spec states no ratio anywhere; §"Theming and contrast" says so
explicitly and names the gamut-mapping rule only to say it is not exercised.
`src/lib/contrast.ts:20-22,155-195` is the CSS Color 4 §13 chroma-reduction
implementation (clipping only once the OKLab error is under the JND), and
nothing here goes near it. The WCAG 1.4.11 logotype exemption is the right
authority, and re-colouring an asset the condominium chose would be the wrong
thing to do even if it were permitted.

**5. Fixed height + `w-auto` + `max-w-*` + `object-contain` — the mechanism is
correct; the criterion that asserts it is not.** With the mock's concrete values
(`h-7 w-auto max-w-32 object-contain`): height is pinned at 1.75rem, `w-auto`
lets a 10:1 banner ask for ~280px, `max-w-32` clamps it to 128px, and
`object-contain` then fits the 10:1 content inside the 128×28 box, letterboxing
vertically and centring. The header's own height cannot move, because no track
is sized by the image. Inside the two `flex items-center` ancestors the image is
centred rather than stretched, so nothing defeats it. The design works. What
does not work is expected result 8, which asserts "a fixed height token" and "a
`max-w-*` token" without naming either — see finding 3.

---

## 3. The two already-recorded questions — are the defaults right?

Not re-raised as findings. Both defaults are right.

- **Logo at every breakpoint (spec picks yes).** This is the right default and
  it is in fact the task's entire justification: the switcher is suppressed
  below two memberships (`Navbar.tsx`), so the single-condominium user — the
  majority case — has no condominium identity anywhere in the chrome. Choosing
  "phone only" would leave that user exactly where they are today and reduce the
  task to a cosmetic change on mobile.
- **No white card for a black-ink logo in dark mode (spec picks show it
  plainly).** Right, and it is the only answer consistent with the other
  decisions: a plate is a colour decision taken on the condominium's behalf, it
  would apply to every logo including the ones that do not need it, and it would
  reintroduce exactly the brand-surface question APRAS-80/90 owns.

---

## 4. The mock

Opens standalone in the sense that matters (no build step, no server); it does
pull Tailwind and Lucide from CDNs at lines 7-8, so offline it renders unstyled.
That is this repository's existing mock convention, not a defect.

It renders the states on a faithful header strip — hamburger, PT/EN pair, user
block with `Síndica` as the office (the vocabulary is used correctly throughout:
nothing in the spec or mock conflates `tenant_admin` with `síndico`, and the
spec states explicitly that nothing here is permission-gated). The broken-asset
card is driven for real: `BROKEN` points at a nonexistent file and a live
`error` listener swaps the anchor for the fallback mark, rather than drawing the
outcome. The 10:1 banner is a real 400×40 SVG, so the letterboxing is actually
shown and not asserted. Good mock.

Two notes, neither blocking: it presents **five** cards for the six states,
merging no-logo/loading/error into one card titled as all three (honest, since
the output is identical, but expected result 13 enumerates six and a literal
reader will count five); and the mock fixes `h-7`/`max-w-32` that the spec
itself leaves unnamed, which is the evidence that finding 3 is a wording gap and
not a missing decision.

Both question sections answer with one letter. Each has an A and a B card
rendered side by side on the affected strip, each labelled in operator language
("logo on every screen size" / "phone only, as the APRAS dot is today";
"no card, logo as drawn" / "white card behind the logo in dark mode"), each
marked with the spec's pick, and each closing with "**A or B is enough.**" An
operator can answer both without reading the spec.

---

## 5. Adversarial pass over the expected results

For each criterion: what implementation satisfies it while the feature is broken
or absent?

- **ER1** (file exists, is rendered, `size-3.5` gone from `Navbar.tsx`) — a
  component that renders `null` satisfies it. Covered by ER2, which forces the
  image. Acceptable as a structural criterion. Wording nit in Suggestions.
- **ER2** (`src` exactly `tenantLogoUrl("vila-nova")`, `alt` exactly the
  fixture's `name`) — the strongest criterion in the spec. Exact equality on
  both attributes, and it cannot be satisfied by rendering `logo_url`. Note it
  is unambiguous in practice because `api/client.ts:7` defaults `baseURL` to the
  absolute `http://localhost:8000/api/v1`, so jsdom's resolved `.src` property
  and the attribute agree. Good.
- **ER3** (link named by the fixture, `href="/"`, exactly one link) — this is
  what fails if the `aria-label` survives on the logo branch. Good.
- **ER4** (`logo_url: null` → no img, fallback present, `getByRole("link", { name: "APRAS" })`) —
  the link assertion is solid; "the fallback mark element is present" is not.
  Finding 4.
- **ER5/ER6** (pending, error) — both are satisfied by a component that *always*
  renders the fallback. ER2 is the only thing preventing that, which is fine, but
  the negative "no element with role `status`/`progressbar` is added" is a good
  specific guard and worth keeping.
- **ER7** (`fireEvent.error`, then img gone and fallback present, then a
  different slug yields an image again) — this is the right shape: it drives the
  mutation and asserts its effect, rather than asserting a handler exists. It is
  also the criterion that silently passes under either reading of the latch key
  — finding 5.
- **ER8** (class tokens) — unverifiable as written. Finding 3. Its negative half
  (no `dark:`-prefixed token, no `invert`, no `filter`-prefixed token) is sound,
  and is only meaningful because `classTokens` splits on whitespace.
- **ER9** (`md:hidden` absent on the logo link, present on the fallback's
  wrapper) — right instinct, asserted both ways, which is what keeps it from
  being vacuous. Names the fallback's element as "wrapper" where ER4 calls it
  "the fallback mark element"; folded into finding 4.
- **ER10-ER12** (new test file runs; the four Navbar files pass with no case
  deleted or skipped and a case count no lower than before; full suite shows no
  newly failing file; `npm run build` exits 0) — the no-deletion/no-skip clause
  is exactly the right guard for a change that touches four existing test files,
  and is the criterion that stops the easy regression here (silencing a Navbar
  file instead of mocking the hook).
- **ER13** (lint not worse) — soft but workable; measured baseline differs from
  the stated figure (Suggestions).
- **ER14** (`git diff --name-only` contains nothing under `backend/`) — good,
  and it is the criterion that makes the "no backend work" claim mechanical.
  Note it also *forecloses* the easiest remedy for finding 1, which is why that
  finding asks for a recorded decision rather than a cache header.
- **ER15** (mock exists and shows the states) — weakly verifiable for a visual
  artefact; acceptable.

No criterion is written in a language other than English, none is empty, and
none asserts an outcome the spec gives no way to produce. The defects are
confined to the four criteria named below.

---

## Blocking Findings

1. **The logo bytes are a new app-wide request against an uncached,
   rate-limited public route, and the spec records no decision about it.**
   §Approach claims "the header adds no network request". That is true of the
   `/tenant-profile` JSON — `TenantBrandTheme.tsx:32` already mounts the query
   app-wide under the same key, verified — but it is not true of the image.
   `backend/app/api/v1/endpoints/public_branding.py:99-135` carries
   `@limiter.limit("30/minute")` **per IP**, and its own docstring states "No
   `Cache-Control` and no `ETag`" and then names the amplification risk in
   terms: *"this route is public, uncached and performs an outbound fetch
   buffering up to 2 MiB on every hit, so one cheap inbound request buys one
   outbound request we pay for."* With no validator of any kind the browser has
   a heuristic freshness lifetime of zero, so every full page load refetches.
   Today the only consumers are two low-frequency screens
   (`TenantProfilePage`, `BrandedEntryPage`); this task moves the asset into the
   chrome of **every authenticated screen**, which is precisely the
   amplification that docstring flags, and several users behind one office NAT
   share the 30/minute budget. §Out of Scope disclaims only *cache
   invalidation* (staleness), which is a different concern and does not cover
   request volume. The spec must state the decision — accept the cost, with the
   429 response enumerated as a state alongside the other failure modes, or
   bound it — rather than leave it unmentioned behind a "no backend work,
   no network request" framing. ER14 (`git diff` touches no `backend/` file)
   forecloses fixing it with a cache header inside this task, which makes the
   recorded decision the deliverable.

2. **The `onError` latch wedges permanently for exactly the user this task
   exists for.** State 5 says the latch "is keyed on the `src` it failed for, so
   switching condominium retries rather than staying permanently fallen back."
   That escape hatch is unavailable to a single-condominium user: the switcher
   does not render below two memberships (verified in `Navbar.tsx`), so the slug
   never changes, and `Navbar` is mounted by `AppChrome` *above* the `<Outlet/>`
   (`App.tsx:130-137`), so it never unmounts across soft navigation. One
   transient failure — a 429 from finding 1, a dropped connection, a cold Blob
   read — therefore replaces the condominium's logo with the generic mark for
   the rest of the browser session, and on desktop with *nothing at all*, since
   the fallback keeps `md:hidden`. The spec needs a second clearing condition
   that a one-condominium user can actually reach (clear the latch when the
   query's `data` identity changes on a refetch, or allow one retry, or scope
   the latch to a mount), plus a criterion that drives it.

3. **ER8 names no class values, so it cannot be verified mechanically.** It
   requires `classTokens(img)` to contain "a fixed height token" and "a
   `max-w-*` token". `classTokens` returns exact strings; QA holding only the
   expected results cannot decide pass or fail against an unnamed token or a
   glob, and two implementers would pick different values. The mock already
   fixes them (`h-7 w-auto max-w-32 object-contain`, mock line 174) — state those
   literals in the criterion so the asserted tokens and the drawn tokens cannot
   drift. Related: as a class-token assertion this criterion proves four strings
   are present, not that a 10:1 banner letterboxes. The mechanism is correct
   (see §2.5) and jsdom has no layout engine, so token assertions are the only
   instrument available here — but the criterion should say that the mock's
   extreme-aspect card is where that behaviour is actually demonstrated, so the
   token list is not mistaken for proof of it.

4. **"The fallback mark is present" appears in four criteria (ER4, ER5, ER6,
   ER7) with no stated way to select it.** The mark is a decorative `div` inside
   a `Link` — no role, no accessible name of its own, no text, no test id. A QA
   agent holding only the expected results cannot resolve "the fallback mark
   element", and the obvious implementation, `container.querySelector(".size-3.5")`,
   is exactly the cheap presence assertion this project's audit records 19+
   instances of: it stays green for any `div` carrying that class, in any
   position, whether or not the slot renders. Name the selector once and reuse
   it in all four criteria — the discriminating pair is already in ER4
   (`getByRole("link", { name: "APRAS" })` **and** no `img` in the banner), and
   that is what should be asserted, with the class token checked on that link's
   child rather than found by query. ER9 compounds the problem by calling the
   same element "the fallback mark's wrapper" where ER4 calls it "the fallback
   mark element"; pick one noun and bind it to one selector.

5. **The latch key is ambiguous between the rendered `src` and the event
   target's `src`.** "keyed on the `src` it failed for" admits two
   implementations: storing the URL from the current render, or reading
   `event.currentTarget.src` in the handler. They differ observably when the slug
   changes while a request is in flight — changing an `<img>`'s `src` mid-load
   aborts the old load and can fire `error`, at which point the element already
   carries the **new** URL, so the event-target reading latches the new slug as
   failed and the freshly switched condominium shows the fallback with no way
   back. ER7 passes under both readings (it re-renders only after the error has
   settled), so nothing catches it. State which URL is stored, and that the
   handler compares against the URL of the render rather than reading it off the
   element.

## Suggestions

- `Navbar.tsx:65` has no literal `role="banner"`; the role is implicit. Write it
  as "the `<header>` (implicitly `role="banner"`)" so nobody greps for an
  attribute that is not there.
- "the other four `<header>` elements in `src` are page-section headings" is
  true of three. `LandingPage.tsx:29` is a direct child of a `div` on a public
  route outside `AppChrome`, so it is a `banner` landmark too. Inconsequential
  (it never co-renders with `Navbar`), but the sentence as written is wrong.
- Write the `vi.mock` default **inside** the factory (`useTenantProfile: vi.fn(() => NO_LOGO)`),
  not via a later `mockReturnValue`. `Navbar.tenantAdmin.test.tsx:89` calls
  `vi.restoreAllMocks()` in `beforeEach`, and `Navbar.test.tsx:52-56` documents
  that the config sets neither `restoreMocks` nor `clearMocks`. On the installed
  Vitest 4.1.11 an implementation passed to `vi.fn(impl)` survives the restore
  and one installed afterwards does not — worth one sentence in §Files touched
  so the developer does not lose a round to it.
- Say explicitly that a logo which loads but is transparent or blank is accepted
  and undetectable (no `onError`, and distinguishing it would mean sampling
  pixels). The visible result is an empty slot that looks like a bug, so it is
  better acknowledged than silent.
- `w-auto` is already the `<img>` default; asserting it documents intent but
  guards nothing. Keep it, and say that is why.
- The measured lint baseline on this checkout is `370 problems (368 errors, 2
  warnings)`, not "roughly 375 errors across 64 files". The "not worse" framing
  is right; the number should match what the command prints.
- ER1 says `grep -c … returns 0`. `grep -c` *prints* 0 and *exits* 1 when there
  is no match. Write it as "prints 0" so the criterion is not read as an exit
  status.
- The mock renders five cards for six states, merging no-logo/loading/error into
  one (correctly — the output is identical). ER15 enumerates six states; either
  say the three share a card or have ER15 list what is actually drawn.
- Mock lines 7-8 load Tailwind and Lucide from CDNs, so "opens standalone" means
  "needs no build step", not "works offline". Fine as the house convention, but
  ER15's "opens standalone" is worth qualifying.
- Neither existing renderer handles `onError` (`TenantProfilePage.tsx:239`,
  `BrandedEntryPage.tsx:195`), so today a broken logo shows the browser's broken
  image icon on both. This task's state 5 is strictly better; saying so would
  make clear it is a deliberate improvement rather than an inconsistency with
  the two precedents the spec otherwise follows closely.

VERDICT: REJECTED

1. The logo bytes are a new app-wide request against an uncached,
   rate-limited (`@limiter.limit("30/minute")` per IP, no `Cache-Control`, no
   `ETag`) public route whose own docstring names this amplification as the open
   concern; §Approach's "the header adds no network request" is true only of the
   `/tenant-profile` JSON, §Out of Scope disclaims only cache *staleness*, no
   429 state is enumerated, and ER14 forecloses fixing it in-task — so the
   decision must be recorded.
2. The `onError` latch wedges permanently for a single-condominium user: the
   switcher does not render below two memberships, so the slug never changes,
   and `Navbar` is mounted above the `<Outlet/>` so it never unmounts. The
   spec's stated escape ("switching condominium retries") is unreachable for
   exactly the user the task exists for. A second clearing condition and a
   criterion driving it are needed.
3. ER8 requires "a fixed height token" and "a `max-w-*` token" without naming
   either, so QA holding only the expected results cannot decide pass or fail.
   The mock already fixes `h-7 w-auto max-w-32 object-contain`; state those
   literals, and say the mock's extreme-aspect card is where letterboxing is
   actually demonstrated.
4. "The fallback mark is present" (ER4, ER5, ER6, ER7) names an element with no
   stated selector — a decorative `div` with no role, name, text or test id. The
   obvious `querySelector(".size-3.5")` is the cheap presence assertion this
   project's audit exists to prevent. Bind the phrase to the discriminating pair
   already in ER4 (`getByRole("link", { name: "APRAS" })` plus no `img` in the
   banner), and use one noun for it across all four criteria.
5. "keyed on the `src` it failed for" is implementable two ways — the URL of the
   current render, or `event.currentTarget.src` — which differ when the slug
   changes mid-flight, and ER7 passes under both. State which URL is stored and
   that the comparison is against the render, not the element.
