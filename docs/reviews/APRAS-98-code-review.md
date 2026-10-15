# APRAS-98 — Code review

Subject: `git -C /Users/heitor/workspace/apras/.claude/worktrees/agent-a0968c01940cb4819 diff --cached -M`
— 9 paths, 685 insertions / 41 deletions, 2 renames.
Spec: `docs/tasks/APRAS-98-spec.md`.

## Scope of the staged set

`git status --porcelain` in the worktree shows exactly the nine expected paths
and **nothing else**: no unstaged modifications, no untracked files. So
`alert-modal.tsx` is untouched (R1 satisfied — it keeps its own document-level
Escape effect), and `ObraPrintDialog`'s own test file is byte-identical to `HEAD`
by the same evidence (it is absent from both the staged and the unstaged diff).

**One divergence from the dispatch to flag.** The branch is on top of
`25e9dc6` ("fix(APRAS-120): keep datetime columns naive…"), not `1f0079b`. The
main checkout is three commits ahead (`2cb0d48` APRAS-91, `1f0079b` APRAS-97,
`e1d19f2` APRAS-111 docs), and APRAS-91/97 both touched frontend tests. Nothing
in this diff conflicts with them on inspection, but the merge must be re-verified
at landing time rather than assumed. Not a defect in the change.

### The renames (R5)

```
R100  features/project-management/lib/focusTrap.ts      -> lib/focusTrap.ts
R099  features/project-management/__tests__/focusTrap.test.ts -> lib/__tests__/focusTrap.test.ts
```

`focusTrap.ts` is a true 100% rename — identical blob (`11dca67` on both sides),
and `shasum` of the two blobs agrees (`d98de682…`). So the module contents,
including the `// skipcq: JS-R1005` block and its now partly-stale prose, are
byte-identical, as Decision 1/2 and R5 require. A direct `diff -u` of the two
test blobs shows exactly one changed line, the import specifier
`"../lib/focusTrap"` → `"../focusTrap"`. `grep` finds no remaining reference to
`project-management/lib/focusTrap` anywhere under `src`, and
`features/project-management/lib/` now holds only `obraPrintDocument.ts`.

`src/lib/` as the destination matches AGENTS.md:422-423 ("Generic utility
functions"); `src/hooks/` is an existing shared-hooks directory with twelve
siblings. Architecture compliant.

## Implementation

`useDialogFocus.ts` does what Decision 3 and 3b specify, and the specific points
asked about all check out:

- `onClose` is kept current by **its own** `React.useEffect(… , [onClose])`
  (lines 42-44), never by a render-time assignment, and the comment states the
  reason (a discarded render).
- the closed branch is `if (!open) return undefined;` (line 51) with the JS-0045
  rationale in a comment immediately above it.
- `panelRef` and `data-testid="tenant-slug-confirm-panel"` are on the **panel**
  `div` (`className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl"`), not on
  the `fixed inset-0 … bg-black/40` scrim, and the inline comment says why.
- the `useDialogFocus(confirming, () => setConfirming(false), panelRef)` call
  sits at line 117, above `if (isPending || !data) return <Spinner />` (line
  119). Hook order is stable.
- `ObraPrintDialog` lost its whole effect (-37/+13) and now only supplies the
  panel ref; its docstring was reworded to point at the hook, as the spec asked.
- the focus ring is **option A**: exactly
  `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring` on
  both buttons, no `ring-offset-*`, no other class changed, no raw palette class.
  That matches the operator's recorded answer, not the spec body's earlier
  default-B prose.
- translation keys are untouched (`slugConfirmTitle/Body/Cancel/Cta`).

KISS/DRY: the hook is the single copy of the effect, the trap is the single copy
of the algorithm, and no speculative options were added (no `useCallback`
requirement, no `initialFocusRef`, no `returnFocusRef`). No security surface:
no user input reaches a selector, no DOM is built from strings, no secrets.

## Unit test quality — verified by mutation, not by reading

This is the part the task's history demanded, so every claim below was produced
by changing the implementation and watching the suite.

### 1. The Decision 3b pair really discriminates

I set the keydown effect's deps to `[open, onClose]` (the rejected
implementation) and ran `src/hooks/__tests__/useDialogFocus.test.tsx`:
**2 failed / 8 passed**, and they are exactly the two claimed cases, failing for
exactly the claimed reasons:

- *leaves focus on a non-first control across a re-render with a new onClose
  identity* — `expected <button data-testid="first"> to be <button
  data-testid="middle">`, i.e. the teardown/setup pair dragged focus off
  `middle` onto `first`, at `useDialogFocus.test.tsx:156`.
- *adds and removes no keydown listener across a re-render with a new onClose
  identity* — `expected 1 to be +0` on the `removeEventListener` delta, at
  `useDialogFocus.test.tsx:173`.

