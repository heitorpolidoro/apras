# APRAS-97 — Spec Review (round 1)

VERDICT: APPROVED

Spec reviewed: `docs/tasks/APRAS-97-spec.md`
Tree state: `master` @ `2cb0d48`

## Blocking Findings

None.

## Verification performed

Every factual claim in the spec was checked against the tree rather than taken
from the document.

### Element map — correct

`frontend/src/features/user-administration/components/Navbar.tsx` (176 lines):

| Spec claim | Verified |
| --- | --- |
| 73–81 hamburger, already has `type="button"`, not the target | **true** — `<button>` opens at 73, `type="button"` at 74, closes at 81; `onClick={toggleMobile}`, `aria-label={t("nav.openMenu")}` |
| 128–143 is the `LANGUAGES.map` language button, no `type` | **substantially true** — `LANGUAGES.map` at 129, `<button>` 130–141, `))}` at 142, wrapper `<div>` at 128. The quoted range is the wrapper block, not the button element itself (see Suggestions) |
| 164–169 logout button, untouched | **true** — `<button onClick={logout}>` 164–169, no `type` |
| `aria-pressed` appears nowhere in the component | **true** — zero matches in the file |
| active test is `currentLang.startsWith(lang.code)` over `i18n.resolvedLanguage ?? i18n.language` (line 31), driving the `cn(...)` ternary | **true** — `currentLang` defined at line 31, predicate at line 135 selecting `bg-primary text-primary-foreground` vs `text-muted-foreground hover:text-foreground` |

### Measured baselines — all exact

- `npx eslint` on the two touched files: **`Navbar.tsx` 0 errors / 0 warnings**;
  **`Navbar.test.tsx` 26 errors**, all 26 `@typescript-eslint/no-explicit-any`.
  Matches the spec to the rule id and the count.
- `frontend/vitest.config.ts` thresholds: `lines: 80, functions: 78,
  branches: 76, statements: 80`. Matches exactly; the spec's "do not restate
  different figures" is well-placed since the config comment records the much
  higher *measured* figures (88.26/83.37/79.16/87.41), which an implementer
  could easily mistake for the gate.
- `npx tsc -b` exits **0** at `2cb0d48`, so result 9's tsc clause starts from a
  clean baseline.
- The repo-wide "~375 errors across 64 files" was not re-measured; it is
  context, not a gate — the spec correctly makes the gate per-file.

### The six protected APRAS-91 cases — all six exist

The caller confirmed four. The other two are present and byte-identical to the
spec's quoting:

- `"exposes exactly one link in the banner, the appName logo pointing at /"` — 1 match
- `"renders hamburger toggle button on mobile and desktop collapse button in sidebar"` — 1 match (line 690, in the outer `describe("Navbar")`, not the banner block — the spec does not claim otherwise)

**Is naming them enough to protect them?** Yes, in combination with the other
results, though not on its own. A name list protects against deletion and
renaming only; an implementer could keep a name and gut the body. Result 7 says
"still pass **unedited**", and result 8 restricts the diff to two files — so
`git diff` over `Navbar.test.tsx` showing additions only is a mechanical check
that covers bodies as well as names. The protection is real.

**Is the "existing tests pass untouched" claim plausible?** Verified
structurally rather than by applying the change (I am forbidden to modify
`frontend/`): the test file contains **no** `toMatchSnapshot`,
`toMatchInlineSnapshot`, `outerHTML` or `innerHTML` assertion, so no case can be
broken by an added attribute. The `getByRole("button", { name: "PT" })` lookups
are unaffected — `aria-pressed` changes neither the computed role nor the
accessible name. No case queries by the `pressed` state. The claim holds.

### Default fixture — correct

`src/test/setup.ts` mocks `useTranslation` with `i18n: { language: "pt",
changeLanguage: vi.fn() }` and **no** `resolvedLanguage`, exactly as the spec
says, so `currentLang` resolves to `"pt"` via the `??` fallback in the default
case. `stubI18n` spreads overrides onto that base, so
`stubI18n({ language: "pt", resolvedLanguage: "en" })` yields
`currentLang === "en"` while `i18n.language` stays `"pt"` — which is what makes
mutation 4 catchable at all.

## The four points weighed

### 1. The ARIA decision — sound, and correctly reasoned

Judged against the WAI-ARIA APG, `aria-pressed` on two toggle buttons is the
right call here, and the spec's stated reasons are the real ones.

