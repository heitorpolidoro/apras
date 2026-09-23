# APRAS-79 — Migrate lot-management components to semantic theme tokens

Child 2 of 8 of the APRAS-77 split. This task **consumes** the three artefacts
APRAS-78 published at `1538bf6` and may not extend any of them: it adds no row
to `docs/frontend/theme-token-mapping.md`, no gap code, no token to
`frontend/src/index.css`. Where this spec makes a call, it is an *application*
of a published rule to a named call site, never a new rule. The one exception
is the guard's own **test suite**, which cannot accept a second pinned
directory without three assertions being rewritten; that rewrite is specified
below, in a form the six following children reuse without re-deciding it.

## Scope

`frontend/src/features/lot-management/components` — the nine files
`LinkUserAccountModal`, `LotDetailsView`, `LotFormModal`, `LotTable`,
`LotsPage`, `ResidentFormModal`, `ResidentTable`, `ResidentsTab`,
`UserLotAssignmentModal` — migrated from hard-coded Tailwind palette classes to
the semantic tokens the table names, with every class left behind logged in the
ledger and excepted in the guard; then
`"src/features/lot-management/components"` appended to `MIGRATED_DIRECTORIES`.

Not covered: `lot-management/hooks`, `lot-management/__tests__`, any other
feature directory, `index.css`, the backend, the `.dark` block, and any
amendment to the mapping table, the ledger's rules or the guard's grammar.

## The re-measurement

Measured at `1538bf6` with the §3b grammar exactly as the guard builds it
(scale alternatives longest-first, both word boundaries, opacity suffix), over
the nine non-test `.tsx` files:

| Figure | Value |
| --- | --- |
| Palette occurrences | **520** — the task's reported figure reproduces exactly |
| Distinct classes | 92 |
| Six-digit hex literals in a class context | **0** |
| `dark:`-prefixed occurrences | **236** (45.4%), against **284** non-`dark:` |
| Per file | LotDetailsView 120, ResidentTable 82, ResidentFormModal 75, LotTable 54, LotFormModal 45, UserLotAssignmentModal 45, LinkUserAccountModal 37, ResidentsTab 34, LotsPage 28 |

This directory is therefore the **first real exercise of §1g's `dark:` rule**,
which the pilot could not test at all (`src/components/ui` has zero `dark:`
occurrences), and the first real exercise of **§1f case 2**.

## Pairing a `dark:` class with its base

§1g's two halves both key on *the base class*, so the pairing rule has to be
stated before any count is: a `dark:` occurrence pairs with the **nearest
preceding class in the same `className` span that has the same utility prefix
and the same non-`dark:` variant chain**. The variant chain is what makes it
correct, and getting it wrong is worth eight occurrences here. In

```
border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700
  dark:text-slate-400 dark:hover:text-slate-300
```

`dark:text-slate-400`'s chain is empty, so its base is `text-slate-500`
(migrated → **deleted**), *not* `hover:text-slate-700`; and
`dark:hover:text-slate-300`'s chain is `hover`, so its base is
`hover:text-slate-700` (a gap → kept). Likewise every
`dark:border-slate-700` in this directory pairs with `border-slate-300`, which
§1c migrates — never with the `focus:border-blue-500` that precedes it in the
same span.

On that rule, **235 of the 236** `dark:` occurrences have a base. Exactly one
does not: `UserLotAssignmentModal.tsx:149`'s `dark:bg-slate-800`, on a checkbox
with no light `bg-` class. Neither half of §1g reaches it, so it is left and
logged (code below).

## The disposition of all 520

| Disposition | n |
| --- | --- |
| Light class migrated to a token | **166** |
| `dark:` sibling of a migrated class, **deleted** (§1g) | **143** |
| Left untouched and logged | **211** (118 non-`dark:`, 93 `dark:`) |
| **Total** | **520** |

Per file, as `migrated / deleted / logged`:

| File | m / d / l |
| --- | --- |
| `LinkUserAccountModal.tsx` | 16 / 10 / 11 |
| `LotDetailsView.tsx` | 38 / 33 / 49 |
| `LotFormModal.tsx` | 9 / 9 / 27 |
| `LotTable.tsx` | 19 / 19 / 16 |
| `LotsPage.tsx` | 13 / 10 / 5 |
| `ResidentFormModal.tsx` | 27 / 27 / 21 |
| `ResidentTable.tsx` | 18 / 14 / 50 |
| `ResidentsTab.tsx` | 15 / 11 / 8 |
| `UserLotAssignmentModal.tsx` | 11 / 10 / 24 |

The 211 occupy **148** distinct `(file, class)` pairs, which is the number of
exceptions entries this task appends (the ledger keeps one row per occurrence;
the exceptions file has no line number, so it keys on the pair).

## The gap codes, each derived from its own membership

Each figure below is counted from the membership named beside it. The total is
what the six produce, not a target they were fitted to: **58 + 49 + 38 + 46 +
12 + 8 = 211**, which is the same 211 the disposition table reaches from the
other direction, 520 − 166 − 143.

| Code | Occ. | Derivation |
| --- | --- | --- |
| `GAP-SWATCH` | **58** | `getAssocBadge` 4 branches (`LotDetailsView` 57, 63, 69, 75) × 5 classes per branch (`bg-*`, `text-*`, `ring-*`, `dark:bg-*`, `dark:text-*`) = 20; `getRelationshipBadge` 6 branches (`ResidentTable` 30, 36, 42, 48, 54, 60) × 5 = 30; the two avatar circles (`LotDetailsView:225`, `ResidentTable:107`) × 4 = 8 |
| `GAP-OUT-OF-BUDGET` | **49** | `text-slate-700` 22 + `hover:text-slate-700` 2 + their `dark:` siblings (`dark:text-slate-300` 22, `dark:hover:text-slate-300` 2) + the single orphan `dark:bg-slate-800` |
| `GAP-TINT` | **46** | 4 red tint triples × 4 (`bg-red-50`, `text-red-6/700`, `dark:bg-red-*`, `dark:text-red-400`) = 16; 3 confirm-dialog `border-red-200` + `dark:border-red-900/50` = 6; 3 emerald `OCCUPIED`/`is_active` status badges × 4 = 12; the `inactive` slate badge `ResidentTable:155` × 4; `LinkUserAccountModal:98` selection fill × 2; `ResidentTable:125` linked-user chip × 6 |
| `GAP-NO-TOKEN` | **38** | blue: 7 focus classes (`focus:border-blue-500` 6, `focus:ring-blue-500` 1) + 8 in the `VACANT` badges + 3 checkbox accents = 18; amber: 12 in the `UNDER_CONSTRUCTION` badges + 6 `Unlink` icon classes + 2 on the warning dialog's border = 20 |
| `GAP-BORDER-100` | **12** | `border-slate-100` 5 + `divide-slate-100` 1 + `dark:border-slate-800` 5 + `dark:divide-slate-800` 1 |
| `GAP-OVERLAY` | **8** | `bg-black/40` 6 + `bg-black/50` 2 — modal scrims, no `dark:` siblings |

No `GAP-NO-SURFACE` and no `GAP-UNLISTED` occurrence exists here. The
amber and blue members of the badge sets above are `GAP-NO-TOKEN` and **not**
`GAP-SWATCH`, because they are status badges rather than category badges — the
distinction is drawn in the judgement calls below.

## Behaviour — the substitutions

Every substitution is a table row applied verbatim. Published ΔE in brackets.

