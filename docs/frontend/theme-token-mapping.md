# The theme token mapping

The authoritative class → token table for `frontend/src`, published by
**APRAS-78** (child 1 of 8 of the APRAS-77 split).

Children APRAS-79 … APRAS-85 **consume** this document, the ledger in
[`unmapped-colours.md`](./unmapped-colours.md) and the guard in
`frontend/src/__tests__/themeTokenMigration.test.ts`. They may not re-derive,
extend or amend any of the three: **a sibling may not add a row, add a gap
code, or add a token.** A sibling that believes a row is wrong, or unusable at
its call site, **raises a table-amendment task against APRAS-78's artefacts and
blocks on it** — it does **not** reach for `GAP-UNLISTED`, which is defined
(§1h code 8) for a class that has **no** row and no other code, and was never
meant to cover a class that has one. APRAS-88 is the worked example: brand text
had a row, the row was wrong, and the answer was an amendment — this §1k — not
an exception. One owner, seven consumers.

## How the numbers were derived

Source side: `frontend/node_modules/tailwindcss/theme.css`, Tailwind
**4.2.4**. Target side: the `:root` block of `frontend/src/index.css`. Both
sides are `oklch()`, so **ΔL** is directly comparable; **ΔE** is the euclidean
distance in OKLab over (ΔL, Δa, Δb) with L in 0–100 units and chroma scaled by
100. Neither figure involves gamut mapping, so both are exact arithmetic on the
two declared values. All figures are published **to two decimals**, because
`frontend/src/__tests__/themeTokenCompile.test.ts` re-derives every one of them
from the compiled stylesheet and asserts it to **±0.1**.

Contrast ratios are a different measurement and are **never** computed from
ΔL or ΔE. Every ratio in this document is re-derived with
`frontend/src/lib/contrast.ts` (OKLab → linear sRGB, chroma-bisection gamut
map, WCAG 2.1) — the repository's single contrast implementation, which is
imported and never reimplemented.

## Binding context (restated, not re-decided)

The operator's decision on APRAS-77 is binding and **no review may report any
of these as a defect**:

- primary buttons go from white-on-indigo (and white-on-emerald) to
  dark-on-emerald, because APRAS-76 made `--primary-foreground` dark;
- `text-slate-400` → `text-muted-foreground` darkens by 17.40 L points, which
  incidentally repairs a contrast failure;
- `indigo` shifts from hue 277 to hue 160.

APRAS-77's literal wording "the colours must not move" is **not achievable**
and this document does not pretend otherwise. Neutral surface and border rows
land within 1–3 ΔE and are effectively invisible; the three groups above move
plainly and are accepted. They are **operator-named moves, not regressions**.

### The status-colour ruling (operator) — binding and permanent

**Success, warning and info colours stay hard-coded** and are **never**
migrated.

> A status colour is **semantic, not brand**. Green means success in every
> condominium, and a condominium whose brand is red must not see "success"
> rendered in red.

The ruling is about **not migrating**; it does not fix the ledger label. Each
such class is logged under whichever code §1h's precedence assigns:
**`GAP-TINT`** for `emerald` and `red`, families that have a token which is
deliberately withheld, and **`GAP-NO-TOKEN`** for `amber` and `blue`, families
with no token at all. Both codes forbid migration equally, so the outcome is
identical either way and only the recorded label differs; the ledger's `why`
column still names the role (`warning alert tint`).

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
   overridden by a tenant (`frontend/src/api/tenantProfile.ts` states this
   explicitly). Binding error colours to it changes nothing semantically — a
   red-branded condominium still sees errors in the same red. (Subject to
   §1j's tint-triple exception, which is a *contrast* constraint, not a
   semantic one.)
2. **Success stays**, and **not** because its token is missing. Emerald's
   token exists: `--primary` is `oklch(0.62 0.15 160)`. `--primary` is a
   **brand** token, so binding success to it would make "success" follow the
   tenant's brand — exactly what the ruling forbids. Success is the paradigm
   case of a token that exists and is **deliberately withheld**, which is what
   §1h code 4 `GAP-TINT` names.
3. **Warning and info stay** because **no token exists at all** — there is no
   `--warning` and no `--info`, and `amber` and `blue` have no row at any
   scale. That is §1h code 3 `GAP-NO-TOKEN`, which precedence puts first.

Adding `--success` / `--warning` / `--info` on the same never-branded footing
as `--destructive` is the natural follow-up and is **out of scope** (it would
extend `build_theme`, a backend change).

---

## 1a. The budget rule

| ΔE | Budget class | Meaning |
| --- | --- | --- |
| ≤ 3 | `invisible` | migrate silently |
| > 3 and ≤ 12 | `noted` | migrate; the row carries a one-line note |
| > 12 | `moves` | migrate **only** if the operator decision names it |
| > 12, unnamed | `GAP` | do not migrate; log under a code from §1h |

`GAP` is a fourth value of the budget-class column, not a separate concept: it
is what a `moves` row becomes when the operator decision does not name it. The
**five** named moves are:

1. the **indigo family**, which since APRAS-88 names **two** targets and since
   APRAS-84 names **three** — `*-primary` for graphical objects,
   **`*-primary-text` for characters** (§1k), and
   **`accent-primary-foreground` for `accent-indigo-600`**, the one `accent-`
   utility in the tree, at ΔE 45.18. The third has to be named because ΔE
   45.18 is over 12, which makes the row `moves`, and a `moves` row the
   operator decision does not name is a `GAP`;
2. **`text-*-400` → `text-muted-foreground`**;
3. **`text-white` → `text-primary-foreground`**;
4. **`text-emerald-500` → `text-primary-text`**, at ΔE 18.60 (APRAS-88,
   operator-vetoable). It needs naming because emerald-as-brand is otherwise
   `noted` and inside budget: retargeting it to the darker text token pushes
   4 occurrences past every emerald figure this document published. The
   alternative — a new gap code — is worse, because it reopens a set §1h
   requires to stay closed at eight;
5. **`bg-slate-300` → `bg-primary`**, at ΔE 29.21 (APRAS-84). The zoom-slider
   track at `AvatarCropEditor.tsx`, the tree's only occurrence of that class.
   Named for the same budget reason: the operator decided the track carries the
   tenant's brand and the thumb carries the token the theme guarantees is
   legible on it, which is a swap of the colour-carrying roles rather than a
   call-site judgement. §1f case 2 cannot reach it — case 2's candidate set is
   `muted` / `accent` and its scope is the 50/100/200 scales.