The developer's claim is therefore accurate as stated. The hook was restored
from a pre-mutation copy and `cmp`/`shasum` confirm byte identity
(`f75d741d6acf72bb4e16d9e6aec5b8a9847c34b6`).

The converse also holds. The non-discriminating phrasing *"a later Escape
invokes the new callback"* **passed** under the mutation — and it is present
only as a third case whose own name says so: `"invokes the latest onClose on a
later Escape (a different bug — not 3b)"`. It is inside the 3b describe block but
cannot be mistaken for one of the two. The second excluded phrasing, *"the
re-render does not re-capture the opener"*, is not written anywhere in the file.
No `not.toContainElement` and no "focus is outside the panel" phrasing exists in
either new test file.

### 2. Restoration is proven where the spec says it is, and only there

I deleted `opener?.focus()` from the cleanup and ran the hook, page and
`ObraPrintDialog` suites: **5 failures**, and the set is exactly right.

- hook: *restores focus to the opener and drops the listener when open goes
  false*
- `ObraPrintDialog` (pre-existing, unmodified): *closes on Escape and returns
  focus to the control that opened it*; *returns focus to the opener after a
  completed print too* — so the extraction is pinned from the old side as well
- page: *closes on Escape, sends nothing, and returns focus to the Save button*;
  *returns focus to the Save button when Cancel closes the dialog*

The Confirm → `document.body` case did **not** redden, which is precisely what
the spec predicted and what the test file says about itself. Escape and Cancel
carry the restoration proof; Confirm pins an outcome. Empirically confirmed, not
taken on trust.

I also removed the `cycleTabWithin` branch: 4 failures, two in the hook tests
and two in the page tests (*keeps Tab inside the panel when it walks past the
last control*, *cycles Shift+Tab from the first control to the last*). The trap
assertions are load-bearing too. Both mutations restored and `cmp`-verified.

### 3. The R7 guard reddens

