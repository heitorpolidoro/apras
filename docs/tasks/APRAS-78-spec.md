# APRAS-78 — Publish the theme token mapping and migration guard, with components/ui as the pilot

Child 1 of 8 of the APRAS-77 split. It is the **foundation**: children 2–8
consume the table, the ledger and the guard published here and may not
re-derive, extend or amend any of them. No sibling may start before this one
merges.

*Revision 4. Reviews: `.meridian/reports/APRAS-78-spec_review-1.md`,
`.meridian/reports/APRAS-78-spec_review-2.md`,
`.meridian/reports/APRAS-78-spec_review-3.md`.*

## Scope

This task publishes four artefacts and proves them on one directory:

1. `docs/frontend/theme-token-mapping.md` — the authoritative class→token
   table, **exhaustive** over the palette classes present in `frontend/src`.
2. `docs/frontend/unmapped-colours.md` — the ledger of colours left untouched.
3. `frontend/src/__tests__/themeTokenMigration.test.ts` plus
   `frontend/src/__tests__/themeTokenMigration.exceptions.json` — the guard and
   its narrow exceptions file.
4. The pilot migration of `frontend/src/components/ui/*`, the compile-time
   verification test and the brand-reach proof.

It does **not** migrate any file outside `src/components/ui/`, does not change
the token set in `src/index.css` (not one property, not one value), does not
enable the `.dark` block, and touches no backend file, no Alembic revision and
no route registry.

## Binding context (restated, not re-decided)

The operator's decision on APRAS-77 is binding and **no review may report any
of these as a defect**:

- primary buttons go from white-on-indigo (and white-on-emerald) to
  dark-on-emerald, because APRAS-76 made `--primary-foreground` dark;
- `text-slate-400` → `text-muted-foreground` darkens by 17.40 L points, which
  incidentally repairs a contrast failure;
- `indigo` shifts from hue 277 to hue 160.

APRAS-77's literal wording "the colours must not move" is **not achievable**
and this spec does not pretend otherwise. Neutral surface/border rows land
within 1–3 ΔE and are effectively invisible; the three groups above move
plainly and are accepted.

### The status-colour ruling (operator, round 1) — binding and permanent

**Success, warning and info colours stay hard-coded** and are **never**
migrated. The ruling is about *not migrating*; it does not fix the ledger
label. Each such class is logged under whichever code §1h's precedence
assigns: **`GAP-TINT`** where the family has a token that is deliberately
withheld (`emerald`, `red`), **`GAP-NO-TOKEN`** where the family has no token
at all (`amber`, `blue`). Both codes forbid migration equally, so the outcome
is identical either way and only the recorded label differs; the ledger's `why`
column still names the role (`warning alert tint`).

> A status colour is **semantic, not brand**. Green means success in every
> condominium, and a condominium whose brand is red must not see "success"
> rendered in red.

**No sibling may attempt to migrate them, and no review may treat their
absence from the migration as incomplete work.** Two consequences are recorded
here so they are not rediscovered as bugs:

1. Those surfaces **never respond to the tenant's brand**. That is the
   intended behaviour, not a reach failure of APRAS-68.
2. They are still hard-coded *light-scheme* colours, so **the task that
   eventually enables the `.dark` block inherits them** and must resolve them
   there. Enabling `.dark` is out of scope here and has its own decisions.

**Three cases, three different reasons** — and §1h's codes 3 and 4 fall out of
them. Do not compress them into one:

1. **Red migrates**, because `--destructive` is a **never-branded status
   token**: it is **not** in `build_theme`'s 13 `AUTHORED_KEYS` and is never
   overridden by a tenant (`src/api/tenantProfile.ts` states this explicitly).
   Binding error colours to it changes nothing semantically — a red-branded
   condominium still sees errors in the same red. (Subject to §1j's tint-triple
   exception, which is a *contrast* constraint, not a semantic one.)
2. **Success stays**, and **not** because its token is missing. Emerald's token
   exists: `--primary` is `oklch(0.62 0.15 160)`. `--primary` is a **brand**
   token, so binding success to it would make "success" follow the tenant's
   brand — exactly what the ruling forbids. Success is the paradigm case of a
   token that exists and is **deliberately withheld**, which is what §1h code 4
   `GAP-TINT` names.
3. **Warning and info stay** because **no token exists at all** — there is no
   `--warning` and no `--info`, and `amber`/`blue` have no row at any scale.
   That is §1h code 3 `GAP-NO-TOKEN`, which precedence puts first.

Adding `--success`/`--warning`/`--info` on the same never-branded footing as
`--destructive` is the natural follow-up and is **out of scope** (it would
extend `build_theme`, a backend change).

---

## Deliverable 1 — the mapping table

**File:** `docs/frontend/theme-token-mapping.md`.

**Derivation, already performed; publish these numbers, do not re-derive them
by eye.** Source side: `frontend/node_modules/tailwindcss/theme.css`, Tailwind
**4.2.4**. Target side: the `:root` block of `frontend/src/index.css`. Both
sides are `oklch()`, so ΔL is directly comparable; ΔE is the euclidean
distance in OKLab (ΔL, Δa, Δb) with L in 0–100 units and chroma scaled by 100.
Neither figure involves gamut mapping, so both are exact arithmetic on the two
declared values. **All figures are published to two decimals**, because the
verification test asserts them to ±0.1.

### 1a. The budget rule

| ΔE | Budget class | Meaning |
| --- | --- | --- |
| ≤ 3 | `invisible` | migrate silently |
| > 3 and ≤ 12 | `noted` | migrate; the row carries a one-line note |
| > 12 | `moves` | migrate **only** if the operator decision names it |
| > 12, unnamed | `GAP` | do not migrate; log under a code from §1h |

`GAP` is a fourth value of the published budget-class column, not a separate
concept: it is what a `moves` row becomes when the operator decision does not
name it. The three named moves are the indigo family, `text-*-400` →
`muted-foreground`, and `text-white` → `text-primary-foreground`.

### 1b. Neutral surfaces

| Source class | Target | L source → target | ΔL | ΔE | Budget |
| --- | --- | --- | --- | --- | --- |
| `bg-white` | **context — §1f case 1** | 100.00 → 100.00 / 99.00 | 0.00 / 1.00 | 0.00 / 1.00 | invisible |
| `bg-slate-50` | `bg-muted` / **§1f case 2** | 98.40 → 96.00 | 2.40 | 2.61 | invisible |
| `bg-gray-50` | `bg-muted` / **§1f case 2** | 98.50 → 96.00 | 2.50 | 2.70 | invisible |
| `bg-slate-100` | `bg-muted` / **§1f case 2** | 96.80 → 96.00 | 0.80 | 1.44 | invisible |
| `bg-gray-100` | `bg-muted` / **§1f case 2** | 96.70 → 96.00 | 0.70 | 1.32 | invisible |
| `bg-slate-200` | `bg-muted` / **§1f case 2** | 92.90 → 96.00 | 3.10 | 3.54 | noted |
| `bg-gray-200` | `bg-muted` / **§1f case 2** | 92.80 → 96.00 | 3.20 | 3.45 | noted |
| `bg-slate-300` | `bg-muted` | 86.90 → 96.00 | 9.10 | 9.43 | noted (lightens) |
| `bg-slate-900` | `bg-foreground` | 20.80 → 14.00 | 6.80 | 8.20 | noted |
| `bg-slate-950` | `bg-foreground` | 12.90 → 14.00 | 1.10 | 4.69 | noted |