## 1b. Neutral surfaces

| Source class | Target | L source → target | ΔL | ΔE | Budget |
| --- | --- | --- | --- | --- | --- |
| `bg-white` | **context — §1f case 1** | 100.00 → 100.00 / 99.00 | 0.00 / 1.00 | 0.00 / 1.00 | invisible |
| `bg-slate-50` | `bg-muted` / **§1f case 2** | 98.40 → 96.00 | 2.40 | 2.61 | invisible |
| `bg-gray-50` | `bg-muted` / **§1f case 2** | 98.50 → 96.00 | 2.50 | 2.70 | invisible |
| `bg-slate-100` | `bg-muted` / **§1f case 2** | 96.80 → 96.00 | 0.80 | 1.44 | invisible |
| `bg-gray-100` | `bg-muted` / **§1f case 2** | 96.70 → 96.00 | 0.70 | 1.32 | invisible |
| `bg-slate-200` | `bg-muted` / **§1f case 2** | 92.90 → 96.00 | 3.10 | 3.54 | noted |
| `bg-gray-200` | `bg-muted` / **§1f case 2** | 92.80 → 96.00 | 3.20 | 3.45 | noted |
| `bg-slate-300` | `bg-primary` | 86.90 → 62.00 | 24.90 | 29.21 | moves (**named**) |
| `bg-slate-900` | `bg-foreground` | 20.80 → 14.00 | 6.80 | 8.20 | noted |
| `bg-slate-950` | `bg-foreground` | 12.90 → 14.00 | 1.10 | 4.69 | noted |

`bg-secondary` and `bg-accent` are byte-identical to `bg-muted` in `:root`
(`oklch(0.96 0.01 160)`), so every ΔL / ΔE above is the same for all three.
They are **not** interchangeable: `build_theme` lets a tenant author them
apart, so the choice is semantic and is resolved by §1f case 2.

## 1c. Neutral borders, dividers and rings

| Source class | Target | L source → target | ΔL | ΔE | Budget |
| --- | --- | --- | --- | --- | --- |
| `border-slate-200` | `border-border` | 92.90 → 92.00 | 0.90 | 1.94 | invisible |
| `border-gray-200` | `border-border` | 92.80 → 92.00 | 0.80 | 1.52 | invisible |
| `divide-slate-200` | `divide-border` | 92.90 → 92.00 | 0.90 | 1.94 | invisible |
| `divide-gray-200` | `divide-border` | 92.80 → 92.00 | 0.80 | 1.52 | invisible |
| `border-slate-300` | `border-input` | 86.90 → 92.00 | 5.10 | 5.66 | noted (form borders lighten) |
| `border-gray-300` | `border-input` | 87.20 → 92.00 | 4.80 | 5.03 | noted (form borders lighten) |
| `border-white` | `border-card` | 100.00 → 100.00 | 0.00 | 0.00 | invisible |

The four `divide-` classes present in the tree (13 occurrences) are covered:
`divide-*-200` here, `divide-*-100` as a gap in §1h.

## 1d. Neutral text

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

## 1e. Brand, accent and destructive

| Source class | Target | L source → target | ΔL | ΔE | Budget |
| --- | --- | --- | --- | --- | --- |
| `bg-indigo-500` / `border-indigo-500` | `*-primary` | 58.50 → 62.00 | 3.50 | 33.15 | moves (**named**) |
| `text-indigo-500` (**§1k**) | `text-primary-text` | 58.50 → 52.00 | 6.50 | 30.66 | moves (**named**) |
| `ring-indigo-500` | `ring-ring` | 58.50 → 62.00 | 3.50 | 33.15 | moves (**named**) |
| `bg-indigo-600` / `border-indigo-600` | `*-primary` | 51.10 → 62.00 | 10.90 | 37.24 | moves (**named**) |
| `accent-indigo-600` | `accent-primary-foreground` | 51.10 → 15.00 | 36.10 | 45.18 | moves (**named**) |
| `text-indigo-600` (**§1k**) | `text-primary-text` | 51.10 → 52.00 | 0.90 | 32.71 | moves (**named**) |
| `bg-indigo-700` | `bg-primary` (see §1i for `/90`) | 45.70 → 62.00 | 16.30 | 37.33 | moves (**named**) |
| `text-indigo-700` (**§1k**) | `text-primary-text` | 45.70 → 52.00 | 6.30 | 31.25 | moves (**named**) |
| `text-indigo-800` (**§1k**) | `text-primary-text` | 39.80 → 52.00 | 12.20 | 29.11 | moves (**named**) |
| `text-indigo-900` (**§1k**) | `text-primary-text` | 35.90 → 52.00 | 16.10 | 27.20 | moves (**named**) |
| `text-indigo-300` (**§1k**) | `text-primary-text` | 78.50 → 52.00 | 26.50 | 32.58 | moves (**named**) |
| `border-indigo-400` | `border-primary` | 67.30 → 62.00 | 5.30 | 28.84 | moves (**named**) |
| `bg-indigo-50` | `bg-accent` | 96.20 → 96.00 | 0.20 | 2.38 | invisible |
| `bg-indigo-100` | `bg-accent` | 93.00 → 96.00 | 3.00 | 4.92 | noted |
| `bg-indigo-200` | `bg-accent` | 87.00 → 96.00 | 9.00 | 11.38 | noted |
| `border-indigo-100` | `border-border` | 93.00 → 92.00 | 1.00 | 4.02 | noted |
| `border-indigo-200` | `border-border` | 87.00 → 92.00 | 5.00 | 8.58 | noted |
| `bg-emerald-500` / `border-emerald-500` | `*-primary` (**§1f case 3**) | 69.60 → 62.00 | 7.60 | 7.89 | noted |
| `text-emerald-500` (**§1k**, **§1f case 3**) | `text-primary-text` | 69.60 → 52.00 | 17.60 | 18.60 | moves (**named**) |
| `ring-emerald-500` | `ring-ring` (**§1f case 3**) | 69.60 → 62.00 | 7.60 | 7.89 | noted |
| `bg-emerald-600` / `border-emerald-600` | `*-primary` (**§1f case 3**) | 59.60 → 62.00 | 2.40 | 2.59 | invisible |
| `text-emerald-600` (**§1k**, **§1f case 3**) | `text-primary-text` | 59.60 → 52.00 | 7.60 | 8.40 | noted |
| `ring-emerald-600` | `ring-ring` (**§1f case 3**) | 59.60 → 62.00 | 2.40 | 2.59 | invisible |
| `bg-emerald-700` | `bg-primary` (**§1f case 3**, see §1i) | 50.80 → 62.00 | 11.20 | 11.72 | noted |
| `text-emerald-700` (**§1k**, **§1f case 3**) | `text-primary-text` | 50.80 → 52.00 | 1.20 | 1.82 | invisible |
| `text-red-600` / `bg-red-600` | `*-destructive` | 57.70 → 58.00 | 0.30 | 0.60 | invisible |
| `text-red-500` / `bg-red-500` | `*-destructive` | 63.70 → 58.00 | 5.70 | 5.75 | noted |
| `text-red-700` / `bg-red-700` | `*-destructive` | 50.50 → 58.00 | 7.50 | 7.97 | noted |
| `text-white` on `bg-destructive` | `text-destructive-foreground` | 100.00 → 98.00 | 2.00 | 2.00 | invisible |
| `text-white` on `bg-primary` | `text-primary-foreground` | 100.00 → 15.00 | 85.00 | 85.02 | moves (**named**) |

