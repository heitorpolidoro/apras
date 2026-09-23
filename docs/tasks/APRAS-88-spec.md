# APRAS-88 — Make `--primary` legible as text, or forbid it for text in the table

*Round 2 — revised against `.meridian/reports/APRAS-88-spec_review-1.md`.*

## Scope

One deliverable: **a brand text colour that is legible on any light surface, for
any tenant brand derived in simple mode**, plus the contract amendment that
tells APRAS-80…85 when to use it. Concretely: a new *derived* theme variable
`--primary-text`, emitted by `build_theme` and declared in `index.css`; a new
§1k in `docs/frontend/theme-token-mapping.md` drawing the text /
graphical-object boundary; the retargeting of the brand **text** rows in §1e
and in the compile test; and the repair of the `GAP-UNLISTED` contradiction in
the document's preamble.

**Not in scope, and deliberately:** changing any call site. No `.tsx` file is
touched. The ~105 `text-indigo-*` and ~49 `text-emerald-[567]00` occurrences
stay where they are and are migrated by APRAS-80…85 under the amended contract;
the 38 `text-primary` sites already shipped in the tree are APRAS-87's sweep
(see §3). Also out of scope: the 1.4.11 graphical-object floor for pale tenant
brands, and `--destructive` as text on `--muted` (4.2953) — both named as
follow-ups in §2 and §7.

**No mockup.** This task ships no UI. Its entire visual surface is one colour
value, and the value is fully specified by its measured ratios and its painted
hex (`oklch(0.52 0.11 160)` → `#177c52`); a mock would restate the stylesheet.

All ratios below were produced by **importing** `frontend/src/lib/contrast.ts`
(never reimplementing it), or by importing `backend/app/core/branding.py` and
calling its own functions, on the **emitted, 2dp** strings, through the
module's own chroma-bisection gamut map.

## 1. The repair, and why not the alternatives

**Chosen: (b), a distinct derived foreground role — `--primary-text`.**
It is derived from `--primary` by a **bounded** repair that moves lightness on
the 0.01 emittable grid — in the direction §1.2 fixes, never by eye and never
"away from the surfaces" — until it clears 4.5:1 against all of `card`,
`background`, `muted` and `accent` in that scheme. It is **derived,
not authored**: `AUTHORED_KEYS` stays at 13, so no stored advanced palette
breaks and no API request shape changes; `EMITTED_KEYS` goes 17 → 18.

Default light value `oklch(0.52 0.11 160)` — the value the derivation itself
produces from the authored `:root --primary`, not a hand-picked one. Default
dark value `oklch(0.65 0.15 160)`, byte-identical to `.dark --primary`, because
at L 0.65 the brand already clears AA on every dark surface (worst 5.7010 on
`--muted`) and the derivation returns its input unchanged.

| Pair (light) | `--primary` today | `--primary-text` |
| --- | --- | --- |
| on `--card` | 3.4054 | **5.2096** |
| on `--background` | 3.3091 | **5.0622** |
| on `--muted` / `--accent` / `--secondary` | 3.0427 | **4.6547** |

### 1.1 Simple mode: it holds for an arbitrary tenant brand

The token is re-derived per tenant from the tenant's own `--primary` by the same
loop, so hue and (gamut-snapped) chroma survive and only lightness moves. Sweep
through the real `_simple_scheme`, worst of the four surfaces, measured on the
emitted string:

| Brand | light `--primary` | light `--primary-text` | worst light | worst dark |
| --- | --- | --- | --- | --- |
| default emerald | `oklch(0.62 0.14 160)` | `oklch(0.52 0.11 160)` | 4.6547 | 5.0359 |
| pale yellow | `oklch(0.92 0.13 95.92)` | `oklch(0.53 0.10 95.92)` | 4.6917 | 13.7107 |
| navy | `oklch(0.32 0.11 268.96)` | unchanged | 11.5576 | 4.6902 |
| hot pink | `oklch(0.69 0.22 354.05)` | `oklch(0.56 0.22 354.05)` | 4.6492 | 5.6208 |
| near-white | `oklch(0.92 0 89.88)` | `oklch(0.54 0 89.88)` | 4.5070 | 13.6624 |
| near-black | `oklch(0.20 0 89.88)` | unchanged | 16.1215 | 4.7536 |
| orange | `oklch(0.70 0.19 47.60)` | `oklch(0.55 0.15 47.60)` | 4.5658 | 6.0784 |
| cyan | `oklch(0.80 0.13 211.53)` | `oklch(0.53 0.09 211.53)` | 4.5476 | 9.5960 |