- `bg-white` ×30 → **`bg-card`** [0.00] — §1f case 1, settled below.
- `text-slate-900` ×31 → `text-foreground` [8.20].
- `text-slate-500` ×21 → `text-muted-foreground` [5.77].
- `text-slate-600` ×14 of 18 → `text-muted-foreground` [9.76]; the other 4 are gaps.
- `text-slate-400` ×10 → `text-muted-foreground` [18.02] — the **one operator-named move** present in this directory.
- `border-slate-200` ×15 → `border-border` [1.94]; `divide-slate-200` ×3 → `divide-border` [1.94].
- `border-slate-300` ×17 and `hover:border-slate-300` ×2 → `border-input` / `hover:border-input` [5.66].
- `bg-slate-50` ×3 of 5 → `bg-muted`; `hover:bg-slate-50` ×4 → `hover:bg-accent` [2.61] — §1f case 2, settled below.
- emerald 500–700 ×7 of 25 → `primary` / `ring-ring` — §1f case 3, settled below.
- red ×9 of 20 → `destructive` — the free-standing sites only; §1j governs the rest.

Each of those 166 takes its `dark:` sibling with it. The six
`dark:border-slate-700` at `LotFormModal:197,215`, `LotsPage:161,174`,
`UserLotAssignmentModal:107,126`, the seventh at `UserLotAssignmentModal:149`,
and the two `dark:text-slate-400` at `LotDetailsView:166,177` are **deletions**,
not gaps — they are named here because the naive pairing rule misfiles exactly
those eight.

`LotFormModal.tsx:96,220`, `UserLotAssignmentModal.tsx:75,182` and
`LotDetailsView.tsx:99` keep `border-slate-100` (`GAP-BORDER-100`), so their
`dark:border-slate-800` siblings stay too, under the same code.

## The context-dependent cases, settled at the real call sites

**§1f case 1 — `bg-white`.** All 30 take **`bg-card`**; zero take
`bg-background` and zero take `bg-popover`, because this directory contains no
page shell and no floating popover layer. Fourteen are card, modal-panel or
table surfaces (`LinkUserAccountModal:58`, `LotTable:56,63`,
`LotDetailsView:98,189,277`, `LotFormModal:95`, `ResidentsTab:138,176,198`,
`ResidentFormModal:93`, `ResidentTable:73`, `UserLotAssignmentModal:74`,
`LotsPage:237`). Sixteen are form-control fills (every `<input>`, `<select>`
and `<textarea>` in `LinkUserAccountModal:80`, `LotFormModal:197,215`,
`ResidentsTab:125`, `LotsPage:161,174`,
`ResidentFormModal:114,129,141,156,166,187,199,213`,
`UserLotAssignmentModal:107,126`): a field **sits on** the surface it is drawn
against, it is not the page, so the rule's own test gives `bg-card`, which is
also what keeps the field flush with its surroundings exactly as today.
Fourteen of the sixteen sit on a modal panel; the two filter controls at
`LotsPage:161,174` sit directly on the page rather than on a panel, and take
`bg-card` all the same — it is the ΔE 0.00 target for `bg-white`, where
`bg-background` would flatten them into the page they are drawn on.

**§1f case 2 — `bg-muted` versus `bg-accent`.** Three resting fills take
`bg-muted`: the `<thead>` of `LotTable:65`, `LotDetailsView:202` and
`ResidentTable:75`. Four interaction fills take `bg-accent`:
`LinkUserAccountModal:97` (the selectable user row), `LotDetailsView:222`,
`LotTable:97` and `ResidentTable:104` (hovered table rows). The remaining
`bg-slate-50` ×2 and `bg-slate-100` ×2 are not case-2 fills at all — they
belong to the badge and avatar sets below.

**§1f case 3 — emerald 500–700 as brand or as status.** Seven migrate, all
interactive:

| Site | From | To |
| --- | --- | --- |
| `LotDetailsView:165` and `:176` — active tab `<button>` | `border-emerald-600 text-emerald-600` | `border-primary text-primary` |
| `LinkUserAccountModal:107` — `<input type="radio">` | `text-emerald-600 focus:ring-emerald-500` | `text-primary focus:ring-ring` |
| `ResidentTable:191` — `LinkIcon` inside the link-account `<Button>` | `text-emerald-600` | `text-primary` |