The nine `text-` rows above are **§1k rows**: they were split out of the
combined rows in APRAS-88 and retargeted from `*-primary` to
`*-primary-text`, and every one of their Budget classes is recomputed from the
**new** ΔE against `oklch(0.52 0.11 160)` — which moves two of them,
`text-emerald-700` from `noted` (11.72) to **`invisible`** (1.82) and
`text-emerald-500` from `noted` (7.89) to **`moves`** (18.60, named in §1a).
Every `bg-`, `border-`, `ring-` and `accent-` figure is unchanged. The
retargeting is done **in place**, in this table and in
`themeTokenCompile.test.ts`: an appended row would leave the old
`text-*` → `text-primary` row passing — `--primary` does not move — and the
suite would go green over a table contradicting itself.

The indigo rows are individually enumerated rather than folded into one
"indigo family" row, because every one of them carries different numbers and
the compile test asserts each to ±0.1. Every red row above is **conditional**:
see §1j's preamble, which is what governs a red class inside a tint triple.
**`ring-blue-500` has no row in this table** — it is listed under
`GAP-NO-TOKEN` in §1h and §1j, and the operator note at the end explains why
21 focus rings stay blue.

## 1f. The context-dependent cases — the part the test cannot catch

Three source patterns have **no single correct target**. The choice is a human
judgement at each call site, and **the verification test cannot detect a wrong
choice in any of them**, because in cases 1 and 2 both candidates are
identical in `:root` and in case 3 both candidates are legal classes.

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
`bg-amber-500` — it is a gap, not a row (§1h code 5).
The second clause of the rule is **not** scoped to `bg-white`: an element that **is** the page takes `bg-background` whatever its source class, so a page root written `bg-slate-50` or `bg-gray-50` takes `bg-background` and **not** the `bg-muted` its §1b row would otherwise give it — case 1 is consulted before the row, and before case 2. (Operator ruling on APRAS-81 and APRAS-83; carried by APRAS-81.)

**Case 2 — neutral fills at 50/100/200: `bg-muted` or `bg-accent`.**
A fill that is the element's *resting* surface (a panel, a table header, a
code block) is `bg-muted`. A fill that appears on **interaction** —
`hover:`, `focus:`, `focus-visible:`, `group-hover:`, `aria-selected:`,
`data-[state=…]:` — is `bg-accent`, because `accent` is the interaction token
`button.tsx` already uses (`hover:bg-accent hover:text-accent-foreground`).
Measured in the tree: **17** `hover:bg-slate-100`, **15** `hover:bg-gray-100`,
**12** `hover:bg-slate-50`, **6** `hover:bg-gray-50`, **2**
`hover:bg-slate-200`, **2** `hover:bg-gray-200` — 54 occurrences that take
`bg-accent`, against 118 resting fills that take `bg-muted`. The two are
byte-identical in `:root` and differ only under a tenant theme, so **this case
is invisible to every test in this task and is purely a review duty.**

**Case 3 — emerald at 500/600/700: brand accent or success status.**
Emerald is simultaneously the default brand hue (`--primary` is
`oklch(0.62 0.15 160)`) and the conventional success colour, so the same class
means two different things in two places.

**First, note how narrow the judgement is.** Of the **169 non-`dark:`** emerald
occurrences in `frontend/src` (there are a further **54** `dark:` ones, **223**
all in, which §1g governs rather than this case — an implementer who
regenerates the count without excluding `dark:` will get 223 and think the
figure is wrong), **90** are resolved unconditionally by scale alone: emerald
at **50/100/200/300** and at **800/900/950** is *always* `GAP-TINT`, because at
those scales it is only ever a tint surface or on-tint text, never an
interactive fill. Judgement applies only to the **79** occurrences in the
**500–700** band, and only there.

Within that band the discriminator is **one test, and only one**:

- **Migrates to `primary`** — the element is **interactive**: a `<button>` or
  `<a>` fill, a focus ring, an interactive border.
- **Stays hard-coded (`GAP-TINT`)** — the element is **non-interactive**: an
  alert tint, a badge, a status dot, a variant icon or heading, and any border
  belonging to such a variant.

*Interactive* means the element is a control, or is inside one that the colour
belongs to. Nothing else enters the test — in particular, do **not** ask
whether colour is the only signal. That formulation is **rationale, never the
test**: `alert-modal.tsx:28`'s success icon is a `CheckCircle2` glyph whose
*shape* also carries the meaning, so the "only signal" clause returns the
opposite verdict to the one §4a records.

**Rationale, so no sibling relitigates this.** The principle is **WCAG 1.4.1
(Use of Colour)**, reused as a migration rule: where colour is the carrier of
meaning, the colour is semantic and stays; where the accessible name carries
the meaning, the colour is decoration and takes the brand. A button's label
says what it does, so the status ruling's own justification — *a red-branded
condominium must not see "success" rendered in red* — does not reach it; a
green panel with no other signal is exactly what that sentence protects. The
alternative was tested and rejected by the operator: it would leave exactly
one button in the app that the tenant's brand can never reach, which is the
defect APRAS-68 existed to remove.

This boundary is the one place where the operator's status-colour ruling and
the APRAS-77 button decision meet. Both are honoured, and the matter is
settled: do not reopen it.

## 1g. The `dark:` variant rule

