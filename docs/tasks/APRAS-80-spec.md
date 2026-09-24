# APRAS-80 — Migrate visitor-management components to semantic theme tokens

Child 3 of 8 of the APRAS-77 split. Round 2, re-specified from scratch against
the **amended** contract: APRAS-78's three artefacts as extended by APRAS-79
and amended by APRAS-88 at `c7c42fc`. This task **consumes** that contract and
may not extend it: no row added to `docs/frontend/theme-token-mapping.md`, no
new gap code, no token in `frontend/src/index.css`. Every call below is an
*application* of a published rule to a named call site.

**What the amendment changed for this child, in one sentence.** Brand **text**
now migrates to `*-primary-text` (5.2096 on `--card`, 4.6547 on `--accent`)
instead of `*-primary`, so the three sites that blocked round 1 go pass → pass,
the class still migrates, and this task needs **no** gap code, **no** ledger
row and **no** exceptions entry for any of them.

## Scope

`frontend/src/features/visitor-management/components` — the eight files
`AccessLogTimeline`, `AuthorizationFormModal`, `AuthorizationQrModal`,
`GatekeeperDashboard`, `GatekeeperEntryModal`, `QrScannerModal`,
`VisitorAuthPage`, `VisitorTable` — migrated from hard-coded Tailwind palette
classes to the tokens the table names, with every class left behind logged in
the ledger and excepted in the guard; then
`"src/features/visitor-management/components"` appended to
`MIGRATED_DIRECTORIES`.

Not covered: `visitor-management/hooks`, `visitor-management/__tests__`, any
other feature directory, `index.css`, the backend, the `.dark` block, and any
amendment to the mapping table, the ledger's rules or the guard's grammar.

**No mockup.** This is a token substitution. Every migrated pair is either
byte-identical in `:root` or a published, budgeted colour move already
tabulated in `docs/frontend/theme-token-mapping.md`; a `-mock.html` would
restate the stylesheet rather than show a new screen. The visible changes are
enumerated below under *What this proves, and what it misses*.

## The re-measurement

Measured now over the eight non-test files with the §3b grammar exactly as the
guard builds it (scale alternatives longest-first, both word boundaries,
opacity suffix):

| Figure | Value |
| --- | --- |
| Palette occurrences | **464** — the task's reported figure reproduces exactly |
| Distinct classes | 80 |
| Six-digit hex literals anywhere in the eight files | **0** |
| `dark:`-prefixed | **210** (45.3%), against **254** non-`dark:` |
| Per file | AuthorizationFormModal 132, GatekeeperDashboard 112, GatekeeperEntryModal 53, AccessLogTimeline 48, VisitorTable 44, VisitorAuthPage 41, AuthorizationQrModal 20, QrScannerModal 14 |

## Pairing a `dark:` class with its base

The settled rule: a `dark:` occurrence pairs with the class in the **same
class-context span**, with the **same utility prefix**, the **same non-`dark:`
variant chain**, **nearest preceding**. A `dark:` sibling of a migrated class
is deleted (§1g); a `dark:` sibling of a kept class is left and logged under
its base's code.

Applied here, **every one of the 210 `dark:` occurrences has a base** — there
is no orphan, unlike APRAS-79's single `UserLotAssignmentModal:149`.

The variant-chain clause changes the chosen base at exactly **four**
occurrences: `AuthorizationFormModal:218,229` `dark:bg-slate-800` (chain-base
`bg-white`, naive base `hover:bg-slate-50`) and `:253,279` `dark:bg-slate-800`
(chain-base `bg-slate-100`, naive base `hover:bg-slate-200`). **Their
disposition is unchanged**, because in all four both candidates migrate —
stated so a reviewer does not have to re-derive it. The clause is applied from
the start regardless; it is the rule, not a tiebreak.

## The disposition of all 464

| Disposition | n |
| --- | --- |
| Light class migrated to a token | **193** |
| `dark:` sibling of a migrated class, **deleted** (§1g) | **158** |
| Left untouched and logged | **113** (61 non-`dark:`, 52 `dark:`) |
| **Total** | **464** |

The two halves close independently: non-`dark:` 254 = 193 + 61, and `dark:`
210 = 158 + 52.

Per file, as `migrated / deleted / logged`:

| File | m / d / l |
| --- | --- |
| `AccessLogTimeline.tsx` | 11 / 9 / 28 |
| `AuthorizationFormModal.tsx` | 55 / 48 / 29 |
| `AuthorizationQrModal.tsx` | 9 / 8 / 3 |
| `GatekeeperDashboard.tsx` | 57 / 45 / 10 |
| `GatekeeperEntryModal.tsx` | 21 / 13 / 19 |
| `QrScannerModal.tsx` | 6 / 5 / 3 |
| `VisitorAuthPage.tsx` | 20 / 18 / 3 |
| `VisitorTable.tsx` | 14 / 12 / 18 |

The 113 occupy **84** distinct `(file, class)` pairs, which is the number of
exceptions entries this task appends.

**APRAS-88 moves none of these numbers.** It changes the *target* of five
occurrences, not whether they migrate.