Eighteen stay: ten `GAP-TINT` (the `OCCUPIED` / `is_active` status badges at
`LotDetailsView:116`, `LotTable:39`, `ResidentTable:154`; the selected-row fill
`LinkUserAccountModal:98`, whose `bg-emerald-50` §1f case 3 resolves by scale
without judgement; and the linked-user chip `ResidentTable:125`) and eight
`GAP-SWATCH`.

**These three choices are invisible to every test in this task** and remain a
human review duty. `bg-card` versus `bg-background`, and `bg-muted` versus
`bg-accent`, are byte-identical in `:root` and differ only under a tenant
theme; a wrong emerald verdict yields a legal class either way.

## The judgement calls this spec settles, with the rule each applies

1. **The two category-badge functions are `GAP-SWATCH` (§1h code 2), whole.**
   `LotDetailsView.getAssocBadge` (branch `className`s on lines 57, 63, 69, 75)
   and `ResidentTable.getRelationshipBadge` (30, 36, 42, 48, 54, 60) assign one
   hue per enum value — purple, pink, blue, emerald, amber, slate. That is a
   *category swatch*, which code 2 names, and code 2 precedes `GAP-NO-TOKEN`,
   `GAP-TINT` and `GAP-OUT-OF-BUDGET`. Consequence, recorded so it is not
   reported later as a defect: **the "Proprietário / Inquilino / Cônjuge"
   badges never follow the tenant brand**, and the `slate` default branch keeps
   `bg-slate-50 text-slate-600 ring-slate-500/10` even though §1b would migrate
   `bg-slate-50` elsewhere — migrating one member of a swatch set would make
   exactly one category follow the brand.
2. **The two avatar circles are `GAP-SWATCH`** — `LotDetailsView:225`
   (`bg-slate-100 text-slate-600`) and `ResidentTable:107` (`bg-emerald-100
   text-emerald-800`). Code 2 names avatar fills by name.
3. **The status badges are not swatches.** `LotStatus` and `is_active` encode a
   *status*, so the operator's status ruling applies with §1h's precedence:
   emerald and slate members are `GAP-TINT` (code 4 — the token exists and is
   withheld), blue and amber members are `GAP-NO-TOKEN` (code 3 — no token
   exists). Both forbid migration equally.
4. **Red: the triple's verdict governs (§1j), not the §1e row.** Four sites
   repeat the exact form §1j warns about — `LinkUserAccountModal:67`,
   `ResidentFormModal:99` (`bg-red-50 … text-red-600`), `LotFormModal:112`,
   `UserLotAssignmentModal:91` (`bg-red-50 … text-red-700`). They are the only
   four: `bg-red-50` occurs exactly four times in the directory. The surface is
   `GAP-TINT` and cannot move, so **the text does not move either**.
5. **Free-standing red migrates.** Six `text-red-600` — the `Trash2` icons at
   `LotDetailsView:261`, `LotTable:165`, `ResidentTable:201` and the
   confirm-dialog headings at `LotDetailsView:278`, `LotsPage:238`,
   `ResidentsTab:177` — and three `text-red-500` page-level error messages
   (`LotDetailsView:40`, `LotsPage:190`, `ResidentsTab:109`) become
   `text-destructive`. The dialog headings sit on a `bg-white` panel, not on a
   red tint, so they are free-standing in §1j's sense; the panel's
   `border-red-200` stays, because it has no row and a border is not a member
   of the foreground/background pair the ≥ 4.5:1 clause measures. **The ledger
   `why` for those three `border-red-200` rows must say exactly that** — that
   the pair it appears beside was judged free-standing and measured at
   4.8073:1 — so a later reader does not reopen it as a fifth triple.
6. **The orphan `dark:` class.** `UserLotAssignmentModal.tsx:149`'s
   `dark:bg-slate-800` is left and logged under `GAP-OUT-OF-BUDGET` (code 7):
   every target §1b offers for a surface at that role — `bg-muted`,
   `bg-foreground` — exceeds ΔE 12 against `slate-800`, and no operator
   decision names the move. `GAP-UNLISTED` is not used: it is reserved for code
   written after APRAS-78.