`bg-secondary` and `bg-accent` are byte-identical to `bg-muted` in `:root`
(`oklch(0.96 0.01 160)`), so every ΔL/ΔE above is the same for all three. They
are **not** interchangeable: `build_theme` lets a tenant author them apart, so
the choice is semantic and is resolved by §1f case 2.

### 1c. Neutral borders, dividers and rings

| Source class | Target | L source → target | ΔL | ΔE | Budget |
| --- | --- | --- | --- | --- | --- |
| `border-slate-200` | `border-border` | 92.90 → 92.00 | 0.90 | 1.94 | invisible |
| `border-gray-200` | `border-border` | 92.80 → 92.00 | 0.80 | 1.52 | invisible |
| `divide-slate-200` | `divide-border` | 92.90 → 92.00 | 0.90 | 1.94 | invisible |
| `divide-gray-200` | `divide-border` | 92.80 → 92.00 | 0.80 | 1.52 | invisible |
| `border-slate-300` | `border-input` | 86.90 → 92.00 | 5.10 | 5.66 | noted (form borders lighten) |
| `border-gray-300` | `border-input` | 87.20 → 92.00 | 4.80 | 5.03 | noted (form borders lighten) |
| `border-white` | `border-card` | 100.00 → 100.00 | 0.00 | 0.00 | invisible |

`divide-*` had no row at all in revision 1 while appearing in the §3b grammar;
the four `divide-` classes present in the tree (13 occurrences) are now
covered — `divide-*-200` here, `divide-*-100` as a gap in §1h.

### 1d. Neutral text

| Source class | Target | L source → target | ΔL | ΔE | Budget |
| --- | --- | --- | --- | --- | --- |
| `text-slate-900` | `text-foreground` | 20.80 → 14.00 | 6.80 | 8.20 | noted |
| `text-gray-900` | `text-foreground` | 21.00 → 14.00 | 7.00 | 7.95 | noted |
| `text-slate-600` | `text-muted-foreground` | 44.60 → 53.00 | 8.40 | 9.76 | noted (lightens) |
| `text-gray-600` | `text-muted-foreground` | 44.60 → 53.00 | 8.40 | 9.22 | noted (lightens) |
| `text-slate-500` | `text-muted-foreground` | 55.40 → 53.00 | 2.40 | 5.77 | noted |
| `text-gray-500` | `text-muted-foreground` | 55.10 → 53.00 | 2.10 | 4.29 | noted |
| `text-slate-400` | `text-muted-foreground` | 70.40 → 53.00 | 17.40 | 18.02 | moves (**named**) |
| `text-gray-400` | `text-muted-foreground` | 70.70 → 53.00 | 17.70 | 18.00 | moves (**named**) |
| `text-white` | **context — §1f case 1** | 100.00 → 15.00 / 98.00 | 85.00 / 2.00 | 85.02 / 2.00 | moves (**named**) / invisible |

### 1e. Brand, accent and destructive

| Source class | Target | L source → target | ΔL | ΔE | Budget |
| --- | --- | --- | --- | --- | --- |
| `bg-indigo-500` / `text-indigo-500` / `border-indigo-500` | `*-primary` | 58.50 → 62.00 | 3.50 | 33.15 | moves (**named**) |
| `ring-indigo-500` | `ring-ring` | 58.50 → 62.00 | 3.50 | 33.15 | moves (**named**) |
| `bg-indigo-600` / `text-indigo-600` / `border-indigo-600` / `accent-indigo-600` | `*-primary` | 51.10 → 62.00 | 10.90 | 37.24 | moves (**named**) |
| `bg-indigo-700` / `text-indigo-700` | `*-primary` (see §1i for `/90`) | 45.70 → 62.00 | 16.30 | 37.33 | moves (**named**) |
| `text-indigo-800` | `text-primary` | 39.80 → 62.00 | 22.20 | 36.97 | moves (**named**) |
| `text-indigo-900` | `text-primary` | 35.90 → 62.00 | 26.10 | 36.35 | moves (**named**) |
| `text-indigo-300` | `text-primary` | 78.50 → 62.00 | 16.50 | 27.82 | moves (**named**) |
| `border-indigo-400` | `border-primary` | 67.30 → 62.00 | 5.30 | 28.84 | moves (**named**) |
| `bg-indigo-50` | `bg-accent` | 96.20 → 96.00 | 0.20 | 2.38 | invisible |
| `bg-indigo-100` | `bg-accent` | 93.00 → 96.00 | 3.00 | 4.92 | noted |
| `bg-indigo-200` | `bg-accent` | 87.00 → 96.00 | 9.00 | 11.38 | noted |
| `border-indigo-100` | `border-border` | 93.00 → 92.00 | 1.00 | 4.02 | noted |
| `border-indigo-200` | `border-border` | 87.00 → 92.00 | 5.00 | 8.58 | noted |
| `bg-emerald-500` / `text-emerald-500` / `border-emerald-500` | `*-primary` (**§1f case 3**) | 69.60 → 62.00 | 7.60 | 7.89 | noted |
| `ring-emerald-500` | `ring-ring` (**§1f case 3**) | 69.60 → 62.00 | 7.60 | 7.89 | noted |
| `bg-emerald-600` / `text-emerald-600` / `border-emerald-600` | `*-primary` (**§1f case 3**) | 59.60 → 62.00 | 2.40 | 2.59 | invisible |
| `ring-emerald-600` | `ring-ring` (**§1f case 3**) | 59.60 → 62.00 | 2.40 | 2.59 | invisible |
| `bg-emerald-700` / `text-emerald-700` | `*-primary` (**§1f case 3**, see §1i) | 50.80 → 62.00 | 11.20 | 11.72 | noted |
| `text-red-600` / `bg-red-600` | `*-destructive` | 57.70 → 58.00 | 0.30 | 0.60 | invisible |
| `text-red-500` / `bg-red-500` | `*-destructive` | 63.70 → 58.00 | 5.70 | 5.75 | noted |
| `text-red-700` / `bg-red-700` | `*-destructive` | 50.50 → 58.00 | 7.50 | 7.97 | noted |
| `text-white` on `bg-destructive` | `text-destructive-foreground` | 100.00 → 98.00 | 2.00 | 2.00 | invisible |
| `text-white` on `bg-primary` | `text-primary-foreground` | 100.00 → 15.00 | 85.00 | 85.02 | moves (**named**) |

The indigo rows are individually enumerated rather than folded into one
"indigo family" row, because every one of them carries different numbers and
the compile test asserts each to ±0.1. **`ring-blue-500` is not in this table**
— see §1h `GAP-NO-TOKEN` and the operator note at the end.

### 1f. The context-dependent cases — the part the test cannot catch

Three source patterns have **no single correct target**. The choice is a human
judgement at each call site, and **the verification test cannot detect a wrong
choice**, because in cases 1 and 2 both candidates are identical in `:root`.