Measured with the §3b grammar: **872** `dark:`-prefixed palette occurrences
across **63** distinct classes, out of **3,241** total occurrences in the
**114** files that contain any, out of 260 non-test files scanned.

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

`src/components/ui/` contains **zero** `dark:` occurrences, so **the pilot
provides no evidence for either half of this rule**; it is argued from token
semantics and the risk is bounded because `.dark` is never applied. The first
sibling that meets one proves it.

## 1h. Gap codes — the closed set

Nothing may be excepted from the guard except under one of these codes.
**Precedence is top to bottom**: a class matching two codes takes the first.

The order is **objective codes first, judgement codes last**. `GAP-NO-TOKEN`
is a fact about `index.css` that two implementers cannot disagree about;
`GAP-TINT` requires reading the call site. Putting the objective code first
removes the ambiguity without weakening anything, because **both codes forbid
migration equally**; only the recorded label differs, and the ledger's `why`
column still records the role (`warning alert tint`).

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
Siblings may **not** add codes, add rows, or add tokens.

### The gap measurements

`GAP-BORDER-100` and `GAP-OUT-OF-BUDGET` are the two codes that rest on a
number rather than on a role, so the numbers are published. The **quoted ΔE**
is the figure APRAS-77's decision record carries for that class; the
**candidate ΔE** columns are every target §1b–1e admits for the class's own
utility prefix and role, which is what §1h code 7 is defined against. Each
class is a gap on both readings.

| Class | Occ. | Quoted ΔE | …measured against | §1b–1e candidates for its role | Verdict |
| --- | --- | --- | --- | --- | --- |
| `border-slate-100` | 41 | 4.95 | `border` | `border` 4.95, `input` 4.95 | `GAP-BORDER-100` |
| `border-gray-100` | 12 | 4.83 | `border` | `border` 4.83, `input` 4.83 | `GAP-BORDER-100` |
| `divide-slate-100` | 4 | 4.95 | `border` | `border` 4.95 | `GAP-BORDER-100` |
| `divide-gray-100` | 3 | 4.83 | `border` | `border` 4.83 | `GAP-BORDER-100` |
| `ring-gray-100` | 1 | 4.83 | `border` | `ring` 37.83 | `GAP-BORDER-100` |
| `text-gray-700` | 73 | 17.81 | `secondary-foreground` | `foreground` 23.59, `muted-foreground` 16.26 | `GAP-OUT-OF-BUDGET` |
| `text-slate-700` | 71 | 17.93 | `secondary-foreground` | `foreground` 23.66, `muted-foreground` 16.59 | `GAP-OUT-OF-BUDGET` |
| `text-gray-800` | 47 | 14.25 | `foreground` | `foreground` 14.25, `muted-foreground` 25.52 | `GAP-OUT-OF-BUDGET` |
| `text-slate-800` | 16 | 14.58 | `foreground` | `foreground` 14.58, `muted-foreground` 25.57 | `GAP-OUT-OF-BUDGET` |
| `text-slate-300` | 3 | 34.04 | `muted-foreground` | `foreground` 72.94, `muted-foreground` 34.04 | `GAP-OUT-OF-BUDGET` |
| `ring-slate-500` | 2 | 17.54 | `ring` | `ring` 17.54 | `GAP-OUT-OF-BUDGET` |
| `border-slate-800` | 1 | 14.58 | `foreground` | `border` 64.25, `input` 64.25 | `GAP-OUT-OF-BUDGET` |
| `text-red-400` | 1 | 13.45 | `destructive` | `destructive` 13.45 | `GAP-OUT-OF-BUDGET` |

So `text-slate-800` → `text-foreground` is published at **ΔE 14.58** and
`text-gray-800` at **ΔE 14.25**, both **`GAP`**; `text-slate-700` at
**17.93** and `text-gray-700` at **17.81**, both `GAP`; and
`border-slate-100` / `border-gray-100` at **4.95 / 4.83**, gaps by role rather
than by budget. Two rows are worth reading twice: the quoted figure for
`border-slate-800` and for the 700s is measured against a token that is *not*
a candidate for that class's role, which is why the candidate column is
published beside it — the verdict is unchanged either way.

## 1i. Opacity-modified targets

One target carries an alpha today: **`bg-primary/90`**, used for
`bg-indigo-700`, `hover:bg-emerald-700` and the `button.tsx` triple. Any
future `*/N` target follows the same rule:

- **The colour is measured against the base token, and the alpha is declared
  unmeasured.** The row's published ΔL / ΔE are those of `bg-primary` — so
  `bg-indigo-700` → `bg-primary/90` publishes 16.30 / 37.33, the
  `indigo-700 → primary` figures.
- The resolver takes the **unconditional** declaration. Compiled,
  `bg-primary/90` emits `background-color: var(--color-primary)` followed by
  an `@supports (color: color-mix(in lab, red, red))` block re-declaring it as
  `color-mix(in oklab, var(--color-primary) 90%, transparent)`. `parseOklch`
  returns `null` for `color-mix`, so the resolver must read the first,
  unconditional declaration and never the `@supports` one.
- The alpha is nonetheless **checked structurally**: the test asserts the
  `@supports` declaration matches
  `color-mix(in oklab, var(--color-<token>) <N>%, transparent)` with the `N`
  the row declares. The alpha is verified as *present and correct*, just not
  colorimetrically composited.

## 1j. Exhaustiveness — the published appendix

**Read this before the appendix: it partitions at *class* granularity, but the
unit of migration is the *call site*.** A row says what a class means when
nothing else constrains it. Where a call site puts that class inside a
**status tint triple** — a surface, a border and a foreground that encode one
status together — **the triple's verdict governs**, and the class stays even
though its row says migrate. This is general: it holds for every family, now
and for any family a later task adds, and it is the reason emerald's row
carries a dual label. **A cell in the table is never authority to split a
triple.**

The two rules that do the work are stated here and are **binding tree-wide,
not only in the pilot**:

- **Triple-as-a-unit.** A status variant's class triple migrates **as a unit
  or not at all**, and only if **every** member has a row in §1b–1e.
- **The ≥ 4.5:1 clause.** A triple may migrate only if the resulting
  foreground/background pair holds **≥ 4.5:1**, re-derived with
  `frontend/src/lib/contrast.ts` — never by eye, and never with the ΔL / ΔE
  arithmetic in this document, which omits the gamut mapping `contrast.ts`
  performs. §4a *applies* these two rules to `components/ui`; it does not own
  them.

### Why the red row is conditional