## The gap codes, each counted from its own membership

| Code | Occ. | Derivation |
| --- | --- | --- |
| `GAP-TINT` | **61** | the status sets enumerated below: 9 + 4 + 4 + 6 + 6 + 6 + 6 + 4 + 4 + 4 + 6 + 2 |
| `GAP-OUT-OF-BUDGET` | **22** | `text-slate-700` 11 (`AccessLogTimeline:108,115`; `AuthorizationFormModal:140,208,218,229,239,265,298,309,323` — re-measured, exactly those lines) + their 11 `dark:text-slate-300` siblings |
| `GAP-BORDER-100` | **16** | `border-slate-100` 7 + `divide-slate-100` 1 + siblings `dark:border-slate-800` 5, `dark:border-slate-800/80` 2, `dark:divide-slate-800/80` 1 |
| `GAP-NO-TOKEN` | **6** | amber only: `AccessLogTimeline:98` check-out button (`bg-amber-600`, `hover:bg-amber-700`) 2 + `VisitorTable:33` `EXPIRED` badge (`bg-amber-50`, `text-amber-700`, `dark:bg-amber-950/50`, `dark:text-amber-400`) 4 |
| `GAP-OVERLAY` | **5** | `bg-black/40` modal scrims at `AuthorizationFormModal:113`, `AuthorizationQrModal:57`, `GatekeeperEntryModal:47`, `QrScannerModal:57`, `VisitorAuthPage:143`; no `dark:` siblings |
| `GAP-NO-SURFACE` | **3** | `AccessLogTimeline:56` `border-white` + its `dark:border-slate-900` sibling, over the dot's kept palette fill; `AccessLogTimeline:98` `text-white` over `bg-amber-600` |

Cross-check, reached from the other direction: the five non-`GAP-TINT` codes
hold 30 non-`dark:` and 22 `dark:` occurrences, so `GAP-TINT` holds 31 and 30
— 61 — and the totals 61 / 52 close. No `GAP-SWATCH` and no `GAP-UNLISTED`
occurrence exists here: this directory contains no chart series, no avatar
fill and no category-per-enum badge set. Every badge set in it encodes a
*status*, which is why they are `GAP-TINT` and `GAP-NO-TOKEN` rather than
code 2.

## Every status tint set in this directory, and the proof there is no other

The triple rule is binding tree-wide: a status variant's class set migrates as
a **unit or not at all**, every member must have a row in §1b–1e, and the
resulting foreground/background pair must hold ≥ 4.5:1. Sets 1 / 2+3, 6+7 and
each red pair below are the branches of **one** ternary each, so the rule is
applied to the whole ternary, not to a branch.

Every set below fails the "every member has a row" test, so all stay whole:

| # | Set | Members | n |
| --- | --- | --- | --- |
| 1 | `AccessLogTimeline:56–59` timeline status dot | base fill `bg-slate-100`; on-site branch `bg-emerald-100`/`text-emerald-600`/`dark:bg-emerald-950`/`dark:text-emerald-400`; left branch `bg-slate-100`/`text-slate-500`/`dark:bg-slate-800`/`dark:text-slate-400` | 9 |
| 2 | `AccessLogTimeline:78` On-Site badge (on-site branch) | `bg-emerald-50`, `text-emerald-700`, + 2 `dark:` | 4 |
| 3 | `AccessLogTimeline:82` Left badge (the *same* ternary's other branch) | `bg-slate-100`, `text-slate-600`, + 2 `dark:` | 4 |
| 4 | `AuthorizationFormModal:131` error alert | `border-red-200`, `bg-red-50`, `text-red-700`, + 3 `dark:` | 6 |
| 5 | `GatekeeperDashboard:159` scan-error alert | same shape | 6 |
| 6 | `GatekeeperEntryModal:65` + `:70` valid-access banner and its icon | `bg-emerald-50`, `text-emerald-800`, `text-emerald-600`, + 3 `dark:` | 6 |
| 7 | `GatekeeperEntryModal:66` + `:72` invalid-access banner and its icon | `bg-red-50`, `text-red-800`, `text-red-600`, + 3 `dark:` | 6 |
| 8 | `GatekeeperEntryModal:80` check-in error box | `bg-red-50`, `text-red-700`, + 2 `dark:` | 4 |
| 9 | `VisitorTable:26` `ACTIVE` badge | `bg-emerald-50`, `text-emerald-700`, + 2 `dark:` | 4 |
| 10 | `VisitorTable:40` `REVOKED` badge | `bg-red-50`, `text-red-700`, + 2 `dark:` | 4 |
| 11 | `VisitorTable:119` revoke control | `text-red-600`, `border-red-200`, `hover:bg-red-50`, + 3 `dark:` | 6 |
| 12 | `VisitorAuthPage:144` revoke-dialog red border | `border-red-200`, `dark:border-red-900/50` | 2 |

**The rowless member of each.** `bg-emerald-50` (sets 2, 6, 9),
`bg-emerald-100` (set 1), `bg-red-50` (4, 5, 7, 8, 10), `border-red-200` (4, 5,
11, 12), `text-emerald-800` (6), `text-red-800` (7), `hover:bg-red-50` (11).
**Re-checked against the amended §1e**, which gave `text-emerald-600`,
`text-emerald-700` and `text-red-700` rows they did not have in round 1: no
set's verdict moves, because every one of them is still blocked by a
background or border class with no row. Set 3 stays only because it is a
branch of set 2's ternary — read on its own, both its members now have rows,
and a child reading branch-by-branch would wrongly split the badge.

Two further sets are status sets in a family with **no** token, so §1h's
precedence sends them to code 3 rather than code 4, and they stay for the same
reason: `VisitorTable:33` `EXPIRED` badge (4) and `AccessLogTimeline:98`
check-out button (2 + 1 `GAP-NO-SURFACE`).

**The proof there is no thirteenth.** A split set is, by construction, a
class-context span holding both a migrated occurrence and a kept `GAP-TINT`
occurrence. Running that check mechanically over all 464 occurrences grouped
by `(file, span)` returns **exactly one** span: `VisitorAuthPage:144`, which
holds `border-red-200` (kept) beside `bg-white` (migrated to `bg-card`) and
`dark:bg-slate-900` (deleted). That is **not** a split set and is APRAS-79's
precedent #5 applied unchanged: the panel's surface is neutral white and takes
its §1f case 1 row, the panel's red border has no row and stays, and the red
**foreground** for that panel lives on a different element (`:145`) over
`--card`, so it is free-standing and migrates. Every other span is
homogeneous. The implementer must re-run that check and get the same single
span.

## Behaviour — the substitutions

Every substitution is a table row applied verbatim.

- `bg-white` ×32 → **`bg-card`** — §1f case 1, settled below.
- `text-slate-900` ×31 → `text-foreground`.
- `border-slate-200` ×18 → `border-border`; `divide-slate-200` ×1 → `divide-border`.
- `border-slate-300` ×16 → `border-input`.
- `text-slate-400` ×15 → `text-muted-foreground` (the operator-named move); `text-slate-500` ×14; `text-slate-600` ×11.
- **Indigo ×27, split by §1k** — see the next section: 5 → `*-primary-text`, 22 → `primary` / `accent` / `border`.
- Emerald ×6 → `bg-primary` / `hover:bg-primary/90` — §1f case 3, settled below.
- `text-white` ×6 → `text-primary-foreground`; the seventh is a gap.
- Neutral fills ×14: resting `bg-slate-100` ×2 and `bg-slate-50` ×2 → `bg-muted`; interaction `hover:bg-slate-100` ×4, `hover:bg-slate-50` ×3, `hover:bg-slate-50/50` ×1, `hover:bg-slate-200` ×2 → `hover:bg-accent` / `hover:bg-accent/50` — §1f case 2, settled below.
- `text-red-600` ×2 → `text-destructive` — the free-standing sites only (`AuthorizationQrModal:73`, `VisitorAuthPage:145`).

`32 + 31 + 19 + 16 + 40 + 27 + 6 + 6 + 14 + 2 = 193`.

**Opacity modifiers are carried over verbatim**, never dropped and never
rounded to a different `N`: `bg-indigo-50/50` → `bg-accent/50`,
`hover:bg-slate-50/50` → `hover:bg-accent/50`, `text-indigo-600/80` →
`text-primary-text/80`, and `hover:bg-*-700` → `hover:bg-primary/90` per §1i's
named target. This is the only move that adds no row: §1i says any `*/N`
target measures against the base token with the alpha declared **unmeasured**.
`themeTokenCompile.test.ts` asserts §1b–1e's class pairs and does **not** cover
these composites — said plainly rather than implied.

Each of the 193 takes its `dark:` sibling with it: **158 deletions**. The three
emerald `<Button>` fills and the one indigo `<Button>` fill carry no `dark:`
sibling at all.

## §1k applied — which of the 15 indigo text occurrences are characters

§1k asks one question per call site, from the JSX, with no measurement: *does
this element paint glyphs of text?* Traced at every site, not assumed:

**Graphical — keeps `text-primary`, floor 3:1 (10 occurrences, all
`text-indigo-600`).** Each is an icon component with **no children**, the
self-closing shape §1k names explicitly:

| Site | Icon | Surface traced from the JSX | `--primary` on it |
| --- | --- | --- | --- |
| `AuthorizationFormModal:117` | `ShieldCheck` | modal panel `bg-white` → `--card` | 3.4054 |
| `AuthorizationQrModal:61` | `QrCode` | modal panel `bg-white` → `--card` | 3.4054 |
| `QrScannerModal:61` | `ScanLine` | modal panel `bg-white` → `--card` | 3.4054 |
| `GatekeeperDashboard:170` | `Search` | card `bg-white` → `--card` | 3.4054 |
| `GatekeeperDashboard:240` | `History` | card `bg-white` → `--card` | 3.4054 |
| `GatekeeperDashboard:266` | `PackageIcon` | card `bg-white` → `--card` | 3.4054 |
| `GatekeeperDashboard:305` | `PackageIcon` | card `bg-white` → `--card` | 3.4054 |
| `GatekeeperDashboard:129` | `Building2` | page shell — the component roots at `<div className="space-y-6">`, so `--background` | 3.3091 |
| `VisitorAuthPage:58` | `ShieldCheck` | page shell, same | 3.3091 |
| `GatekeeperDashboard:145` | `Users` | the counter card's `bg-indigo-50` → `bg-accent` | **3.0427** |

The icons at `:129`, `:58`, `:170`, `:240`, `:266`, `:305` and
`AuthorizationQrModal:61` / `QrScannerModal:61` sit **inside** an `<h1>`/`<h2>`
that does render text — but that heading carries `text-slate-900`, not the
brand class. §1k is asked of *the element carrying the class*, and that element
is the icon. The mixed-element clause is for one element painting both, which
is `AuthorizationFormModal:146` below.

**Characters — take `text-primary-text`, floor 4.5:1 (5 occurrences).**

| Site | Class → target | Why it is text | Surface | Today → after |
| --- | --- | --- | --- | --- |
| `AuthorizationFormModal:146` | `text-indigo-600` → `text-primary-text` | `<button>` rendering `<UserPlus/>` **and** `{t(...)}` from one `currentColor` — the mixed-element clause | `--card` | 6.4414 → **5.2096** |
| `AuthorizationFormModal:217` | `text-indigo-700` → `text-primary-text` | `<button>` whose child is `{t("authorizations.single")}` | `bg-indigo-50` → `--accent` | 7.2164 → **4.6547** |
| `AuthorizationFormModal:228` | `text-indigo-700` → `text-primary-text` | `<button>` whose child is `{t("authorizations.permanent")}` | `--accent` | 7.2164 → **4.6547** |
| `GatekeeperDashboard:147` | `text-indigo-700` → `text-primary-text` | `<div>` whose child is `{activeLogs.length}` | `--accent` | 7.2164 → **4.6547** |
| `GatekeeperDashboard:150` | `text-indigo-600/80` → `text-primary-text/80` | `<div>` whose child is `{t("gatekeeper.activeVisitorsCount")}` | `--accent` | 4.0551 → **3.2883** (composited; §1i measures the base row at 4.6547) |

**All four full-opacity text sites pass AA after the migration**, which is
exactly the deadlock APRAS-88 cleared. The `/80` site is the one exception and
is read below.

**`text-emerald-500` does not occur in this directory**, so §1a's fourth named
move is not exercised here. The four `text-emerald-[67]00` occurrences that do
exist are all inside status sets 1, 2, 6 and 9 and stay under the triple rule,
so their new §1e rows change nothing.

**The remaining 22 indigo occurrences are non-`text-` utilities and are
graphical by §1k, always:** `bg-indigo-600` ×3 → `bg-primary`;
`hover:bg-indigo-700` ×1 → `hover:bg-primary/90`; `border-indigo-600` ×2 →
`border-primary` (on `--accent`, 3.0427 ≥ 3); `bg-indigo-50` ×3 → `bg-accent`
and `bg-indigo-50/50` ×1 → `bg-accent/50`; `border-indigo-100` ×2 →
`border-border`, taking its explicit §1e row over `GAP-BORDER-100` per the
appendix's † note. The remaining 10 are the graphical `text-indigo-600` above.
`10 + 5 + 12 = 27`.

## The context-dependent cases, settled at the real call sites

**The verification tests cannot detect a wrong choice in any of the three.** In
cases 1 and 2 both candidates are byte-identical in `:root` and differ only
under a tenant theme; in case 3 both candidates are legal classes. All three
are a **human review duty on this diff**.

**§1f case 1 — `bg-white`.** All 32 take **`bg-card`**; zero take
`bg-background`, zero take `bg-popover`. Neither page component declares a page
background — `VisitorAuthPage` and `GatekeeperDashboard` both root at
`<div className="space-y-6">` inside the app shell — so this directory contains
no page shell and no floating popover layer. Sixteen are card, panel, modal or
table surfaces (`AccessLogTimeline:39,70`; `AuthorizationFormModal:114,218,229`;
`AuthorizationQrModal:58`; `GatekeeperDashboard:168,238,264,303`;
`GatekeeperEntryModal:48`; `QrScannerModal:58`; `VisitorAuthPage:72,111,144`;
`VisitorTable:51`). Sixteen are form-control fills — every `<input>`,
`<select>` and `<textarea>` at
`AuthorizationFormModal:161,170,177,186,194,305,316,330`,
`GatekeeperDashboard:182,201,276,286,344`, `GatekeeperEntryModal:122`,
`VisitorAuthPage:80,97` — and a field **sits on** its panel rather than being
the page, so the rule's own test gives `bg-card`, which also keeps the field
flush with its panel exactly as today.

**§1f case 2 — `bg-muted` versus `bg-accent`.** Four resting fills take
`bg-muted`: the unselected day/shift chips at `AuthorizationFormModal:253,279`
(`bg-slate-100`, unprefixed), the visitor-detail panel at
`GatekeeperEntryModal:86` and the `<thead>` at `VisitorTable:53` (both
`bg-slate-50`). Ten interaction fills take `bg-accent`: the four modal close
buttons (`AuthorizationFormModal:124`, `AuthorizationQrModal:66`,
`GatekeeperEntryModal:55`, `QrScannerModal:66`), the two unselected chips'
`hover:bg-slate-200`, the two unselected auth-type buttons' `hover:bg-slate-50`
at `:218,229`, the hovered search result at `GatekeeperDashboard:210`, and the
hovered table row at `VisitorTable:72` (`hover:bg-slate-50/50` →
`hover:bg-accent/50`). The remaining three `bg-slate-100`
(`AccessLogTimeline:56,59,82`) are not case-2 fills at all — they belong to
status sets 1 and 3.

**§1f case 3 — emerald 500–700.** The band holds **10** non-`dark:`
occurrences here. **Six migrate**, all interactive `<Button>` fills:
`GatekeeperEntryModal:131` (confirm check-in), `GatekeeperDashboard:225`
(check in a searched visitor) and `:350` (confirm package pickup), each
`bg-emerald-600 hover:bg-emerald-700` → `bg-primary hover:bg-primary/90`, with
their `text-white` → `text-primary-foreground`. **Four stay**, all
non-interactive status glyphs or badge text inside sets 1, 2, 6 and 9:
`AccessLogTimeline:58`, `:78`, `GatekeeperEntryModal:70`, `VisitorTable:26`.
A further five emerald occurrences are resolved by scale alone and need no
judgement (`bg-emerald-50` ×3, `bg-emerald-100`, `text-emerald-800`), plus nine
`dark:` siblings.

The three migrated `<Button>`s carry no `variant` prop, so their className
becomes byte-identical to the `default` variant they already render — the same
outcome the pilot recorded for `button.tsx`'s `success` variant, and correct
rather than a bug. **Substitute in place; do not delete the now-redundant
className**, which would be a markup change rather than a colour change.

## Contrast, re-derived by importing `frontend/src/lib/contrast.ts`

Measured by importing `contrastRatio` and `parseOklch` from
`frontend/src/lib/contrast.ts` — never reimplemented — with token values read
from `src/index.css` and palette values read from
`node_modules/tailwindcss/theme.css` (**Tailwind 4's OKLCH palette**, not a
hard-coded v3 hex list; the v3 hexes are off by up to 0.07 and would not
reproduce APRAS-78). The measurement reproduces APRAS-78's published figures to
the digit — `text-red-700` on `bg-red-50` 5.9842, `--muted-foreground` on
`--muted` 4.6684, `--primary-foreground` on `--primary` 5.7588 — which is the
check that it is the same measurement.

| Pair | Background | Today | After |
| --- | --- | --- | --- |
| Body heading `text-slate-900` → `text-foreground` | `--card` | 17.8448 | **19.8801** |
| Secondary text `text-slate-500` → `text-muted-foreground` | `--card` | 4.7670 | **5.2249** |
| Loading text `text-slate-500` → `text-muted-foreground` | `--background` | 4.6322 | **5.0771** |
| Table head `text-slate-500` on `bg-slate-50` → `text-muted-foreground` on `bg-muted` | `--muted` | 4.5540 | **4.6684** |
| Unselected chip `text-slate-600` on `bg-slate-100` → `text-muted-foreground` on `bg-muted` | `--muted` | 6.8989 | **4.6684** |
| Revoke-dialog heading `text-red-600` → `text-destructive` | `--card` | 4.8619 | **4.8073** |
| QR error `text-red-600` → `text-destructive` | `--card` | 4.8619 | **4.8073** |
| Check-in / pickup buttons `text-white` on `bg-emerald-600` → `text-primary-foreground` on `bg-primary` | `--primary` | 3.7194 | **5.7588** — repairs an AA failure |
| Package button `text-white` on `bg-indigo-600` → `text-primary-foreground` on `bg-primary` | `--primary` | 6.4414 | **5.7588** |
| **New-visitor link `text-indigo-600` → `text-primary-text`** | `--card` | 6.4414 | **5.2096** |
| **Selected auth-type chip `text-indigo-700` → `text-primary-text`** ×2 | `--accent` | 7.2164 | **4.6547** |
| **Counter number `text-indigo-700` on `bg-indigo-50` → `text-primary-text` on `bg-accent`** | `--accent` | 7.2164 | **4.6547** |
| **Counter label `text-indigo-600/80` → `text-primary-text/80`** | `--accent` | 4.0551 | **3.2883** |

Kept pairs, measured so the ledger's `why` can state them and so nobody later
attributes them to this migration: `text-slate-500` on `bg-slate-100` (timeline
dot glyph) **4.3481**, `text-emerald-600` on `bg-emerald-100` (dot, on-site)
**3.2766**, `text-white` on `bg-amber-600` (check-out button) **3.1884** — all
three already below AA today and all three kept unchanged. Passing kept pairs:
`text-emerald-700` on `bg-emerald-50` 5.1582, `text-emerald-800` on
`bg-emerald-50` 7.2679, `text-red-700` on `bg-red-50` 5.9842, `text-red-800` on
`bg-red-50` 7.6659, `text-amber-700` on `bg-amber-50` 4.8611, `text-slate-600`
on `bg-slate-100` 6.8989.

### The gatehouse reading — what "passes AA" hides

`GatekeeperDashboard`, `QrScannerModal` and `VisitorAuthPage` are used at a
gatehouse, on a phone or tablet, often in daylight. Three results must be read
with that in mind rather than filed as "passes":

1. **The active-visitor counter now passes, and only just.**
   `GatekeeperDashboard:147` is `text-2xl font-black` — the single most-read
   number on the gatehouse screen. Under the old contract it would have gone to
   3.0427; under §1k it goes to **4.6547**, which clears the normal-text floor
   by 0.15 and the large-text floor by 1.65. This is the amendment doing its
   job. It is still the *tightest* full-opacity pair this task produces, and
   because `--primary-text` is re-derived per tenant with **no cushion** — the
   derivation stops at the first passing 0.01 step, worst case 4.5000 over
   APRAS-88's lattice sweep — a tenant brand can land this number at exactly
   4.50 in daylight. That is APRAS-88's property, not this child's defect, but
   it is where it will first be *seen*.
2. **The counter's label at `:150` still fails AA, and this task makes it
   worse.** `text-indigo-600/80` on `bg-indigo-50` measures **4.0551** today
   and `text-primary-text/80` on `bg-accent` measures **3.2883** — a
   pre-existing failure worsened by 0.77. §1i declares the alpha unmeasured, so
   the *contract's* row is `--primary-text` on `--accent` at 4.6547 and the
   migration is mandatory; the composite is what a person at the gate actually
   reads. Under the old contract it would have been 2.3635, so the amendment
   improves it by 0.92 while leaving it sub-AA. **Recommendation to the
   operator: open one follow-up, "drop the `/80` from brand text on a brand
   tint", scoped tree-wide** — it is a one-token deletion per site that takes
   this pair to 4.6547, but deleting a modifier is a markup change and §1i
   forbids this child from making it. Do not block this child on it.
3. **The `Users` glyph in that same card sits at 3.0427.** `--primary` on
   `--accent` clears the 1.4.11 graphical floor of 3:1 by **0.043**, and for a
   pale tenant brand it does not clear it at all (APRAS-88 §1k records pale
   yellow on `--card` at 1.2617). §1k routes it there deliberately and records
   this as APRAS-68 behaviour predating APRAS-77 and needing its own task. This
   child changes the class and must not be read as having introduced the
   number.

## The guard suite — what changes

Re-read against the file as it stands at `13d4276`, because **round 1's
description of this suite is stale**: APRAS-79 replaced the shared
`expect(PINNED).toHaveLength(18)` literal with a derived total
(`perDirectory.reduce(...)`), so **there is no shared count for this child to
bump**. The changes are:

1. `MIGRATED_DIRECTORIES` gains `"src/features/visitor-management/components"`.
2. `describe("MIGRATED_DIRECTORIES") › "pins every non-test source file…"`
   gains one `toContain`
   (`src/features/visitor-management/components/GatekeeperDashboard.tsx`),
   matching the two already there.
3. A new **appended, directory-scoped** `describe("APRAS-80's ledger
   arithmetic")`, in the shape APRAS-79 established: this directory's 8 pinned
   files, its 113 ledger rows, its 84 exception pairs, its six gap-code counts,
   and the twelve status sets still whole. **No child's existing block is
   edited**, and no assertion inside the pilot's or APRAS-79's block changes.

### Whether the shape still scales

Measured now: the suite runs **41 tests in 416 ms** with 170 exceptions over 18
files. The cost is dominated by `it("fails when any single exception is
removed")`, which calls `violations()` once per exception; the scan memo lives
inside `violations()`, so each call re-scans every pinned file — `O(exceptions
× files)` scans, 3,060 today and ≈6,600 after this child.

**This child does not refactor it.** The memo is shared helper code every
sibling depends on, and 2.2× of 416 ms is nowhere near the 5 s per-test
timeout. What this child owes instead: **report the suite's measured wall time
after the change**, and if any single test exceeds **2 s**, hoist the memo to
module scope keyed on `file + "\0" + source` (still a pure function of its
arguments, so the mutated-argument tests keep biting) in the same PR and say
so. Child 4 re-checks; this spec does not claim the shape is final, and by
child 8's ~3,000 exceptions over ~111 files it will not be.

## Files touched

- The eight `frontend/src/features/visitor-management/components/*.tsx`, per the `migrated / deleted / logged` table.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — the directory entry, one `toContain`, and the new scoped `describe`.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — **84** new entries, `src/`-relative, `task` `APRAS-80`.
- `docs/frontend/unmapped-colours.md` — **113** appended rows, one per kept occurrence, sorted by file then line, plus a closing `APRAS-80 total` paragraph in the shape APRAS-78's and APRAS-79's use. Nothing already in the file is rewritten.
- `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts` — new.

## Test criteria

1. `npx vitest run src/__tests__/themeTokenMigration.test.ts` green with the new directory pinned: zero unexcused grammar matches across the eight files, no stale exception, no unknown code, ledger parity in both directions, the pilot's own 24 and APRAS-79's own 211 untouched, and the new block's 113.
2. The new contrast test asserts, by **importing** `contrastRatio` and `parseOklch` from `src/lib/contrast.ts`, that every foreground/background pair this task changes either holds ≥ `MINIMUM_CONTRAST_RATIO` or appears in an explicit in-file list of declared sub-AA pairs carrying its measured before/after ratio. Ratios to ±0.001 against the table above, each against its declared background. Token values are read from `src/index.css` and palette values from `node_modules/tailwindcss/theme.css`; no colour literal is hard-coded in the test. The `/80` composite and the three kept pre-existing failures are **declared, not hidden**. The graphical pairs are asserted against the 3:1 floor, the four full-opacity text pairs against 4.5.
3. `src/features/visitor-management/__tests__/` — `GatekeeperDashboard.test.tsx`, `AuthorizationFormModal.test.tsx`, `AuthorizationQrModal.test.tsx`, `QrScannerModal.test.tsx` and `VisitorAuthPage.test.tsx` pass **unmodified**. They prove the components still render and behave; none asserts on a class name, so none proves a colour.
4. `npx tsc -b` clean.
5. `npx vitest run --coverage` meets exactly **80 lines / 78 functions / 76 branches / 80 statements**.
6. `npx eslint` diff-scoped. Re-measured now: the repository carries **375 errors + 2 warnings across 64 files**, and **the eight touched files carry 6 errors across 3 files** — `AuthorizationFormModal.tsx` 3, `GatekeeperDashboard.tsx` 2, `GatekeeperEntryModal.tsx` 1. The touched-file figure is the criterion; the feature directory's test files are not touched and are not it.
7. `git diff --exit-code frontend/src/index.css` succeeds; `docs/frontend/theme-token-mapping.md` is byte-unchanged; no backend file, no Alembic revision, no route-registry entry in the diff; the `.dark` block stays unapplied.

## What this proves, and what it misses

**Proved.** Every substitution is a §1b–1e row, and `themeTokenCompile.test.ts`
already asserts each row's ΔL/ΔE from the compiled stylesheet to ±0.1,
including the nine §1k rows APRAS-88 retargeted. The guard certifies nothing
was dropped or silently substituted: each of the 464 is either gone from the
file or present in **both** the ledger and the exceptions file. The contrast
test certifies the pairs that change.

**Not proved, stated plainly.** Five things.

- No Playwright, no Storybook, no Chromatic, no Percy, and jsdom does not run
  the Tailwind pipeline: **no pixel and no computed-style proof**, and adding
  that infrastructure is out of scope.
- **The three §1f cases and every §1k verdict are invisible to every test
  here.** `bg-card` versus `bg-background` and `bg-muted` versus `bg-accent`
  are byte-identical in `:root`; a wrong emerald verdict yields a legal class
  either way; and `text-primary` versus `text-primary-text` on an icon is two
  legal classes that differ only in a tenant theme and in a ratio nothing
  compiles. The 32 `bg-white`, the 14 neutral fills, the 10 emerald band
  occurrences and the 10-graphical / 5-text indigo split settled above are a
  **review duty on this diff**, not a covered behaviour.
- The rendering *does* move where the table says it moves: `text-slate-400` →
  `text-muted-foreground` at 15 sites (named), the indigo hue shift at 27,
  `text-slate-600` lightening at 11, `border-slate-300` → `border-input` at 16.
  Named and `noted` budget rows, accepted.
- The **158 deleted `dark:` siblings** change nothing today, because `.dark` is
  never applied — which is why deleting them is untestable here. What changes
  is what the future dark-mode task inherits, alongside the 52 `dark:` classes
  kept.
- **The guard cannot enforce per-site completeness**, because the exceptions
  file carries no line number. Several `(file, class)` pairs are migrated at
  some sites and kept at others in the same file — `AccessLogTimeline.tsx`
  `text-slate-500`, `text-slate-600`, `bg-slate-100` and
  `dark:text-slate-400`, `GatekeeperEntryModal.tsx` `text-red-600`,
  `VisitorTable.tsx` `text-red-600` — and once excused, an unmigrated
  occurrence of that pair anywhere in that file passes. **The same hole now
  exists in the other direction:** `AuthorizationFormModal.tsx`
  `text-indigo-600` migrates to `text-primary` at `:117` and to
  `text-primary-text` at `:146`, and nothing mechanical distinguishes a
  correct split from a wrong one. The disposition table (193 / 158 / 113, with
  the per-file split), the twelve-set inventory and the §1k site table are what
  a reviewer must check the diff against.

## Out of scope

Adding `--success` / `--warning` / `--info` tokens; dropping the `/80` from
brand text on a brand tint (the follow-up recommended above); the 1.4.11
graphical floor for pale tenant brands (APRAS-88 §1k's own named follow-up);
APRAS-87's repo-wide §1k sweep of the 38 `text-primary` occurrences already in
the tree; enabling the `.dark` block; visual-regression infrastructure; any
other feature directory; and any amendment to APRAS-78's mapping table, ledger
rules or grammar.

## Expected Results

- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts` passes with `MIGRATED_DIRECTORIES` containing `"src/features/visitor-management/components"`, `pinnedFiles()` returning the directory's 8 source files, and `violations(PINNED, EXCEPTIONS, LEDGER)` returning `[]`.
- [ ] Re-measuring the eight files with the §3b grammar accounts for all 464 baseline occurrences as 193 migrated + 158 deleted `dark:` siblings + 113 left and logged, both halves closing independently (254 non-`dark:` = 193 + 61; 210 `dark:` = 158 + 52), and the files retain exactly 113 matches and zero six-digit hex literals.
- [ ] `docs/frontend/unmapped-colours.md` gains 113 `APRAS-80` rows — 61 `GAP-TINT`, 22 `GAP-OUT-OF-BUDGET`, 16 `GAP-BORDER-100`, 6 `GAP-NO-TOKEN`, 5 `GAP-OVERLAY`, 3 `GAP-NO-SURFACE`, and zero `GAP-SWATCH` and zero `GAP-UNLISTED` — and `themeTokenMigration.exceptions.json` gains 84 `APRAS-80` entries, with the guard's parity check passing in both directions.
- [ ] The five text-bearing indigo sites carry `text-primary-text`: `AuthorizationFormModal:146`, `:217`, `:228`, `GatekeeperDashboard:147` and `:150` (as `text-primary-text/80`, the `/80` preserved verbatim); the ten icon-only sites carry `text-primary` (`AuthorizationFormModal:117`, `AuthorizationQrModal:61`, `QrScannerModal:61`, `GatekeeperDashboard:129,145,170,240,266,305`, `VisitorAuthPage:58`); and no `text-primary-text` appears on any non-`text-` utility anywhere in the diff.
- [ ] `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts` passes, importing `contrastRatio` and `parseOklch` from `src/lib/contrast.ts` and reading every colour from `src/index.css` and `node_modules/tailwindcss/theme.css` with no hard-coded literal, asserting to ±0.001 that `--primary-text` on `--card` is 5.2096 and on `--accent` 4.6547, `--primary-foreground` on `--primary` 5.7588, `--destructive` on `--card` 4.8073, `--muted-foreground` on `--muted` 4.6684, and `--primary` on `--accent` 3.0427 against the 3:1 graphical floor; and declaring as sub-AA-by-decision the `/80` composite 4.0551 → 3.2883 plus the three unchanged pre-existing failures 4.3481, 3.2766 and 3.1884.
- [ ] All twelve status sets stay whole: `AccessLogTimeline:56-59,78,82`, `AuthorizationFormModal:131`, `GatekeeperDashboard:159`, `GatekeeperEntryModal:65,66,70,72,80`, `VisitorTable:26,40,119` and `VisitorAuthPage:144` still carry their original classes, each with a ledger row, and grouping every occurrence by class-context span shows exactly one span that mixes a migrated occurrence with a kept occurrence whose ledger gap code is `GAP-TINT` — `VisitorAuthPage:144`, where kept `border-red-200` sits beside migrated `bg-card`. (Spans mixing a migrated occurrence with a kept occurrence carrying any other gap code — e.g. `AccessLogTimeline:106` `GAP-BORDER-100`, `AuthorizationFormModal:218` `GAP-OUT-OF-BUDGET` — are expected and are not counted by this check.)
- [ ] The pilot's and APRAS-79's own blocks still hold unedited: `describe("the pilot's own ledger arithmetic")` reports 24, `describe("APRAS-79's ledger arithmetic")` reports 211 rows and 148 exception pairs, and no APRAS-78 or APRAS-79 ledger row or exceptions entry is modified.
- [ ] No `dark:` sibling of a migrated base survives anywhere in the eight files: zero `dark:text-white`, `dark:bg-slate-900`, `dark:border-slate-700`, `dark:text-indigo-400`, `dark:text-indigo-300`, `dark:bg-indigo-*`, `dark:border-indigo-*`, `dark:divide-slate-800` or `dark:hover:bg-slate-800*` remains, and none appears in the ledger.
- [ ] `git diff --exit-code frontend/src/index.css` and `git diff --exit-code docs/frontend/theme-token-mapping.md` both succeed, and the diff contains no backend file, no Alembic revision and no route-registry change.
- [ ] `npx tsc -b` completes with no error.
- [ ] `npx vitest run --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint` over the eight touched component files reports at most the 6 errors across 3 files present today (`AuthorizationFormModal.tsx` 3, `GatekeeperDashboard.tsx` 2, `GatekeeperEntryModal.tsx` 1), and the repository total stays at 375 errors + 2 warnings across 64 files.
- [ ] The five existing `src/features/visitor-management/__tests__/*.test.tsx` suites pass without modification, and `npx vitest run src/__tests__/themeTokenMigration.test.ts` completes with every individual test under 2 s (baseline: 41 tests in 416 ms) and its measured wall time reported in the implementation report.