## Contrast, re-derived by importing `frontend/src/lib/contrast.ts`

Measured by importing `contrastRatio` and `parseOklch` from
`frontend/src/lib/contrast.ts` — never reimplemented. The measurement
reproduced APRAS-78's five published figures to the digit (5.9842, 4.4006,
4.4506, 4.6684, 5.7588), which is the check that it is the same measurement.

**Every row below names one background**, and every "today"/"after" pair is
measured against that same background.

| Pair | Background | Today | After |
| --- | --- | --- | --- |
| Confirm-dialog heading `text-red-600` → `text-destructive` | `--card` | 4.8619 | **4.8073** |
| Page error text `text-red-500` → `text-destructive` | `--background` | 3.7118 | **4.6713** — repairs an AA failure |
| Page loading text `text-slate-500` → `text-muted-foreground` | `--background` | 4.6322 | **5.0771** |
| Red tint triples, kept: `text-red-700` on `bg-red-50` | `bg-red-50` | 5.9842 | 5.9842 — unchanged; migrating the text alone gives 4.4006 and fails |
| Red tint triples, kept: `text-red-600` on `bg-red-50` | `bg-red-50` | 4.4506 | 4.4506 — pre-existing AA failure, §1j says explicitly it is not this task's to fix |
| Body text `text-muted-foreground` | `--card` / `--muted` | — | 5.2249 / 4.6684 |
| **Active tab `text-emerald-600` → `text-primary`** | `--background` | **3.6142** | **3.3091** — both fail AA; see the recorded decision |

The three page-error sites (`LotDetailsView:40`, `LotsPage:190`,
`ResidentsTab:109`) are bare `<div className="p-8 text-center text-red-500">`
blocks in the page flow, siblings of the table and the cards, with no panel of
their own. **They sit on `--background`**, not on a card, and the same holds
for the three `text-slate-500` loading blocks beside them. That is the
call-site ruling the ±0.001 assertions below are written against; 3.8199 is the
same class on `--card` and is not a figure this directory uses.

**The same tracing applies to the active tab, and revision 2 of this spec
corrects it.** The tab label sits in the nav at `LotDetailsView:158`
(`border-b border-border`, no fill), inside the component root at
`LotDetailsView:81` (`space-y-6`, no fill), rendered at `LotsPage:93` inside
`LotsPage:92` (`container mx-auto max-w-7xl px-4 py-8`, no fill). The nearest
ancestor that paints anything is `App.tsx:86`/`:112`, which is
`bg-background` — there is **no `bg-card` in that chain**. The call-site
figures are therefore **3.6142 → 3.3091**. The 3.7194 → 3.4054 this spec
carried through review round 1 is the same pair measured against `--card`, a
surface the label does not sit on; it is kept in the test as a labelled
reference figure so APRAS-87's justification, which quotes it, stays traceable.
`--background` is `oklch(0.99 0 0)` and `--card` is `oklch(1 0 0)`, which is
why the two differ at all.

## Recorded decision — the active tab (not an open question)

`LotDetailsView`'s active tab label is `text-sm font-semibold` — not WCAG large
text — and fails AA **today** at 3.6142:1 on the `--background` it actually
sits on. §1f case 3 mandates its migration (a `<button>` is interactive) and
§1j's ≥ 4.5:1 clause does not reach it (it is not a status tint triple), so the
migration carries that pre-existing failure to 3.3091:1 at two sites. (Measured
against `--card`, the same pair reads 3.7194 → 3.4054; that is the figure this
spec quoted before its background was traced, and it is not the call site.)

**The operator has decided: migrate and record.** The repair is owned by
**APRAS-87 — "Raise the active-tab label contrast, which fails WCAG AA"**,
which is on the board and is where a fix belongs, because fixing it means
changing `--primary` in `index.css`, which no child of APRAS-77 may touch.