**The guarantee is structural, and it has no cushion.** Over the reviewer's
117,504-combination lattice sweep the worst case is **exactly 4.5000** in light
(brand `oklch(0.92 0.04 255)` → `oklch(0.54 0.03 255.00)`) and **4.5023** in
dark (brand `oklch(0.00 0.22 300)` → `oklch(0.63 0.22 300.00)`); both reproduce
here. That is the 0.01 loop stopping at the first passing step, not margin. A
later change to `_STEP`, to `_LIGHT_MUTED` or to `_LIGHT_ACCENT_LIGHTNESS` would
therefore land under AA silently, so §8 requires those two worst cases to be
**pinned by a test**, and the derivation site to carry a comment saying why.

### 1.2 Advanced mode: bounded, valid, and **not** guaranteed

**Advanced mode carries no AA guarantee for this token, and the spec says so
rather than implying one.** A tenant authoring all 13 colours can produce a
palette for which no legible brand text colour exists — the review's is one, and
`audit_contrast` accepts it today:

```
background #ffffff  foreground #111111  card #ffffff  card-foreground #111111
primary #009f68     primary-foreground #00261a
secondary #009f68   secondary-foreground #00261a
accent #1a1a1a      accent-foreground #ffffff
muted #f5f5f5       muted-foreground #555555   border #cccccc
```

A white card and a near-black accent cannot both be cleared. Reproduced: the
unbounded `_repair_text` returns `OklchColor(-0.38, 0.0, 160)` and emits
`--primary-text: oklch(-0.38 0.00 160.00)` — negative lightness, brand chroma
stripped, and `parseOklch` accepts it downstream.

**Specified behaviour: two bounded walks, a deterministic tie-break, and a
defined non-convergence result.** The direction is part of the rule, because it
cannot be inherited: `_advanced_scheme(palette)` takes **no** `dark` parameter —
`build_theme` calls it once per authored scheme — so there is nothing to pass,
and "away from the surfaces" is *wrong* whenever the brand starts between them
(witness below).

1. Two walks are attempted from `--primary`, one **down** and one **up**, each
   stepping 0.01 and each refusing any step that would leave lightness
   `[0.00, 1.00]`. A walk ends at a value clearing all four surfaces
   (converged), or at the bound / `_MAX_STEPS` (failed).
2. If exactly one converges, its value is emitted. If both converge, the
   **down** value is emitted — a deterministic tie-break, and the one that
   leaves every simple-mode value unchanged.
3. If neither converges, `--primary` is emitted unchanged.

Because the two walks between them visit **every** lightness on the emittable
grid at the brand's hue and snapped chroma — down covers `[0.00, L]`, up covers
`[L, 1.00]` — rule 3 fires **iff no such value exists at all**. That is a proof
from the construction, not a sample, and it is what makes this section's claim
literally true; a single walk reaching a bound proves nothing of the kind.

**Why the direction must be written down.** A second palette, also accepted by
`audit_contrast` today:

```
background #f97316  foreground #000000  card #eeeeee  card-foreground #000000
primary #cccccc     primary-foreground #000000
secondary #cccccc   secondary-foreground #000000
accent #eeeeee      accent-foreground #000000
muted #ff4da6       muted-foreground #000000   border #999999
```

`--primary` is `oklch(0.85 0.00 89.88)` and the four surfaces sit at L 0.95,
0.70, 0.69, 0.95 — the text starts **between** them. Down converges to
`oklch(0.29 0.00 89.88)`, worst **4.5306**; up falls back to `--primary`, worst
**1.3663**. Reproduced here. Over a sweep of structured advanced palettes,
**1,147 of 1,970** that `audit_contrast` accepts are direction-asymmetric, so
three implementers choosing three plausible directions would disagree on the
majority of them, each disagreement being legible text against illegible text.

The palette recorded at the top of this section is **direction-blind** — both walks fail on it — so it
cannot be the only pinned case; §8 pins both.

