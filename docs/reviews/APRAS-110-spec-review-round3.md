# APRAS-110 — spec review, round 3

**Scope of this round.** Narrow, findings-driven. Round 2 approved the spec with
no blocking findings and independently verified the approach, the data source,
the `alt` derivation, the fallback, the aspect-ratio handling, the no-backend
scope, the one-retry 60 s latch, the three-way `md:hidden` rule and the
`data-testid` hook. None of that is re-litigated here, and option A for
question 2 is not re-argued: the operator read the tradeoff the mock stated and
chose B.

What I examined is the revision that made the white card coherent with
criteria originally written around the opposite decision: the two new expected
results, the amendments to the image-token and logo-bytes results, the mock
result, the new Out of Scope bullet, the mock's card markup and question
labelling, and the removal of the numeric cross-references that the two
inserted results invalidated.

Documents read: `/Users/heitor/workspace/apras/docs/tasks/APRAS-110-spec.md`,
`/Users/heitor/workspace/apras/docs/tasks/APRAS-110-mock.html`.
Contract reference read first:
`/Users/heitor/workspace/meridian/plugin/plugins/meridian/references/schema.md`.

---

## 1. The token choice `dark:bg-foreground` — verified in the files

Every claim the reviser made about this token holds, and I checked each in the
source rather than accepting the prose.

**`--foreground` is the dark scheme's near-white.**
`/Users/heitor/workspace/apras/frontend/src/index.css`:

- `:root` (line 34): `--foreground: oklch(0.14 0.01 160)` — near-**black**.
- `.dark` block opens at line 90 and line 92 reads
  `--foreground: oklch(0.98 0.01 160)` — near-**white**.

So the second half of the reviser's reasoning is correct and load-bearing:
unprefixed, `bg-foreground` would paint a near-black patch in the light scheme,
which is the opposite of the operator's decision. The `dark:` prefix is doing
two jobs, exactly as the spec claims — gating the paint, and keeping the
light scheme unpainted rather than wrongly painted. The spec's framing of this
as a deliberate role inversion (a mark colour used as a surface) is accurate,
and `--color-foreground: var(--foreground)` at line 7 is what makes
`bg-foreground` resolve as a utility at all.

**It is a token, not a raw palette class.**
`/Users/heitor/workspace/apras/docs/frontend/theme-token-mapping.md` lines 152
and 153 publish `bg-slate-900 → bg-foreground` and `bg-slate-950 →
bg-foreground`, with line 512 counting seven call sites migrated that way. The
reviser cited exactly the right rows.

**`bg-white` would genuinely trip the migration guard.**
`frontend/src/__tests__/themeTokenMigration.test.ts` walks `frontend/src`
recursively (`walk` at line 3698, cross-checked against an independently
computed walk at line 3735) and requires a `(file, class)` entry in
`themeTokenMigration.exceptions.json` for every match of its pattern, which at
line 75 is `${VARIANTS}${PREFIX}-(?:${FAMILY}-${SCALE}|white|black)`. A new
`TenantHeaderLogo.tsx` carrying `bg-white` would have no entry and would fail.
`bg-foreground` is not matched by that pattern — `foreground` is neither a
family nor `white`/`black` — so the correct token is not itself a violation.
The claim is exactly right in both directions.

**`rounded-md` is a radius token.** `--radius-md: calc(var(--radius) - 2px)` at
`index.css:27`. Verified.

## 2. Geometry: `px-1`, no vertical padding, exactly `h-7`

The height claim checks out. The image is `h-7` (1.75rem); the card is an
`inline-flex` box with horizontal padding only, so its content-box height is
the image's height and its border-box height is the same 1.75rem. It cannot
move the header, which is the invariant §"Aspect ratio and layout" protects.
Keeping `px-1` unprefixed does make the layout scheme-invariant, which is what
lets a single sorted-set equality decide the whole rule — that part of the
argument is sound, not decorative.