The decision establishes a precedent that binds the six remaining children:
**no child may except a pair from migration on the ground that migrating makes
it worse.** The obligation is to migrate what the table mandates, measure the
pair with `contrast.ts`, and declare the number — not to invent a local
exception, which would require a gap code a child may not add.

## The guard suite — what actually changes

`MIGRATED_DIRECTORIES` gains one entry, but the **suite around it cannot stay
as shipped**: three assertions are written against a single pinned directory
and fail the moment a second appears. All three are rewritten so that they are
derived from `MIGRATED_DIRECTORIES` rather than from a hard-coded path, which
is what makes them survive the remaining six children and APRAS-85's inversion
unchanged.

1. `describe("MIGRATED_DIRECTORIES") › "is seeded with exactly src/components/ui"`
   — `toEqual(["src/components/ui"])` becomes a containment plus a uniqueness
   assertion: the list **contains** `"src/components/ui"` and
   `"src/features/lot-management/components"`, and has no duplicate entry. The
   test is renamed to say it holds every directory a child has pinned. Each
   later child appends one `toContain`, and nothing else.
2. `describe("MIGRATED_DIRECTORIES") › "pins every non-test source file in that directory"`
   — the predicate `file.startsWith("src/components/ui/")` becomes *every
   pinned file starts with one of `MIGRATED_DIRECTORIES`*, with the recursion
   marker stripped. Written that way it never needs editing again. The
   existing `toContain("src/components/ui/button.tsx")` stays and is joined by
   `toContain("src/features/lot-management/components/LotTable.tsx")`; the
   assertion that no `*.test.tsx` is pinned stays as is. With both entries,
   `pinnedFiles()` returns **18** files — but that total is asserted
   **derivationally, never as the literal 18**: a sibling test sums
   `pinnedFiles([entry])` over `MIGRATED_DIRECTORIES` and asserts `PINNED` has
   exactly that length, plus that no entry pins zero files. The derived form is
   strictly stronger than the literal — it catches an entry that pins nothing,
   and because `pinnedFiles()` de-duplicates through a `Set`, equality with the
   sum is also an assertion that no two entries overlap — and unlike the
   literal it is not per-child churn: it survives all six remaining children
   and APRAS-85's inversion unedited. Each child asserts **its own**
   directory's file count inside its own scoped `describe`; APRAS-79 asserts
   **9**.
3. `describe("the pilot's own ledger arithmetic") › "leaves 24 of the pilot's 31 palette occurrences in place"`
   — `remaining` is computed over all of `PINNED`, so it measures **544** today
   and would never be 24 again. It becomes **pilot-scoped**, filtering `PINNED`
   by `src/components/ui/` exactly as the `pilot` ledger variable in the same
   `describe` already does. APRAS-78's arithmetic then stays true forever and
   is never touched by a later child.

APRAS-79 then adds **one new sibling `describe` block**, scoped the same way —
"APRAS-79's ledger arithmetic" over rows whose file starts with
`src/features/lot-management/components/` — asserting 211 ledger rows, the
per-code figures 58 / 49 / 38 / 46 / 12 / 8, and 211 remaining grammar matches
in that directory. **That is the precedent**: one scoped `describe` per child,
appended; no child edits another child's block.

## Files touched

- The nine `frontend/src/features/lot-management/components/*.tsx`, per the
  `migrated / deleted / logged` table above.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — the
  `MIGRATED_DIRECTORIES` entry, the three assertion rewrites, and the new
  scoped `describe`.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — **148** new
  entries, one per distinct `(file, class)` pair, `src/`-relative, `task`
  `APRAS-79`. Eleven pairs play two roles in one file (e.g. `ResidentTable.tsx`
  `bg-emerald-50` is a swatch at :48 and a tint at :125); each such entry
  carries the code §1h precedence puts first, which is `GAP-SWATCH` in all
  eleven.
- `docs/frontend/unmapped-colours.md` — **211** appended rows, one per kept
  occurrence with its own per-site code, sorted by file then line, plus a
  closing `APRAS-79 total` line in the shape APRAS-78's uses. Nothing already
  in the file is rewritten.