Rationale for rule 3 over the alternatives: falling back to `--primary` is
exactly what the product renders today, so an impossible palette is left no
worse than before; it keeps the brand hue, which the clamp-to-black alternative
destroys (the recorded palette clamps to `oklch(0 0 160)`); and it is a single
deterministic value. On that palette the bounded derivation returns
`oklch(0.62 0.14 160.00)` — exactly that scheme's `--primary`. Verified.

**Simple mode is untouched by all of this.** Re-measured under rules 1–3: all
eight brands in §1.1, both `index.css` defaults and both §1.1 worst-case
witnesses return byte-identical values to those published — `:root` still
`oklch(0.52 0.11 160.00)`, `.dark` still its own input, the light witness still
4.500005203749431 and the dark still 4.502343552547213. In the light scheme
only `down` ever converges; in the dark scheme the brand already passes at step
zero, so the tie-break never bites.

Implement it as a **new** bounded function, leaving `_repair_text` byte-
unchanged: that function also derives `--muted-foreground`, and changing it
would put a shipped, 422-guarded token at risk for no gain.

**Operator decision taken while you sleep, vetoable.** The new variable is not
added to `branding.MEASURED_PAIRS`. That tuple is the **422 refusal contract**,
mirrored in `contrast.ts` and pinned by `backend/tests/data/contrast_fixtures.json`;
adding four pairs to it would start refusing advanced palettes that are stored
and working today, and would drag two otherwise byte-unchanged files into scope.
The consequence — that `--primary-text` is the only text variable in the emitted
scheme with no 422 guard — is precisely why the non-convergence rule above *is*
the guard, and why it must be pinned by a test rather than left to the loop.

### 1.3 Why not (a), darken `--primary` itself

Measured, not argued: to reach 4.5:1 on `--muted` the brand must fall to
**L 0.52** (4.5345; L 0.53 gives 4.3587). At L 0.52 the *other* side breaks —
`--primary-foreground` `oklch(0.15 0.02 160)` on it measures **3.8642**, so the
shipped `themeContrast` guard fails, `_pick_foreground` flips to near-white
(4.7908), and the operator-approved dark-on-emerald button from APRAS-76/77
silently reverts to white-on-emerald. And it does not generalise: `_clamp_input`
caps lightness at 0.92, so a pale-yellow brand stays at L 0.92 whatever the
default is.

### 1.4 Why not (c) alone, forbid and redirect to an existing token

There is no existing token that is both brand-coloured and guaranteed dark.
`--primary-foreground` is picked per tenant from near-white *or* near-black, so
for a dark brand it is `oklch(0.98 0 0)` — invisible on a card.
`--accent-foreground` / `--foreground` are neutrals: redirecting there deletes
the brand from every link, tab and chip, a larger visible change than the
indigo→emerald one the operator approved. So the answer to "(c) name the
replacement" is `--primary-text`, and (c) is subsumed by (b): the table *does*
forbid `text-primary` for characters, and (b) supplies what replaces it.

## 2. The 1.4.11 boundary — which sites are text

New **§1k**, scoped to the **nine retargeted classes** (`text-indigo-300`,
`-500`, `-600`, `-700`, `-800`, `-900`, `text-emerald-500`, `-600`, `-700`) and
to no wider wildcard, so that it cannot collide with §1a's `text-*-400` named
move. It is stated so a child never judges:

- One of the nine classes takes **`text-primary-text`** *iff* the JSX element
  carrying it **renders characters** — it has among its children a string
  literal, a text-rendering expression (`{t(...)}`, `{value}`), or any non-icon
  child element. Floor 4.5:1.
- It is **graphical** — keeps its present `*-primary` row, floor 3:1 — when
  the element's only children are icon components or `<svg>`, **and when the
  element is itself an icon component or an `<svg>` with no children at all**,
  e.g. `AuthorizationFormModal.tsx:117`
  `<ShieldCheck className="size-5 text-indigo-600 …" />`. That self-closing
  shape is the commonest in the tree — 53 sites — and the graphical branch must
  name it rather than cover it vacuously.
- The same graphical verdict holds for every non-`text-*` utility: `bg-`,
  `border-`, `ring-`, `divide-`, `outline-`, `fill-`, `stroke-`, `accent-`.