**Case 1 — `bg-white`, `text-white`, `border-white`.**
`bg-white` is `bg-card` on a card, a modal panel, a table surface or a popover
(ΔL 0.00), and `bg-background` on a page shell or a full-bleed section
(ΔL 1.00). Rule: *if the element sits **on** the page, it is `bg-card`; if the
element **is** the page, it is `bg-background`.* `bg-popover` only on a
floating layer that already carries `popover` semantics.
`text-white` names the same token family as the background it sits on:
`text-primary-foreground` over `bg-primary`, `text-destructive-foreground`
over `bg-destructive`. Over any background that carries **no** token — an
image, a gradient, an arbitrary value, or a palette colour with no row such as
`bg-amber-500` — it is a gap, not a row.

**Case 2 — neutral fills at 50/100/200: `bg-muted` or `bg-accent`.**
A fill that is the element's *resting* surface (a panel, a table header, a code
block) is `bg-muted`. A fill that appears on **interaction** —
`hover:`, `focus:`, `focus-visible:`, `group-hover:`, `aria-selected:`,
`data-[state=…]:` — is `bg-accent`, because `accent` is the interaction token
`button.tsx` already uses (`hover:bg-accent hover:text-accent-foreground`).
This resolves the revision-1 contradiction between the flat
`bg-slate-100 → bg-muted` row and §1b's own "a hover fill" example. Measured in
the tree: **17** `hover:bg-slate-100`, **15** `hover:bg-gray-100`, **12**
`hover:bg-slate-50`, **6** `hover:bg-gray-50`, **2** `hover:bg-slate-200`,
**2** `hover:bg-gray-200` — 54 occurrences that take `bg-accent`, against 118
resting fills that take `bg-muted`. The two are byte-identical in `:root` and
differ only under a tenant theme, so **this case is invisible to every test in
this task and is purely a review duty.**

**Case 3 — emerald at 500/600/700: brand accent or success status.**
Emerald is simultaneously the default brand hue (`--primary` is
`oklch(0.62 0.15 160)`) and the conventional success colour, so the same class
means two different things in two places.

**First, note how narrow the judgement is.** Of the **169 non-`dark:`** emerald
occurrences in `frontend/src` (there are a further **54** `dark:` ones, **223**
all in, which §1g governs rather than this case — an implementer who
regenerates the count without excluding `dark:` will get 223 and think the
figure is wrong), **90** are resolved unconditionally by scale
alone — emerald at **50/100/200/300** and at **800/900/950** is *always*
`GAP-TINT`, because at those scales it is only ever a tint surface or on-tint
text, never an interactive fill. Judgement applies only to the **79**
occurrences in the 500–700 band, and only there.

Within that band the discriminator is **one test, and only one**:

- **Migrates to `primary`** — the element is **interactive**: a `<button>` or
  `<a>` fill, a focus ring, an interactive border.
- **Stays hard-coded (`GAP-TINT`)** — the element is **non-interactive**: an
  alert tint, a badge, a status dot, a variant icon or heading, and any border
  belonging to such a variant.

*Interactive* means the element is a control or is inside one that the colour
belongs to. Nothing else enters the test — in particular, do **not** ask
whether colour is the only signal. Revision 2 carried a "whose colour is the
only signal" clause and the pilot falsified it: `alert-modal.tsx:28`'s success
icon is a `CheckCircle2` glyph whose *shape* also carries the meaning, so that
clause returned the opposite verdict to the one §4a records. It survives below
as rationale, never as a test.

**Rationale, so no sibling relitigates this.** The principle is **WCAG 1.4.1
(Use of Colour)**, reused as a migration rule: where colour is the carrier of
meaning, the colour is semantic and stays; where the accessible name carries
the meaning, the colour is decoration and takes the brand. A button's label
says what it does, so the status ruling's own justification — *a red-branded
condominium must not see "success" rendered in red* — does not reach it; a
green panel with no other signal is exactly what that sentence protects. The
alternative was tested and rejected by the operator: it would leave exactly one
button in the app that the tenant's brand can never reach, which is the defect
APRAS-68 existed to remove, and it would shrink the pilot to a single
substitution, which proves nothing about the table.

This boundary is the one place where the operator's status-colour ruling and
the APRAS-77 button decision meet. Both are honoured, and the matter is
settled: do not reopen it.

### 1g. The `dark:` variant rule

Measured with the §3b grammar: **872** `dark:`-prefixed palette occurrences
across **63** distinct classes, out of **3,241** total occurrences in the
**114** files that contain any, out of 260 non-test files scanned.
(Revision 1's "~3,243" came from a grammar whose scale
alternation matched `50` inside `500`; see §3b.)

**When the class being migrated is replaced by a token, its `dark:` sibling is
deleted, not remapped** — the token already carries its own dark value in
`index.css`'s `.dark` block, and a surviving `dark:bg-slate-800` beside
`bg-card` would win on variant specificity and defeat the token. Deleting them
changes nothing today, because `.dark` is never applied. This rule does **not**
enable dark mode.

**When the base class does *not* migrate — it is a gap — the `dark:` sibling
is left untouched too, and gets its own ledger row and its own exceptions
entry under the same code as its base.** This is the common case in the tree
(`text-slate-700 dark:text-slate-300`, where the base is `GAP-OUT-OF-BUDGET`),
and without this sentence such a class matches the grammar with no legal move.

`src/components/ui/` contains **zero** `dark:` occurrences, so the pilot
provides no evidence for either half of this rule; it is argued from token
semantics and the risk is bounded because `.dark` is never applied. The first
sibling that meets one proves it.

### 1h. Gap codes — the closed set

Nothing may be excepted from the guard except under one of these codes.
**Precedence is top to bottom**: a class matching two codes takes the first.

The order is **objective codes first, judgement codes last**. `GAP-NO-TOKEN`
is a fact about `index.css` that two implementers cannot disagree about;
`GAP-TINT` requires reading the call site. Revision 2 had them the other way
round, which made every amber and blue occurrence ambiguous — `GAP-TINT` by
role, `GAP-NO-TOKEN` by family — and §1j and §4a resolved that ambiguity
differently. Putting the objective code first removes the ambiguity without
weakening anything, because **both codes forbid migration equally**; only the
recorded label differs, and the ledger's `why` column still records the role
(`warning alert tint`).

