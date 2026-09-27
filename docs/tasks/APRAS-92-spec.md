# APRAS-92 — Serve the obras report publicly at `/c/<slug>/obras`, in the condominium's own identity

Mock: `docs/tasks/APRAS-92-mock.html` — the report shell under the unbranded
fallback and under each of §A's five measured brands.

## Scope

Make the construction-projects report (APRAS-60) reachable by a visitor who is
not signed in, at `/c/<slug>/obras`, showing exactly what the internal report
shows today for the condominium the slug names.

**In scope:** one new unauthenticated backend route that renders the report for
a slug-named tenant; the seam that lets the existing renderer run with no
logged-in user; the `/c/:slug/obras` React route that is the URL a visitor is
given; the allowlist and route-classification tests those two move; **and the
document's own identity — its palette derived from the tenant's stored brand
theme instead of the hard-coded green-and-gold, and its logo embedded as bytes
instead of referenced by URL** (§A and §B below).

**Both identity changes are in the shared renderer, so they change the
internal report too.** `GET /api/v1/projects/report` and
`POST /api/v1/projects/report/save` emit the same document
`render_report_html` produces, so a branded condominium's *internal* report is
branded from this task on, and its logo is embedded there as well. That is
intended and is an improvement — the saved copy in the Document Center becomes
genuinely self-contained — and it is the reason §A's fallback rule is written
the way it is: a tenant with no brand theme must keep rendering today's
palette, byte for byte, so `test_project_report.py`'s
`test_the_document_carries_the_ported_print_css`,
`test_the_footer_names_the_tenant_and_the_caller` and their siblings keep
holding unchanged.

**Not in scope, explicitly:**

- **The theme-token migration of the frontend.** The React screens still carry
  hard-coded palette classes. This task changes no Tailwind palette class in
  `frontend/src` and must not assume that migration has landed anywhere. §A is
  a *backend* change, inside one `CSS` string in
  `project_report_service.py`, and shares nothing with it.
- **The obra dataset.** APRAS-89 (blocked, deferred) covers replacing the
  hard-coded data in the untracked local script
  `backend/scripts/sync_drive_obras.py`. That script is excluded via
  `.git/info/exclude`, is not in version control, and is not touched here. The
  public report shows whatever the database holds.
- **Authenticated behaviour.** `GET /api/v1/projects/report` keeps its
  `projects:read` guard and its current response byte-for-byte;
  `POST /api/v1/projects/report/save` is untouched.
- **Rate limiting and caching.** See "Decisions already taken" — both were
  considered and both were declined for this slice.

The screen itself already exists and its approved mock is committed at
`docs/tasks/APRAS-60-mock.html`. §A changes how that document *looks* for a
branded condominium, so this task carries its own mock at
`docs/tasks/APRAS-92-mock.html`: the same report shell under the unbranded
fallback and under each of the five brands this repository already uses as
typed cases, with the measured contrast figures of §A beside it.

## Decisions already taken by the operator

These were decided before the spec and are not re-opened here.

**D1 — Reach is the condominium slug, open on the internet.** The URL is
`/c/<slug>/obras`, following APRAS-74's `/c/<slug>` pattern, chosen over an
unguessable per-link token. The operator was shown that this makes the page
reachable by anyone who guesses or enumerates a slug, and indexable by search
engines, and chose it.

**D2 — Budget figures are included: full parity with the internal report.** The
public report shows everything the internal one shows, the budget block and the
remaining-balance gauge included. Chosen over dropping the figures or showing
percentages only.