- **Mixed element wins for text**: a control rendering an icon *and* a label
  from one `currentColor` is text.
- **No large-text carve-out.** WCAG's 3:1 allowance for ≥24px (or ≥18.66px
  bold) text is deliberately not used: `--primary-text` clears 4.5 on **all four
  text surfaces**, so the allowance would buy nothing and would force every
  child to measure font sizes. Characters take `primary-text` at any size.
  (`--primary-text` on `--border` is 4.1271; `--border` is not a text surface
  and is not among the four.)

The test is "does this element paint glyphs of text", answerable from the JSX
with no measurement, which is what keeps an icon from being over-corrected.

Recorded, not repaired here: in the **default** theme the graphical path clears
1.4.11 with thin margins (`--primary` on `--accent` 3.0427, on `--background`
3.3091, on `--card` 3.4054) but for a pale tenant brand it does not at all
(pale yellow on `--card` **1.2617**, cyan **1.7917**). That is APRAS-68
behaviour that predates APRAS-77 and is not introduced by any child — it needs
its own task. The repair cannot reduce the default margins: `--primary` does not
move, and under §1k a site either stays on `*-primary` or moves to
`*-primary-text` at 4.6547 or better.

## 3. APRAS-87 — recommendation: keep it separate, rescoped

**Keep separate.** APRAS-88 owns the token and the contract and touches **no**
`.tsx`; APRAS-87 owns the call-site sweep. Reasons: the sweep is repo-wide (38
`text-primary` occurrences already in the tree, plus the two lot-management
tabs), most of them in directories APRAS-79…85 own, and folding them in would
put `.tsx` edits from six directories into the PR that six children are blocked
on — the slowest possible shape for a CRITICAL blocker. Nothing is lost by
sequencing: after this task the sweep is mechanical (§1k decides every site).

Board changes to record (orchestrator action, not this spec's implementation):
APRAS-87's `blockedBy` becomes `APRAS-88` (it no longer needs APRAS-79), and its
scope narrows to "apply §1k repo-wide and update APRAS-79's pinned constants".

## 4. What APRAS-80…85 are told

In `docs/frontend/theme-token-mapping.md`:

1. **New §1k**, exactly the boundary in §2 above, marked binding tree-wide.
2. **§1e's brand rows are re-cut, not merely retargeted.** Only three of the
   nine classes have a row to themselves (`text-indigo-300`, `-800`, `-900`);
   the other six share a **combined row** with non-`text-` prefixes. Each of
   those six rows is **split in two**:

   | Combined row today | non-text half keeps | new text row gets |
   | --- | --- | --- |
   | `bg-/text-/border-indigo-500` | 3.50 / 33.15, moves (named) | `text-indigo-500` → `text-primary-text`, 6.50 / 30.66 |
   | `bg-/text-/border-/accent-indigo-600` | 10.90 / 37.24, moves (named) | `text-indigo-600` → `text-primary-text`, 0.90 / 32.71 |
   | `bg-/text-indigo-700` | 16.30 / 37.33, moves (named) | `text-indigo-700` → `text-primary-text`, 6.30 / 31.25 |
   | `bg-/text-/border-emerald-500` | 7.60 / 7.89, noted | `text-emerald-500` → `text-primary-text`, 17.60 / 18.60 |
   | `bg-/text-/border-emerald-600` | 2.40 / 2.59, noted | `text-emerald-600` → `text-primary-text`, 7.60 / 8.40 |
   | `bg-/text-emerald-700` | 11.20 / 11.72, noted | `text-emerald-700` → `text-primary-text`, 1.20 / 1.82 |

   The three standalone rows are retargeted in place: `text-indigo-300`
   26.50 / 32.58, `-800` 12.20 / 29.11, `-900` 16.10 / 27.20. Every `ring-`,
   `bg-`, `border-` and `accent-` figure in §1e is unchanged.
   **The Budget column of each new text row is recomputed against its new ΔE**,
   which moves two of them: `text-emerald-700` 11.72 → **1.82**, `noted` →
   `invisible`; `text-emerald-500` 7.89 → **18.60**, `noted` → `moves`.
   Figures follow the document's method (OKLab euclidean, L in 0–100 units,
   chroma ×100, no gamut mapping), target `oklch(0.52 0.11 160)`.