Red is the family where the class-level row and the call-site rule pull
hardest in opposite directions, and following the row alone ships a **measured
AA regression**. **29 of the 62** `text-red-[567]00` occurrences in
`frontend/src` (25 `text-red-700`, 4 `text-red-600`) share a class string with
a red tint surface — forms literally repeated across the tree, such as
`"rounded-lg bg-red-50 p-2 text-sm text-red-700"` and `"bg-red-50
text-red-700 text-sm p-3 rounded-lg border border-red-200"`. `bg-red-50`,
`bg-red-100` and `border-red-200` are all `GAP-TINT` in the appendix below, so
the surface cannot move; migrating the text alone gives, measured with
`frontend/src/lib/contrast.ts` (OKLab → linear-sRGB, chroma-bisection gamut
map, WCAG 2.1):

| Pair | Ratio | Verdict |
| --- | --- | --- |
| `text-red-700` on `bg-red-50` — today | **5.9842:1** | passes AA |
| `text-destructive` on `bg-red-50` — after migrating the text alone | **4.4006:1** | **fails AA** |
| `text-destructive` on `bg-red-100` | **3.9381:1** | **fails AA** |

This is the mirror image of §4a's emerald argument ("migrating the surface
alone is incoherent"): for red it is the *foreground* that cannot move alone.
So a red 500–700 class inside a tint triple is **`GAP-TINT`** (code 4 — an
error status in a family that has a token), and only a free-standing red class
— an error message on a neutral or white background, an icon, a destructive
control — takes the §1e row.

Pre-existing and **not** this task's to fix: `text-red-600` on `bg-red-50`
already measures **4.4506:1** and fails AA today. Those sites keep their
current classes, and the ledger's `why` should say so, so a later reader does
not attribute the failure to this migration.

### Why `amber` and `blue` are not split the way `red` and `emerald` are

`red` and `emerald` have tokens, so a status use of them is a token
deliberately withheld — `GAP-TINT`, code 4 — while a non-status use takes a
row. `amber` (133 occurrences) and `blue` (75) have no token at any scale, so
code 3 `GAP-NO-TOKEN` catches them first, whatever their role. They are
therefore listed family-wise below, consistent with §1h's precedence. The
outcome is identical either way: leave the class untouched and log it.

### The appendix

Generated **mechanically**, not by eye: walk `frontend/src` for `.ts` / `.tsx`
excluding `__tests__/` and `*.test.*`, apply the §3b grammar, strip variants
and the opacity modifier, and group. The figures below are the state of the
tree at APRAS-78's baseline, **before** the pilot migration, so that a sibling
regenerating them is comparing like with like; the pilot then removes 7 of
them (`bg-emerald-600` 9 → 7, `bg-emerald-700` 11 → 9, `text-white` 49 → 46)
and no class disappears.

**152 distinct non-`dark:` classes over 2,369 occurrences**, plus 63 distinct
`dark:` classes over 872 — **3,241** occurrences in total, in **114** files
that match, out of 260 files scanned. Every one of the 152 is accounted for,
with **no residue**.