I planted my own three decoys under `src/lib/` (not the developer's) and ran
`focusTrapSingleImplementation.test.ts`. All three detection paths fired:

```
has no second copy …                 → ["src/lib/decoyReviewM1.ts (M1)",
                                        "src/lib/decoyReviewM2.ts (M2)"]
carries the JS-R1005 suppression …   → + "src/lib/decoyReviewSkipcq.ts"
proves the sweep and M1 work …       → + "src/lib/decoyReviewM1.ts"
```

The `M2` decoy was a realistic hand-rolled copy — `querySelectorAll<HTMLElement>(`
newline, then the inlined `'button:not([tabindex="-1"]), [href], …'` string — and
`/querySelectorAll\s*(<[^>]*>)?\s*\([^)]*tabindex/i` matched it. So the regex
does match what it claims to, across a line break and through the generic
parameter, and the developer's report of closing that gap is verified. Note the
matcher is reported by name in the failure message, which makes the guard read as
a report rather than a bare boolean.

I then tested the exception route itself: with
`[{"file":"src/lib/decoyReviewM1.ts","matcher":"M1","reason":"  ","task":"APRAS-98"}]`
the copy assertion correctly *passed* (the file was subtracted) while
*carries every exception with a reason and a task* **failed** on the blank
reason — and the positive control failed independently, which is a good
property: an exemption cannot hide a copy from every assertion at once.
Both decoys deleted, exceptions file restored and `cmp`-verified; the worktree
is back to nine staged entries and zero untracked files.

## The four escalations

**1. The one `eslint-disable-next-line react-hooks/exhaustive-deps`. I agree
with the developer: keep it.** I verified both halves of its argument. Removing
the directive with `[open]` intact produces exactly one finding —
`78:6 warning React Hook React.useEffect has a missing dependency: 'panelRef'`
— and nothing about `onClose`, which does independently confirm the callback is
read through the ref rather than closed over. The suppression-free alternative is
also real: with `[open, panelRef]` and no directive, `npx eslint
src/hooks/useDialogFocus.ts --report-unused-disable-directives` exits 0 silently
and all 10 hook tests pass, including both discriminating cases — so
"observably identical" is verified, not accepted. I still prefer the shipped
form, for one reason the developer undersells: Expected Result 4 says the keydown
effect "depends on `[open]` **alone**", and a reviewer or QA reading
`[open, panelRef]` has to re-derive ref stability before it is obviously
compliant. A one-line suppression with two lines of comment saying what it
suppresses and why is the cheaper thing to read. If a future task wants the
directive gone, `[open, panelRef]` is the right move and this review records that
it was measured as equivalent.

**2. Deleting the unmount-restore test. The call was defensible; the stated
reason is slightly too strong, and that leaves a small real gap.** The narrower
test (*drops the listener when the holder unmounts while open*) is honest and its
comment explains itself. But "unmounting takes the opener with it" is a property
of *that harness*, not of the DOM: the harness renders the opener inside the tree
it unmounts. I wrote a throwaway probe with the opener appended to
`document.body` outside the rendered container, unmounted the dialog, and
`document.activeElement` was the opener — it passes, so the unmount path is
provable. It matters a little because `ObraPrintDialog`'s real shape is exactly
that: the print button lives in the parent and survives the dialog's unmount, so
the production path is reachable and currently covered only by the `open`-goes-
false case running the same cleanup. Same code, so no behaviour is unverified —
hence a suggestion, not a blocker. Probe deleted.

**3. The Confirm case's labelling. Satisfied, with one correction to the
developer's report.** The describe-block docstring states it in plain English
("**Escape and Cancel prove restoration** … The **Confirm** case does not prove
it and is not credited with doing so; it pins a known outcome"), and the
assertion carries `// Pinned, not credited: see this describe's note.` The
*test name* — "submits the changed slug on Confirm and leaves focus on
document.body" — names the node but does **not** itself say the case proves
nothing. The spec's requirement (the case must not stand in for the other two) is
met; the report's "the test name … states so" is not quite right.

**4. The 0%-covered exceptions JSON. The developer is right, and the precedent is
stronger than claimed.** `coverage.include` is `src/**/*` with no JSON exclude,
and `coverage-summary.json` lists **both**
`src/__tests__/themeTokenMigration.exceptions.json` and
`src/__tests__/focusTrapSingleImplementation.exceptions.json` with
`{"total": 0, "covered": 0, "pct": 0}`. Zero statements, so it cannot move any
aggregate or any threshold — the `0%` is a display artefact, not a coverage loss.
Leaving `vitest.config.ts` alone was correct.

## Re-measured gates

All figures below are my own runs in the worktree, not the developer's.

| Gate | Result |
|---|---|
| `npx vitest run --coverage` | exit 0 — **190 files / 2518 tests passed**; 92.24 lines / 87.86 functions / 85.23 branches / 91.52 statements, all above the 80/78/76/80 thresholds |
| `npx tsc -b` | exit 0 |
| `npx eslint .` | **377 errors / 2 warnings / 66 files** |
| eslint baseline | **377 errors / 2 warnings / 66 files**, per-file diff **NONE** |

The baseline was measured without touching the worktree: `git archive HEAD
frontend` extracted into the scratchpad with `node_modules` symlinked, then
`eslint . -f json` there, and the two per-file maps compared in Python. Zero
files changed their counts. The developer's correction of the spec's approximate
"~375 across 64" to 377/2/66 is accurate.

Coverage of the new code: `src/hooks/useDialogFocus.ts` 100% lines / 100%
statements, `src/lib/focusTrap.ts` 100% / 100%.

## Suggestions

- Rebase onto current `master` before landing and re-run the frontend suite: the
  branch base is `25e9dc6`, three commits behind, and two of those commits
  (APRAS-91, APRAS-97) touched frontend tests.
- `useDialogFocus.ts` exports both a named and a default binding, and it is the
  only file in `src/hooks/` with a default export. Pick one — the named export,
  to match the eleven siblings — and update the two call sites.
- *carries every exception with a reason and a task* iterates an empty array and
  therefore asserts nothing in the shipped tree. The loop does work (I reddened
  it with a blank-`reason` entry), but consider validating a synthetic entry in a
  table-driven case so the validator is exercised by the committed test rather
  than only by a reviewer's decoy.
- Add the unmount-restore case back in the shape that can prove it: an opener
  created outside the rendered container, focused, then the dialog unmounted,
  asserting `document.activeElement` is that opener by identity. I verified it
  passes against the current hook. That closes escalation 2's gap honestly.
- The guard's header says `M2` "has never fired against a real file in this
  repository". It has now, against a decoy file in a review run. Consider
  rewording to "never fires against the shipped tree, by design", which is the
  durable claim, and recording that the regex was exercised.
- Guard assertion 3 pins the consumers by the import string only, so it survives
  a change that keeps the import but drops the `cycleTabWithin` call (verified —
  it stayed green through that mutation). The hook and page tests do catch it, so
  this is only about not over-reading assertion 3; a sentence in the "does not
  detect" list would cover it.
- `src/features/user-administration/components/TenantBrandColors.tsx:384` also
  registers a document-level `keydown`. The spec's "two document-level Escape
  effects exist after this task" is therefore an undercount of document keydown
  listeners overall (three). Worth naming in whatever task eventually unifies
  `AlertModal`'s trap.

VERDICT: APPROVED

Blocking findings: None