3. **§1a gains a fourth named move — and this is the largest operator decision
   in the task.** `moves` at ΔE > 12 migrates only if the operator decision
   names it. `text-emerald-500` → `text-primary-text` at 18.60 is named by
   nobody today: emerald-as-brand is `noted`, inside budget, and is **not** one
   of §1a's three named moves. So the list goes **three → four**: the indigo
   family, `text-*-400`, `text-white`, and now `text-emerald-500` →
   `text-primary-text`. Separately, the **indigo** entry alone gains a second
   target, so that the six indigo text rows name `*-primary-text` as well as
   `*-primary`. *Operator-vetoable, and flagged as the bigger of the two:*
   accepting it moves 4 `text-emerald-500` occurrences further than any
   published emerald figure. The alternative — a new gap code — is worse: it
   reopens a set the contract requires to stay closed at eight.
4. A child decides at a call site with one question — **does this element render
   characters?** — and nothing else. No new gap code, no ledger row, no
   exceptions entry: a brand text class still **migrates**, just to a different
   token, so the guard grammar and `themeTokenMigration.exceptions.json` are
   untouched and APRAS-80's ledger counts are unaffected.

## 5. The `GAP-UNLISTED` contradiction

**§1h code 8 governs and is left exactly as written** (post-APRAS-78 code, no
row, no other code; log, leave, do not block). The **preamble sentence** is
wrong and is rewritten: a sibling that believes a row is wrong or unusable at
its call site **raises a table-amendment task against APRAS-78's artefacts and
blocks on it** — it does not reach for `GAP-UNLISTED`, which was never defined
to cover a class that has a row.

**Which of the eight codes should a child use for a pair the table now forbids
migrating? None, and there is no such pair.** The amendment supplies a *target*
rather than a prohibition, so "right row, wrong call site" ceases to exist for
brand text. The set stays closed at eight.

## 6. What already sits in the tree

`frontend/src/features/lot-management/__tests__/lotManagementContrast.test.ts`
is **unchanged and stays green**. Its `ACTIVE_TAB_ON_CARD = { today: 3.7194,
then: 3.4054 }` and its `PRE_EXISTING_SUB_AA` 3.6142 → 3.3091 are measurements
of `--primary` against surfaces this task does not move, and it asserts
`ratio(after(), background()) < 4.5` — still true, because no call site changes.
Those constants become APRAS-87's to update at the moment it points the two tabs
at `--primary-text`; this spec requires the file to be byte-unchanged and green.

## 7. Files touched

- `frontend/src/index.css` — add `--color-primary-text: var(--primary-text)` to
  `@theme`; `--primary-text: oklch(0.52 0.11 160)` to `:root`;
  `--primary-text: oklch(0.65 0.15 160)` to `.dark`, each with the one-line
  reason and the binding ratio, in the style of the existing
  `--primary-foreground` and `--muted-foreground` comments. **Also corrects the
  pre-existing typo on line 39**: the `--primary-foreground` comment reads
  "5.7548:1" where the measured value, and APRAS-78's published figure, is
  **5.7588** — a one-token fix, stated here so it is in scope rather than an
  unexplained drive-by. **This is the only task permitted to edit this file**;
  see §8 for what that means for APRAS-78's guarantee.
- `backend/app/core/branding.py` — `EMITTED_KEYS` gains `primary-text`
  (`AUTHORED_KEYS` and `MEASURED_PAIRS` unchanged); a named constant for the
  four surfaces; a **new bounded** derivation function implementing §1.2's three
  rules — both walks, the prefer-`down` tie-break and the `--primary` fallback —
  called from both `_simple_scheme` and `_advanced_scheme`, with a comment
  recording the zero-margin worst cases from §1.1. Because the function tries
  both directions it takes **no** direction argument, so `_advanced_scheme`'s
  signature does not change and `build_theme` passes no flag; `_repair_text` is
  left byte-unchanged; the "17 emitted" comments become 18.
- `backend/app/schemas/tenant.py` — the "17 CSS variables" docstring.
- `frontend/src/api/tenantProfile.ts` — line 25's "the 17 emitted properties"
  becomes 18. (Comment only; `ThemeScheme` is `Record<string, string>`, so no
  type and no `.tsx` changes.)