| # | Code | Definition |
| --- | --- | --- |
| 1 | `GAP-OVERLAY` | `bg-black` or `bg-white`, with or without an opacity modifier, used as a scrim or backdrop. No overlay token exists. |
| 2 | `GAP-SWATCH` | A data-encoding colour: chart series, avatar fills, category swatches. Must not follow the brand. |
| 3 | `GAP-NO-TOKEN` | A family with **no** token in `index.css` at all: `amber`, `blue`, `green`, `orange`, `yellow`, `lime`, `teal`, `cyan`, `sky`, `violet`, `purple`, `fuchsia`, `pink`, `rose`, `zinc`, `neutral`, `stone`. Applies **whatever the role** — a warning tint in `amber` is `GAP-NO-TOKEN`, not `GAP-TINT`, because no amber token exists to be withheld. |
| 4 | `GAP-TINT` | A colour whose job is to encode a **status** (success / warning / info / error) to the eye, **in a family that does have a token** — `emerald`, `red`, `indigo`, `slate`, `gray`. This is the operator's ruling exactly: the token exists and is deliberately *withheld*, because the colour is semantic and not brand. Covers a status variant's entire class set at any scale and any utility prefix — surface, border, ring, icon and heading text. Permanent. |
| 5 | `GAP-NO-SURFACE` | `text-white`, `text-black` or `border-white` over **any** background that carries no token — an image, a gradient, an arbitrary value, or a palette colour with no row, such as `bg-amber-500`. |
| 6 | `GAP-BORDER-100` | `border-*-100`, `divide-*-100`, `ring-*-100`. A hairline divider, not a border: the only candidate (`border`, ΔE 4.83–4.95) is the *border* role one step darker, and applying it would make dividers read as borders. Operator-named gap. |
| 7 | `GAP-OUT-OF-BUDGET` | Every candidate target **this table offers for that class's role** exceeds **ΔE 12**, and the operator decision does not name the move. "Candidate" means the tokens §1b–1e admit for that utility prefix and role, not the nearest colour anywhere in the token set — `text-slate-700` is a gap even though `destructive` happens to sit closer in ΔE, because `destructive` is not a candidate for neutral body text. Subsumes the second operator-named gap, `text-*-700`. |
| 8 | `GAP-UNLISTED` | **Reserved escalation.** A class that appears in code written *after* this task and has no row and no other code. The sibling logs it, leaves the class untouched, and **does not block**. |

A class that does not fall under one of these codes **must be migrated**.
Siblings may **not** add codes, add rows, or add tokens. Amending §1b–1e or
§1h is the property of this task's artefacts, so the table keeps one owner
instead of seven; a sibling that believes a row is wrong raises a
table-amendment task and uses `GAP-UNLISTED` meanwhile.

### 1i. Opacity-modified targets

Three targets carry an alpha: `bg-primary/90` (for `bg-indigo-700`,
`hover:bg-emerald-700` and the `button.tsx` triple), and any future
`*/N` target. The rule, so two implementers do not do two different things:

- **The colour is measured against the base token, and the alpha is declared
  unmeasured.** The row's published ΔL/ΔE are those of `bg-primary`
  (i.e. `bg-indigo-700 → bg-primary/90` publishes 16.30 / 37.33, the
  `indigo-700 → primary` figures).
- The resolver takes the **unconditional** declaration. Compiled,
  `bg-primary/90` emits `background-color: var(--color-primary)` followed by an
  `@supports (color: color-mix(in lab, red, red))` block re-declaring it as
  `color-mix(in oklab, var(--color-primary) 90%, transparent)`. `parseOklch`
  returns `null` for `color-mix`, so the resolver must read the first,
  unconditional declaration and never the `@supports` one.
- The alpha is nonetheless **checked structurally**: the test asserts the
  `@supports` declaration matches
  `color-mix(in oklab, var(--color-<token>) <N>%, transparent)` with the `N`
  the row declares. The alpha is verified as *present and correct*, just not
  colorimetrically composited.

### 1j. Exhaustiveness — the published appendix

**Read this before the table: the appendix partitions at *class* granularity,
but the unit of migration is the *call site*.** A row says what a class means
when nothing else constrains it. Where a call site puts that class inside a
**status tint triple** — a surface, a border and a foreground that encode one
status together — the **triple's** verdict governs, and the class stays even
though its row says migrate. This is general: it holds for every family, now
and for any family a later task adds, and it is the reason emerald's row
carries a dual label. **A cell in the table is never authority to split a
triple.** The two rules that do the work are stated here and are **binding
tree-wide, not only in the pilot**:

- **Triple-as-a-unit.** A status variant's class triple migrates **as a unit or
  not at all**, and only if **every** member has a row in §1b–1e.
- **The ≥ 4.5:1 clause.** A triple may migrate only if the resulting
  foreground/background pair holds **≥ 4.5:1**, re-derived with
  `src/lib/contrast.ts` — never by eye, and never with the ΔL/ΔE arithmetic in
  this document, which omits the gamut mapping `contrast.ts` performs. §4a
  *applies* these two rules to `components/ui`; it does not own them.

**Why the red row is conditional.** Red is the family where the class-level
row and the call-site rule pull hardest in opposite directions, and following
the row alone ships a measured AA regression. **29 of the 62**
`text-red-[567]00` occurrences in `frontend/src` (25 `text-red-700`, 4
`text-red-600`) share a class string with a red tint surface — forms literally
repeated across the tree, such as `"rounded-lg bg-red-50 p-2 text-sm
text-red-700"` and `"bg-red-50 text-red-700 text-sm p-3 rounded-lg border
border-red-200"`. `bg-red-50`, `bg-red-100` and `border-red-200` are all
`GAP-TINT` in this same appendix, so the surface cannot move; migrating the
text alone gives, measured with `src/lib/contrast.ts` (lines 121–210,
OKLab→linear-sRGB, chroma-bisection gamut map, WCAG 2.1):

| pair | ratio | verdict |
| --- | --- | --- |
| `text-red-700` on `bg-red-50` — today | **5.9842:1** | passes AA |
| `text-destructive` on `bg-red-50` — after migrating the text alone | **4.4006:1** | **fails AA** |
| `text-destructive` on `bg-red-100` | **3.9381:1** | **fails AA** |

This is the mirror image of §4a's emerald argument ("migrating the surface
alone is incoherent"): for red it is the *foreground* that cannot move alone.
So a red 500–700 class inside a tint triple is **`GAP-TINT`** (code 4 — an
error status in a family that has a token), and only a free-standing red class
— an error message with a neutral or white background, an icon, a destructive
control — takes the §1e row.

(Pre-existing and **not** this task's to fix: `text-red-600` on `bg-red-50`
already measures **4.4506:1** and fails AA today. Those sites keep their
current classes; the ledger's `why` should say so, so a later reader does not
attribute the failure to this migration.)

The mapping document ends with an appendix listing **every** distinct palette
class present in `frontend/src` with its row or its code. It is generated
**mechanically**, not by eye: walk `frontend/src` for `.ts`/`.tsx` excluding
`__tests__/` and `*.test.*`, apply the §3b grammar, strip variants and the
opacity modifier, and group. Measured for this spec: **152 distinct non-`dark:`
classes over 2,369 occurrences**, plus 63 distinct `dark:` classes over 872 —
**3,241** occurrences in total, in **114** files that match, out of 260 files
scanned. Every one of the 152 is accounted for below; the implementer
regenerates this list and must arrive at the same partition.

**Why `amber` and `blue` are not split the way `red` and `emerald` are.**
`red` and `emerald` have tokens, so a status use of them is a token
deliberately withheld — `GAP-TINT`, code 4 — while a non-status use takes a
row. `amber` (133 occurrences) and `blue` (75) have no token at any scale, so
code 3 `GAP-NO-TOKEN` catches them first, whatever their role. They are
therefore listed family-wise below, and that is now consistent with §1h's
precedence rather than in conflict with it. The outcome is identical either
way: leave the class untouched and log it.

