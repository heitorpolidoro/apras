# APRAS-68 — White-label: the condominium's brand colours in the profile and in the app

Deliverable 4 of `docs/superpowers/specs/2026-09-21-tenant-onboarding-and-branded-entry-design.md`
(D4). Siblings: APRAS-66 (slug, done), APRAS-74 (public `/c/<slug>` branding
endpoint, which consumes what this task derives).

**Revision note (round 4).** Round 3's spec exposed two colours but reduced the
second one to a ~1% tint; it also measured a colour the browser does not paint
(out-of-gamut `oklch()` is gamut-mapped by chroma reduction, not clipped), and
it stated the repair rule and the `*-foreground` rule in two mutually
contradictory ways. This revision fixes all four: the accent now lands on
`--secondary` at **full chroma**, every emitted colour is **snapped into the
sRGB gamut before it is measured**, the repair side is stated **per pair**, and
every foreground's starting value is **listed**. Every figure below was
re-derived for this revision (sweeps in the task's report), not carried over.

## Scope

Brand colours per tenant, edited on the condominium profile screen (APRAS-61)
under the existing `tenants:profile_update`, stored by a new Alembic revision
in one JSON column, and applied at runtime by overriding the CSS custom
properties `frontend/src/index.css` already declares. No new route, no new
permission.

### Coverage boundary — what "the brand colours in the app" actually re-themes

The mechanism reaches exactly the components that consume the semantic tokens,
and **that is a minority of this UI today**. Measured over `frontend/src`:

- **56 of 266 `.tsx` files** use semantic classes (`text-muted-foreground`
  ×190, `text-foreground` ×85, `text-primary` ×38, `bg-card` ×32, `bg-primary`
  ×28, `bg-secondary` ×7, `hover:bg-accent` ×9, `ring-ring` ×9). These
  re-theme.
- **108 files** hard-code Tailwind palette classes that no CSS variable can
  reach — `text-slate-400` ×147, `text-gray-500` ×122, `border-slate-800` ×114,
  `text-slate-900` ×106, `border-gray-200` ×103, `bg-slate-800` ×94,
  `text-indigo-600` ×67. These do **not** re-theme, and will still look
  slate-and-indigo after a síndico sets the condominium's colours.

So a tenant sees its colours on buttons, cards, focus rings, muted text and
surfaces built from shadcn primitives, and sees today's palette everywhere a
screen was written with literal palette classes. Migrating those 108 files is
a **named follow-up task** (`APRAS-77 — migrate hard-coded palette classes to
semantic tokens`, already in the backlog); it is
deliberately **not** in this PR, which would otherwise touch 100+ files and be
unreviewable. Every expected result below can pass while that follow-up is
outstanding — that is the honest boundary of this deliverable.

Also not in scope: the public, unauthenticated branding endpoint for `/c/<slug>`
(APRAS-74, which reuses `app/core/branding.build_theme` and the column this
task adds); logo work (APRAS-61/65); a dark-mode *toggle* (none exists today —
`.dark` is declared and never applied, and this task only emits it); typography
and custom fonts; per-module colours; the `--destructive*`, status and priority
tokens, which are semantic and identical for every tenant; the `--radius`
scale; and the contrast of the **hard-coded defaults in `index.css`** (see
"A finding about today's default") — this task never edits that file.

## Decisions

- **D-A — two modes, one stored object.**
  - *Simple*: the tenant picks a **primary** and an **accent** colour. Every
    other variable, and the whole `.dark` counterpart, is derived in OKLCH.
    Contrast is guaranteed by construction because the derivation owns **both**
    sides of every measured pair.
  - *Advanced*: the tenant authors the full palette listed in "The exposed
    variables". The construction guarantee is gone — the tenant chose both
    sides by hand — so advanced mode **measures every pair and refuses**
    anything below 4.5:1.
- **D-B — the refusal lives in the API.** `PATCH /api/v1/tenant-profile`
  returns **422** with the failing pairs and their measured ratios. The
  frontend runs the same measurement for live feedback, but that is a
  convenience; a request that bypasses the UI is refused all the same.
- **D-C — the measurement is on the emitted, rounded, in-gamut value.** Every
  component is rounded to 2dp **and then chroma-reduced into sRGB** before any
  ratio is computed, in both modes, for both the derivation loop and the
  refusal check. See step 1 and step 2: this is the round-1 defect (measuring
  an internal float) and the round-3 defect (measuring a naive per-channel clip
  instead of the browser's chroma-reduction mapping) closed together.
- **D-D — the derivation and the measurement run on the backend**, in
  `app/core/branding.py`. One implementation serves this task and APRAS-74's
  public endpoint, under pytest's 90% gate. The frontend ports **only** the
  two-colours-in, ratio-out WCAG function (≈30 lines) plus the gamut predicate
  it needs, never the derivation, and a shared fixture keeps the two honest.
- **D-E — the existing `GET/PATCH /api/v1/tenant-profile` carries it.** No new
  route, therefore no `ROUTE_PERMISSIONS` entry and no parity-matrix baseline
  change.
- **D-F — no branding stored means the app renders exactly as today**: the API
  returns `theme: null` and the client injects nothing at all.
- **D-G — the accent colour lands on `--secondary`, at full chroma.** This is
  the deliberate reversal of round 3. Reducing the accent to
  `oklch(0.96 0.01 H)` made the tenant's second colour a near-white tint —
  measured, the entire emittable light-tint range is **`#e3f6f5` … `#ffeee8`**,
  152 distinct 8-bit colours all within a few steps of the `#ecf4ef` default.
  That is not "more colours"; it is an invisible input. Instead:
  - **`--secondary` / `--secondary-foreground` carry the accent at its full
    clamped chroma**, derived by the *same* rule as `--primary` (clamp, snap,
    pick the better foreground, repair). `#0ea5e9` emits
    `oklch(0.68 0.14 237.32)` = **`#23a3e3`** with
    `--secondary-foreground` `oklch(0.15 0.02 237.32)` at **6.96:1**. Chosen
    because `bg-secondary` has **7** call sites (the "Depois" / "Cancelar" /
    secondary-action buttons a person meets in every dialog) and
    `--secondary` carries text, so it is a surface with a real, measured
    contrast obligation rather than a decoration.
  - **`--accent` / `--accent-foreground` stay the pale hover tint** of the
    accent *hue* (`oklch(0.96 max(0.01, C×0.1) H)` light,
    `oklch(0.22 max(0.02, C×0.2) H)` dark), because the shadcn shape needs one:
    `hover:bg-accent` has 9 call sites and a saturated hover block would be
    wrong. **Disclosed**: the light `--accent` range is the `#e3f6f5 …
    #ffeee8` band quoted above. It is a tint, on purpose, and it is not where
    the tenant sees its second colour.
  - **`--ring` stays `← primary`** (9 `ring-ring` / `focus-visible:ring-ring`
    sites), unchanged from today's `index.css` relationship.
  - **Consequence: `muted ← secondary` is dropped.** `--secondary` is now a
    saturated surface, so `--muted` can no longer be a copy of it. In simple
    mode `--muted` takes the neutral default at the *primary's* hue; in
    advanced mode it becomes the **13th authored key**.

## (a) Storage

One nullable JSON column, `tenant.brand_theme`, **following the
`disabled_modules` precedent** on the same table (`sa_column=Column(JSON,
nullable=False, server_default="[]")` there; here `nullable=True`, no server
default, no backfill). Portable `JSON`, not Postgres `JSONB`, exactly as
`disabled_modules` is, so SQLite-backed tests need no data step.

*Why not discrete columns.* Advanced mode carries 13 colours per scheme plus a
mode discriminator and an optional second scheme — 27 nullable columns, every
one of them meaningless in the other mode, and every future palette change a
new migration. The stored object is read and written whole, never queried by
component and never indexed, which is precisely the shape `disabled_modules`
already established. The cost — no database-level validation — is paid by the
Pydantic model and `app.core.branding`, which are the only writers.

Two valid shapes, discriminated on `mode`:

```json
{"mode": "simple",   "primary": "#7c3aed", "accent": "#0ea5e9"}
{"mode": "advanced", "light": {…13 keys…}, "dark": null | {…13 keys…}}
```

Every colour is an sRGB hex `#rrggbb`. **Input is case-insensitive and
normalised to lowercase before storage**: `#FFE680` is stored — and returned by
every read — as `#ffe680`. Brand guides conventionally write hex uppercase, so
rejecting case would be a validation error the síndico cannot act on. The rule
lives once, in `app.core.branding.is_valid_hex_color` (case-insensitive
predicate) and `normalize_hex_color` (validate then lowercase), as
`app.core.slug` does for the slug; the mirrored frontend `HEX_COLOR_PATTERN` is
the same pattern with the case-insensitive flag and **pre-validates only, never
lowercases**, so the server is the single normalisation point. A value that is
not `#` plus exactly six hex digits, an unknown or missing key, or an unknown
`mode`, reaches `TenantService` and returns 422 (`InvalidBrandThemeError`, an
ordinary `DomainError`).

## (b) The exposed variables

`index.css` declares 80 custom-property declarations (61 unique names).
Exposing all of them is wrong: 18 are the status and priority tokens, 2 are
`--destructive*`, and those are semantic — a "cancelled" chip must read as
cancelled in every condominium — and `--radius*` is not a colour. What remains
is the **17**-colour shadcn core of `:root`/`.dark`, and that is the whole of
what this task emits.

**Advanced mode authors 13 per scheme:**

`background`, `foreground`, `card`, `card-foreground`, `primary`,
`primary-foreground`, `secondary`, `secondary-foreground`, `accent`,
`accent-foreground`, `muted`, `muted-foreground`, `border`.

**4 more are derived inside the same scheme**, never asked for:
`popover` ← `card`, `popover-foreground` ← `card-foreground`, `input` ←
`border`, `ring` ← `primary`.

Total emitted per scheme: **13 + 4 = 17**. Untouched, in both modes:
`--destructive`, `--destructive-foreground`, the 10 status tokens, the 8
priority tokens, `--radius`.

## (c) Dark mode, per mode

- **Simple**: derived — the same `(L, C, H)` inputs with the dark lightness
  rule (`--primary` starts at `max(L, 0.62)`, `--secondary` likewise from the
  accent; the neutral family keeps the `.dark` defaults and takes the primary's
  hue) and its own contrast pass. No second input.
- **Advanced**: `dark` is **optional**.
  - `"dark": null` (the default the UI offers) → the dark scheme is produced by
    the **simple-mode dark derivation** fed with the authored `primary` and
    `accent`. Justification: no per-variable inversion of a hand-authored light
    palette can preserve either the tenant's intent or its contrast — inverting
    lightness turns a chosen off-white background into an arbitrary near-black
    the tenant never approved. Falling back to the one derivation this task
    already proves correct is the only option that keeps the guarantee.
  - `"dark": {…13 keys…}` → a full second palette, validated and **refused** by
    exactly the same 8-pair check as the light one.

Because `.dark` is declared but never applied today, neither branch is visible
until a dark-mode toggle ships. One consequence worth stating: a tenant who
authors a dark `--background` in advanced mode will keep the 18 status/priority
chips at their pale `:root` values (`.dark` never redeclares them today). They
stay internally legible, so this is not a refusal case, but it will look wrong
until those tokens get a dark variant.

## Derivation and measurement (`app/core/branding.py`, pure Python, no new dependency)

1. **Conversion, and the luminance trap.** hex → linear sRGB → OKLab → OKLCH.
   Clamp `C ≤ 0.22` and `L` into `[0.20, 0.92]` first — **this clamp applies
   only to the two simple-mode input colours**, so an extreme input still
   yields a usable hue; it is never applied to authored advanced-mode colours
   (see step 3). The inverse (OKLCH → linear sRGB) already yields
   **linear-light** channels, so **relative luminance is computed on them
   directly**; applying the sRGB→linear transfer a second time is a bug the
   tests must catch. Its direction is counter-intuitive and therefore
   dangerous: a double transfer does not halve ratios, it **inflates** them for
   light-on-light pairs — the shipped `--muted-foreground`/`--muted` pair reads
   **4.2913** correctly and **10.9585** under the bug, i.e. the bug makes
   illegible palettes *pass* and silently neutralises both the repair loop and
   the advanced-mode 422. Pinned by exact numbers in the test criteria (BF-7).
2. **Rounding, then gamut snapping — both before any measurement.**
   1. Every emitted component (`L`, `C`, `H`) is rounded to **2 decimal
      places**, the precision every value in `index.css` is authored at.
   2. Then `C` is **reduced on the same 0.01 grid until `(L, C, H)` is inside
      the sRGB gamut** (all three linear channels within `[0, 1]`, tolerance
      1e-4). Only then is anything measured, and the repair loop of step 5
      re-applies this snap after every step.

   *Why this is not a detail.* CSS Color 4 §13 requires a browser to gamut-map
   an out-of-range `oklch()` by chroma reduction at constant `L`/`H`, not by
   per-channel clipping — so an out-of-gamut string is painted as a colour
   nobody measured, and UAs differ. Measured over the emittable brand-surface
   lattice (`L ∈ [0.20, 0.92]` × 0.01 × `C ∈ [0, 0.22]` × 0.01 × `H` × 2°,
   light + dark = **604,440** derivations) under the *old* rule:
   **202,556 emitted colours out of gamut** and **1,791 pairs certified ≥ 4.5
   by the spec's own measurement but rendering below it**, worst
   `oklch(0.52 0.22 210)` on `oklch(0.15 0.02 210)` — measured **4.522**,
   rendered **3.741**. Reachable from real hex input (sRGB cube at stride 6,
   79,507 inputs): **3,381 out-of-gamut** and **3 inputs certified but
   illegible**, e.g. `#008a5a` → `oklch(0.56 0.13 160.15)` measured **4.5129**,
   rendered **4.498**. With the snap: **0 out-of-gamut, 0 rendered failures**,
   over both sweeps. This is the same defect *class* as round 1 — measuring
   something other than what the browser paints — and it is pinned with a sweep
   for the same reason.
3. **Scheme assembly (simple mode).** `H` is the primary's hue, `AH` the
   accent's, both at 2dp.

   | token | light | dark |
   |---|---|---|
   | `background` | `0.99 0 0` | `0.14 0.01 H` |
   | `card` | `1 0 0` | `0.16 0.01 H` |
   | `popover` | ← `card` | ← `card` |
   | `primary` | primary `(L, C)`, repaired | primary `(max(L,0.62), C)`, repaired |
   | `secondary` | accent `(L, C)`, repaired | accent `(max(L,0.62), C)`, repaired |
   | `accent` | `0.96 max(0.01, C_a×0.1) AH` | `0.22 max(0.02, C_a×0.2) AH` |
   | `muted` | `0.96 0.01 H` | `0.22 0.02 H` |
   | `border`, `input` | `0.92 0.01 H` | `0.25 0.02 H` |
   | `ring` | ← `primary` | ← `primary` |

   **The six foregrounds, per scheme, explicitly (BF-2).** The
   "better of `oklch(0.98 0 0)` and `oklch(0.15 0.02 H)`" rule governs **only
   the two brand surfaces**; every other foreground is a fixed default. Taken
   as a blanket rule it would make `--muted-foreground` near-black and delete
   muted text from the product, which is not intended.

   | foreground | light start | dark start |
   |---|---|---|
   | `foreground` | `0.14 0.01 H` | `0.98 0.01 H` |
   | `card-foreground` | `0.14 0.01 H` | `0.98 0.01 H` |
   | `popover-foreground` | ← `card-foreground` | ← `card-foreground` |
   | `primary-foreground` | better of `0.98 0 0` / `0.15 0.02 H` | same rule |
   | `secondary-foreground` | better of `0.98 0 0` / `0.15 0.02 AH` | same rule |
   | `accent-foreground` | `0.20 0.02 AH` | `0.98 0.01 AH` |
   | `muted-foreground` | `0.55 0.02 H`, repaired **down** | `0.65 0.02 H`, repaired **up** |

   Input is never trusted for a foreground in either case: the two computed
   ones are picked from two fixed candidates, the rest are constants.

   *Advanced mode*: the 13 authored colours, converted, rounded and
   gamut-snapped, plus the 4 in-scheme derivations. Nothing is adjusted.
   **Explicitly: step 1's clamp — on both `L` into `[0.20, 0.92]` and
   `C ≤ 0.22` — is a simple-mode-input rule and is not applied here.** An
   authored colour is emitted literally; only 2dp rounding and the gamut snap
   of step 2 touch it, and the snap is not an adjustment of intent but what
   makes the colour renderable at all. So authored `#7c3aed` emits
   `oklch(0.54 0.25 293.01)` (`#7c38ee`), not the clamped
   `oklch(0.54 0.22 293.01)` (`#7945df`).
4. **`audit_contrast(scheme) -> list[ContrastFailure]`**, the single
   measurement used by both modes. It parses the **emitted** `oklch(...)`
   strings back out and measures these **8 pairs** with the WCAG 2.1
   relative-luminance ratio: `foreground/background`, `card-foreground/card`,
   `primary-foreground/primary`, `secondary-foreground/secondary`,
   `accent-foreground/accent`, `muted-foreground/muted`,
   `muted-foreground/background`, `muted-foreground/card`. Non-text pairs
   (`border`, `input`, `ring` against their surfaces) are not measured; the
   3:1 non-text minimum is explicitly out of scope.
5. **Simple mode repairs; advanced mode refuses.**

   *Simple* — **which side moves is fixed per pair**, not inferred (BF-1):

   | pair | side that moves | direction | notes |
   |---|---|---|---|
   | `foreground` / `background` | — | — | both are constants; passes for every hue by construction, asserted never to repair |
   | `card-foreground` / `card` | — | — | idem |
   | `primary-foreground` / `primary` | `--primary` (non-text) | away from its foreground | foreground picked once, then held |
   | `secondary-foreground` / `secondary` | `--secondary` (non-text) | away from its foreground | idem |
   | `accent-foreground` / `accent` | `--accent` (non-text) | away from its foreground | the tint surface, not the brand one |
   | `muted-foreground` / `muted`, `/background`, `/card` | `--muted-foreground` (the **text** side) | down in light, up in dark | one token measured against three surfaces; the loop runs until it clears **all three**. The surfaces cannot move: `--background` and `--card` are page-level, and `--muted` is a neutral the tenant did not choose |

   Steps are 0.01 on the emittable grid, each followed by the gamut snap of
   step 2, at most 100 steps. The loop always converges: lightness 0 against
   white and 1 against black both reach 21:1. `audit_contrast` on the repaired
   scheme must return empty — that assertion, not the loop, is the guarantee.

   *Advanced*: a non-empty result is an `InsufficientContrastError` (422) whose
   body lists every failing pair, its measured ratio and the 4.5 minimum.
   Nothing is repaired and nothing is stored.
6. **`build_theme`.** `build_theme(None) is None`. Otherwise it returns
   `{"light": {...}, "dark": {...}}`, keys being CSS variable names **without**
   the leading `--`, values `oklch(L C H)` strings at 2dp.

**Measured guarantee for this revision.** Brand-surface family (the rule shared
by `--primary` and `--secondary`), same 604,440-derivation lattice as above,
measured **under CSS chroma-reduction mapping**: **0 failures**, worst
**4.500031**, **0 out-of-gamut emissions**; 202,556 of the 604,440 needed the
chroma snap. Neutral + accent-tint family (driven by hue × accent chroma, 8,280
schemes × 8 pairs): **0 failures**, worst **4.500239**. Hostile set
(`#ffe680`, `#ffffff`, `#000000`, `#808080`, `#0000ff`, `#10b981`, `#857046`,
`#0ea5e9`, `#7c3aed`) × itself × both schemes (162 schemes, 1,296 pairs):
**0 failures**, worst **4.5006**. Round 1's pin survives unchanged: `#857046`
has raw `L = 0.555`, which rounds to `0.56` and measures **4.4073**; the loop
steps once to `0.55`, emitting `oklch(0.55 0.06 83.88)` over `oklch(0.98 0 0)`
at **4.5959**.

### A finding about today's default

Measuring the shipped `index.css` values with the rule above,
`--muted-foreground` `oklch(0.55 0.02 160)` on `--muted` `oklch(0.96 0.01 160)`
is **4.2913** — already below AA today. This is not specific to hue 160: the
pair measures **4.290 – 4.350 across all 360 hues**, so it fails for **every**
hue and the `muted-foreground` loop therefore engages for **every** simple-mode
theme. Two consequences, both deliberate:

- Simple mode repairs it by moving the **text** side (per the table above),
  landing on `0.53` or `0.54` depending on hue — over 360 hues, `0.54` for 206
  and `0.53` for 154. A branded tenant's muted text is very slightly darker
  than an unbranded one's. That is the correct direction and the price of a
  real guarantee.
- **`index.css` is not edited by this task** — a tenant with no branding keeps
  exactly today's rendering, including this pair. Fixing the product default is
  a separate task; this spec records the measurement so it is not rediscovered.

## API

`TenantProfileRead` gains `brand_theme: BrandTheme | None` (the stored object,
normalised) and `theme: dict[str, dict[str, str]] | None` (derived on read,
never stored). `TenantProfileUpdate` gains `brand_theme: BrandTheme | None`:
absent leaves it alone (the `exclude_unset` shape `update_profile` already
uses), explicit `null` clears it. Same permission guard as the rest of the
writes. `BrandTheme` is a discriminated union on `mode`.

## Frontend

A render-nothing `TenantBrandTheme` mounted in `App` inside `TenantProvider`
reads the profile (only while authenticated) and writes a single
`<style id="tenant-brand-theme">` **appended to `document.head`**, after the
bundled stylesheet, holding `:root{…}` and `.dark{…}`; it removes the element
when `theme` is `null`. The injected rule and `index.css`'s `:root` have equal
specificity, so document order decides — the selector is written `:root:root{…}`
to win regardless, because Vite's dev HMR can re-inject the bundled stylesheet
after an element appended at mount. Because `["tenantProfile"]` is reset on a
tenant switch, switching condominium re-themes with no extra wiring.
`useTenantProfile` takes an optional `{ enabled }` so the injector does not fire
on the login screen.

The profile screen gains a "Cores da marca" section: a mode switch (Simples /
Avançado), two colour inputs in simple mode, the 13 inputs per scheme in
advanced mode with a "derivar o modo escuro" checkbox, a live contrast panel
listing each measured pair with its ratio, a save that reuses
`useUpdateTenantProfile` and is **disabled while any pair fails**, a "voltar ao
padrão" action sending `{brand_theme: null}`, a preview strip rendered from the
returned `theme`, and the 422 body mapped to per-pair messages. Switching
simple → advanced pre-fills the 13 inputs from the currently derived light
scheme, so nobody starts from a blank palette.

## Files touched

- `backend/app/core/branding.py` — new: colour conversion, the gamut predicate and chroma snap, WCAG ratio, `audit_contrast`, `build_theme`, the hex predicate/normaliser.
- `backend/app/core/exceptions.py` — `InvalidBrandThemeError`, `InsufficientContrastError` (both 422).
- `backend/app/models/tenant.py` — the nullable `brand_theme` JSON column.
- `backend/alembic/versions/0004_tenant_brand_theme.py` — new revision on `0003_tenant_invitation`.
- `backend/app/schemas/tenant.py` — `BrandTheme` union, the new read and update fields.
- `backend/app/services/tenant_service.py` — validate, measure, refuse or write in `update_profile`.
- `backend/app/api/v1/endpoints/tenant_profile.py` — build `theme` into the response (all four routes return the same body).
- `backend/tests/test_branding.py`, `backend/tests/test_tenant_profile.py`, `backend/tests/test_migrations_postgres.py` — see test criteria.
- `backend/tests/data/contrast_fixtures.json` — new: shared pairs + expected ratios, read by pytest and by vitest.
- `backend/scripts/assert_no_skips.py` — `MIN_CASES` re-pinned to the real collected count.
- `frontend/src/api/tenantProfile.ts` — types plus the mirrored `HEX_COLOR_PATTERN`.
- `frontend/src/lib/contrast.ts` — new: the ratio function and the gamut predicate only (no derivation).
- `frontend/src/hooks/useTenantProfile.ts` — optional `enabled`.
- `frontend/src/components/TenantBrandTheme.tsx` — new injector.
- `frontend/src/App.tsx` — mount it.
- `frontend/src/features/user-administration/pages/TenantProfilePage.tsx` — the two-mode colour section.
- `frontend/src/i18n/locales/{pt,en}.json` — `tenantProfile.brand.*`, key-identical.
- `frontend/src/components/__tests__/TenantBrandTheme.test.tsx`, `frontend/src/lib/__tests__/contrast.test.ts`, `frontend/src/features/user-administration/__tests__/TenantProfilePage.test.tsx` — tests.

## (d) Migration shape

`0004_tenant_brand_theme` — **an ordinary new revision**, never an edit to
`0001_initial_schema.py`; that rule expired when production applied `0001` on
2026-09-19. `down_revision = "0003_tenant_invitation"`, so the chain is
`0001 → 0002 → 0003 → 0004` with a single Alembic head.

*Why not `0003`.* `backend/alembic/versions/0003_tenant_invitation.py` already
exists in the worktree (APRAS-71, in flight) with
`down_revision = '0002_tenant_slug'`. A second revision chaining off `0002`
would be two heads: `alembic upgrade head` fails and
`test_migrations_postgres.py`'s `EXPECTED_HISTORY` stops being a single chain.
**APRAS-68 yields**, because APRAS-71's code is on disk and mid-implementation
while this task is still in spec review — a spec edit is cheaper than renaming
a written, tested migration. **Conditional clause**: if APRAS-71 has *not*
landed when this task is implemented, this becomes `0003_tenant_brand_theme`
with `down_revision = "0002_tenant_slug"`; APRAS-71's own D12 carries the
mirror-image clause, so the pair reconciles in either landing order.

The revision id `0004_tenant_brand_theme` is **23 characters**, inside
`alembic_version.version_num`'s hard `VARCHAR(32)`. `upgrade` is a single
`add_column("tenant", sa.Column("brand_theme", sa.JSON(), nullable=True))`;
`downgrade` drops it. No backfill, no server default, no data step. The module
**imports nothing from the `app` package** — and if a later change gives it a
helper, that helper is copied in as a frozen local literal exactly as `0001`
does for `DEFAULT_TENANT_ID` and `0002` does for `slugify`.

*Consequence for siblings:* APRAS-70, APRAS-71 and APRAS-73 refer in prose to
`0003_tenant_brand_color`. The id is now `0004_tenant_brand_theme`; those
specs' `down_revision` and `EXPECTED_HISTORY` lines are theirs to update when
next touched, and are not blockers here.

## (e) The no-colour case

`brand_theme IS NULL` → `GET /api/v1/tenant-profile` returns
`brand_theme: null, theme: null`, and the client injects **no element at all**
— not an empty `<style>`. The app renders today's `index.css` byte for byte,
including the 4.29 muted pair noted above. `PATCH {"brand_theme": null}`
returns any tenant to that state.

## (f) The `build_theme` contract APRAS-74 depends on

APRAS-74's expected results require that its `theme` be produced by calling
`app/core/branding.build_theme(...)`, with no second derivation anywhere and no
TypeScript port. **The contract is kept in every respect that matters**: same
module, same function name, same arity (one positional argument), same return
shape (`{"light": …, "dark": …}` or `None`), same status as the only derivation
in the codebase. The single change is the argument's type — the tenant's whole
branding object rather than a lone hex string. APRAS-74's spec never writes the
call site literally, so nothing there needs restructuring. The frontend's
`contrast.ts` is *not* a port of the derivation; it measures two given colours
and cannot produce a theme.

## Test criteria

- `test_branding.py`:
  - **Luminance regression, pinned by number** (this must fail loudly, because
    the double-gamma bug *inflates* ratios and its failure mode is otherwise
    silent): `contrast_ratio(oklch(0.55 0.02 160), oklch(0.96 0.01 160)) ==
    4.29 ± 0.01` (it reads **10.96** under a double transfer) and the WCAG
    canonical `#767676` on `#ffffff` `== 4.54 ± 0.01` (measured 4.5422).
  - **Gamut**: every colour in every emitted scheme satisfies the in-gamut
    predicate (all linear channels within `[0, 1] ± 1e-4`), so clipping,
    CSS §13 chroma-reduction mapping and rendering coincide; plus a direct
    case — the pre-snap triple `oklch(0.52 0.22 210)` on `oklch(0.15 0.02 210)`
    measures 4.52 but renders 3.74, and the snap must mean no emitted scheme
    can contain it — and `#008a5a` emits an in-gamut primary.
  - hex→OKLCH→hex round-trips within one 8-bit step; `build_theme(None) is
    None`; every emitted value matches `oklch(<=2dp> <=2dp> <=2dp>)`.
  - **Contrast is asserted by parsing the emitted strings out of
    `build_theme`'s output** — never by re-running internal floats. Simple
    mode: `audit_contrast` returns empty for the hostile set (`#ffe680`,
    `#ffffff`, `#000000`, `#808080`, `#0000ff`, `#10b981`, `#857046`,
    `#0ea5e9`, `#7c3aed`) × every accent in that set, in both schemes;
    `#857046` light is pinned at its exact emitted pair `oklch(0.55 0.06
    83.88)` over `oklch(0.98 0 0)` at 4.596, and `#0ea5e9` as accent is pinned
    at `--secondary` `oklch(0.68 0.14 237.32)` with `--secondary-foreground`
    `oklch(0.15 0.02 237.32)` at 6.96.
  - A lattice sweep (`L ∈ [0.20, 0.92]` at 0.01 × `C ∈ [0, 0.22]` at 0.01 ×
    `H` at 5°, both schemes) over the brand-surface rule asserts **0 failures**
    and **0 out-of-gamut emissions**; a second sweep over hue × accent chroma
    asserts the neutral and tint pairs never fail.
  - The `muted-foreground` repair is asserted to move the **text** side and the
    `primary`/`secondary`/`accent` repairs the **non-text** side, and
    `foreground/background` and `card-foreground/card` are asserted never to
    repair for any hue.
  - Advanced mode: a palette of black text on near-black background yields
    failures naming the exact pairs; a known good palette yields none.
    `normalize_hex_color("#FFE680") == "#ffe680"` and `build_theme` returns the
    identical map for the uppercase and lowercase objects. The emitted key set
    equals the 17 declared variables per scheme, and the accepted authored key
    set equals the 13 — no status, priority, destructive or radius token
    appears.
- `test_tenant_profile.py`: PATCH simple with uppercase hex returns 200 and the
  next GET returns lowercase plus a non-null `theme`
  (`test_patch_accepts_uppercase_hex_and_stores_lowercase`); PATCH advanced
  with a sub-4.5 pair returns **422** naming the pair and nothing is persisted
  (`test_advanced_palette_below_aa_is_refused_by_the_api`); PATCH advanced with
  `dark: null` returns a `theme` whose dark scheme equals the simple-mode dark
  derivation of the authored primary/accent; PATCH `{"brand_theme": null}`
  clears it and the next GET returns `brand_theme: null, theme: null`; `#GGG`,
  `red`, `#abc`, a 12-key advanced palette, an unknown key and an unknown
  `mode` each 422 (shape only, never case); a caller without
  `tenants:profile_update` gets 403; a rename alone leaves branding untouched.
- `test_migrations_postgres.py` against real PostgreSQL on 55432 (throwaway,
  UTF-8, never the dev database): `EXPECTED_HISTORY` gains
  `0004_tenant_brand_theme` after `0003_tenant_invitation` and remains a single
  chain, upgrade/downgrade/upgrade replays, the column exists nullable, a row
  inserted before the upgrade has `brand_theme IS NULL`. `assert_no_skips`'
  `MIN_CASES` equals the module's real collected count.
- `contrast.test.ts`: the TypeScript ratio function reproduces every entry of
  `backend/tests/data/contrast_fixtures.json` within 0.01 — the fixture
  includes the two pinned luminance numbers and at least one out-of-gamut
  triple, so a TS port that clips where Python snaps fails — and pytest asserts
  the same file against the Python helper.
- `TenantBrandTheme.test.tsx`: with `theme: null` **no** `#tenant-brand-theme`
  element is ever added; with a theme the element is the last child of
  `document.head`, its rules are `:root:root` and `.dark`, and it carries
  `--primary` and `--secondary`; clearing removes it.
- `TenantProfilePage.test.tsx`: the mode switch renders 2 inputs in simple and
  13 (+ the derive-dark checkbox) in advanced; a failing pair disables the save
  button and shows the pair's name and ratio; the API's 422 body renders even
  when the client check passed.
- Gates: pytest green at 90%, `ruff check`/`ruff format --check` clean,
  `tsc -b`, vitest 80/78/76/80, diff-scoped eslint against 375 errors + 2
  warnings, `pt.json`/`en.json` key-identical.

## Expected Results

- [ ] `PATCH /api/v1/tenant-profile` with `{"brand_theme": {"mode": "simple", "primary": "#FFE680", "accent": "#0EA5E9"}}` returns 200, and every later read returns the values normalised to lowercase and a non-null derived `theme`; a malformed hex, an unknown key or an unknown `mode` returns 422.
- [ ] `PATCH /api/v1/tenant-profile` with an advanced palette containing at least one text/background pair below 4.5:1 returns **422** listing each failing pair with its measured ratio, and a subsequent GET shows the tenant's branding unchanged — proven by a test that sends the request with no UI involved.
- [ ] The accent colour reaches the user at **full chroma** on `--secondary`/`--secondary-foreground`: accent `#0ea5e9` emits `--secondary: oklch(0.68 0.14 237.32)` (≈ `#23a3e3`) with `--secondary-foreground: oklch(0.15 0.02 237.32)` measured ≥ 6.9:1, asserted by a test; `--accent` remains the documented pale hover tint and `--ring` remains derived from `--primary`.
- [ ] Every emitted colour is inside the sRGB gamut: after 2dp rounding, `C` is reduced on the 0.01 grid until the triple is in gamut, before any measurement or repair, and a test asserts the in-gamut predicate holds for every token of every scheme in the lattice sweep — so measured and browser-rendered contrast coincide.
- [ ] Contrast is measured on the emitted, rounded, in-gamut `oklch(...)` strings parsed back out of `build_theme`'s output, never on internal floats: `#857046` in simple mode emits `oklch(0.55 0.06 83.88)` over `oklch(0.98 0 0)` at ≥ 4.5:1, and a lattice sweep of every emittable `(L, C, H)` reports 0 pairs below 4.5:1 in both light and dark.
- [ ] The repair loop moves the side the spec names for each pair: `--primary`, `--secondary` and `--accent` move (non-text side), `--muted-foreground` moves (text side) until it clears all three of `--muted`, `--background` and `--card`, and `foreground/background` and `card-foreground/card` never repair — asserted per pair by tests, and `--muted` is no longer a copy of `--secondary`.
- [ ] Simple mode stores exactly two colours and `audit_contrast` returns empty for all 8 measured pairs, in both light and dark, for every ordered pair of the hostile-input set; the tenant supplies no dark-mode input.
- [ ] Advanced mode accepts exactly the 13 documented keys per scheme (a 12-key body is a 422) and emits 17 CSS custom properties per scheme; a test asserts the emitted key set, so no `--destructive*`, status, priority or `--radius` token is ever overridden.
- [ ] Advanced mode emits authored colours literally: step 1's clamp on `L` and `C` is not applied to them, so an advanced palette whose `primary` is `#7c3aed` emits `--primary: oklch(0.54 0.25 293.01)`, which round-trips to `#7c38ee`, within one 8-bit step of the authored value — asserted by a test (a clamping implementation emitting `oklch(0.54 0.22 293.01)` / `#7945df` fails it).
- [ ] Advanced mode with `"dark": null` emits a dark scheme byte-identical to the simple-mode dark derivation of the same primary and accent; with `"dark"` supplied, the second palette passes the same 8-pair refusal check.
- [ ] Branding is stored in one nullable JSON column `tenant.brand_theme` created by a new ordinary revision `0004_tenant_brand_theme` whose `down_revision` is `0003_tenant_invitation` (or `0002_tenant_slug` as `0003_tenant_brand_theme` if APRAS-71 has not landed), leaving a single Alembic head, and which imports nothing from the `app` package; `0001_initial_schema.py` is unmodified in the diff.
- [ ] A luminance regression test pins `contrast_ratio(oklch(0.55 0.02 160), oklch(0.96 0.01 160)) == 4.29 ± 0.01` and `#767676` on `#ffffff` `== 4.54 ± 0.01`, so a double sRGB→linear transfer (which inflates these to 10.96) fails the suite.
- [ ] A tenant with no branding gets `brand_theme: null, theme: null` from `GET /api/v1/tenant-profile` and no `#tenant-brand-theme` element in the DOM at all, proven by a backend and a frontend test; `frontend/src/index.css` is unmodified in the diff.
- [ ] `app/core/branding.build_theme` remains the only theme derivation in the repository — one positional argument, returning `{"light": …, "dark": …}` or `None` — and `grep` finds no derivation in TypeScript; `frontend/src/lib/contrast.ts` contains the contrast ratio function and gamut predicate only, pinned against `backend/tests/data/contrast_fixtures.json` by both suites.
- [ ] The profile screen switches between simple and advanced, shows each measured pair's ratio live, and disables save while any pair is below 4.5:1; the API's 422 body is rendered when it arrives.
- [ ] Backend pytest green at the 90% gate with ruff clean and `MIN_CASES` re-pinned; frontend `tsc -b`, vitest (80/78/76/80) and diff-scoped eslint pass over the 375 + 2 baseline; `pt.json` and `en.json` stay key-identical.