- `backend/tests/test_branding.py` — `len(scheme) == 17` → 18; a sweep
  asserting `primary-text` ≥ 4.5:1 on all four surfaces in both schemes; the two
  worst-case witnesses pinned; **two** advanced palettes pinned as regression
  cases — the direction-blind one of §1.2 and the direction-sensitive one, since
  the first alone cannot detect a wrong direction; an assertion that `MEASURED_PAIRS` still has 8 members.
- `frontend/src/__tests__/themeContrast.test.ts` — `--primary-text` is not
  matched by `backgroundOf` (neither `-foreground` nor `-fg`), so its four
  surfaces are added to `EXTRA_PAIRS` and `MINIMUM_PAIRS` goes **19 → 23**; the
  "pairs this task repaired" block gains the before/after 3.0427 → 4.6547.
- `frontend/src/__tests__/themeTokenCompile.test.ts` — the **nine existing
  `text-*` rows are retargeted in place** (`text-indigo-500` :105, `-600` :109,
  `-700` :113, `-800` :114, `-900` :115, `-300` :116, and the three
  `text-emerald-[567]00` rows), each changing both `target` and its `dL`/`dE` to
  the §4.2 figures. **Not appended to:** an appended implementation leaves the
  nine stale `text-primary` rows in place, and because `--primary` does not move
  they would still pass, greening a suite that contradicts the table it guards.
- `frontend/src/lib/brandStylesheet.ts` — doc comment "the 17 keys" → 18.
- `docs/frontend/theme-token-mapping.md` — preamble, §1a, §1e, new §1k.
- **Unchanged, and asserted so:** `frontend/src/lib/contrast.ts`,
  `backend/tests/data/contrast_fixtures.json`,
  `frontend/src/__tests__/themeTokenMigration.test.ts` and its
  `exceptions.json`, `lotManagementContrast.test.ts`, every `.tsx`.

## 8. Test criteria and gates

- Every ratio asserted by **importing** `frontend/src/lib/contrast.ts` (or, in
  the backend, `app.core.branding`), on the emitted 2dp string, to ±0.001 —
  **except** the two zero-margin worst cases, which are pinned to their full
  floats, 4.500005203749431 and 4.502343552547213, because ±0.001 around
  "4.5000" would admit 4.4990, a value below AA. The accompanying
  "≥ 4.5:1 for every brand in the sweep" assertion is what alarms, so nothing is
  left unguarded either way.
- `themeContrast` proves the token's AA in both schemes from the file itself;
  `test_branding` proves it for derived tenant themes, pins the zero-margin
  worst cases, and pins the advanced-mode non-convergence result;
  `themeTokenCompile` proves the nine retargeted rows resolve to the new token
  through the `var()` chain.
- **APRAS-78's byte-identical guarantee.** §4b/§4c rest on `index.css` being
  untouched by the *migration* children; this task is the table's own amendment,
  so it edits the file by design. Nothing pinned breaks, because no existing
  declaration changes value: `themeTokenCompile`'s pinned ΔL/ΔE all derive from
  tokens that do not move, and the only numbers that change there are the nine
  rows this task retargets. The children's guarantee is restated as "no child of
  APRAS-77 may edit `index.css`", which remains true.
- Gates: `npx tsc -b` clean; `npx vitest run --coverage` at exactly 80 lines /
  78 functions / 76 branches / 80 statements; `npx eslint src` **re-measured**
  and unchanged at 375 errors + 2 warnings across 64 files (this task adds no
  `.tsx` and no new lint surface); `ruff check` / `ruff format --check` clean;
  `pytest backend/tests/test_branding.py backend/tests/test_tenant_profile.py`
  green.

## Expected Results

- [ ] `frontend/src/index.css` declares `--primary-text: oklch(0.52 0.11 160)`
      in `:root`, `--primary-text: oklch(0.65 0.15 160)` in `.dark`, and
      `--color-primary-text: var(--primary-text)` in `@theme`; the
      `--primary-foreground` comment reads `5.7588:1`; and no existing
      declaration in the file changes value.
- [ ] Measured by importing `frontend/src/lib/contrast.ts`, `--primary-text` on
      `--card` is 5.2096, on `--background` 5.0622, on `--muted` and on
      `--accent` 4.6547 (±0.001), and `--primary` still measures 3.4054 /
      3.3091 / 3.0427 on the same three surfaces.