One over-statement, non-blocking (see Suggestions): the spec says `inline-flex
items-center` "keep the wrapper's box exactly the image's box … so inserting it
changes no geometry". As the mock draws it, the wrapping `Link` is `flex
items-center`, and a flex item's `inline-flex` is blockified to `flex` by the
container, so the token is doing nothing there — and `items-center` on a single
auto-height item is also a no-op. The *outcome* the spec describes is correct
either way, and because the spec does not fix the `Link`'s display, the token
is defensible as a guard against a non-flex parent. But the spec gives `w-auto`
an explicit honesty note for precisely this shape of redundancy and does not
give `inline-flex` one.

## 3. No colour figure anywhere, and the provenance guard passes

I grepped both documents for `oklch`, six-digit hex, and ratio shapes. The spec
publishes **no** colour figure — no hex, no ratio, no `oklch()`→hex
equivalence. Its `:1` hits are all aspect ratios (`4:1`, `10:1`, `128×28`), not
contrast ratios. The reasoning for stating none is correct: a logotype is not a
text/surface pair, WCAG 1.4.11 exempts it, and there is nothing for
`contrast.ts` to measure, so publishing a figure would mean inventing one.

The mock's one raw literal is gone as claimed: `.plate` at
`APRAS-110-mock.html:57` now reads `background: var(--foreground)`, with a
comment (lines 51–56) tying it to the component's `dark:bg-foreground` and
saying why a variable rather than a literal, "for the same reason the component
uses a token rather than `bg-white`". No `oklch(0.99 0 0)` survives.

I re-ran the guard the reviser reported, from `frontend/`:

```
npx vitest run src/__tests__/docsColourProvenance.test.ts src/__tests__/themeTokenMigration.test.ts
→ Test Files 2 passed (2) · Tests 193 passed (193)
```

193 passing, matching the reviser's report exactly. `docsColourProvenance`
scans `docs/tasks/**` for both `.md` and `.html` (its `SCANNED_DIRECTORIES`),
so both documents under review are genuinely inside its scan and genuinely
pass — this is not a vacuous green.

I also re-measured the lint baseline the spec pins, because a stale baseline
burns a developer round:

```
npx eslint . -f json → 370 problems (368 errors, 2 warnings) across 64 files
```

Byte-identical to the figure in the expected result. Verified rather than
assumed.

## 4. The first new criterion — the two-render token equality

This is where I spent the most effort, constructing defective implementations
and checking each one fails. The criterion requires, in both a render with no
`.dark` ancestor and one inside `<div className="dark">`:
`getByTestId("tenant-header-logo-plate")` resolves,
`img.parentElement === plate`, and `classTokens(plate).sort()` equals exactly
`["dark:bg-foreground", "inline-flex", "items-center", "px-1", "rounded-md"]` —
the same array both times.

`classTokens` (`frontend/src/test/classTokens.ts`) is
`element.className.split(/\s+/).filter(Boolean)` — a whole-token split, so the
equality is a real set comparison and not a substring match. Correct
instrument.

Defective implementations I constructed, and their fate:

| Defect | Outcome |
|---|---|
| Unconditional paint: `bg-foreground` without the prefix | array contains `bg-foreground`, not `dark:bg-foreground` → **fails** |
| Belt-and-braces: `bg-white dark:bg-foreground` | six tokens → **fails**, and `bg-white` also fails `themeTokenMigration` |
| JS branch on `document.documentElement.classList.contains("dark")` | the test puts `.dark` on a `<div>` inside the render container, not on `documentElement`, so the branch is false in *both* renders → four tokens, missing `dark:bg-foreground` → **fails** |
| JS branch on a context/`matchMedia` scheme value | yields two different arrays, or one array missing the token → **fails** |
| `invert` / `filter` on the image instead of a card | **fails** the image-token result, and `getByTestId` if no card is rendered |
| No card at all | **fails** `getByTestId` |
| Card rendered as a sibling rather than a wrapper | **fails** `img.parentElement === plate` |

Note the third row in particular: I expected it to be the hole, since a
scheme-detecting implementation that reads `documentElement` would see the same
(false) answer in both renders and could in principle produce one consistent
array. It does produce one consistent array — but a four-token one, so the
equality still rejects it. Any JavaScript branch that yields the required
five-token array in *both* renders must emit `dark:bg-foreground`
unconditionally, which **is** the correct implementation. The criterion is
tighter than I assumed going in.

**The limit the reviser asked me to judge.** Could an implementation pass this
while painting nothing in either scheme? Yes, in exactly one way: emit the
literal string `dark:bg-foreground` in a form Tailwind's source scanner cannot
see — e.g. `` `dark:bg-${"foreground"}` `` or a token assembled from a lookup
table — so no CSS rule is ever generated. jsdom has no Tailwind and the
criterion reads no computed style, so the test would pass on a card that paints
nothing.

I judge this an acceptable limit rather than a hole, for three reasons. First,
the spec closes it in prose with a mandate, not a hope: §"Theming and contrast"
fixes the class list as "**exactly these five tokens**" and writes them out as
literals, so a dynamically composed class violates the spec text itself even
when the test is green. Second, the evasion is not a plausible accident — it is
not a shortcut a reasonable implementer reaches for under time pressure, which
is the category round 1 was right to reject (reading `event.currentTarget.src`,
omitting the `key`, asserting a handler's existence instead of its effect). It
requires deliberately defeating a build-time scanner. Third, the paint is
demonstrated for the operator's own eye in the mock, in a real browser, which
is the same division of labour the spec already states for the aspect-ratio
tokens.

Where the spec is slightly overconfident is the sentence "The equality is what
decides the rule in both directions", which enumerates four defeats and names
no escape. That is a prose overstatement, not a verification gap, and it is
fixable with the same one-line honesty note the spec already gives `w-auto`.
Suggestion, not a finding.

## 5. The second new criterion — the mandatory negative

All four fallback states are present and the pair does its job:
`logo_url: null`, `{ data: undefined, isPending: true }`,
`{ data: undefined, isError: true }`, and on the logo branch after
`fireEvent.error(within(screen.getByRole("banner")).getByRole("img"))`, with the
latched case additionally asserted inside a `.dark` ancestor. That last
addition is the one that matters most, since the dark scheme is the only one
that paints.

An implementation that hoists the card out of the logo branch and renders it
always passes the presence criterion of §4 and fails all four of these. The
pair genuinely kills it. The spec also grounds the invariant structurally, not
just in the test: §Behavior state 6 says "The card is part of state 1's markup,
so it exists exactly when the image does and never behind the fallback mark",
so the criterion is asserting a property the design already has rather than
bolting one on.

## 6. The dark-variant dependency, and dark mode's reachability

Both load-bearing facts are confirmed:

- `frontend/src/index.css:3` is `@custom-variant dark (&:is(.dark *));`. The
  variant matches **descendants** of `.dark`, so a hand-added class must be on
  an *ancestor* of the component, never on its own root. The criterion's
  insistence on `<div className="dark">` as a wrapper is correct and necessary.
- No code in `src` applies `.dark` to any element. I grepped `classList` across
  `src` (only `obraPrintDocument.ts` touches it, for print break classes) and
  every `"dark"` / `'dark'` string literal: all are palette-scheme keys in
  `TenantBrandColors.tsx`, `brandPalettePaste.ts` and `themeContrast.test.ts`,
  none a DOM class application. And since the variant is class-based, no
  `prefers-color-scheme` path reaches it either. The spec's reviewer note is
  accurate, and it is why the test must add the class by hand.

Worth saying plainly, since it is the honest consequence: the card the operator
chose will not be visible in the running application until dark-mode activation
ships, which the spec puts out of scope. The spec states both halves of this
(the reviewer note, and the Out of Scope bullet on dark-mode activation) but
never joins them into that sentence. This does not change the verdict — round 2
approved the dark-scheme image-token criterion on exactly the same footing, and
the decision is correctly recorded for when activation lands — but it belongs in
the Suggestions so the operator is not surprised.

## 7. The amendments, each checked

- **Image-token result** keeps its prohibition verbatim: "no token starting
  with `dark:`, no `invert` and no token starting with `filter`", on an exact
  four-token equality. It gained only the clarifying sentences that the
  operator's card is a wrapper element and never a token on the image.
  Prohibition intact; nothing weakened to accommodate the reversal.
- **Logo-bytes result** names **APRAS-124** by id (spec line 567), as do
  §"The cost of the logo bytes" (line 122), the question-3 preamble (line 24)
  and the Out of Scope bullet (line 601). Consistent everywhere; no
  "a follow-up will be filed" hedge survives.
- **Mock result** requires the dark-scheme card drawn "**with the light card
  painted behind the logo**, which is what the operator chose", still five
  cards for six states, and both question sections labelled with the operator's
  choice (question 1: A; question 2: B) "rather than the one the spec had
  recommended". Matches the mock as built.
- **New Out of Scope bullet** (lines 608–611) excludes the card in the light
  scheme and any filtering/inverting/re-colouring in either scheme. It
  contradicts nothing: §Theming says the card "must not paint in the light
  scheme", state 6 says the image is untouched, and the image-token result
  forbids `filter`/`invert`. One wording tension, non-blocking, in Suggestions.
- **Question preamble** (lines 11–26) records both questions as settled rather
  than open, and is explicit that question 2 reverses the spec's own
  recommendation and that A is not re-argued below. I confirmed no residual
  advocacy for A survives in §Theming — the surviving fragment of the old
  reasoning is only the logotype/WCAG-1.4.11 point, which is used to justify
  *not re-colouring the artwork*, a claim the card does not contradict. The
  spec draws that distinction itself and correctly makes it the reason the card
  is a wrapper rather than a filter.

## 8. Stale cross-references — none survive

This is the failure mode the reviser flagged and it is clean. I grepped both
documents for `expected result N`, `result N`, `criterion N`, `§N` and
`bullet N`: **zero matches in either file.** The three former numeric
references now read as descriptions, and the positional ones that remain are
accurate: "the next two are what assert the card" (line 515) does point at the
card-parent and card-absence results, and "the result above" (line 534) does
point at the card-parent result immediately preceding. The spec also replaced
line-number lookups with name lookups in the two places line numbers moved —
"find it by that name, not by line number, which moved when the card was added"
for the mock's `logoLink` helper, and "find it by that title" for
`Navbar.test.tsx`'s one-link case.

## 9. The mock, opened and checked against its claims

- **`.plate`** at line 57 paints `var(--foreground)` with the comment tying it
  to `dark:bg-foreground`. Confirmed.
- **The card wrapper is always rendered on the logo branch.** `logoLink`
  (line 189) emits `<span data-testid="tenant-header-logo-plate" class="inline-flex
  items-center px-1 rounded-md${plate ? " plate" : ""}">` with the `<img>` as
  its only child. So the wrapper exists in the light-scheme cards too, painting
  nothing — which is exactly the component's shape, and a useful fidelity. One
  precision on the dispatch's wording: the mock carries **four** of the five
  real tokens plus the `.plate` stand-in, not five. That is correct and
  honestly documented — the comment at lines 183–188 writes out all five real
  tokens and explains that `plate: true` "is what the component gets for free
  from the `dark:` prefix" because the CDN build cannot see the app's custom
  variant. The stand-in is the only way to draw a class-gated variant in a
  file with no access to the project's `@custom-variant`, and it is labelled
  as a stand-in rather than passed off as the shipped class.
- **No vertical padding**, so the card is exactly 1.75rem; the comment says so
  and the markup carries only `px-1`. The `.logoimg` rule pins
  `height: 1.75rem` with its own comment explaining that `max-w-32` is v4
  spelling the CDN v3 build lacks.
- **Section 1's dark-scheme card renders the card twice** (lines 263–265):
  `SQUARE` with `plate: true`, then `DARKINK` with `plate: true`, with the note
  "A black-ink logo is shown second, because it is the case the card exists
  for". Exactly as claimed.
- **Both question headings** read `Answered: A` (line 105) and `Answered: B`
  (line 128), each with prose naming what the operator chose and why. The
  option cards are labelled "(chosen by the operator)" and "(not chosen)" on
  both questions, so the record of the rejected option survives without
  re-arguing it.
- **Still standalone, no build step**: two CDN `<script>` tags
  (`cdn.tailwindcss.com`, `unpkg.com/lucide@latest`), no bundler, no server, no
  local asset other than the deliberately missing `BROKEN` path that drives the
  real `onerror`. The broken-bytes card still drives the latch *and* its one
  retry for real on a 3 s stand-in, with the comment stating the app's value is
  60 s.
- Five cards for six states, as the expected result requires, and the
  no-logo/loading/profile-error card still carries the note that the three
  render identically.

One cosmetic divergence, pre-existing and not a round-3 change: the mock's own
light `--foreground` is `oklch(0.2 0.02 160)` where the app's is
`oklch(0.14 0.01 160)`. It is inert here — `.plate` is only applied on
`dark: true` strips, where the mock's value `oklch(0.98 0.01 160)` matches the
app exactly — and `docsColourProvenance` passes on it, so it is not a published
claim. Noted for completeness, not as a finding.

## 10. Other mechanical claims spot-checked

- `grep -c "size-3.5" Navbar.tsx` currently finds exactly one occurrence
  (line 90, `size-3.5 rounded-full bg-primary`), so the expected result's
  "prints `0`" is a real state change, and its warning about `grep -c` exiting
  1 on no match is correct.
- The banner `<header>` at `Navbar.tsx:65` carries no literal `role`
  attribute, as the spec says; the only `aria-label`s in the file are
  `nav.openMenu`, `common.appName` and `tenant.switcherLabel`.
- `classTokens` is importable from `src/test/classTokens.ts` and is a whole-
  token split, so every "does not contain `md:hidden`" assertion in the spec is
  non-vacuous.

## 11. Schema conformance

Nothing in either document asks for a task-state write, a timestamp, or a
status outside the ten. The spec's self-referential expected results (the
"cost of the logo bytes" section, the mock) are document assertions, which is
the right shape for a decision whose deliverable is the record, given no
`backend/` file may change. `expected_results` are non-empty, each one
mechanically decidable by someone holding only the list — a file path to grep,
a command to run and judge, or a named Testing Library query with an exact
expected value. The two new ones are the strongest in the list in that respect.

---

## Verdict reasoning

The revision did the hard part correctly: it reversed a recommendation without
leaving the old recommendation's reasoning lying around to contradict the new
decision, it chose a token the project's own guards accept rather than the
`bg-white` those guards exist to catch, it put the paint on a wrapper so the
"never re-colour the artwork" rule survives the reversal intact, and it shipped
the negative criterion in the same breath as the positive one instead of
leaving the presence assertion to stand alone. The numeric cross-references
that the two insertions invalidated are all gone. Every factual claim I was
asked to verify held in the files, and the two test suites and the lint
baseline reproduce the exact figures the reviser reported.

The two new criteria survive adversarial construction. The one escape I found
is narrow, requires defeating a build-time scanner on purpose, and is already
forbidden by the spec's literal-token mandate.

## Suggestions

- §"Theming and contrast" and the card's expected result claim the two-render
  equality "decides the rule in both directions" and name four defeats. Add the
  one escape as an honesty note, in the same voice the spec already uses for
  `w-auto`: jsdom has no Tailwind and the criterion reads no computed style, so
  a `dark:bg-foreground` assembled dynamically would satisfy the equality while
  generating no CSS. One sentence saying "the class list is fixed as literals
  for this reason; code review is where a composed class name is caught" would
  make the criterion's reach exact rather than slightly overstated.
- The new Out of Scope bullet opens "The light card in the **light** colour
  scheme". Its subject is the *paint*, and the surrounding sentence makes that
  clear, but read alone it can be taken to put the card **element** out of
  scope in the light scheme — which directly contradicts the expected result
  requiring `getByTestId("tenant-header-logo-plate")` to resolve in the render
  with no `.dark` ancestor. The criterion catches a developer who misreads it,
  so nothing can ship wrong, but a round is cheaper to save than to spend:
  "Painting the card in the light colour scheme (the wrapper element is still
  rendered there; it simply paints nothing)".
- Join the two facts the spec currently states separately — that no code in
  `src` applies `.dark`, and that dark-mode activation is out of scope — into
  the sentence they imply: the card the operator chose is correctly specified
  and fully asserted, but will not be visible in the running application until
  dark-mode activation ships. The operator chose from the mock, where it is
  visible, so this is not a reason to revisit the decision; it is a reason not
  to expect the card on screen after this task lands.
- Give `inline-flex items-center` on the card the same honesty note `w-auto`
  has. As the mock draws the logo branch the wrapping `Link` is `flex
  items-center`, which blockifies the span's `inline-flex` to `flex`, and
  `items-center` on a single auto-height item is a no-op — so "inserting it
  changes no geometry" is true of the outcome but not because of these two
  tokens. They are a reasonable guard against a non-flex parent, since the spec
  does not fix the `Link`'s display; saying so is more accurate than the current
  rationale.
- The spec says the image's four tokens are "the same four tokens the mock
  draws", while the mock's `<img>` carries a fifth, `logoimg`, for the CDN v3
  build's lack of `max-w-32`. The mock explains itself in a comment and this
  predates round 3, so it is purely a wording tidy if §"Aspect ratio and
  layout" is ever touched again.

VERDICT: APPROVED

Blocking findings: None
