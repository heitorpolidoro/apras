# APRAS-98 — spec review, round 3 (findings-only)

Spec: `/Users/heitor/workspace/apras/docs/tasks/APRAS-98-spec.md`
Mock: `/Users/heitor/workspace/apras/docs/tasks/APRAS-98-mock.html`
Tree: `master` @ `2cb0d48`. Nothing written outside this file; nothing staged.

VERDICT: NEEDS_REVISION

## Scope of this round

Round-2 blocking findings B8 and B9 only, plus a consistency pass over the
sections the generator changed to fix them (Decision 3b, Decision 4 + the new
§ 2 question, § Test criteria, expected results 3/4/6/8, and the mock).

---

## 1. B9 — the mock's colours. RESOLVED.

Verified by recomputing every figure from `src/index.css` rather than trusting
the spec. Conversion: oklch → linear sRGB → WCAG relative luminance (note the
oklch matrix already yields *linear* sRGB; applying the sRGB transfer function a
second time is the mistake that produced the earlier "3.34" / "8.41" confusion —
the correct light-mode figure is 3.356:1).

| pair | measured | spec/mock claim |
|---|---|---|
| `--ring` light `oklch(0.62 0.15 160)` → `#00a166` | — | `#00a166` ✓ |
| ring on `--card` (light, `#ffffff`) | **3.3564:1** | 3.36:1 ✓ |
| ring on `--destructive` (light, `#e60016`) | **1.4252:1** | 1.43:1 ✓ |
| `--destructive` light → hex | `#e60016` | `#e60016` ✓ |
| previous round's drawn blue `#1d4ed8` on card | 6.7016:1 | matches the round-2 finding |

The mock now carries `--foreground: oklch(0.14 0.01 160)`,
`--muted-foreground: oklch(0.53 0.02 160)`, `--destructive: oklch(0.58 0.24 27)`
and `--ring: oklch(0.62 0.15 160)`, all byte-equal to `src/index.css:34-66`; the
header swatch names the token, its oklch value, its hex and the 3.36:1 figure;
and every panel in both § 1 and § 2 carries `max-w-md`. B9 is fully addressed.

One residual, non-blocking: the mock has **no `.dark` block**. Dark mode is where
the measurements invert — ring on dark card is **6.4408:1** (far more prominent)
and ring on dark destructive is **1.8085:1** (still near-invisible). The light
panel is the right one to decide on, so this does not block, but a dark row would
make the § 2 question complete.

## 2. B8 — the Decision 3b test. PARTLY RESOLVED; the replacement's second half
reintroduces the same defect.

I read `ObraPrintDialog.tsx:40-69` to fix the exact teardown/setup ordering the
discrimination argument depends on. The rejected `[open, onClose]` effect, on a
re-render while open, does:

1. cleanup: `removeEventListener`, then `opener?.focus()`
2. setup: `const opener = document.activeElement`, then
   `focusableWithin(panel)[0]?.focus()`, then `addEventListener`

**Test (a) now discriminates — this is a real fix.** Moving focus to a control
that is *not* `focusableWithin(panel)[0]`, asserting that node by identity
*first*, then re-rendering with a fresh `onClose` and asserting the same node:
under the alternative, step 2 drags focus to `panel[0]`, so the assertion fails.
The premise assertion is what removes the vacuity the old phrasing had. Good.

**Test (b) does not discriminate, and the spec asserts that it does.** The spec
(lines 348-355) claims "the setup re-captures the opener from
`document.activeElement` at re-render, so this fails too". Trace it: step 1
focuses the *original* opener before step 2 reads `document.activeElement`.
Therefore the re-captured opener **is the original opener** — the same node — and
the later Escape restores focus to it. Test (b) passes under the rejected
`[open, onClose]` implementation exactly as it passes under the ref
implementation. The re-capture the spec is worried about cannot be observed this
way precisely *because* the cleanup that precedes it restores focus first.

This matters more than a wrong sentence in the prose, because expected result 4
promotes it to a verifiable claim: "Two hook tests prove it, **both of which fail
against a `[open, onClose]` implementation**". An implementer who honours that
result literally cannot (test (b) cannot be made to fail), and QA, reading only
the results, will credit a test that carries nothing. It is B8's defect
relocated, not removed.

The decision itself is still covered — by test (a) alone. Two ways out, either
acceptable, neither of which I will write:

- demote (b) the way the old Escape assertion was demoted: keep it as a
  regression case for "the opener is captured once", state that it passes under
  both implementations, and remove it from result 4's "both fail" claim; or
- replace (b) with an observable that is actually one-directional about teardown
  — e.g. spy on `document.addEventListener`/`removeEventListener` and assert the
  call counts are unchanged across a re-render with a fresh `onClose`. That
  observes "the effect did not tear down" directly, which is what 3b says.

**The demotion of the old assertion is stated clearly enough.** It appears
twice — § Test criteria lines 331-335 ("It may be kept as a separate case for
that different bug, but it does not test 3b") and, decisively, inside the
recorded result itself (lines 400-402: 'may be asserted as well but does **not**
count towards this result: it passes under `[open, onClose]` too'). Since QA
reads only the results, having it in result 4 is what makes it safe. No finding
here.

## 3. The § 2 question. Claims verified; the question is sound; the default is wrong.

Every factual claim checks out:

- **The split is real.** `src/components/ui/button.tsx:7` carries
  `focus-visible:ring-offset-2`; `src/components/ui/alert-modal.tsx:115` carries
  `focus-visible:ring-2 focus-visible:ring-ring` with no offset. Nine files use
  `focus-visible:ring-ring`; only two (`button.tsx`,
  `GeneralDashboardPage.tsx:162`) add an offset. And `TenantProfilePage`'s two
  controls are hand-rolled `<button>`s, not `Button`, so neither precedent is
  automatic.
- **1.43:1 and 3.36:1** — confirmed above.
- **`--color-card` is in the `@theme` block** — `src/index.css:8`,
  `--color-card: var(--card)`. And Tailwind v4 resolves `ring-offset-<color>`
  from the `--color` namespace, so `ring-offset-card` is a valid utility.
- **Tailwind v4's default ring-offset colour is a hard-coded `#fff`** — confirmed
  in the installed `tailwindcss@4.2.4`:
  `node_modules/tailwindcss/dist/lib.js` contains the literal
  `ring-offset-color","#fff"`. So pinning `ring-offset-card` is not decoration:
  bare `ring-offset-2` paints a white gap on a dark card under `.dark`.

**Is it a genuine question?** Yes. Both branches are compliant (the ring keeps a
3.36:1 boundary against the card in either form; A's inner edge against the red
fill is the only edge that fails, and 1.4.11 is satisfied by one distinguishable
boundary), both are drawn side by side on the screen the choice affects, both
are labelled A and B, the mock says in plain words that one letter is a complete
answer, and the spec pins exactly what changes on each branch ("appends
`focus-visible:ring-offset-2 focus-visible:ring-offset-card` to both buttons and
nothing else in this spec changes"). This is the first version of this question I
would put in front of an operator.

**The default should be B, not A.** Asked directly, my answer is: *keep the
question, flip the default to B.* Not "close on B and drop the question" — the
gap is a visible change to a dialog the operator looks at, and it diverges from
the sibling dialog's appearance, so it is legitimately theirs to decide. But the
un-answered path should be the safer one, and A is not:

- By the spec's own measurement, A ships a near-invisible inner edge on the
  **destructive** button — the one whose activation is irreversible (the slug
  change breaks every saved link, with no redirect).
- For a `<button>`, `button.tsx` is the stronger precedent than a hand-rolled
  `<button>` inside `alert-modal.tsx`; `alert-modal.tsx`'s omission reads as an
  oversight, not a decision, since the component it bypasses sets the offset.
- The margin is machine-checked nowhere: `src/lib/contrast.ts:59` states that
  `border`, `input` and `ring` are not measured and the 3:1 non-text minimum is
  out of scope, and `MEASURED_PAIRS` has no `ring` entry. Nothing downstream will
  catch A's weak edge.

This one is a suggestion, not a blocking finding: A is defensible and compliant,
so the spec is shippable as written.

## 4. The exit-path table. RESOLVED.

Expected result 3 (lines 388-390) carries it verbatim in the *result*, not only
the prose: "Escape and Cancel are the two cases that prove restoration; the
Confirm case pins a known outcome and does not." QA reading only the results
gets the discrimination warning. The mock's table agrees ("Only the first two
rows fail if restoration regresses"). No finding.

## 5. What `M2` actually catches.

`M2` = `/querySelectorAll\s*(<[^>]*>)?\s*\([^)]*tabindex/i`.

Against `focusTrap.ts:39`, `querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)`:
**it does not match.** The generic group `(<[^>]*>)?` consumes `<HTMLElement>`
fine, but the argument text is the identifier `FOCUSABLE_SELECTOR` — the word
`tabindex` is on lines 34-35, in the constant's own definition, nowhere inside
that call's parentheses. The regex is correct for its stated purpose and that
call is simply not its target.

So, precisely: `M2` catches only a `querySelectorAll` whose argument *text*
inlines `tabindex` — i.e. the hand-rolled copy that pastes the selector list as a
literal, `querySelectorAll('button:not([tabindex="-1"]), [tabindex]:not(…)')`.
That is exactly the duplication shape the guard exists for, and it is also why
`focusTrap.ts` is caught by `M1` instead. Nothing in the assertions breaks:
assertion 1 excludes `focusTrap.ts` anyway, and assertion 4's positive control is
scoped to `M1` explicitly.

Two consequences worth recording, both non-blocking:

- The spec's own sentence at lines 265-266 names `focusTrap.ts:39` while
  explaining the generic group, which invites an implementer to conclude the
  regex is *meant* to match that line, find that it does not, and "fix" it until
  it does — at which point assertion 1 starts failing on the real module. One
  clause ("`M2` does not match that call, and must not: its argument is the
  constant") removes the trap.
- `M2` has no positive control anywhere, and cannot have one over the real tree,
  since by construction no file inlines the selector. The spec is honest that the
  filter checks are self-referential, but it stops short of saying `M2` is
  unproven. A clearly-labelled synthetic match (not a substitute for the real-tree
  control, which `M1` carries) would at least prove the regex compiles and matches
  the shape it names.

---

## Blocking Findings

- **B10 — Decision 3b's second test passes under the implementation 3b
  rejects, and expected result 4 asserts the opposite.** § Test criteria lines
  348-355 and result 4 (b) claim a re-render with a new `onClose` while focus is
  inside the panel makes the alternative "re-capture the opener", so a later
  Escape restores the wrong node. It does not: under `[open, onClose]` the
  cleanup runs `opener?.focus()` *before* the setup reads
  `document.activeElement` (`ObraPrintDialog.tsx:51-54` captures, then
  `:68` restores), so the re-captured opener is the *same original opener* and
  the Escape assertion passes identically under both implementations. Result 4's
  "**both of which fail against a `[open, onClose]` implementation**" is
  therefore unsatisfiable, and QA — which reads only the results — will credit a
  test with no discriminating power, which is round-2's B8 relocated rather than
  fixed. Test (a) does discriminate and is correct. Either demote (b) in the
  result the way the old Escape assertion was demoted, or replace it with an
  observable that is one-directional about teardown (for example, listener
  add/remove call counts across the re-render).

## Suggestions

- Flip § 2's default from A to B while keeping the question. A's own stated
  measurement puts a 1.43:1 edge on the irreversible destructive button, the
  margin is machine-checked nowhere (`src/lib/contrast.ts:59` excludes `ring`),
  and for a `<button>` `button.tsx` is the stronger precedent than
  `alert-modal.tsx`'s hand-rolled one. If the operator never answers, the spec
  should ship the stronger indicator.
- Say that option B as specified is *better* than `button.tsx`'s form rather than
  equal to it: `button.tsx:7` and `GeneralDashboardPage.tsx:162` both use bare
  `ring-offset-2` with no offset colour, which resolves to Tailwind v4's
  hard-coded `#fff` and paints a white gap on a dark card. Adding
  `ring-offset-card` is the fix those two sites lack. The mock's "matches
  `button.tsx`" caption undersells it.
- Add a `.dark` row or panel to the mock. Dark mode inverts both figures (ring on
  dark card 6.44:1, ring on dark destructive 1.81:1), and it is the mode where
  `ring-offset-card` versus the `#fff` default is visible.
- Add the clause that `M2` deliberately does not match
  `focusTrap.ts:39`'s `querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)`, so
  nobody "repairs" the regex until it does, and state that `M2` is unproven over
  the real tree.
- Result 8 is conditional on an answer QA cannot see. Once the operator answers,
  edit the result to one unconditional class list rather than leaving the
  disjunction for QA to resolve.