| Verdict | Classes | Occ. |
| --- | --- | --- |
| §1b `bg-*-50/100/200` → `bg-muted` / `bg-accent` | `bg-slate-50` 41, `bg-slate-100` 38, `bg-gray-50` 33, `bg-gray-100` 30, `bg-slate-200` 4, `bg-gray-200` 2 | 148 |
| §1b `bg-slate-300` → `bg-primary` | `bg-slate-300` 1 | 1 |
| §1b `bg-*-900/950` → `bg-foreground` | `bg-slate-950` 4, `bg-slate-900` 3 | 7 |
| §1c → `border-border` / `divide-border` | `border-gray-200` 107, `border-slate-200` 90, `divide-slate-200` 5, `divide-gray-200` 1 | 203 |
| §1c → `border-input` | `border-slate-300` 56, `border-gray-300` 24 | 80 |
| §1d → `text-foreground` | `text-slate-900` 106, `text-gray-900` 73 | 179 |
| §1d → `text-muted-foreground` | `text-gray-500` 126, `text-slate-500` 95, `text-slate-400` 59, `text-slate-600` 55, `text-gray-600` 38, `text-gray-400` 33 | 406 |
| §1e indigo → `primary` / `ring` | `text-indigo-600` 67, `bg-indigo-600` 29, `bg-indigo-700` 22, `ring-indigo-500` 16, `text-indigo-700` 12, `text-indigo-500` 9, `text-indigo-800` 3, `border-indigo-500` 2, `border-indigo-600` 2, `accent-indigo-600` 1, `bg-indigo-500` 1, `border-indigo-400` 1, `text-indigo-300` 1, `text-indigo-900` 1 | 167 |
| §1e indigo tints → `accent` / `border` † | `bg-indigo-50` 25, `border-indigo-200` 5, `bg-indigo-100` 3, `border-indigo-100` 3, `bg-indigo-200` 1 | 37 |
| §1e red → `destructive`, **except where the class belongs to a red tint triple (see this section's preamble), which stays `GAP-TINT`** — **29** of the 62 `text-red-[567]00` occurrences are in that position | `text-red-600` 26, `text-red-700` 26, `text-red-500` 10, `bg-red-500` 3, `bg-red-600` 1, `bg-red-700` 1 | 67 |
| §1f case 3 emerald 500–700 (brand **or** `GAP-TINT`) | `text-emerald-600` 24, `text-emerald-700` 22, `bg-emerald-700` 11, `bg-emerald-600` 9, `bg-emerald-500` 4, `text-emerald-500` 3, `border-emerald-600` 2, `ring-emerald-600` 2, `border-emerald-500` 1, `ring-emerald-500` 1 | 79 |
| §1f case 1 white/black | `bg-white` 203, `text-white` 49, `border-white` 2 → rows; `bg-black` 54 → `GAP-OVERLAY` | 308 |
| `GAP-TINT` | `bg-red-50` 31, `bg-emerald-50` 30, `border-red-200` 23, `text-emerald-800` 19, `border-emerald-200` 16, `bg-emerald-100` 14, `text-emerald-900` 8, `bg-red-100` 7, `text-red-800` 6, `border-emerald-300` 3 | 157 |
| `GAP-NO-TOKEN` | 67 classes across `amber`, `blue`, `green`, `orange`, `yellow`, `cyan`, `sky`, `teal`, `purple`, `pink`, `rose` — largest: `text-amber-700` 24, `bg-amber-50` 21, `ring-blue-500` 21, `bg-amber-100` 16, `text-amber-800` 15, `border-amber-200` 14, `text-amber-600` 14; full list below | 255 |
| `GAP-BORDER-100` | `border-slate-100` 41, `border-gray-100` 12, `divide-slate-100` 4, `divide-gray-100` 3, `ring-gray-100` 1 | 61 |
| `GAP-OUT-OF-BUDGET` | `text-gray-700` 73, `text-slate-700` 71, `text-gray-800` 47, `text-slate-800` 16, `text-slate-300` 3, `ring-slate-500` 2, `border-slate-800` 1, `text-red-400` 1 | 214 |

**152 classes, 2,369 occurrences, no residue.**

† `border-indigo-100` takes its explicit §1e row rather than `GAP-BORDER-100`:
§1h code 6 names the neutral hairline dividers, and a class that §1e
enumerates by name is governed by that row. It is the only class in the tree
where the two overlap.

The 67 `GAP-NO-TOKEN` classes in full, so the appendix is exhaustive rather
than summarised:

`text-amber-700` 24, `bg-amber-50` 21, `ring-blue-500` 21, `bg-amber-100` 16,
`text-amber-800` 15, `border-amber-200` 14, `text-amber-600` 14, `bg-blue-50` 9,
`text-amber-900` 7, `text-blue-600` 7, `bg-blue-100` 6, `border-blue-500` 6,
`text-blue-700` 6, `text-blue-800` 6, `bg-amber-500` 5, `border-blue-200` 4,
`bg-amber-400` 3, `bg-blue-600` 3, `bg-blue-700` 3, `bg-purple-50` 3,
`text-amber-500` 3, `text-purple-700` 3, `bg-amber-600` 2, `bg-orange-100` 2,
`bg-rose-50` 2, `bg-rose-500` 2, `bg-sky-100` 2, `border-amber-300` 2,
`border-amber-500` 2, `ring-blue-700` 2, `text-orange-800` 2, `text-rose-600` 2,
`text-sky-800` 2, `bg-amber-200` 1, `bg-amber-700` 1, `bg-blue-500` 1,
`bg-cyan-50` 1, `bg-green-50` 1, `bg-green-500` 1, `bg-orange-500` 1,
`bg-pink-50` 1, `bg-purple-500` 1, `bg-rose-100` 1, `bg-teal-50` 1,
`bg-yellow-200` 1, `border-amber-950` 1, `border-cyan-200` 1,
`border-orange-200` 1, `border-purple-200` 1, `border-rose-200` 1,
`border-teal-200` 1, `ring-amber-600` 1, `ring-pink-700` 1, `ring-purple-600` 1,
`ring-purple-700` 1, `text-amber-950` 1, `text-blue-500` 1, `text-cyan-700` 1,
`text-green-500` 1, `text-orange-500` 1, `text-pink-700` 1, `text-purple-500` 1,
`text-rose-500` 1, `text-rose-700` 1, `text-rose-800` 1, `text-sky-700` 1,
`text-teal-700` 1.

---

## 1k. Characters or graphical object — which brand token a class takes

**Binding tree-wide, and scoped to exactly nine classes:** `text-indigo-300`,
`-500`, `-600`, `-700`, `-800`, `-900`, `text-emerald-500`, `-600` and `-700`.
It is deliberately *not* a `text-*` wildcard, so it cannot collide with §1a's
`text-*-400` → `text-muted-foreground` named move.

**Why the split exists.** `--primary` is a *surface* colour. Measured with
`frontend/src/lib/contrast.ts` it fails WCAG 2.1 AA as normal text on every
light surface: **3.4054:1** on `--card`, **3.3091:1** on `--background` and
**3.0427:1** on `--muted` / `--accent` / `--secondary`. Routing brand text at
`*-primary` therefore shipped a new AA failure at every migrated call site.
APRAS-88 adds a derived token, `--primary-text` — `--primary` walked down the
0.01 lightness grid until it clears 4.5:1 on all four text surfaces
(**5.2096 / 5.0622 / 4.6547 / 4.6547**), re-derived per tenant from that
tenant's own brand so hue and chroma survive.

A child answers **one** question at the call site, from the JSX, with no
measurement: **does this element paint glyphs of text?**

- **Characters → `text-primary-text`, floor 4.5:1.** The element renders
  characters if it has among its children a string literal, a text-rendering
  expression (`{t(...)}`, `{value}`, `{count}`), or any non-icon child element.
- **Graphical object → keeps its present `*-primary` row, floor 3:1.** That is
  the case when the element's only children are icon components or `<svg>`,
  **and** when the element is itself an icon component or an `<svg>` with no
  children at all — e.g. `AuthorizationFormModal.tsx:117`,
  `<ShieldCheck className="size-5 text-indigo-600 …" />`. That self-closing
  shape is the commonest in the tree, **53 sites**, and is named here rather
  than covered vacuously.
- **Every non-`text-*` utility is graphical**, always: `bg-`, `border-`,
  `ring-`, `divide-`, `outline-`, `fill-`, `stroke-`, `accent-`.
- **A mixed element counts as text.** A control rendering an icon *and* a
  label from one `currentColor` takes `text-primary-text`.
- **No large-text carve-out.** WCAG's 3:1 allowance for ≥24px (or ≥18.66px
  bold) text is deliberately unused: `--primary-text` clears 4.5:1 on all four
  text surfaces, so the allowance would buy nothing and would force every child
  to measure font sizes. Characters take `primary-text` **at any size**.
  (`--primary-text` on `--border` is 4.1271:1; `--border` carries no text and
  is not one of the four.)

**The same question governs a bare `text-primary` that predates this rule.**
The nine classes above are the *migration* scope; they are not the only way the
brand reaches a call site. A `text-primary` written before APRAS-88 existed
carries no information about which role it was meant for, so it is answered
the same way: if the element paints glyphs it takes **`text-primary-text`**, and
if it is a graphical object it keeps `text-primary` at the 3:1 floor. APRAS-87
applied that answer tree-wide and recorded the graphical side in
`frontend/src/__tests__/brandTextRole.test.ts`, whose `GRAPHICAL_PRIMARY_SITES`
names every surviving bare `text-primary` by file and element. The guard is a
**set equivalence**, not a total: a sibling that migrates a palette-coloured
icon to `text-primary` appends one entry — from the classification its own spec
already published — and nothing here is re-measured. Editing a bare token class
is **not** a migration: it adds no ledger row, no exceptions entry and no
`MIGRATED_DIRECTORIES` member.