**D3 — No rate limit, no cache.** The route is unguarded, tenant-resolved from
the slug, and rendered fresh on every request. A per-IP limiter was considered
(APRAS-74's `@limiter.limit("30/minute")`) and declined. `Cache-Control` was
then considered as a substitute and also declined: a browser-held copy cannot be
invalidated on demand, so a freshly published bulletin would stay invisible for
the whole TTL — exactly the staleness the operator wants to avoid. The
purgeable alternative does not fit the infrastructure either, and this was
verified: `backend/pyproject.toml` and `backend/requirements.txt` contain no
`redis`, `cachetools`, `memcache` or any other cache dependency, and
`backend/app/core/limiter.py` builds `Limiter(key_func=get_remote_address)` with
no `storage_uri`, so both a cache and a limit would be per-process on Vercel's
serverless runtime and would behave inconsistently between instances.

**The accepted risk, stated once.** The slug is guessable by the operator's own
decision (D1). The report renders every project of the tenant into a single
self-contained HTML document, with the remaining-balance gauge emitted as inline
SVG and one `<img>` per bulletin photo. With neither a limit nor a cache, a
caller can walk the slug space and pull every tenant's full report, budget
figures included, at whatever rate they like, and each hit costs a full render:
one `select` over `ConstructionProject` plus a lazy load of milestones and
bulletins per project, then string assembly of the whole document. This is a
deliberate, revisitable decision taken to get the screen shown today. (One
detail of the premise, checked: the photos are **URL references**, not base64
payloads — `decode_photos` returns strings that become `<img src>`, and the
bytes are fetched separately by the browser from the already-public
`/static/uploads` mount. The render cost above is the database work and the
document assembly, not image encoding.)

**D4 — The report's colours come from the tenant's brand theme, not from the
stylesheet.** The operator's words: *"Se possível o logo e as cores virem do
sistema e não chumbados nem de urls públicas."* Today every condominium's
report is the same green-and-gold, whatever brand it has stored
(`project_report_service.py:146`). From this task the palette is derived from
`Tenant.brand_theme` through `app.core.branding.build_theme`, which is and
stays the **only** theme derivation in the repository. A tenant with no
branding keeps today's palette exactly — `build_theme(None) is None`, and
graceful degradation is this renderer's documented behaviour. See §A.

**D5 — The logo is embedded in the document *whenever its bytes can be read
locally*, and only linked when they cannot.** The operator's condition is part
of the decision and is kept in it: *"**Se possível** o logo e as cores virem do
sistema e não chumbados nem de urls públicas."* Today `_masthead_html` renders
`<img src="{logo_url}">` unconditionally, so the document only shows a logo
while the URL it names is reachable. From this task the bytes are read from the
storage provider and embedded when the provider can read its own objects back,
so a report printed or filed in the Document Center carries its own logo; when
it cannot, §B's rung 2 keeps today's `<img src="{logo_url}">`, which is what
"se possível" allows for and exposes nothing new — APRAS-74's
`PublicTenantBrandingRead` already publishes `logo_url` to anonymous callers.

**What that means in production, stated plainly rather than implied.** Once
**APRAS-94** lands, uploads go to Vercel Blob, and the Blob provider inherits
`BaseStorageProvider.read_file`'s `None` default — so rung 2, the *linked* logo,
becomes the path for essentially every tenant that has one, and embedded logos
will be the exception (local development and any legacy `/static/uploads` file)
until a Blob read exists. Rung 2 is therefore time-bounded, not permanent:
**APRAS-96** — "Let the Blob provider read its own objects back, so reports can
embed the logo" — owns closing it and is already created and blocked by
APRAS-94. APRAS-92 does **not** depend on APRAS-96, is not blocked by it, and
moves none of its own work into it. See §B.

*If this is revisited*, **APRAS-93** owns the question: the cheapest close
looks like an `ETag` plus a server-side render cache keyed per tenant and
invalidated on writes to `ConstructionProject`, `ProjectMilestone` and
`ProjectUpdate`, which needs a shared store and therefore a dependency
decision. APRAS-92 does not depend on APRAS-93, is not blocked by it, and ships
the route as specified here. One input for APRAS-93 that this spec does not
otherwise mention: **a lower embed ceiling with a rung-3 fallback** — say
512 KiB instead of §B's 2 MiB — is a one-constant alternative that caps the
per-render payload without any shared store, and is cheaper than both an `ETag`
and a render cache. It is recorded there, not adopted here, because it would
refuse logos the product accepted.

**What an anonymous caller can now see.** On the record, because the report's
existing omissions were calibrated for a different audience:
`_updates_html` omits the bulletin author and `cost_impact` with the stated
reason that the report is "published to the whole condominium". That boundary
was drawn for condominium-wide, not internet-wide. Under D2 nothing further is
removed, so an anonymous caller sees: the condominium's name and logo, every
project's title, kind, status, dates and progress, its full budget block —
contracted value, spent, remaining balance and the gauge — its milestone lists,
and the three latest bulletins with their text and photos. Only the two
pre-existing omissions stay omitted.

## Approach

### Behaviour

**New route.** `GET /api/v1/public/tenants/{slug}/projects/report` returns
`200` with `Content-Type: text/html` and the same document
`project_report_service.render_report_html` produces for the internal route,
rendered for the tenant the slug names. No `Authorization` and no
`X-Tenant-Id` are read or required.

It reuses APRAS-74's shape rather than inventing one: mounted on the same
`/public` prefix with `dependencies=GLOBAL_SCOPED`, tagged `public`, and
resolving the tenant with `TenantService.get_by_slug`. **404 for an unknown
slug and for an inactive condominium alike, in one condition**, with the same
`"Tenant not found"` detail — an inactive tenant is refused to everyone
elsewhere, so answering 200 here would publish a condominium that cannot be
signed into. It carries **no** `@limiter.limit` and sets **no**
`Cache-Control` (D3); APRAS-74's own limiter decorator is not touched.

**The tenant seam.** The renderer resolves its tenant from the session, not
from the caller: `_acting_tenant` reads `acting_tenant_id(session)` and
`_acting_projects` relies on the ambient `with_loader_criteria` of
`app.core.tenant_context`. An anonymous request resolves no acting tenant, so
the handler establishes one for the duration of the render by entering
`tenant_context.acting_tenant_scope(session, tenant.id)` around the render
call. That is the smallest seam available: it needs no change to either
tenant-resolution helper, and it keeps milestone and bulletin access on the
already-narrowed `project.milestones` / `project.updates` relationships, so the
module still contains no `select()` over an inherited table.
`acting_tenant_scope`'s docstring states that any second production caller needs
a justifying review comment; this is that caller, and the comment must be
written both at the call site and in the docstring's caller list.

**The absent user.** `render_report_html(session, user)` uses `user` for
exactly one thing: the footer's `Gerado em … por <full_name>`. The signature
widens to `User | None`, and with `None` the footer renders the timestamp
without the `por …` clause. Nothing else in the renderer reads `user`.
`save_report` and the internal route keep passing a real `User`, so their
output does not change.

**URL ownership.** The frontend owns `/c/<slug>/obras`; the backend owns the
document. They are different deployments — `frontend/vercel.json` rewrites
every path to `index.html`, and the API is a separate Vercel function behind
`VITE_API_URL` — so the backend cannot serve a path on the frontend's origin.
The mapping is concrete: React route `/c/:slug/obras` renders a public page
that fetches
`GET {VITE_API_URL}/public/tenants/{slug}/projects/report` as text and displays
it in a full-viewport iframe with `srcDoc` and `sandbox=""`, the same treatment
`AssemblyMinutesView` gives server-rendered minutes. The page also offers a
plain `<a target="_blank">` to the API URL for printing: because the route is
unauthenticated, a direct link works and the report's own print CSS applies to
a real top-level document — this is precisely the constraint that forced
`ConstructionTrackerPage` into the object-URL workaround and that no longer
applies. A 404 renders a short "report not available" panel, never a blank
screen and never a redirect. The route sits outside `ProtectedRoute` and gets
no `ROUTE_ACCESS`, `NAV_ITEMS` or `NAV_GROUPS` entry, exactly like `/c/:slug`.

**Indexing.** Left alone, as the operator accepted indexing (D1). *A
recommendation only, not part of this task's expected results:* if they later
want the page out of search results, a `<meta name="robots" content="noindex">`
in the rendered document is the one-line change, and it is not added here.

### §A — The palette comes from the tenant's theme (D4)

**Where it comes from.** `render_report_html` already resolves the tenant row
(`_acting_tenant`). It passes `tenant.brand_theme` to
`app.core.branding.build_theme` and uses the returned `["light"]` scheme —
keys are CSS variable names without the leading `--`, values are `oklch(L C H)`
strings at 2dp. The `["dark"]` scheme is **not** used: the report is a printed
A4 document with one page surface, and nothing in the product applies `.dark`.
No colour arithmetic is added anywhere: the renderer looks values up, it never
derives, clamps or repairs one. A second derivation is exactly what
`branding.py`'s docstring forbids.

**The fallback.** `build_theme(None) is None`, so a tenant with no branding —
which is every tenant until someone saves a brand — gets today's ten hex
values, and every colour the document paints is unchanged for them. This is
what keeps `test_the_document_carries_the_ported_print_css` green: its seven
asserted hexes are the fallback block, and the suite's fixture tenants carry no
`brand_theme`.

**The mapping, role by role.** The stylesheet's `:root` block becomes generated
rather than literal, emitting these 19 names. Each row is *one* semantic role;
where two names collapse onto one theme key under a theme, the two names still
exist because the fallback distinguishes them and the CSS body is not rewritten.

| variable | used for | theme key | fallback |
|---|---|---|---|
| `--surface` | `.page` background | `background` | `#f7f1e5` |
| `--card` | every `#fff` card and the bar's `.mark` tick | `card` | `#fff` |
| `--desk` | `body` background behind the pages (screen only) | `border` | `#d9d3c4` |
| `--hero` | the whole `.hero` `background` value | `var(--tint)`, i.e. `accent` | today's three-layer gradient, verbatim |
| `--ink` | headings, `.mast .name`, every large figure, `.grp` list text | `foreground` | `#082f2a` |
| `--text` | `body` text | `foreground` | `#1d2925` |
| `--muted` | every secondary text (`.when`, `.hero p`, labels, `.note`, `.empty`, bulletin body) | `muted-foreground` | `#6f746e` |
| `--soft` | `.budget-row.total`, `.noimg`, the gauge's empty-tank gradient `id="e"`, stops 0 and 1 | `muted` | `#eee6d7` |
| `--soft-sheen` | the **mid stop** of the gauge's empty-tank gradient `id="e"` | `muted` | `#fbf8f1` |
| `--line` | every 1px border, `.tag` rules, both bar tracks (today `#ded8c8`), the gauge strokes, and the two `rgba(198,160,74,…)` borders on `.pill`/`.hero-card` | `border` | `#ddd1b6` |
| `--brand` | brand as a **fill**: `.seg.a`, `.progress span` gradient start, `.grp.done h4 i`, the gauge's filled-tank gradient `id="g"`, stops 0 and 1 | `primary` | `#174b40` |
| `--brand-sheen` | the **mid stop** of the gauge's filled-tank gradient `id="g"`, and the meniscus ellipse's `fill` | `primary` | `#2d6b5c` |
| `--brand-ink` | the gauge's `%` label, which sits on `--brand` | `primary-foreground` | `#fff` |
| `--brand-text` | brand as **characters**: `.pill`, `.grp.done h4`, `.tag.real b` | `primary-text` | `#174b40` |
| `--kicker` | the small uppercase eyebrow labels and `.grp.doing h4` | `primary-text` | `#9b7327` |
| `--brand-alt` | the ornament `--gold` carried: `li::marker`, `.grp.doing` border and dot, `.seg.b`, `.tag.real` rule, the footer's top rule, the gauge's meniscus stroke, the progress gradient's end | `secondary` | `#c6a04a` |
| `--foot` | `.foot` background | `primary` | `#082f2a` |
| `--foot-ink` | `.foot` text | `primary-foreground` | `#aebcb7` |
| `--foot-ink-strong` | `.foot b` | `primary-foreground` | `#fff` |

Six consequences of that table are decisions, and each is deliberate:

1. **`--navy` is gone, split in two.** Today one variable is both dark text and
   the footer's *background*. A theme cannot satisfy both: the footer's
   background has to be a surface whose paired foreground is known. So the text
   uses become `--ink` ← `foreground`, and the footer becomes
   `--foot` ← `primary` with `--foot-ink` ← `primary-foreground` — an
   already-paired pair `build_theme` measures and, in advanced mode, refuses a
   palette over. The footer's two-tone `#aebcb7`/`#fff` collapses to one colour
   under a theme, with `.foot b` distinguished by weight; under the fallback it
   keeps both hexes.
2. **`--gold` and `--kicker` are ornament, and they part company.** `--kicker`
   is *text* — 8pt bold uppercase, which WCAG still counts as normal text — so
   it maps to `primary-text`, APRAS-88's brand-as-characters token, whose
   derivation guarantees 4.5:1 against `card`, `background`, `muted` and
   `accent`. `--brand-alt` (today's `--gold`) carries no text at all, so it maps
   to `secondary`, the theme's second brand surface: it is the only key that is
   both visible on a card and the tenant's own second colour. `--gold-light` is
   referenced nowhere in the stylesheet and is simply not emitted under a theme.
3. **Brand text and brand fill are different variables.** `--primary` fails AA
   as normal text on every light surface (3.4054 on `--card` in the default
   theme); that is what APRAS-88's `--primary-text` exists for. Routing the
   `.pill` label and `.grp.done h4` through `primary` would be the yellow-brand
   bug in a new place.
4. **`.hero`'s decorative gradient is replaced by one measurable surface.**
   Under a theme `--hero` is flat `accent`; the three hard-coded stops
   (`#d8e7df`, `rgba(198,160,74,.25)`, `#edf1e9`, `#f4e8cb`) carry the hero's
   `h1` and `p` and cannot survive a tenant palette. Holding the whole
   `background` *value* in a variable is what lets the fallback keep the
   designed gradient verbatim.
5. **Two classes of literal stay literal, on purpose.** Translucent shadows
   (`rgba(8,47,42,.08–.18)`) are not colours a reader compares and vanish under
   `@media print`; and `#c0392b`, the "behind schedule" segment, is a *status*
   colour — `branding.py` states that `--destructive` and the status tokens are
   semantic and identical in every condominium and are never overridden.
   `#c0392b` is a raw literal, so that rule does not name it by token; it stays
   literal **by the same rule**, as the status colour it is in substance. So the
   one bar state that matters most never depends on the tenant's palette.
6. **The gauge's two gradients flatten under a theme and keep their stops under
   the fallback.** `_cylinder_svg` holds *seven* distinct literals, not five:
   besides `#174b40`, `#c6a04a`, `#ddd1b6`, `#eee6d7` and `#fff` it carries
   `#2d6b5c` (the mid stop of the filled-tank gradient `id="g"` **and** the
   meniscus ellipse's `fill`) and `#fbf8f1` (the mid stop of the empty-tank
   gradient `id="e"`). Both are hand-picked lighter tints, of `--brand` and
   `--soft` respectively, and §A forbids adding colour arithmetic — so they are
   **not** re-derived. They become the two variables above, whose theme key is
   the same key as the stop they sit between: under a theme both gradients
   therefore resolve to three identical stops and render as **flat fills**,
   `primary` for the filled tank and `muted` for the empty one, and the meniscus
   ellipse becomes `--brand` distinguished from the tank only by its
   `--brand-alt` 1.2px stroke, which it already had. Under the fallback
   (`brand_theme is None`) the two hexes are emitted unchanged, so the designed
   sheen survives byte for byte. The developer therefore has no choice to make:
   the gradient elements and their three stops stay in the markup, only the
   colour values move onto variables. This is a **visible** change for branded
   tenants and it has its own expected result.

   **State the asymmetry plainly, because it reads backwards:** the branded
   gauge is the *plainer* of the two. A condominium that configured its
   identity gets a flat tank; one that configured nothing keeps the designed
   sheen. That is accepted because every alternative is worse. Keeping the two
   literals would paint `#2d6b5c` — a green — into the tank of a red-branded
   condominium, which is not a sheen but a wrong colour. Re-deriving a lighter
   tint is a second derivation, which D4 forbids and which `branding.py` keeps
   as the backend's sole responsibility. And routing `--brand-sheen` to
   `secondary` instead buys nothing: in simple mode — the mode all five typed
   brands use — `secondary` and `primary` collapse to the same emitted colour,
   so the tank is flat either way. If a future task wants the sheen back for
   branded tenants, the thing to change is `branding.py`, by emitting a tint
   key the whole product can use, not this renderer.

**The contrast measurement.** Measured with `app.core.branding.contrast_ratio`
on the emitted `oklch()` strings, for `build_theme` in simple mode with the five
brands this repository already types as cases. The numbers were cross-checked
against `frontend/src/lib/contrast.ts` by executing that module directly
(`npx tsx`): `muted-foreground/muted` for `#059669` reads 4.6679 in both,
`primary-text/card` for `#facc15` 5.0718 in both, `primary/border` 2.9478 and
1.2111 in both, `primary-foreground/primary` for `#dc2626` 4.5159 in both. The
two implementations agree because both are pinned to
`backend/tests/data/contrast_fixtures.json`.

**Every text pair the report produces, all five brands (4.5:1 needed):**

| pair | `#059669` | `#dc2626` | `#2563eb` | `#7c3aed` | `#facc15` | today |
|---|---|---|---|---|---|---|
| `--ink` / `--surface` | 19.32 | 19.37 | 19.35 | 19.36 | 19.34 | 12.87 |
| `--ink` / `--card` | 19.88 | 19.93 | 19.91 | 19.92 | 19.91 | 14.48 |
| `--ink` / `--soft` | 17.76 | 17.69 | 17.72 | 17.70 | 17.73 | 11.68 |
| `--ink` / `--hero` | 17.76 | 17.69 | 17.72 | 17.67 | 17.74 | 11.89 |
| `--muted` / `--surface` | 5.08 | 4.96 | 4.92 | 4.95 | 4.91 | **4.24 ✗** |
| `--muted` / `--card` | 5.22 | 5.11 | 5.06 | 5.09 | 5.06 | 4.77 |
| `--muted` / `--soft` | 4.67 | 4.53 | 4.51 | 4.52 | 4.50 | **3.85 ✗** |
| `--muted` / `--hero` | 4.67 | 4.53 | 4.51 | 4.51 | 4.50 | **3.92 ✗** |
| `--brand-text` / `--card` | 5.20 | 5.21 | 5.10 | 5.62 | 5.07 | 9.92 |
| `--brand-text` / `--surface` | 5.06 | 5.06 | 4.95 | 5.46 | 4.93 | 8.82 |
| `--brand-text` / `--soft` | 4.65 | 4.62 | 4.54 | 4.99 | 4.52 | — |
| `--brand-text` / `--hero` | 4.65 | 4.62 | 4.54 | 4.98 | 4.52 | — |
| `--kicker` / `--card` | 5.20 | 5.21 | 5.10 | 5.62 | 5.07 | **4.31 ✗** |
| `--kicker` / `--hero` | 4.65 | 4.62 | 4.54 | 4.98 | 4.52 | **3.54 ✗** |
| `--foot-ink` / `--foot` | 5.27 | 4.52 | 4.81 | 5.30 | 12.82 | 7.36 |
| `--brand-ink` / `--brand` | 5.27 | 4.52 | 4.81 | 5.30 | 12.82 | 9.92 |

**No text pair fails, for any of the five brands**; the worst figure in the
whole table is 4.5028 (`--muted`/`--soft`, `#facc15`) — a cushion of 0.0028,
0.06% above the 4.5 floor. That thinness is not fragility and not luck: it is
`build_theme`'s own repair loop converging on its 0.01 lightness grid, stopping
at the first step that clears the floor. The pair it clears,
`("muted-foreground","muted")`, is in `MEASURED_PAIRS`, so the 422-refusal and
repair contract owns the figure and this report only *reads* the result — no
palette can be stored that misses it. There is no float drift to fear either:
both implementations measure 2dp-snapped `oklch()` strings and agree to four
decimal places. And if the derivation ever moves, ER 15's `>= 4.5` fails loudly
in CI rather than degrading silently. The yellow brand — the
case this repository has measured trouble with before — is safe here precisely
because none of these pairs is invented: `--muted`, `--brand-text` and
`--foot-ink` are the theme's own paired foregrounds, and the pale brand's
`primary-text` is derived down to `oklch(0.54 0.11 91.94)` rather than used at
face value. Five pairs that **fail today** are repaired by this change for every
branded tenant (marked ✗ above); the unbranded fallback keeps them as they are,
because repainting the designed palette is a decision nobody asked for and
`test_the_document_carries_the_ported_print_css` pins it.

**The graphical pairs, where it does not hold (3:1 needed for a meaningful
graphic, WCAG 1.4.11):**

| pair | `#059669` | `#dc2626` | `#2563eb` | `#7c3aed` | `#facc15` | today |
|---|---|---|---|---|---|---|
| `--brand` / `--card` | 3.72 | 4.78 | 5.10 | 5.62 | **1.53 ✗** | 9.92 |
| `--brand` / `--line` (bar fill on its track) | **2.95 ✗** | 3.76 | 4.02 | 4.42 | **1.21 ✗** | 6.97 |
| `--brand-alt` / `--card` | 3.72 | 4.78 | 5.10 | 5.62 | **1.53 ✗** | **2.46 ✗** |
| `--brand-alt` / `--line` | **2.95 ✗** | 3.76 | 4.02 | 4.42 | **1.21 ✗** | **1.73 ✗** |
| `--line` / `--card` (hairlines) | 1.26 | 1.27 | 1.27 | 1.27 | 1.27 | 1.51 |
| `--surface` / `--desk` (page edge) | 1.23 | 1.24 | 1.23 | 1.23 | 1.23 | 1.33 |

Named rather than omitted, with the figures for a tenant whose two typed
colours differ: with `primary=#059669, accent=#c6a04a`, `--brand-alt`/`--card`
is 2.4952 and `--brand`/`--brand-alt` is 1.4911; with
`primary=#2563eb, accent=#facc15`, `--brand-alt`/`--card` is 1.5338. **The two
bar segments can therefore be indistinguishable from each other** — 1.0 exactly
when the síndico types the same hex for both colours, against 4.03 today.

**What the renderer does about them: nothing chromatic, and that is the
decision.** It cannot repair a colour without becoming a second derivation, and
`build_theme`'s refusal contract (`MEASURED_PAIRS`) deliberately excludes
`border`, `input` and `ring`, so widening it would start rejecting palettes that
are stored and working. Instead the document is made to not *depend* on those
distinctions, which it almost already does:

- every quantity a bar or the gauge encodes is printed as text next to it —
  `.tag`/`.tag.real` carry `previsto`/`realizado` with their percentages, the
  progress bar carries `--pct-- concluído` above it and its labels below, the
  budget block prints contracted/spent/remaining in full, and the gauge's own
  `%` label sits on `--brand` at ≥4.52 for all five brands **whenever it sits on
  the tank at all**. That qualifier is load-bearing and is recorded rather than
  glossed: the label's `y` is `max(fy + 22, top + 30)`, so below roughly 8%
  remaining balance it is pushed past the tank's bottom ellipse and lands on the
  card instead. The defect is pre-existing — today that is `#fff` on `#fff` —
  but under a theme it becomes brand-dependent: a near-white
  `primary-foreground` (as `#dc2626` derives) measures ≈1.05 against `--soft`.
  The 1.4.1 conclusion is unaffected, because the budget block prints the
  remaining balance in full next to the gauge, so the figure is never conveyed
  by the label alone. Repairing the label's placement is not this task's (see
  Out of Scope). So no information is conveyed by colour alone (WCAG 1.4.1 holds
  even where 1.4.11 misses);
- the segment boundary keeps its 1.5px `--card` tick and the planned `.mark`, so
  the two segments remain separated geometrically when they are not separated
  chromatically;
- the behind-schedule state keeps `#c0392b`, untouched by any theme;
- the hairlines and the page edge are pure decoration, which 1.4.11 exempts, and
  the page edge additionally keeps its box-shadow.

This is the same accepted, named risk APRAS-84 recorded for `--primary` as a
graphical token and the same reasoning; the tree-wide repair is not this task's.
The spec requires it to be **written into the renderer as a comment naming the
failing pairs and their figures**, not left to a reader to rediscover.

### §B — The logo is embedded, not linked (D5)

**The dependency, plainly.** Logo upload is **broken in production** today:
`LocalStorageProvider.save_file` writes to a read-only serverless filesystem,
and APRAS-94 owns the fix. Until it lands, almost no tenant has a `logo_url` to
embed, so the path that matters most in practice is the **no-logo** path. This
task does not depend on APRAS-94 and must not be read as making a logo appear.

**How the bytes are obtained — locally, never over the network.** The renderer
adds no outbound HTTP request. On a public, unlimited, uncached route (D3) a
per-request fetch to an arbitrary host would be both an amplification vector and
an SSRF surface, so:

- `LocalStorageProvider` gains `resolve_own_url(url) -> Path | None` — the
  mapping from a URL under its own `url_prefix` back to a path under its own
  `base_dir` — and `read_file(url) -> bytes | None` on top of it.
  `BaseStorageProvider.read_file` is added as a **concrete** default returning
  `None` ("this backend cannot read back"), so the three unimplemented provider
  stubs stay untouched and no new `NotImplementedError` can reach a client.

  **Unless it is already there.** APRAS-96 ("Let the Blob provider read its own
  objects back") owns the same two base defaults — `read_file` and
  `resolve_own_url` — and the two tasks are independent: neither blocks the
  other and either may land first. So this task adds each default only if it is
  absent, and leaves it exactly as it is if present. If APRAS-96 landed first
  its `read_file` default carries the wider signature
  `read_file(url, *, max_bytes: int | None = None)`; that is the preferred form
  and this task must not narrow it, since the one-positional-argument call this
  ladder makes is valid against both. Nothing in CI type-checks this — there is
  no mypy and no pyright — so a narrowed base would be caught by nobody.
- That mapping rule already exists once, in `tenant_service._delete_stored_logo`
  ("only a `/static/uploads/` value is mapped back, relative to the provider's
  own `base_dir`"). It moves into `resolve_own_url` and `_delete_stored_logo`
  calls it, so the rule is stated once rather than twice.
- **`resolve_own_url` adds a containment check the current code does not have.**
  `_delete_stored_logo` today joins `Path(base_dir) / relative` and trusts the
  result; this task promotes that same join into a *read* primitive invoked from
  a public, unauthenticated route. It is not reachable today — the only writer of
  `logo_url` is the validated upload path, and the value is not client-writable —
  so this is defence in depth, and it is one line: `resolve_own_url` resolves the
  joined path (`Path.resolve()`) and returns `None` unless it
  `is_relative_to(base_dir.resolve())`, with a comment saying that a stored value
  is data and a read primitive on an anonymous route must not depend on who wrote
  it. `_delete_stored_logo` inherits the check by calling the same function.
- `TenantService` gains `logo_data_uri(tenant) -> str | None`, next to
  `LOGO_MAX_FILE_SIZE` and `LOGO_ALLOWED_MIME_TYPES`, which already own every
  logo rule. It returns `data:<mime>;base64,<…>` or `None`.
  `project_report_service` calls it (it already imports `document_service`, and
  `tenant_service` imports nothing from it, so there is no cycle).
- The MIME type comes from the stored suffix through a new explicit inverse map
  in `app.core.uploads`, restricted to the three image types the logo allowlist
  permits. A suffix outside it — including `.svg` and the inert `.bin` — yields
  `None` and is never embedded: an SVG is active content, which is exactly why
  `LOGO_ALLOWED_MIME_TYPES` excludes it.

**The ceiling.** Embedding is refused above `TenantService.LOGO_MAX_FILE_SIZE`
(2 MiB) — the upload ceiling itself, so **no logo the product ever accepted is
refused**, and the bound exists only against a file swapped on disk. The
consequence is stated rather than hidden: base64 inflates by 4/3, so a
worst-case logo adds ≈2.7 MiB to every render of an uncached public route (D3).
Real logos are tens of kilobytes; if this ever matters it is the same
composition question APRAS-93 already owns.

**Failure and absence.** One rule, three outcomes, in order:

1. bytes obtained, typed and inside the ceiling → `<img src="data:…;base64,…">`,
   same `alt`, same class, same layout;
2. bytes not obtainable (file missing, unreadable, over the ceiling, untyped
   suffix, or a provider that cannot read back) **and** the stored value is an
   absolute `http(s)://` URL → today's `<img src="{logo_url}">`, unchanged. This
   is the one remaining external reference, and it is kept deliberately: it is
   the only way an externally hosted logo — or a Blob URL after APRAS-94, until
   **APRAS-96** gives the Blob provider a `read_file` — renders at all, and
   refusing it would *remove* a logo that works today. After APRAS-94 this is the
   rung nearly every logo takes, per D5. `_delete_stored_logo`'s "somebody else's file, left
   alone" rule is the same judgement;
3. anything else, `logo_url` absent included → **no `<img>` at all**, exactly
   today's no-logo masthead, which already degrades correctly: the `.mast`
   flexbox simply puts the report block alone on the row. No exception escapes
   the renderer; a read failure is logged at warning level and nothing more.

### How this can land (a suggestion, not a split)

§A (the palette re-mapping) and §B (the logo-read plumbing) touch disjoint code
and can land as **two commits inside this task** — `refactor(APRAS-92): …` for
the generated `:root` and the gauge variables, then `feat(APRAS-92): …` for the
storage read primitive and the masthead's three rungs, with the route and the
frontend in either. That keeps the 19-variable re-mapping reviewable apart from
the `resolve_own_url`/`read_file`/`logo_data_uri` chain. It changes no scope and
no expected result; both commits are in the range ER 22 checks.

### Files touched

- `backend/app/api/v1/endpoints/public_projects.py` — **new.** The one route,
  with a module docstring in `public_branding.py`'s register: why it is
  `GLOBAL_SCOPED`, why the tenant comes from the path, the 404 rule, and D3's
  accepted risk with the operator's decision named.
- `backend/app/api/v1/endpoints/public_branding.py` — docstring only: its
  opening claim to be "the only unauthenticated tenant-shaped read in the
  product" becomes false. No behaviour change, no decorator change.
- `backend/app/api/v1/api.py` — import and `include_router` on `prefix="/public"`,
  `tags=["public"]`, `dependencies=GLOBAL_SCOPED`.
- `backend/app/core/permissions.py` — one entry in `UNGUARDED_ROUTES` with the
  reason comment (it authenticates nobody, so there is nobody to hold a
  permission), taking it from 29 to **30**.
- `backend/app/services/project_report_service.py` — `user: User | None`
  through `render_report_html` / `get_report_html` / `_page_html` /
  `_footer_html`, and the footer's author clause made conditional; **§A**: the
  `CSS` constant's literal `:root` replaced by a generated block, the two role
  tables (`REPORT_ROLE_SOURCES` var → theme key, `FALLBACK_PALETTE` var → hex)
  as module constants, the stylesheet body and `_cylinder_svg`'s **seven**
  literals (`#174b40`, `#2d6b5c`, `#c6a04a`, `#ddd1b6`, `#eee6d7`, `#fbf8f1`,
  `#fff`) moved onto the new variable names, and the comment naming §A's failing
  graphical pairs with their figures; **§B**: `_masthead_html`'s three-outcome
  logo rule.
- `backend/app/services/storage_service.py` — `BaseStorageProvider.read_file`
  as a concrete `None`-returning default, plus `resolve_own_url` and
  `read_file` on `LocalStorageProvider`.
- `backend/app/services/tenant_service.py` — `logo_data_uri`, and
  `_delete_stored_logo` rewritten to call `resolve_own_url` instead of
  restating the prefix rule.
- `backend/app/core/uploads.py` — the explicit extension → image MIME inverse
  map, with the comment saying why it is restricted to the three image types
  and why it is not derived from `CONTENT_TYPE_EXTENSIONS` by inversion.
- `backend/app/core/tenant_context.py` — docstring only: `acting_tenant_scope`
  names its second production caller.
- `backend/tests/test_permission_registry.py` — `29` → `30` at both length
  assertions and at `len(ROUTE_PERMISSIONS) == total - 29`, with the docstring
  paragraph extended the way APRAS-74's was.
- `backend/tests/test_permission_parity_matrix.py`,
  `backend/tests/test_superuser_grant.py`,
  `backend/tests/test_tenant_modules_api.py` — the same `UNGUARDED_ROUTES`
  length literal, `29` → `30`.
- `backend/tests/test_tenant_route_scope.py` — the new `GLOBAL_ROUTES` entry
  plus its comment, and `33` → `34`.
- `backend/tests/test_superuser_grant.py`,
  `backend/tests/test_tenant_modules_api.py` — the `GLOBAL_ROUTES` length
  literal, `33` → `34`.
- `backend/tests/test_public_project_report.py` — **new.** See test criteria.
- `backend/tests/test_project_report_branding.py` — **new.** §A's mapping,
  fallback and measured pairs, and §B's four logo outcomes.
- `docs/tasks/APRAS-92-mock.html` — **new.** The report shell under the
  fallback and under the five brands, with §A's figures.
- `frontend/src/api/publicProjects.ts` — **new.** The unauthenticated text
  fetch, alongside `publicBranding.ts` and documented the same way.
- `frontend/src/features/project-management/components/PublicObrasReportPage.tsx`
  — **new.** The `/c/:slug/obras` screen.
- `frontend/src/App.tsx` — the route, beside `/c/:slug`.
- `frontend/src/i18n/locales/en.json`, `pt.json` — the page's strings.
- `frontend/src/features/project-management/__tests__/PublicObrasReportPage.test.tsx`
  — **new.**

### Test criteria

Backend (`backend/tests/test_public_project_report.py`):

- an unauthenticated `GET` on a known, active slug answers `200`,
  `text/html`, and the body contains the project's title and the same budget
  markers the internal report's tests assert;
- the response carries no `Cache-Control` header;
- an unknown slug and an active-but-`is_active=False` tenant both answer `404`
  with the same detail;
- cross-tenant isolation: with projects in two tenants, the body for slug A
  contains A's project titles and none of B's, and the masthead/footer name
  tenant A;
- the anonymous footer renders `Gerado em …` with no `por` clause, while the
  authenticated route's footer still names the caller (the existing
  `test_the_footer_names_the_tenant_and_the_caller` must stay green unchanged);
- the internal route still answers `403` to a caller without `projects:read`
  (existing `test_projects_rbac.py` unchanged).

Branding and logo (`backend/tests/test_project_report_branding.py`):

- with `brand_theme = None` the document contains every fallback hex of
  `FALLBACK_PALETTE` — the seven the existing suite already pins plus the gauge's
  two sheen stops `#2d6b5c` and `#fbf8f1` — and none of `oklch(`; and
  `test_the_document_carries_the_ported_print_css` is left unchanged as the
  authenticated half of that claim;
- under a theme the gauge's two gradients carry three identical stops each:
  `--brand`/`--brand-sheen` resolve to the same `oklch()` string and so do
  `--soft`/`--soft-sheen`, while the `<linearGradient>` elements and their stop
  count are unchanged from today's markup;
- with a simple-mode theme stored, the document contains no fallback hex in a
  `:root` position and each of the 19 variables is assigned the
  `oklch(...)` string `build_theme` emits for the theme key
  `REPORT_ROLE_SOURCES` names — asserted by reading that constant, not by
  restating the table;
- `set(REPORT_ROLE_SOURCES) == set(FALLBACK_PALETTE)`, and every variable named
  in either is referenced at least once in the stylesheet body (so a dead
  variable cannot be added, which is how `--gold-light` survived);
- parametrised over the five brands `#059669`, `#dc2626`, `#2563eb`, `#7c3aed`,
  `#facc15`: the 16 text pairs of §A, enumerated once in a module constant
  `REPORT_TEXT_PAIRS` in this test file (variable-name pairs, not restated
  figures), all measure ≥ 4.5 via `branding.contrast_ratio` on the emitted
  strings, with the in-file list of graphical pairs that fail and their figures
  asserted as recorded, so a change that makes one worse fails rather than
  passes silently;
- a project rendered for a branded tenant still shows its title, its budget
  block and its gauge (the palette change breaks no markup);
- logo: a tenant whose stored `/static/uploads/...` file exists renders
  `src="data:image/png;base64,` and the document contains no `<img
  src="/static/uploads/`; a tenant whose stored file is missing renders **no**
  `<img>` in the masthead and still answers 200; a tenant whose value is an
  absolute `https://…` URL renders that URL verbatim and triggers no outbound
  request (asserted by the absence of any HTTP client call); a tenant with
  `logo_url = None` renders the masthead with no `<img>`;
- a stored file above `LOGO_MAX_FILE_SIZE` is not embedded, and a `.svg` or
  `.bin` suffix is not embedded.

Registry and classification: `test_permission_registry.py`,
`test_tenant_route_scope.py`, `test_permission_parity_matrix.py`,
`test_superuser_grant.py` and `test_tenant_modules_api.py` all pass with the new
literals; no golden or parity baseline file is written, because an unguarded
route adds no parity cell and `ROUTE_PERMISSIONS` does not move.

Frontend: a component test that `/c/:slug/obras` renders the fetched HTML into
an iframe's `srcDoc`, and that a rejected fetch renders the unavailable panel
rather than a blank page.

## Expected Results

- [ ] `GET /api/v1/public/tenants/{slug}/projects/report` exists and, sent with
      no `Authorization` header and no `X-Tenant-Id` header for a known active
      condominium slug, answers HTTP `200` with a `Content-Type` beginning
      `text/html` and a body starting with `<!DOCTYPE html>`.
- [ ] That unauthenticated response body contains the title of a construction
      project belonging to that condominium, and its budget block — the
      contracted value, the amount spent and the remaining-balance figure —
      exactly as the authenticated `GET /api/v1/projects/report` body does for
      the same data.
- [ ] Sent with an unknown slug, that route answers HTTP `404`; sent with the
      slug of a condominium whose `is_active` is `false`, it also answers HTTP
      `404`, with the same response detail in both cases.
- [ ] With construction projects existing in two different condominiums, the
      unauthenticated response for condominium A's slug contains A's project
      titles and none of condominium B's project titles, and names A in its
      header and footer.
- [ ] The unauthenticated response carries no `Cache-Control` header, and the
      route answers a 31st request from the same IP inside one minute with
      `200` rather than `429`.
- [ ] The unauthenticated response's footer shows a `Gerado em <date time>`
      timestamp with no author name after it; the authenticated
      `GET /api/v1/projects/report` response still shows
      `Gerado em <date time> por <caller full name>`.
- [ ] `GET /api/v1/projects/report` still answers `403` to an authenticated
      caller who does not hold `projects:read`, and
      `POST /api/v1/projects/report/save` still creates a document for a caller
      holding `projects:read` + `documents:create`.
- [ ] `app.core.permissions.UNGUARDED_ROUTES` has length `30` and contains
      `("GET", "/api/v1/public/tenants/{slug}/projects/report")`;
      `backend/tests/test_permission_registry.py` passes in full (its
      allowlist-length case updated to the new length, renamed if its name
      still spells the old one), and `ROUTE_PERMISSIONS` is unchanged at 208
      entries.
- [ ] `tests/test_tenant_route_scope.py::GLOBAL_ROUTES` has length `34` and
      contains the new route, and every test in
      `backend/tests/test_tenant_route_scope.py` passes — including
      `test_route_count_is_fully_accounted_for` and
      `test_global_auth_routes_resolve_a_scope_explicitly`.
- [ ] `backend/tests/test_permission_parity_matrix.py`,
      `backend/tests/test_superuser_grant.py` and
      `backend/tests/test_tenant_modules_api.py` pass, and no parity baseline
      or golden file under `backend/tests/` is added or modified by this task.
- [ ] Visiting `/c/<slug>/obras` in the browser while signed out displays the
      report document, and the same path for an unknown slug displays a short
      "report unavailable" message rather than a blank page or a redirect to
      `/login`.
- [ ] Rendered for a condominium whose `brand_theme` is `null`, the report body
      contains all nine of `#082f2a`, `#174b40`, `#2d6b5c`, `#c6a04a`,
      `#f7f1e5`, `#ddd1b6`, `#eee6d7`, `#fbf8f1`, `#9b7327` and contains no
      `oklch(` anywhere, on both the authenticated
      `GET /api/v1/projects/report` and the public route — so the budget gauge
      keeps today's two three-stop gradients unchanged for an unbranded
      condominium.
- [ ] Rendered for a condominium whose `brand_theme` is
      `{"mode":"simple","primary":"#dc2626","accent":"#dc2626"}`, the report
      body contains `oklch(0.58 0.22 27.33)` and contains none of `#174b40`,
      `#c6a04a`, `#9b7327` or `#f7f1e5`; the same is true of the body returned
      by the authenticated `GET /api/v1/projects/report`.
- [ ] For that same branded condominium, the budget gauge's two
      `<linearGradient>` elements (`id="g"` and `id="e"`) are still present with
      three `<stop>` children each, and within each gradient all three
      `stop-color` values resolve to the **same** colour — `var(--brand)` and
      `var(--brand-sheen)` carry one identical `oklch()` string, as do
      `var(--soft)` and `var(--soft-sheen)` — so each gauge gradient renders as a
      flat fill under a theme. The meniscus ellipse keeps its
      `stroke-width="1.2"` outline.
- [ ] A test parametrised over the brands `#059669`, `#dc2626`, `#2563eb`,
      `#7c3aed` and `#facc15` measures, with
      `app.core.branding.contrast_ratio` on the `oklch()` strings the report
      actually emits, the **16** text-on-surface pairs enumerated in the module
      constant `REPORT_TEXT_PAIRS` of
      `backend/tests/test_project_report_branding.py`, which is exactly:
      `--ink` on each of `--surface`, `--card`, `--soft` and `--hero`; `--muted`
      on those same four; `--brand-text` on those same four; `--kicker` on
      `--card` and on `--hero`; `--foot-ink` on `--foot`; and `--brand-ink` on
      `--brand`. `len(REPORT_TEXT_PAIRS) == 16`, and every one of the 80
      resulting figures is at least `4.5`, the lowest of them being `4.5028`
      (`--muted` on `--soft`, brand `#facc15`).
- [ ] The same test declares in an explicit in-file list, with figures, every
      graphical pair left below `3:1`, and **asserts** those figures rather than
      skipping or `xfail`-ing them: `--brand`/`--line` at `2.9478` for `#059669`
      and `1.2111` for `#facc15`; `--brand`/`--card` at `1.5338` for `#facc15`;
      `--brand-alt`/`--card` at `1.5338` and `--brand-alt`/`--line` at `1.2111`
      for `#facc15`; and, for a theme whose two typed colours differ,
      `--brand-alt`/`--card` at `2.4952` and `--brand`/`--brand-alt` at `1.4911`
      with `primary=#059669, accent=#c6a04a`, `--brand-alt`/`--card` at `1.5338`
      with `primary=#2563eb, accent=#facc15`, and `--brand`/`--brand-alt` at
      exactly `1.0` when one hex is typed for both brand colours.
- [ ] `backend/app/services/project_report_service.py` contains a comment that
      names those below-3:1 graphical pairs with the same figures, so the
      accepted risk is readable at the code.
- [ ] A condominium whose stored logo file exists on disk gets a report whose
      masthead `<img>` `src` begins `data:image/`, and the document contains no
      `<img src="/static/uploads/`; a condominium whose `logo_url` is `null`,
      and one whose stored file is missing, each get a report that answers
      `200` with no `<img>` element inside `<header class="mast">` — all of this
      on both the authenticated `GET /api/v1/projects/report` and the public
      `GET /api/v1/public/tenants/{slug}/projects/report`.
- [ ] Rendering a report makes no outbound HTTP request: with `httpx`,
      `requests` and `urllib.request` each patched so that any call raises, a
      report for a condominium whose `logo_url` is an absolute `https://…` value
      still answers `200` on both routes, and that URL appears verbatim as the
      masthead `img` `src`.
- [ ] `backend/tests/test_project_report.py` passes **unmodified** — in
      particular `test_the_footer_names_the_tenant_and_the_caller` and
      `test_the_document_carries_the_ported_print_css`.
- [ ] `LocalStorageProvider.resolve_own_url` returns `None` for a stored value
      that escapes its own base directory — `"/static/uploads/../../../etc/passwd"`
      is enough — and a condominium whose `logo_url` holds such a value gets a
      report that answers `200` with no `<img>` in its masthead and no file
      content from outside the uploads directory in the body.
- [ ] Over the commits of this task — those whose subject matches
      `^[0-9a-f]{40} [a-z]+\(APRAS-92\):` in the output of
      `git log --format='%H %s'` — `git show --stat <sha>` lists **no** path
      other than `backend/app/api/v1/api.py` and paths beginning
      `backend/app/api/v1/endpoints/`, `backend/app/core/`,
      `backend/app/services/`, `backend/tests/`, `frontend/src/` or
      `docs/tasks/APRAS-92-`. In particular `backend/scripts/sync_drive_obras.py`
      appears in none of them, and no path under `backend/alembic/` or
      `docs/adr/` does either.
- [ ] Over that same commit range, `git show -U0 <sha>` contains no added or
      removed line matching
      `(bg|text|border|ring)-(slate|gray|zinc|neutral|stone|emerald|green|amber|rose|red|blue|indigo|violet)-[0-9]`,
      so no Tailwind palette class is added, removed or renamed anywhere.
- [ ] `docs/tasks/APRAS-92-mock.html` exists, opens with no network dependency
      beyond the Tailwind and Lucide CDNs, and lets a reader switch the rendered
      report shell between "sem marca" and each of the five brands, with the
      budget gauge showing its three-stop sheen under "sem marca" and a flat
      fill under each brand.
- [ ] `cd backend && uv run pytest` and the frontend test suite both pass, and
      `uv run ruff check .` reports no new finding.

## Out of Scope

- The theme-token migration of the React screens (no Tailwind palette class
  changes under `frontend/src`).
- APRAS-89's obra dataset / `sync_drive_obras.py`. The hard-coded obra data
  stays as it is — the operator asked for this slice *"mesmo com os dados
  mockados"*.
- Any change to `GET /api/v1/projects/report`'s guard or
  `POST /api/v1/projects/report/save`. Their *output* does change, by §A and
  §B, and that is intended.
- Any change to `build_theme`, `MEASURED_PAIRS` or the 422 refusal contract, and
  any second colour derivation. The report reads the theme; it never computes
  one.
- Reading logo bytes out of Vercel Blob. APRAS-94 implements the provider.
- Repairing the graphical pairs §A records below 3:1, in the report or anywhere
  else in the tree.
- Repairing the gauge `%` label's placement, which below roughly 8% remaining
  balance falls off the tank onto the card (pre-existing; §A records the figures
  and WCAG 1.4.1 still holds because the balance is printed in full beside it).
- Giving the Vercel Blob provider a `read_file`: **APRAS-96**, blocked by
  APRAS-94. Until it lands a Blob-stored logo renders as §B's rung 2, per D5.
- The dark scheme. `build_theme` returns one, and the report uses only
  `["light"]`.
- Rate limiting, caching, `ETag`, and any `robots` directive (D3; the `robots`
  option is recorded as a recommendation only).