The honest tension the caller raises is real: APG does model a set of mutually
exclusive options as a radio group (its Toolbar example implements independent
font styles as toggle buttons and *text alignment* as a radio group), so two
`aria-pressed` buttons under-describe the set — they convey each button's state
but not that the two are mutually exclusive. The question is whether that
under-description is **misleading about the state**, which is what this task
exists to fix. It is not. A screen-reader user tabbing to the pair hears
"PT, toggle button, pressed" and "EN, toggle button, not pressed": the active
language is announced on the active control *and* its absence is announced on
the inactive one. That is precisely the information colour alone was carrying.
Nothing announced is false; the grouping relationship is merely unstated.

The radiogroup alternative is worse on this component, for two reasons — one the
spec gives and one it does not:

- **Given.** `role="radiogroup"` + `aria-checked` obliges roving `tabindex` and
  arrow-key navigation (APG Radio Group). The component implements neither, and
  announcing the radio role promises keyboard behaviour that is absent — a
  user who presses Right expecting to move to EN gets nothing. That is a
  regression in truthfulness traded for a gain in grouping, and the spec's
  judgement that it is a bad trade is correct.
- **Not given, and it strengthens the case.** A radiogroup needs an accessible
  name, which here means a new i18n key — explicitly out of scope by the spec's
  own i18n exclusion. So the declined option is not merely larger, it collides
  with another stated boundary.

The `aria-current` rejection is also correct: it is defined for current *item
within a set of navigational items*, and crucially it has no meaningful "false"
announcement to pair with "true", so the inactive button would carry nothing —
reintroducing exactly the asymmetry being removed.

One thing the decision is silent on, which I raise only as a suggestion below:
the grouping *can* be conveyed with zero keyboard obligation.

### 2. The single-expression requirement — not literally verifiable, and the checkable substitute is sufficient

The caller's instinct is right: **no test can distinguish one evaluation of a
predicate from two evaluations that agree.** An implementation written as

```tsx
aria-pressed={currentLang.startsWith(lang.code)}
className={cn(..., currentLang.startsWith(lang.code) ? ... : ...)}
```

is two evaluations and passes every case the spec requires, identically to the
single-binding form the spec demands. So "one evaluation" is not a
*behavioural* criterion at all.

It is, however, a **structural** one, and structurally it is decidable by
inspection: either the diff introduces a local binding inside the `map` callback
that both channels read, or it writes the expression twice. The spec states the
required form concretely ("computed once inside the `map` callback and consumed
by both the `cn(...)` ternary and the attribute"), so an inspector can decide it
without judgement. That is enough for it to stand as a requirement.

And the result that *is* test-checkable — the two channels agreeing on the same
two rendered elements (result 6) — does carry the user-visible guarantee. The
single-binding rule only buys resistance to a *future* edit, which the spec says
openly rather than overselling it. The pairing is honest: the behavioural
requirement is tested, the structural one is inspected, and the spec does not
pretend the test proves the structure. No blocking finding; see Suggestions for
a phrasing improvement to result 2.

### 3. The mutation table — all four mappings traced, all four discriminate

Traced against the real `stubI18n` and the real setup fixture, not read off the
table:

| Mutation | Mapped case | Trace | Holds |
| --- | --- | --- | --- |
| `aria-pressed="true"` hard-coded on both | default fixture | EN renders `"true"`, case asserts `"false"` | **yes** |
| `"true"` on PT only | the swap (`resolvedLanguage: "en"`) | EN renders `"false"`, case asserts `"true"`; PT renders `"true"`, case asserts `"false"` — fails twice | **yes** |
| `===` instead of `startsWith` | the regional tag (`pt-BR`) | `"pt-BR" === "pt"` is false → PT renders `"false"`, case asserts `"true"`; and EN is `"false"` as expected, so the *PT* assertion is the one that must be present — it is | **yes** |
| `i18n.language` instead of `currentLang` | the swap | `i18n.language` is `"pt"` → `"pt".startsWith("pt")` → PT renders `"true"`, case asserts `"false"` | **yes** |

Note the fourth mapping depends on the swap fixture holding `language: "pt"`
while `resolvedLanguage: "en"` — verified above in `stubI18n`. Had the spec
specified the swap as `{ language: "en" }`, mutation 4 would have been
undetectable. The fixture choice is load-bearing and the spec got it right.

Two further mutations not in the table are also caught by the same case set,
which is a good sign the set is over- rather than under-specified:
inverting the predicate (`!isActive`) fails the default fixture, and reversing
the arguments (`lang.code.startsWith(currentLang)`) fails the `pt-BR` case.

Given this repository's record of mutation claims that read correctly and fail
under execution, I note the one way an implementer could still land a passing
but worthless result: writing `aria-pressed={isActive || undefined}`, which
React omits entirely rather than rendering `"false"`. The spec forecloses this
explicitly — result 2 requires the attribute to resolve to the literal
`"false"` on the inactive button, and the default-fixture and swap cases assert
`toHaveAttribute` on both buttons, which fails on an absent attribute. Covered.

### 4. Mechanical decidability of the 9 results by QA

Results 1–8 are decidable from the list alone (named file, named callback,
named attribute, named fixture values, named class tokens, named case strings,
named file boundary).

Result 9 is the compound one the caller flags, and it survives: it names the
directory to run from, both commands, the four threshold figures, and the
per-file ESLint numbers with the file names repeated — `0` in `Navbar.tsx`, `26`
in `Navbar.test.tsx`. Nothing in it points back at the spec body. The "no new
`any`" clause is in fact *subsumed* by the numeric baseline (any new `any`
raises the count above 26), so it is redundant rather than vague. Decidable.