**No new gap code, no ledger row, no exceptions entry.** A brand text class
still *migrates* — it simply migrates to a different token — so the §3b guard
grammar, `themeTokenMigration.exceptions.json` and the ledger counts are all
untouched. §1h stays closed at **eight** codes and code 8 is unchanged.

**Two things this section records but does not repair.** In the *default*
theme the graphical path clears 1.4.11 with thin margins (`--primary` on
`--accent` 3.0427, on `--background` 3.3091, on `--card` 3.4054), and for a
pale tenant brand it does not clear it at all (pale yellow on `--card`
**1.2617**, cyan **1.7917**). That is APRAS-68 behaviour predating APRAS-77,
introduced by no child, and it needs its own task. Second, `--primary-text`
carries **no 422 guard**: it is not in `MEASURED_PAIRS`, because adding four
pairs there would start refusing advanced palettes stored and working today.
Its guard is the derivation's own non-convergence rule — when no legible value
exists for an authored palette, `--primary-text` is emitted equal to
`--primary`, which is exactly what the product renders now.

---

## 2. The ledger

Every class left untouched gets a row in
[`unmapped-colours.md`](./unmapped-colours.md): six columns
(`task`, `file`, `line`, `class`, `code`, `why`), append-only, sorted by file
then line, one row per occurrence. **No child of APRAS-77 may add a property
to — or otherwise edit — `frontend/src/index.css`** — `build_theme` emits
exactly 18 keys, so a new one would be unbranded forever. The one exception is
a task that amends *this table*: APRAS-88 added `--primary-text` to the
stylesheet **and** to `build_theme` in the same change, which is what keeps the
invariant true rather than broken.

## 3. The guard

`frontend/src/__tests__/themeTokenMigration.test.ts` exports
`MIGRATED_DIRECTORIES`, seeded with exactly `"src/components/ui"`; each sibling
appends exactly one entry. It walks every `.tsx` / `.ts` file under each pinned
directory, excluding `__tests__/` and `*.test.ts(x)`, and fails on any match of
the grammar below that is not listed in
`themeTokenMigration.exceptions.json`.

### 3b. The grammar

Built from named parts, not one hand-written literal:

```
variants = (?:[a-z0-9][a-z0-9.\-]*(?:\[[^\]]*\])?:)*
prefix   = (?:bg|text|border(?:-[trblxyse])?|ring|outline|
              divide(?:-[trblxyse])?|placeholder|caret|accent|
              decoration|shadow|fill|stroke|from|via|to)
family   = (?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|
              green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|
              pink|rose)
scale    = (?:950|900|800|700|600|500|400|300|200|100|50)
opacity  = (?:/(?:[0-9]{1,3}|\[[^\]]*\]))?

palette  = (?<![\w-]) variants prefix - (?: family - scale | white | black )
           (?![\w-]) opacity
```

Three details are load-bearing:

- **`scale` must list its alternatives longest-first.** With `50` before `500`
  the engine matches `text-gray-50` inside `text-gray-500` and silently
  under-reports. The test asserts that the grammar's match of `text-gray-500`
  is the whole class, not a prefix of it.
- **The boundaries `(?<![\w-])` and `(?![\w-])`** prevent matching inside a
  longer identifier or a compound class name.
- **`prefix`'s side qualifier is optional, exactly one letter, and applies to
  `border` and `divide` only.** `border-t-slate-400` and `divide-y-gray-100`
  match; `bg-t-slate-400` and `ring-t-blue-500` are not Tailwind classes and
  must not match, and neither must the two-letter `border-tr-slate-400`.
  APRAS-85 made this amendment under an operator authorisation recorded on
  that task — the sole authorisation any child of APRAS-77 has to amend this
  document's published §3b, and it extends to the `prefix` production and to
  this prose and to nothing else. The alternation set is unchanged by it: the
  same sixteen keywords in the same order, none added and none dropped. §1j's
  appendix was generated with the **pre-amendment** grammar and is therefore 5
  occurrences short of the widened one — the five `border-t-*` header stripes
  of `task-management/components/TaskBoard.tsx`, kept verbatim and ledgered by
  APRAS-85. §1j is not edited, because it publishes APRAS-78's baseline and
  rewriting a baseline is worse than annotating it.

A third pattern covers `#[0-9a-fA-F]{6}` appearing inside a `className` string
or a `cva` / `cn` argument.

### 3c. The exceptions file

`themeTokenMigration.exceptions.json` is an array of objects with exactly four
keys:

```json
{ "file": "src/components/ui/badge.tsx", "class": "bg-amber-100", "code": "GAP-NO-TOKEN", "task": "APRAS-78" }
```

`file` is `src/`-relative; `class` is the verbatim matched text; `code` is one
of the eight in §1h; `task` is the appending task's id. There is **no line
number** — it would rot on every edit and turn the guard into noise. Four
rules keep it from becoming a place to hide unmigrated work, and the guard
asserts all four: closed reason codes, no stale entries, exact pairs only, and
ledger parity in both directions.

### 3d. Designed for APRAS-85's inversion

APRAS-85 inverts the allow-list into a repo-wide deny and keeps this same
exceptions file. The directory walk is written so that replacing
`MIGRATED_DIRECTORIES` with a single recursive `src` entry is the entire
change, and entries are already `src/`-relative with no allow-list-shaped
assumption. Rules 1–4 are unchanged by the inversion.

---

## 4. The pilot — `src/components/ui/`

`src/components/ui/` holds nine files; **four** contain palette classes, with
**31** occurrences: `alert-modal.tsx` 14, `badge.tsx` 8, `alert.tsx` 6,
`button.tsx` 3. Zero six-digit hex literals, zero `dark:` variants.

The pilot **applies** the two tree-wide rules stated in §1j — triple-as-a-unit
and the ≥ 4.5:1 clause re-derived with `frontend/src/lib/contrast.ts`. They are
not pilot-local; §1j owns them.

**Migrated — 7 occurrences** (all §1f case 3 "interactive fill" or §1f case 1):

| Site | From | To |
| --- | --- | --- |
| `button.tsx` `success` variant | `bg-emerald-600 text-white hover:bg-emerald-700` | `bg-primary text-primary-foreground hover:bg-primary/90` |
| `alert-modal.tsx` success branch | `bg-emerald-600 text-white hover:bg-emerald-700` | `bg-primary text-primary-foreground hover:bg-primary/90` |
| `alert-modal.tsx` destructive branch | `text-white` | `text-destructive-foreground` |