- `frontend/src/features/lot-management/__tests__/lotManagementContrast.test.ts`
  — new; the contrast assertions below.

## Test criteria

1. `npx vitest run src/__tests__/themeTokenMigration.test.ts` green with the
   new directory pinned: zero unexcused grammar matches across the nine files,
   no stale exception, no unknown code, ledger parity in both directions, the
   pilot's own arithmetic still 24, and the new scoped block's 211.
2. The new contrast test asserts, by **importing** `contrastRatio` and
   `parseOklch` from `src/lib/contrast.ts`, that every foreground/background
   pair this task changes either holds ≥ `MINIMUM_CONTRAST_RATIO` or appears in
   an explicit in-file list of pre-existing sub-AA pairs carrying its measured
   before/after ratio — so the active-tab pair is declared rather than hidden,
   and any future pair that drops below AA fails loudly. Ratios are asserted to
   ±0.001 against the contrast table above, each against its declared
   background.
3. `src/features/lot-management/__tests__/LotsPage.test.tsx` and
   `ResidentsTab.test.tsx` pass unchanged. Neither asserts on a class name, so
   what they prove is that the components still render and behave — not that
   the colours are unchanged.
4. `npx tsc -b` clean.
5. `npx vitest run --coverage` meets exactly **80 lines / 78 functions / 76
   branches / 80 statements**.
6. `npx eslint` diff-scoped. Re-measured at `1538bf6`: the repository carries
   **375 errors + 2 warnings across 64 files**, and **the nine touched files
   carry 4 errors across 3 files** — `LinkUserAccountModal.tsx` 1,
   `LotFormModal.tsx` 1, `ResidentFormModal.tsx` 2. (The feature directory's
   12 errors across 5 files include its two untouched test files, which this
   task does not touch and which are not the criterion.)
7. `git diff --stat frontend/src/index.css` empty; no backend file, no Alembic
   revision, no route-registry entry in the diff; the `.dark` block stays
   unapplied.

## How this proves the default theme did not change — and what that misses

**What is proved.** Every substitution above is a row of §1b–1e, and
`frontend/src/__tests__/themeTokenCompile.test.ts` already asserts each of
those rows' ΔL/ΔE from the compiled stylesheet to ±0.1, so the colour each
class becomes is certified. The guard certifies that nothing was dropped or
silently substituted: every one of the 520 is either gone from the file or
present in both the ledger and the exceptions file. The contrast test certifies
the foreground/background pairs that actually change.

**What is not proved, stated plainly.** Four things.

- There is no Playwright, no Storybook, no Chromatic, no Percy, and jsdom does
  not run the Tailwind pipeline, so there is **no pixel and no computed-style
  proof**, and adding that infrastructure is out of scope. "The rendering is
  unchanged" is an argument from published ΔE figures, not a measurement of
  this directory's rendering.
- The rendering *does* move where the table says it moves. The largest move is
  the named one, `text-slate-400` → `text-muted-foreground` at 10 sites
  (ΔE 18.02); `text-slate-600` → `text-muted-foreground` lightens by ΔE 9.76 at
  14 sites, and `border-slate-300` → `border-input` lightens form borders by
  ΔE 5.66 at 19. These are `noted` and `named` budget rows, accepted by the
  operator decision, not regressions.
- The **143 deleted `dark:` siblings** change nothing today, because `.dark` is
  never applied — which is exactly why deleting them is untestable here. What
  they change is what the future dark-mode task inherits, alongside the 93
  `dark:` classes this task leaves in place.
- **The guard cannot enforce per-site completeness.** The exceptions file has
  no line number by design, so for the **12** `(file, class)` pairs that are
  migrated at some sites and kept at others in the same file — `bg-slate-50`
  and `text-slate-600` in both `LotDetailsView.tsx` and `ResidentTable.tsx`,
  plus eight `dark:` classes — once the pair is excused, an unmigrated
  occurrence of it anywhere in that file passes. The disposition table
  (166 / 143 / 211, with the per-file split) is what a reviewer must check the
  diff against; the guard alone cannot.