- [ ] `npx vitest run src/__tests__/themeContrast.test.ts` passes with
      `--primary-text` measured against `card`, `background`, `muted` and
      `accent` in **both** schemes, each ≥ 4.5:1, and `MINIMUM_PAIRS` is 23.
- [ ] `build_theme` emits 18 keys per scheme including `primary-text`;
      `AUTHORED_KEYS` is still the same 13 and `MEASURED_PAIRS` still the same
      8; `backend/tests/data/contrast_fixtures.json` and
      `frontend/src/lib/contrast.ts` are byte-unchanged.
- [ ] A test in `backend/tests/test_branding.py` asserts that for every brand in
      a lattice sweep, in both schemes, the emitted `primary-text` reaches
      ≥ 4.5:1 against `card`, `background`, `muted` and `accent`, and pins the
      two worst cases — light `oklch(0.92 0.04 255)` → `oklch(0.54 0.03 255.00)`
      at **4.500005203749431**, dark `oklch(0.00 0.22 300)` →
      `oklch(0.63 0.22 300.00)` at **4.502343552547213** — so that a change
      which erodes the margin fails loudly.
- [ ] For the advanced palette recorded in §1.2 (white card, `#1a1a1a` accent),
      where neither walk converges, `build_theme` emits `--primary-text` equal
      to that scheme's `--primary`, `oklch(0.62 0.14 160.00)`.
- [ ] For the **direction-sensitive** advanced palette in §1.2 (`#f97316`
      background, `#cccccc` primary, `#eeeeee` card and accent, `#ff4da6`
      muted), `build_theme` emits `--primary-text: oklch(0.29 0.00 89.88)`,
      whose worst of the four surfaces is 4.5306 — not the `--primary` fallback
      at 1.3663 that a single upward walk would produce.
- [ ] For **every** palette, simple or advanced, the emitted `--primary-text`
      parses as `oklch(L C H)` with `0 ≤ L ≤ 1` and `C ≥ 0`.
- [ ] `docs/frontend/theme-token-mapping.md` contains a §1k stating the
      text / graphical-object boundary — characters → `*-primary-text` at 4.5:1;
      an element that is itself an icon or `<svg>`, an element whose only
      children are icons, and every non-`text-*` utility → `*-primary` at 3:1;
      mixed elements count as text; no large-text carve-out — scoped to the nine
      named classes.
- [ ] In §1e, the six combined brand rows are split so that each has a `text-`
      row targeting `*-primary-text` and a non-`text-` row keeping its published
      figures (3.50/33.15, 10.90/37.24, 16.30/37.33, 7.60/7.89, 2.40/2.59,
      11.20/11.72); the three standalone text rows are retargeted; all nine new
      text rows carry the §4.2 ΔL/ΔE and a Budget recomputed from the new ΔE,
      with `text-emerald-700` `invisible` and `text-emerald-500` `moves`.
- [ ] §1a lists **four** named moves, the fourth being `text-emerald-500` →
      `text-primary-text`, and the indigo entry names both `*-primary` and
      `*-primary-text`.
- [ ] The document's preamble no longer instructs a sibling to use
      `GAP-UNLISTED` for a row it believes wrong; §1h still defines exactly
      **eight** codes, code 8 unchanged, and the document states that a brand
      text class still migrates and therefore needs no gap code, no ledger row
      and no exceptions entry.
- [ ] `npx vitest run src/__tests__/themeTokenCompile.test.ts` passes, and no
      entry in its `ROWS` targets `text-primary` for any of the nine classes any
      more — each is retargeted in place, none appended.
- [ ] `frontend/src/features/lot-management/__tests__/lotManagementContrast.test.ts`
      and `frontend/src/__tests__/themeTokenMigration.exceptions.json` are
      byte-unchanged, and the former still passes.
- [ ] No `.tsx` file under `frontend/src/` is modified by this task.
- [ ] `npx tsc -b` is clean; `npx vitest run --coverage` meets 80 / 78 / 76 / 80;
      `npx eslint src` reports 375 errors and 2 warnings across 64 files;
      `ruff check backend` is clean; the backend test suite passes.