The `--primary-foreground` / `--primary` pair holds **5.7588:1** re-measured
with `contrast.ts`; `index.css` documents 5.7548:1 for the same pair, measured
by `src/__tests__/themeContrast.test.ts`'s independent oracle, whose gamut map
steps chroma on the 0.01 grid the stylesheet is authored on rather than
bisecting. Both are comfortably over AA, and the 0.004 between them is the
difference between the two gamut maps, not a disagreement about the colour.

The `success` button variant thereby becomes byte-identical to `default`. That
is correct, not a bug: `--primary` *is* emerald, so the two already differed by
2.40 L points, and leaving `success` literal would make it the one button in
the app a tenant's brand never reaches. Removing the now-duplicate variant is
an API change and is **out of scope**.

**What the pilot cannot exercise**, stated as plainly as the `dark:` rule in
§1g: `src/components/ui/` contains **zero** neutral fills at 50/100/200 —
`button.tsx` already uses `hover:bg-accent` — so **the pilot provides no
evidence for §1f case 2**, the `bg-muted`-versus-`bg-accent` choice that
governs 172 occurrences elsewhere in the tree. Like the `dark:` rule, case 2
is argued from token semantics rather than demonstrated here, and unlike the
`dark:` rule it is **invisible to every test in this task**, because `muted`
and `accent` are byte-identical in `:root`. The first sibling that meets a
`hover:bg-slate-100` is the first real exercise of it, and it is a review duty
there, not a test.

**Left untouched and logged — 24 occurrences**, each with its code:

| Site | Classes | n | Code |
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
  objective code wins (§1h code 3).
- `alert-modal.tsx:122`'s `text-white` takes `GAP-NO-SURFACE` (§1h code 5): it
  sits on `bg-amber-500`, a palette colour with no row, which is exactly what
  that code names.

The `GAP-TINT` verdict is the operator's permanent ruling, and it is also what
the measurement supports: the tint *surfaces* map well (`bg-emerald-50` →
`bg-muted` is ΔE 2.20) but their *text* does not — the darkest brand-family
foreground is `text-primary` at L 62, and `text-primary` on a `bg-primary/5`
tint measures **3.2161:1** composited over `--card`, against the **6.7502:1**
that `text-emerald-800` on `bg-emerald-100` holds today (both re-measured with
`frontend/src/lib/contrast.ts`). Migrating the surface alone is incoherent;
migrating both would introduce an AA failure. Both the semantics and the
numbers point the same way.

## 4b. What the verification test proves, and what it does not

This repository has **no Playwright, no Storybook, no Chromatic and no
Percy**, and jsdom does not run the Tailwind pipeline, so computed-style
assertions and visual regression are both unavailable without new
infrastructure — deliberately out of scope.

`frontend/src/__tests__/themeTokenCompile.test.ts` compiles `src/index.css`
through Tailwind 4.2.4's own `compile()` over a fixture containing **every
class pair in §1b–1e**, resolves each emitted declaration through the `var()`
chain (`.bg-primary` → `var(--color-primary)` → `var(--primary)` → the value),
reads both sides with `parseOklch` / `hexToOklch` from `src/lib/contrast.ts`,
and asserts the measured ΔL and ΔE match this document to **±0.1**. Opacity
rows follow §1i.

Three resolver requirements, each a trap that would silently certify a
different table:

1. **Take the `:root` block that `index.css` contributes** — the last `:root`
   rule in the compiled output that declares `--primary` without a `.dark`
   qualifier. Tailwind's own theme layer emits `:root, :host` before it, so
   the selector is not unique even before `.dark` is considered.
2. **Never `.dark`.** The compiled stylesheet declares `--primary` twice —
   `0.62` in `:root`, `0.65` in `.dark`. A last-wins resolver validates the
   dark scheme.
3. The test **asserts the trap directly**: it checks that the resolver returns
   `oklch(0.62 0.15 160)` and not `oklch(0.65 0.15 160)` for `--primary`, so a
   later simplification to last-wins fails loudly.

A fourth trap is Tailwind's own authoring format: its palette declares
lightness as a **percentage** (`oklch(98.4% 0.003 247.858)`), which
`parseOklch`'s grammar rejects, and `--color-white` is three-digit hex. Both
are normalised before being handed to `contrast.ts`; neither is a second
implementation of its arithmetic.

**This proves the table is truthful and that no unlisted substitution slipped
in. It does not prove the right row was chosen at the right call site.** §1f
names three cases it cannot see: `bg-white` on a page shell mapped to
`bg-card` passes; `hover:bg-slate-100` mapped to `bg-muted` instead of
`bg-accent` passes *with identical numbers*, because the two tokens are
byte-identical in `:root`; and emerald migrated as brand where it meant
success passes. All three remain a human review duty on every sibling.

## 4c. The brand-reach proof

`frontend/src/components/__tests__/TenantBrandReach.test.tsx` mounts a
**migrated** component — `<Button variant="success">` — together with
`TenantBrandTheme`, under a mocked `useTenantProfile` returning a
`DerivedTheme` whose `light.primary` differs from `index.css`'s
`oklch(0.62 0.15 160)`, and an authenticated `useAuth`. It asserts that the
injected element exists, that
`getComputedStyle(document.documentElement).getPropertyValue("--primary")`
resolves to the mocked theme's value, and that the rendered button carries
`bg-primary` — **the assertion is against the tenant token, never against a
colour literal**. A negative case asserts that under a `null` theme no element
is injected. `TENANT_BRAND_STYLE_ID` is imported by name, because
`src/lib/brandStylesheet.ts` carries a second id (`PUBLIC_BRAND_STYLE_ID`,
APRAS-74).

---

## Operator note — 21 focus rings stay blue

`focus:ring-blue-500` appears 21 times and `ring-indigo-500` 16 times, both as
focus rings. Indigo migrates to `ring-ring` under the named decision; blue has
no token, so by §1h precedence it is `GAP-NO-TOKEN` and stays. The app
therefore has two kinds of focus ring, one branded and one blue.

Measured, `ring-blue-500` → `ring-ring` is **ΔL 0.30** (L 62.30 → 62.00) — the
two are lightness-identical and the entire **ΔE 28.15** is hue, the same shape
as the already-accepted indigo move. Naming it would migrate all 21 with no
lightness change at all. Absent an operator answer the default holds: the
rings stay blue and are logged, and a later task can migrate them.