## Out of scope

Adding `--success` / `--warning` / `--info` tokens; migrating the 7 blue focus
classes (the operator note keeps focus rings blue by default); raising the
active tab to AA (**APRAS-87**); enabling the `.dark` block; visual-regression
infrastructure; any other feature directory; and any amendment to APRAS-78's
mapping table, ledger rules or grammar.

## Expected Results

- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts` passes with `MIGRATED_DIRECTORIES` containing both `"src/components/ui"` and `"src/features/lot-management/components"`, and `violations()` returning an empty array. `pinnedFiles()` returns 18 files (9 + 9), but the suite asserts that total **derivationally and not as a literal**: the child-agnostic test sums `pinnedFiles([entry])` over `MIGRATED_DIRECTORIES`, asserts `PINNED` has exactly that length and that no entry pins zero files, while `describe("APRAS-79's ledger arithmetic")` asserts its own directory pins **9**. A literal `18` is blind to an entry that pins nothing and to two entries overlapping, and would have to be edited by each of the six remaining children.
- [ ] Re-measuring the nine files with the §3b grammar accounts for all 520 baseline occurrences as 166 migrated + 143 deleted `dark:` siblings + 211 left and logged, and the files retain exactly 211 matches.
- [ ] `docs/frontend/unmapped-colours.md` gains 211 `APRAS-79` rows — 58 `GAP-SWATCH`, 49 `GAP-OUT-OF-BUDGET`, 46 `GAP-TINT`, 38 `GAP-NO-TOKEN`, 12 `GAP-BORDER-100`, 8 `GAP-OVERLAY` — and `themeTokenMigration.exceptions.json` gains 148 `APRAS-79` entries, with the guard's parity check passing in both directions.
- [ ] The pilot's own assertions still hold after the rewrite: `describe("the pilot's own ledger arithmetic")` reports 24 ledger rows and 24 remaining matches scoped to `src/components/ui/`, and no APRAS-78 ledger row or exceptions entry is modified.
- [ ] `git diff --exit-code frontend/src/index.css` succeeds, and the diff contains no backend file, no Alembic revision and no route-registry change.
- [ ] `frontend/src/features/lot-management/__tests__/lotManagementContrast.test.ts` passes, importing `contrastRatio` from `src/lib/contrast.ts`, asserting to ±0.001 that `text-destructive` holds 4.8073:1 on `--card` and 4.6713:1 on `--background` (against 3.7118:1 for `text-red-500` on the same background), and declaring the active-tab pair's 3.6142 → 3.3091 on the `--background` its ancestry is traced to as a pre-existing sub-AA pair owned by APRAS-87, with 3.7194 → 3.4054 kept beside it as the labelled `--card` reference figure.
- [ ] The four red tint triples at `LinkUserAccountModal:67`, `ResidentFormModal:99`, `LotFormModal:112` and `UserLotAssignmentModal:91` still carry their original `bg-red-50` / `text-red-[67]00` classes, each with a ledger row.
- [ ] No `dark:border-slate-700` and no `dark:text-slate-400` paired with a migrated base survives: `LotFormModal:197,215`, `LotsPage:161,174`, `UserLotAssignmentModal:107,126,149` and `LotDetailsView:166,177` carry none of them, and none appears in the ledger.
- [ ] `npx tsc -b` completes with no error.
- [ ] `npx vitest run --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint` over the nine touched component files reports at most the 4 errors across 3 files present at `1538bf6` (`LinkUserAccountModal.tsx` 1, `LotFormModal.tsx` 1, `ResidentFormModal.tsx` 2), and the repository total stays at 375 errors + 2 warnings across 64 files.
- [ ] `src/features/lot-management/__tests__/LotsPage.test.tsx` and `ResidentsTab.test.tsx` pass without modification.