| Verdict | Classes | Occ. |
| --- | --- | --- |
| §1b `bg-*-50/100/200` → `bg-muted`/`bg-accent` | `bg-slate-50` 41, `bg-slate-100` 38, `bg-slate-200` 4, `bg-gray-50` 33, `bg-gray-100` 30, `bg-gray-200` 2 | 148 |
| §1b `bg-slate-300` → `bg-muted` | `bg-slate-300` 1 | 1 |
| §1b `bg-*-900/950` → `bg-foreground` | `bg-slate-900` 3, `bg-slate-950` 4 | 7 |
| §1c → `border-border` / `divide-border` | `border-gray-200` 107, `border-slate-200` 90, `divide-slate-200` 5, `divide-gray-200` 1 | 203 |
| §1c → `border-input` | `border-slate-300` 56, `border-gray-300` 24 | 80 |
| §1d → `text-foreground` | `text-slate-900` 106, `text-gray-900` 73 | 179 |
| §1d → `text-muted-foreground` | `text-gray-500` 126, `text-slate-500` 95, `text-slate-400` 59, `text-slate-600` 55, `text-gray-600` 38, `text-gray-400` 33 | 406 |
| §1e indigo → `primary`/`ring` | `text-indigo-600` 67, `bg-indigo-600` 29, `bg-indigo-700` 22, `ring-indigo-500` 16, `text-indigo-700` 12, `text-indigo-500` 9, `text-indigo-800` 3, `border-indigo-500` 2, `border-indigo-600` 2, `accent-indigo-600` 1, `bg-indigo-500` 1, `border-indigo-400` 1, `text-indigo-300` 1, `text-indigo-900` 1 | 167 |
| §1e indigo tints → `accent`/`border` | `bg-indigo-50` 25, `border-indigo-200` 5, `bg-indigo-100` 3, `border-indigo-100` 3, `bg-indigo-200` 1 | 37 |
| §1e red → `destructive`, **except where the class belongs to a red tint triple (see this section's preamble), which stays `GAP-TINT`** — **29** of the 62 `text-red-[567]00` occurrences are in that position | `text-red-600` 26, `text-red-700` 26, `text-red-500` 10, `bg-red-500` 3, `bg-red-600` 1, `bg-red-700` 1 | 67 |
| §1f case 3 emerald 500–700 (brand **or** `GAP-TINT`) | `text-emerald-600` 24, `text-emerald-700` 22, `bg-emerald-700` 11, `bg-emerald-600` 9, `bg-emerald-500` 4, `text-emerald-500` 3, `border-emerald-600` 2, `ring-emerald-600` 2, `border-emerald-500` 1, `ring-emerald-500` 1 | 79 |
| §1f case 1 white/black | `bg-white` 203, `text-white` 49, `border-white` 2 → rows; `bg-black` 54 → `GAP-OVERLAY` | 308 |
| `GAP-TINT` | `bg-red-50` 31, `bg-emerald-50` 30, `border-red-200` 23, `text-emerald-800` 19, `border-emerald-200` 16, `bg-emerald-100` 14, `text-emerald-900` 8, `bg-red-100` 7, `text-red-800` 6, `border-emerald-300` 3 | 157 |
| `GAP-NO-TOKEN` | 67 classes across `amber`, `blue`, `green`, `orange`, `yellow`, `cyan`, `sky`, `teal`, `purple`, `pink`, `rose` — largest: `text-amber-700` 24, `ring-blue-500` 21, `bg-amber-50` 21, `bg-amber-100` 16, `text-amber-800` 15, `border-amber-200` 14, `text-amber-600` 14 | 255 |
| `GAP-BORDER-100` | `border-slate-100` 41, `border-gray-100` 12, `divide-slate-100` 4, `divide-gray-100` 3, `ring-gray-100` 1 | 61 |
| `GAP-OUT-OF-BUDGET` | `text-gray-700` 73 (ΔE 17.81), `text-slate-700` 71 (17.93), `text-gray-800` 47 (14.25), `text-slate-800` 16 (14.58), `text-slate-300` 3 (34.04), `ring-slate-500` 2 (17.54), `border-slate-800` 1 (14.58), `text-red-400` 1 (13.45) | 214 |

152 classes, 2,369 occurrences, no residue.

---

## Deliverable 2 — the unmapped-colour ledger

**File:** `docs/frontend/unmapped-colours.md`.

A task that meets a colour with no row **leaves the class exactly as it is**
and appends one line. **No task may add a property to
`frontend/src/index.css`** — a one-off token per call site turns the token set
into landfill, and `build_theme` emits exactly 17 keys, so a new one would be
unbranded forever.

A single Markdown table, append-only, sorted by file then line, one row per
occurrence, with exactly these six columns:

```
| task | file | line | class | code | why |
```

- `task` — the Meridian id appending the row (`APRAS-78` … `APRAS-85`).
- `file` — repo-relative from the repo root.
- `line` — the line number at the time of writing. Drift is expected and is
  not an error; the guard does not check it.
- `class` — verbatim, variants and opacity included (`hover:bg-amber-600`,
  `bg-black/40`, `dark:text-slate-300`).
- `code` — one of the eight in §1h, verbatim.
- `why` — one sentence, ≤ 120 characters, naming the *role* the class plays
  (`warning alert tint`, `modal scrim`), not restating the code.

The file opens with a preamble stating the no-new-token rule, the
status-colour ruling and its two consequences, and linking to §1h.

---

## Deliverable 3 — the guard and its exceptions file

**Files:** `frontend/src/__tests__/themeTokenMigration.test.ts` and
`frontend/src/__tests__/themeTokenMigration.exceptions.json`.

### 3a. The allow-list

The test exports `MIGRATED_DIRECTORIES: readonly string[]`, seeded with
exactly one entry, `"src/components/ui"`. Each sibling appends exactly one.
Paths are `src/`-relative and match non-recursively unless suffixed `/**`.

The test walks every `.tsx`/`.ts` file under each pinned directory, excluding
`__tests__/` and `*.test.ts(x)`, reads it with `node:fs`, and fails on any
match of the palette grammar not listed in the exceptions file. The failure
message names file, line, the matched text, and points at
`docs/frontend/theme-token-mapping.md`.

### 3b. The grammar

Built from named parts, not one hand-written literal:

```
variants = (?:[a-z0-9][a-z0-9.\-]*(?:\[[^\]]*\])?:)*
prefix   = (?:bg|text|border|ring|outline|divide|placeholder|caret|accent|
              decoration|shadow|fill|stroke|from|via|to)
family   = (?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|
              green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|
              pink|rose)
scale    = (?:950|900|800|700|600|500|400|300|200|100|50)
opacity  = (?:/(?:[0-9]{1,3}|\[[^\]]*\]))?

palette  = (?<![\w-]) variants prefix - (?: family - scale | white | black )
           (?![\w-]) opacity
```

Two details are load-bearing and cost revision 1 a wrong tree-wide count:

- **`scale` must list its alternatives longest-first.** With `50` before `500`
  the engine matches `text-gray-50` inside `text-gray-500` and silently
  under-reports. The test must assert that the grammar's match of
  `text-gray-500` is the whole class, not a prefix of it.
- **The boundaries `(?<![\w-])` and `(?![\w-])`** prevent matching inside a
  longer identifier or a compound class name.

A third pattern covers `#[0-9a-fA-F]{6}` appearing inside a `className` string
or a `cva`/`cn` argument.

The test must contain a table-driven case asserting the grammar matches at
least `hover:dark:bg-slate-800/40`, `data-[state=open]:bg-gray-100`,
`sm:text-indigo-600`, `bg-black/40`, `text-white`, `border-emerald-500/50`,
`text-gray-500` (whole match), `#1e293b`; and does **not** match `bg-primary`,
`bg-primary/90`, `bg-[var(--priority-low-bg)]`, `text-muted-foreground`,
`shadow-sm`, `border-2`, `bg-destructive/5`.

### 3c. The exceptions file — why it must exist now

The grammar matches the gap classes themselves, so the first pinned directory
containing one would fail its own guard. The exceptions file is therefore part
of **this** task.

`themeTokenMigration.exceptions.json` is an array of objects with exactly four
keys:

```json
{ "file": "src/components/ui/badge.tsx", "class": "bg-amber-100", "code": "GAP-TINT", "task": "APRAS-78" }
```

`file` is `src/`-relative; `class` is the verbatim matched text; `code` is one
of the eight in §1h; `task` is the appending task's id. There is **no line
number** — it would rot on every edit and turn the guard into noise.

Four rules keep it from becoming a place to hide unmigrated work, and the
guard asserts all four:

1. **Closed reason codes.** `code` must be one of the eight in §1h. Anything
   else fails, so hiding a migratable class requires editing the published
   table — a visible, reviewable act.
2. **No stale entries.** Every entry must still match something in the named
   file. An exception cannot outlive the code it excuses.
3. **Exact pairs only.** An entry excuses that `class` in that `file` and
   nothing else. No globs, no directory-wide entries, no bare family names.
4. **Ledger parity.** Every exception must have a row in
   `docs/frontend/unmapped-colours.md` with the same file, class and code, and
   every ledger row under a pinned directory must have an exception.

### 3d. Designed for APRAS-85's inversion

APRAS-85 inverts the allow-list into a repo-wide deny and keeps this same
exceptions file. The directory walk must be written so that replacing
`MIGRATED_DIRECTORIES` with `["src/**"]` is the entire change, and entries must
already be `src/`-relative with no allow-list-shaped assumption. Rules 1–4 are
unchanged by the inversion.

---

## Deliverable 4 — the pilot, the verification test and the brand-reach proof

### 4a. The pilot, re-measured

`src/components/ui/` holds nine files; **four** contain palette classes, with
**31** occurrences: `alert-modal.tsx` 14, `badge.tsx` 8, `alert.tsx` 6,
`button.tsx` 3. Zero six-digit hex literals, zero `dark:` variants.

The pilot **applies** the two tree-wide rules stated in §1j — triple-as-a-unit
(every member must have a row) and the ≥ 4.5:1 clause re-derived with
`src/lib/contrast.ts`. They are not pilot-local and they are not restated
here; §1j owns them.

**Migrated — 7 occurrences** (all §1f case 3 "interactive fill" or §1f case 1):

| site | from | to |
| --- | --- | --- |
| `button.tsx:20` `success` variant | `bg-emerald-600 text-white hover:bg-emerald-700` | `bg-primary text-primary-foreground hover:bg-primary/90` |
| `alert-modal.tsx:120` success branch | `bg-emerald-600 text-white hover:bg-emerald-700` | `bg-primary text-primary-foreground hover:bg-primary/90` |
| `alert-modal.tsx:118` destructive branch | `text-white` | `text-destructive-foreground` |

The pair holds 5.7548:1, the figure `index.css` already documents. The
`success` button variant thereby becomes byte-identical to `default`. That is
correct, not a bug: `--primary` *is* emerald, so the two already differed by
2.40 L points, and leaving `success` literal would make it the one button in
the app a tenant's brand never reaches. Removing the now-duplicate variant is
an API change and is **out of scope**.

**What the pilot cannot exercise, stated as plainly as the `dark:` rule in
§1g.** `src/components/ui/` contains **zero** neutral fills at 50/100/200 —
`button.tsx` already uses `hover:bg-accent` — so the pilot provides **no
evidence for §1f case 2**, the `bg-muted`-versus-`bg-accent` choice that
governs 172 occurrences elsewhere in the tree. Like the `dark:` rule, case 2
is argued from token semantics rather than demonstrated here, and unlike the
`dark:` rule it is invisible to every test in this task, because the two
tokens are byte-identical in `:root` (§4b). The first sibling that meets a
`hover:bg-slate-100` is the first real exercise of it, and it is a review
duty there, not a test.

**Left untouched and logged — 24 occurrences**, each with its code:

| site | classes | n | code |
| --- | --- | --- | --- |
| `alert.tsx:12` success variant | `border-emerald-500/50`, `text-emerald-700`, `bg-emerald-50` | 3 | `GAP-TINT` |
| `alert.tsx:13` warning variant | `border-amber-500/50`, `text-amber-700`, `bg-amber-50` | 3 | `GAP-NO-TOKEN` |
| `badge.tsx:32` | `bg-emerald-100`, `text-emerald-800` | 2 | `GAP-TINT` |
| `badge.tsx:33,35` | `bg-red-100` ×2, `text-red-800` ×2 | 4 | `GAP-TINT` |
| `badge.tsx:36` | `bg-amber-100`, `text-amber-800` | 2 | `GAP-NO-TOKEN` |
| `alert-modal.tsx:28,29,30` success config | `text-emerald-500`, `text-emerald-700`, `border-emerald-200` | 3 | `GAP-TINT` |
| `alert-modal.tsx:34,35,36` warning config | `text-amber-500`, `text-amber-700`, `border-amber-200` | 3 | `GAP-NO-TOKEN` |
| `alert-modal.tsx:122` warning branch | `bg-amber-500`, `hover:bg-amber-600` | 2 | `GAP-NO-TOKEN` |
| `alert-modal.tsx:122` warning branch | `text-white` | 1 | `GAP-NO-SURFACE` |
| `alert-modal.tsx:78` backdrop | `bg-black/40` | 1 | `GAP-OVERLAY` |

12 `GAP-TINT` + 10 `GAP-NO-TOKEN` + 1 `GAP-NO-SURFACE` + 1 `GAP-OVERLAY`
= 24; 24 + 7 = 31, with no occurrence unaccounted for.

Two coding notes, both consequences of §1h's precedence:

- The amber classes take `GAP-NO-TOKEN`, not `GAP-TINT`, even though their
  role is a warning status. No amber token exists to be withheld, so the
  objective code wins (§1h code 3). This is what makes §4a and §1j agree;
  revision 2 coded them `GAP-TINT` here and `GAP-NO-TOKEN` in the appendix.
- `alert-modal.tsx:122`'s `text-white` takes `GAP-NO-SURFACE` (§1h code 5): it
  sits on `bg-amber-500`, a palette colour with no row, which is exactly what
  that code names. Revision 1 left it with no code at all, which made the
  pilot uncompletable; revision 2 gave it `GAP-TINT` under the old precedence.
  The outcome is unchanged — the whole warning triple is left alone — only the
  label moves.

The `GAP-TINT` verdict is the operator's permanent ruling, and it is also what
the measurement supports: the tint *surfaces* map well (`bg-emerald-50 →
bg-muted` is ΔE 2.20) but their *text* does not — the darkest brand-family
foreground is `text-primary` at L 62, and `text-primary` on a `bg-primary/5`
tint measures ≈ 3.0:1 against the **6.7502:1** that `text-emerald-800` on
`bg-emerald-100` holds today (re-measured with `src/lib/contrast.ts`). Migrating the surface alone is incoherent;
migrating both would introduce an AA failure. Both the semantics and the
numbers point the same way.

### 4b. The verification test — and what it does not prove

Stated plainly, in the spec and in the test file's own header comment: this
repo has **no Playwright, no Storybook, no Chromatic and no Percy** (verified
against `frontend/package.json` and `.github/`), and jsdom does not run the
Tailwind pipeline. **Computed-style assertions and visual regression are both
unavailable without new infrastructure, which is deliberately out of scope.**

What is available, and what this task builds: Tailwind 4.2.4 exposes
`compile()` from the `tailwindcss` package, verified working from this repo.
`frontend/src/__tests__/themeTokenCompile.test.ts` compiles `src/index.css`
through it — `loadStylesheet` resolving `tailwindcss` to
`node_modules/tailwindcss/index.css` — and calls `build([...])` over a fixture
containing **every class pair in §1b–1e**. For each pair it resolves the
emitted declaration through the `var()` chain (`.bg-primary` →
`var(--color-primary)` → `var(--primary)` → the value), parses both sides with
`parseOklch` from `src/lib/contrast.ts`, and asserts the measured ΔL and ΔE
match the table to **±0.1**. Opacity rows follow §1i.

Three resolver requirements, each a trap that silently certifies a different
table:

1. **Take the `:root` block that `index.css` contributes — the last `:root`
   rule in the compiled output that declares `--primary` without a
   `.dark` qualifier — not merely "the `:root` block".** Tailwind's own theme
   layer emits `:root, :host` before it, so the selector is not unique even
   before `.dark` is considered.
2. **Never `.dark`.** The compiled stylesheet declares `--primary` twice —
   `0.62` in `:root`, `0.65` in `.dark`. A last-wins resolver validates the
   dark scheme.
3. The test must **assert the trap directly**: a case that the resolver returns
   `oklch(0.62 0.15 160)` and not `oklch(0.65 0.15 160)` for `--primary`, so
   that a later simplification to last-wins fails loudly.

**This proves the table is truthful and that no unlisted substitution slipped
in. It does not prove the right row was chosen at the right call site.**
§1f names three cases it cannot see: `bg-white` on a page shell mapped to
`bg-card` passes; `hover:bg-slate-100` mapped to `bg-muted` instead of
`bg-accent` passes *with identical numbers*, because the two tokens are
byte-identical in `:root`; and emerald migrated as brand where it meant
success passes. All three remain a human review duty on every sibling.

### 4c. The brand-reach proof

`TenantBrandTheme` appends a `<style id="tenant-brand-theme">` to
`document.head` whose text is `themeStylesheet(theme)` from
`src/lib/brandStylesheet.ts` — `:root:root { … }` plus `:root:root.dark { … }`,
carrying the 17 keys `build_theme` emits.

`frontend/src/components/__tests__/TenantBrandReach.test.tsx` mounts a
**migrated** component — `<Button variant="success">` — together with
`TenantBrandTheme`, under a mocked `useTenantProfile` returning a
`DerivedTheme` whose `light.primary` differs from `index.css`'s
`oklch(0.62 0.15 160)`, and an authenticated `useAuth`. It asserts that the
injected element exists, that
`getComputedStyle(document.documentElement).getPropertyValue("--primary")`
resolves to the mocked theme's value, and that the rendered button carries
`bg-primary` — the assertion is **against the tenant token, never against a
colour literal**. A negative case asserts that under a `null` theme no element
is injected.

Import `TENANT_BRAND_STYLE_ID` by name; do not hard-code the string.
`src/lib/brandStylesheet.ts` is being edited concurrently by APRAS-74, which
adds a second id (`PUBLIC_BRAND_STYLE_ID`).

---

## Files touched

- `docs/frontend/theme-token-mapping.md` — new; §1 above published verbatim, including the §1j appendix regenerated mechanically, with a contrast column re-derived via `src/lib/contrast.ts`.
- `docs/frontend/unmapped-colours.md` — new; preamble plus the 24 pilot rows.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — new.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — new; the 24 pilot exceptions.
- `frontend/src/__tests__/themeTokenCompile.test.ts` — new.
- `frontend/src/components/__tests__/TenantBrandReach.test.tsx` — new.
- `frontend/src/components/ui/button.tsx` — `success` variant retargeted to the primary token triple.
- `frontend/src/components/ui/alert-modal.tsx` — success branch retargeted; destructive branch `text-white` → `text-destructive-foreground`.

`frontend/src/index.css` is **not** touched. `alert.tsx` and `badge.tsx` are
**not** touched; their classes are logged only.

## Test criteria

- `npx tsc -b` exits clean from `frontend/`.
- `npx vitest run --coverage` passes with thresholds unchanged at **80 lines /
  78 functions / 76 branches / 80 statements**; do not lower them and do not
  write 75.
- `npx eslint .` from `frontend/` reports no new error or warning against the
  baseline of **375 errors + 2 warnings across 64 files** (re-measured
  2026-09-22; 341 are `@typescript-eslint/no-explicit-any`). Diff-scoped: the
  eight touched files contribute zero.
- `src/__tests__/themeContrast.test.ts` continues to pass unmodified.
- A deliberate reintroduction of `hover:dark:bg-slate-800/40` into
  `src/components/ui/button.tsx` fails the guard; so does `#1e293b` inside a
  `className`.
- Removing any single entry from the exceptions file fails the guard; so does
  an unknown `code`, a class absent from its named file, and an entry with no
  matching ledger row.
- The §1j appendix regenerated by the implementer partitions exactly 152
  distinct non-`dark:` classes over 2,369 occurrences, with no class lacking a
  row or a code.
- No file under `backend/` changes; no new Alembic revision; no change to the
  route registry.

## Expected Results

- [ ] `docs/frontend/theme-token-mapping.md` exists and gives, for every row, the source class, the target token, the source and target L values, ΔL and ΔE to two decimals, and a budget class of `invisible`/`noted`/`moves`/`GAP`.
- [ ] The document publishes `text-slate-800` → `text-foreground` at ΔE 14.58 and `text-gray-800` at ΔE 14.25, both as `GAP`, and contains no row for `ring-blue-500`, which is listed under `GAP-NO-TOKEN`.
- [ ] The document records `text-slate-700`/`text-gray-700` (ΔE 17.93/17.81) and `border-slate-100`/`border-gray-100` (ΔE 4.95/4.83) as gaps, and marks the indigo family, `text-*-400` → `text-muted-foreground` and `text-white` → `text-primary-foreground` as operator-named moves, not regressions.
- [ ] The document states the operator's status-colour ruling verbatim — success, warning and info stay hard-coded permanently, because a status colour is semantic and not brand — states that the ruling is about not migrating rather than about the ledger label, and assigns the label by §1h precedence: `GAP-TINT` for emerald and red, `GAP-NO-TOKEN` for amber and blue. No sentence in the document says warning or info is logged under `GAP-TINT`.
- [ ] The document gives three distinct reasons for the three cases: red migrates because `--destructive` is a never-branded status token outside `build_theme`'s 13 `AUTHORED_KEYS`; success stays because `--primary` is a brand token that exists and is deliberately withheld; warning and info stay because no token exists at all. No sentence in the document says that success or emerald has no token.
- [ ] The document defines three context-dependent cases (`bg-white`/`text-white`/`border-white`; neutral fills as `bg-muted` versus `bg-accent` on interaction; emerald 500–700 as brand versus status) and states that the verification test cannot detect a wrong choice in any of them.
- [ ] The document defines exactly eight gap codes in a stated precedence order that places the objective codes (`GAP-OVERLAY`, `GAP-SWATCH`, `GAP-NO-TOKEN`) above the judgement codes, so that a family with no token — `amber`, `blue` — is coded `GAP-NO-TOKEN` whatever its role, in both the appendix and the pilot; and includes `GAP-UNLISTED` as the sole escalation for a class introduced after this task, logged without blocking; and states that siblings may not add rows, codes or tokens.
- [ ] The document states that §1f case 3 turns on **one** test, whether the element is interactive, that the "colour is the only signal" formulation is rationale and not the test, and that 90 of the 169 **non-`dark:`** emerald occurrences (223 including `dark:`) are resolved by scale alone so the judgement applies only to the 79 in the 500–700 band.
- [ ] The document states, before the appendix and as binding tree-wide rather than pilot-only, that a status variant's class triple migrates as a unit or not at all, that every member must have a row, and that the resulting foreground/background pair must hold ≥ 4.5:1 re-derived with `src/lib/contrast.ts`; and that where the appendix's class-level row conflicts with a call site inside a status tint triple, the triple's verdict governs.
- [ ] The appendix's red row is labelled conditionally — `destructive` except where the class belongs to a red tint triple, which stays `GAP-TINT` — and the document publishes the measurement behind it: `text-red-700` on `bg-red-50` 5.9842:1 passes, `text-destructive` on `bg-red-50` 4.4006:1 fails, `text-destructive` on `bg-red-100` 3.9381:1 fails, with 29 of the 62 `text-red-[567]00` occurrences in that position.
- [ ] The document states that the pilot exercises neither the `dark:` rule nor §1f case 2, and that case 2 is invisible to every test in this task because `muted` and `accent` are byte-identical in `:root`.
- [ ] The document ends with a mechanically generated appendix partitioning exactly 152 distinct non-`dark:` palette classes over 2,369 occurrences in `frontend/src`, each with a row or a code and none left over.
- [ ] The document states the `dark:` rule in both directions: a `dark:` sibling of a migrated class is deleted, and a `dark:` sibling of a gap class is left untouched and logged under its base's code.
- [ ] `docs/frontend/unmapped-colours.md` exists, documents the six-column format (`task, file, line, class, code, why`) and the rule that no task may add a property to `frontend/src/index.css`, and carries the 24 rows left untouched in `src/components/ui/` — 12 under `GAP-TINT`, 10 under `GAP-NO-TOKEN`, 1 under `GAP-NO-SURFACE` and 1 under `GAP-OVERLAY`.
- [ ] `frontend/src/__tests__/themeTokenMigration.test.ts` exists, exports `MIGRATED_DIRECTORIES` containing exactly `"src/components/ui"`, and passes.
- [ ] The guard's grammar lists its scale alternatives longest-first, and a test asserts that its match of `text-gray-500` is the whole class rather than `text-gray-50`.
- [ ] The guard fails when `hover:dark:bg-slate-800/40` is added to a file under a pinned directory, and when a 6-digit hex literal is added inside a `className` there.
- [ ] `frontend/src/__tests__/themeTokenMigration.exceptions.json` exists, every entry has exactly the keys `file`, `class`, `code`, `task`, and the guard fails on an unknown `code`, on an entry whose class is absent from its file, and on an entry with no matching ledger row.
- [ ] A test compiles `frontend/src/index.css` through Tailwind 4.2.4's `compile()` over a fixture of every class pair in §1b–1e and asserts each pair's ΔL and ΔE equal the published values to within 0.1.
- [ ] That test resolves `--primary` to `oklch(0.62 0.15 160)` and asserts it is not `oklch(0.65 0.15 160)`, so a last-wins resolver that reads `.dark` fails loudly.
- [ ] For each opacity-modified target the test reads the unconditional declaration for the colour comparison and separately asserts the `@supports` declaration is `color-mix(in oklab, var(--color-primary) 90%, transparent)`.
- [ ] The brand-reach test mounts a migrated `components/ui` component with `TenantBrandTheme` under a mocked `useTenantProfile` and asserts the resolved `--primary` equals the mocked derived theme's value, with no colour literal in the assertion.
- [ ] `frontend/src/components/ui/button.tsx` contains no `emerald` class at all, and in `alert-modal.tsx` the three success-button classes at line 120 are gone while the success *status* classes at lines 28–30 (`text-emerald-500`, `text-emerald-700`, `border-emerald-200`) are still present unchanged, because migrating them is forbidden by the status-colour ruling.
- [ ] `text-white` no longer appears on a `bg-primary` or `bg-destructive` element anywhere in `src/components/ui/`, and still appears at `alert-modal.tsx:122` on `bg-amber-500`, logged under `GAP-NO-SURFACE`.
- [ ] `frontend/src/components/ui/alert.tsx` and `badge.tsx` are unmodified.
- [ ] `frontend/src/index.css` is byte-identical to its state before the task, and the `.dark` block is still never applied.
- [ ] `npx tsc -b` is clean and `npx vitest run --coverage` passes at 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint .` shows no new error or warning against the baseline of 375 errors + 2 warnings across 64 files, with the touched files contributing zero.
- [ ] No file under `backend/` is modified, no Alembic revision is added, and the route registry is unchanged.

## Out of Scope

- Any file outside `frontend/src/components/ui/` and the listed docs/tests.
- Adding, renaming or revaluing any property in `frontend/src/index.css`, including any success/warning/info token.
- Migrating any success, warning or info colour — permanently excluded by the operator ruling.
- Enabling or exercising the `.dark` block.
- Playwright, Storybook, Chromatic, Percy or any other visual-regression or computed-style infrastructure.
- Removing the now-duplicate `success` button variant (an API change).
- Inverting the guard to a repo-wide deny — that is APRAS-85.
- Any backend, migration or route-registry change.

## Operator note (non-blocking; the spec has a default and proceeds)

**21 focus rings stay blue.** `focus:ring-blue-500` appears 21 times and
`ring-indigo-500` 16 times, both as focus rings. Indigo migrates to `ring-ring`
under the named decision; blue has no token, so by §1h precedence it is
`GAP-NO-TOKEN` and stays. The app will therefore have two kinds of focus ring,
one branded and one blue.

Measured, `ring-blue-500 → ring-ring` is **ΔL 0.30** (L 62.30 → 62.00) — the
two are lightness-identical and the entire **ΔE 28.15** is hue, the same shape
as the already-accepted indigo move. Naming it would migrate all 21 with no
lightness change at all.

**Question:** name `blue → primary/ring` as a fourth accepted move, on the same
footing as indigo? The default, absent an answer, is `GAP-NO-TOKEN`: the rings
stay blue and are logged, and a later task can migrate them. APRAS-78 proceeds
either way.