The one result that leans on the spec body is **7** — "the APRAS-91 cases
listed in this spec", of which only four of the six are then quoted inline. QA
holding only the list can still decide it, because the four it quotes are
checkable and the "unedited" clause is checkable via the diff regardless of how
many names are enumerated. It is a soft spot, not a gate failure.

### Scope — one PR, split correctly declined

The spec's own framing (one component, one test file) is accurate and
understated: the production change is two attributes on a single JSX element
plus hoisting one existing expression into a local binding. Four new test cases.
One subsystem, no dependencies, no migration, nothing that could ship
separately. `NEEDS_SPLIT` would be wrong.

### No mock, no operator question — both calls correct

No mock is right. The task adds no class, changes no token, touches no layout:
`before` and `after` render byte-identical CSS. A mock would show two identical
pairs of buttons and could not inform anything, which is the one case where the
visual-decision rule does not bite.

No operator question is right. The single open choice was which ARIA pattern,
and that is a technical decision with a keyboard-behaviour consequence —
precisely the category the rules keep in words rather than on a card. There is
no appearance question here for the operator to have an opinion about, so
inventing one would have cost a round and produced no information.

## Suggestions

- **Result 2's "same single evaluation" is a structural requirement stated in
  behavioural language.** No test can tell one evaluation from two that agree.
  Consider phrasing it as the inspectable artifact it actually is — "a single
  local binding inside the `map` callback is read by both the `aria-pressed`
  attribute and the `cn(...)` ternary; the predicate text
  `currentLang.startsWith(lang.code)` appears exactly once in the file" — which
  a QA agent can decide by `grep -c` rather than by judging intent.
- **The element-map range `128–143` is the wrapper `<div>` block, not the
  button.** The button element is 130–141 (`LANGUAGES.map` at 129, `))}` at
  142). Since the whole point of that table is to stop an implementer verifying
  against the wrong element, the precise range would serve it better. The
  spec's prose identification ("the element inside the `LANGUAGES.map`
  callback") is unambiguous, so nothing is actually at risk.
- **Result 7 quotes four of the six protected case names.** Inlining all six,
  or replacing the enumeration with the stronger and simpler "no pre-existing
  `it(...)` block in `Navbar.test.tsx` is modified — the diff is additions
  only", would make the result fully self-contained for a QA agent that never
  sees the spec.
- **Result 9 bundles three independent gates in one checkbox** (tsc, coverage,
  per-file lint). Each is decidable, but as one checkbox a partial pass has no
  way to be recorded. Splitting into three results would cost nothing.
- **The grouping relationship can be conveyed with no keyboard obligation,
  and Out of Scope could say so.** The spec rightly declines `role="radiogroup"`
  because of the roving-`tabindex`/arrow-key debt. Worth noting for a follow-up:
  `role="group"` plus an accessible name on the **existing** wrapper `<div>`
  (line 128) conveys "these two belong to one set" without implying any
  keyboard pattern — `role="group"` carries no interaction contract. It would
  need one new i18n key, which is why it belongs in a later task, not this one.
  Mentioning it in Out of Scope would record that the exclusivity gap was seen
  and deferred deliberately, rather than leaving the next reader to re-litigate
  the radiogroup question.
- **The suite is the real guard on the "existing tests still pass" claim.** The
  spec cites an APRAS-91 reviewer who ran it. I confirmed the structural reason
  it is safe (no snapshot or raw-HTML assertions anywhere in the file), which is
  a stronger argument than the citation and could replace it.
