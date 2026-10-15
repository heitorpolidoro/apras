# APRAS-98 — Give the slug-change dialog Escape and a focus trap

## Scope

The confirmation dialog rendered by the `confirming` branch of
`frontend/src/features/user-administration/pages/TenantProfilePage.tsx`
(lines 418-468) is a real modal — `role="dialog"`, `aria-modal="true"`,
`aria-labelledby` — with no keyboard behaviour at all: Escape does nothing,
focus never enters the panel, and Tab walks straight out into the page
underneath. This task gives it the three behaviours a modal owes a keyboard
user (Escape closes, Tab is trapped, focus is restored on close) **by reusing
the implementation APRAS-118 already shipped**, not by writing a second one,
and adds the focus indicator those two controls are missing (§ Decision 4).

Out of scope: the dialog's appearance beyond that focus ring, its copy, its
confirm/cancel semantics, the slug validation around it, and
`src/components/ui/alert-modal.tsx`'s own missing trap (`AlertModal` is used in
many places and changing its focus behaviour is a separate, larger task — it is
**not modified here**, and its own document-level Escape effect stays where it
is).

## Decisions this spec closes (these are the point of the task)

**1. `focusTrap.ts` is reused as it stands, and it moves.**
`frontend/src/features/project-management/lib/focusTrap.ts` exports
`FOCUSABLE_SELECTOR`, `focusableWithin(panel)` and `cycleTabWithin(event,
panel)`. It is exactly the Tab behaviour result 2 asks for — both edges, the
mirrored Shift+Tab case, the single-control case, and the escaped-focus
re-entry — it is pure, it takes the panel as an argument, and it has no
dependency on anything under `features/project-management/`. It is reused
unchanged; no new trap is written.

A module used by `user-administration/` as well no longer belongs inside
another feature. **Move it** to the generic-utility home AGENTS.md already
describes (`src/lib/` — "generic utility functions", AGENTS.md:422-423):

- `git mv frontend/src/features/project-management/lib/focusTrap.ts frontend/src/lib/focusTrap.ts`
- `git mv frontend/src/features/project-management/__tests__/focusTrap.test.ts frontend/src/lib/__tests__/focusTrap.test.ts`
  (the sibling of the existing `src/lib/__tests__/contrast.test.ts`)

Cost of the move: two import specifiers (the test's `../lib/focusTrap`, and
`ObraPrintDialog.tsx:6`) plus the new importer. No barrel file, no public API
change, no coverage-config change — `vitest.config.ts` includes `src/**/*`, so
the moved file is measured exactly as before. The file's contents are carried
over verbatim; this is a rename, not a rewrite.

Note what that verbatim carry-over implies for the module's docstring: it opens
"Extracted from `ObraPrintDialog` for two reasons" and talks about "the dialog's
keydown handler". That is true as history and result 4 requires the contents
unchanged, so it is **not** rewritten here — but from `src/lib/` it will read as
project-management-specific. Generalising that prose is a later, cosmetic edit,
deliberately not bundled into a rename this task needs to be byte-identical.

**2. The `skipcq: JS-R1005` on `cycleTabWithin` moves with the function,
untouched.** It is a line-scoped suppression attached to the declaration, so a
rename keeps it effective and no new DeepSource finding appears. The suppression
must appear in exactly one place when this task is done — which is the second
reason not to copy the module.

Its stated removal condition is now **half** satisfied, and the spec records
that rather than acting on it: the comment says "remove this line once the
threshold has landed on `master` and a run there confirms which of the two
explanations held", and
`cyclomatic_complexity_threshold = "medium"` did reach `master` with APRAS-118
(`e71664f`). The second half has not happened — no DeepSource run on `master`
has been read back to tell "config comes from the default branch" apart from
"the analyzer measures this function above 15". Until that reading exists,
removing the suppression would re-open the finding blind. So: **the comment is
not edited and the suppression is not removed in this task**, and this paragraph
is the record of why a half-fired condition is not a fired one.

One consequence to name rather than hide: carrying the comment over verbatim
leaves prose on `master` that is now partly stale — its "this branch could never
see its own fix" was true on the APRAS-118 branch and is not true once the
threshold is on `master`. Rewording it is bundled into the same deferred,
cosmetic follow-up as the module docstring (§ Out of Scope), for the same
reason: result 5 requires this rename to be byte-identical.

**3. "Mirroring" `alert-modal.tsx`'s Escape effect means copying its *shape*,
not importing it — and the copy is made once, in a shared hook.**
`AlertModal`'s Escape handling is a small effect inside a component body
(`alert-modal.tsx:57-65`) and is not exported, so there is nothing to import;
that component keeps its own effect and is untouched. `ObraPrintDialog.tsx`
(lines 41-70) already mirrors that shape and adds the two things this task needs
next to it: focus into the panel on open, and `opener?.focus()` from the
effect's cleanup so every exit path restores focus. Duplicating that effect into
`TenantProfilePage` would be the defect this task exists to avoid.

So **extract it once**: a new hook `frontend/src/hooks/useDialogFocus.ts`
taking `(open, onClose, panelRef)` and owning the whole document-level keydown
effect — focus the first focusable element on open, Escape calls `onClose`, Tab
delegates to `cycleTabWithin`, cleanup removes the listener and returns focus to
the element that was active when the dialog opened. `ObraPrintDialog` then calls
the hook instead of holding its own effect, and the slug dialog calls the same
hook. The hook must keep `ObraPrintDialog`'s `return undefined` on the closed
branch — DeepSource JS-0045 objects to mixing an implicit and an explicit
return. Two document-level Escape effects exist after this task (`AlertModal`'s
and the hook's); that is stated, not hidden.

**3b. The hook's dependency contract — `onClose` lives in a ref, deps are
`[open]`.** This is a decision, not an implementation detail, because the
alternative changes the code and the tests.

`ObraPrintDialog`'s effect has deps `[open, onClose]`. If the hook kept that and
`TenantProfilePage` called it as `useDialogFocus(confirming, () =>
setConfirming(false), panelRef)`, every re-render while the dialog is open would
pass a fresh arrow, tear the effect down (running `opener?.focus()`), and set it
up again — moving focus back to the first control and re-capturing "the opener"
from whatever happened to be focused at that instant. A `useCallback` at each
call site would fix it by convention, i.e. by relying on every future caller to
remember.

Decision: **the hook holds `onClose` in a ref and its keydown effect depends on
`[open]` only.** The ref is kept current by its own `useEffect` with `[onClose]`
deps (never by a bare assignment during render), and the keydown handler reads
`ref.current` at event time. Call sites may therefore pass an inline arrow, and
`TenantProfilePage` does.

Consequence for result 5: `ObraPrintDialog`'s deps array changes from `[open,
onClose]` to the hook's `[open]`. "Unchanged" there means **observably**
unchanged — its existing test file passes with no change in substance — and this
deps narrowing is the one intentional difference, which can only remove a
teardown that was never wanted. The hook carries a test for it (§ Test
criteria).

**4. The two dialog controls get the house focus ring.** Today
`TenantProfilePage.tsx`'s Cancel button (opens at line 447, `className` at 450)
and confirm button (opens at 454, `className` at 457) carry **no**
`focus-visible:` class at all. That was survivable while focus never entered the
panel; this task moves focus in, so without a ring a keyboard user lands on an
invisible selection — a WCAG 2.4.7 failure this change would introduce.

So the ring is added, built on the three classes the house already uses in nine
places, including `alert-modal.tsx:115` and `PublicObrasReportPage.tsx:102`:
`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring`. Of
the three, only `ring-ring` carries a colour, and it is a semantic theme token;
`focus-visible:outline-none` and `focus-visible:ring-2` carry no colour at all.
So APRAS-85's migration guard is satisfied: no raw palette class is added, and
no other class on either button changes.

This decision is **closed in favour of the ring** — "no indicator" is the
accessibility gap the task exists to avoid and is not a shippable outcome. The
accompanying mockup `docs/tasks/APRAS-98-mock.html` therefore frames today's
state and the ring as a **before/after**, not as an A/B to ratify, and renders
the app's real token values (`--ring: oklch(0.62 0.15 160)` — the brand emerald
≈ `#009f68`, measuring 3.4054:1 on `bg-card`, just over the 3:1 WCAG 1.4.11
floor; 6.4180:1 on the `.dark` card, where `--ring` is `oklch(0.65 0.15 160)`),
at the real `max-w-md` panel width.

**Where every ratio and hex in this section comes from.** Each was produced by
**importing `frontend/src/lib/contrast.ts`** (`parseOklch`, `contrastRatio`,
`oklchToHex`) and feeding it the literal `oklch()` strings in `src/index.css` —
not computed by hand, and not by a second conversion written for this spec.
That provenance is load-bearing rather than pedantic: both `--ring` values are
**out of gamut** (`isInGamut` returns `false` for `oklch(0.62 0.15 160)` and
for `oklch(0.65 0.15 160)`), so the naive per-channel clip that `contrast.ts`
rule 2 exists to forbid produces a *different colour*, and therefore different
digits — which is exactly what an earlier draft of this spec carried. The
figures here agree with the repository's own published position:
`docs/tasks/APRAS-87-spec.md:142` publishes `3.4054` for `--ring` on `--card`,
its line 23 publishes `#009f68` for the identical `oklch(0.62 0.15 160)`,
`backend/tests/test_branding.py:370` uses `#009f68`, and six sibling mocks
under `docs/tasks/` use it too. Anyone re-checking these numbers must import
that module as well; re-deriving them by any other method is how they were
wrong before.

The one genuine open question is in the mock's section 2, and **both of its
options are compliant**: `ring-2` flush against the button (option A, what
`alert-modal.tsx`'s hand-rolled footer buttons use) versus `ring-2
ring-offset-2 ring-offset-card` (option B, the form `src/components/ui/button.tsx:7`
— the house `Button` — uses). **This spec picks B as its default**, for three
reasons:

- The destructive button is the weak point of A: the green ring against the red
  fill measures **1.4117:1** on light (`--destructive: oklch(0.58 0.24 27)`
  ≈ `#e60018`) and **1.8021:1** on dark, so that edge of
  the ring all but vanishes on the one control in this dialog whose action is
  irreversible. A card-coloured 2px gap gives the ring a 3.4054:1 (light) /
  6.4180:1 (dark) boundary on both sides instead.
- That margin is machine-checked **nowhere**: `ring` is deliberately excluded
  from the branding contrast guard (`src/lib/contrast.ts:59` — the 3:1 non-text
  minimum is out of scope there) and `--ring` is tenant-derivable, so nothing
  will catch it regressing. A default that does not depend on the weak edge is
  the safer one to ship unattended.
- For a `<button>`, `button.tsx` is the stronger precedent: it is the house
  component every other button in the app routes through, whereas
  `alert-modal.tsx`'s footer buttons are hand-rolled `<button>` elements that
  simply never adopted the house form.

Option B **as specified here is better than `button.tsx`'s own form**, not equal
to it. `button.tsx:7` and `GeneralDashboardPage.tsx:162` both use a bare
`ring-offset-2` with no offset colour, which in Tailwind v4 resolves to the
hard-coded `--tw-ring-offset-color: #fff` (literally present in the installed
`tailwindcss@4.2.4`) and therefore paints a **white** gap — correct on the light
card by accident, and a bright white seam around the button on the `.dark` card.
Naming `focus-visible:ring-offset-card` is the improvement: the gap follows
`--color-card` (`src/index.css:8`, inside `@theme`) in both themes. It is a
semantic theme token, so APRAS-85's migration guard is still satisfied.

If the operator answers **A**, the implementer drops
`focus-visible:ring-offset-2 focus-visible:ring-offset-card` from both buttons
and nothing else in this spec changes.

## Approach

### Behaviour

- Opening the slug confirmation (clicking Save with a changed, well-formed
  slug) moves focus to the first focusable control inside the panel.
- Escape closes the dialog — identical to clicking Cancel: `confirming` goes
  false, no mutation is sent.
- Tab from the last control inside the panel goes to the first; Shift+Tab from
  the first goes to the last; focus that is outside the panel is pulled back in
  on the next Tab. The page behind the dialog is unreachable by keyboard.
- Whichever control holds focus shows a visible ring (Decision 4).
- Closing restores focus deterministically, and the outcome differs by exit
  path. Each is named by identity, because "focus is outside the panel" is true
  of every possible location once the panel is unmounted and therefore
  constrains nothing:
  - **Escape** → `document.activeElement` is the page's Save button
    (`tenantProfile.save`), the control that opened the dialog.
  - **Cancel** → the same Save button.
  - **Confirm** → `document.body`. Note which of the three paths actually
    *prove* restoration: **Escape and Cancel do; Confirm does not.** The
    `document.body` assertion is determinate, but it has no discriminating
    power — a hook that never restored focus at all would also leave
    `document.activeElement` on `<body>` here. QA must not credit the Confirm
    case with proving restoration; it is there to pin a known outcome so an
    implementer does not "fix" it. This is not a loophole, it is the mechanics:
    `submit` (line 157) calls `setConfirming(false)` and then `update.mutate` in
    one handler, so by the time the effect cleanup runs, the Save button is
    `disabled` (`update.isPending`, line 394-396) and `.focus()` on a disabled
    button is a no-op; the panel's own focused button is already removed, so the
    document falls back to `<body>`. The test asserts that exact node. If an
    implementer finds focus somewhere else on this path, that is a real finding
    to report — not a reason to weaken the assertion.
  - Restoring focus to the Save button *after* the mutation settles is out of
    scope: it needs state the dialog no longer owns, and it is a change to
    `TenantProfilePage`'s save flow rather than to its modal keyboard
    behaviour.
- Nothing else about the dialog changes: same two buttons, same translation
  keys, same `submit` with the same slug.

### Files touched

- `frontend/src/lib/focusTrap.ts` — moved from
  `features/project-management/lib/`, contents (including the `skipcq`)
  unchanged.
- `frontend/src/lib/__tests__/focusTrap.test.ts` — moved alongside it; only its
  import path changes.
- `frontend/src/hooks/useDialogFocus.ts` — new. The modal keyboard/focus effect
  extracted verbatim in behaviour from `ObraPrintDialog`, with the ref-based
  `onClose` contract of Decision 3b, importing `focusableWithin` and
  `cycleTabWithin` from `../lib/focusTrap`.
- `frontend/src/features/project-management/components/ObraPrintDialog.tsx` —
  its `React.useEffect` block replaced by a call to `useDialogFocus`; imports
  updated; no observable change. Its component docstring currently describes the
  focus/Escape/restore behaviour as something this component does (lines 19-25);
  reword those sentences to say the component delegates that behaviour to
  `useDialogFocus` and point the reader there. The inline comment at line 56
  pointing to `../lib/focusTrap` leaves with the effect; nothing to do for it.
- `frontend/src/features/user-administration/pages/TenantProfilePage.tsx` —
  `panelRef` goes on the **panel** div at line 425 (`className="w-full max-w-md
  rounded-xl bg-card p-6 shadow-xl"`), not on the `fixed inset-0` scrim wrapper
  at line 419: the trap must read the panel only. Give that div
  `data-testid="tenant-slug-confirm-panel"` so a test can assert containment by
  identity. Plus the `useDialogFocus(confirming, () => setConfirming(false),
  panelRef)` call — unconditional, above the existing `if (isPending || !data)
  return <Spinner />` early return (line 107), so hook order is stable — and the
  focus ring of Decision 4 on the two buttons opening at lines 447 and 454
  (their `className` lines are 450 and 457).
- `frontend/src/hooks/__tests__/useDialogFocus.test.tsx` — new unit tests for
  the hook.
- `frontend/src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
  — new cases for the dialog's keyboard behaviour. This file is also being
  edited by other work in this tree; append cases, do not reformat it.
- `frontend/src/__tests__/focusTrapSingleImplementation.test.ts` — new guard
  test (below).
- `frontend/src/__tests__/focusTrapSingleImplementation.exceptions.json` — new,
  `[]` at this commit; the guard's documented exception route (below).

No class other than the three `focus-visible:` tokens of Decision 4 is added or
changed in either touched component, and no raw palette class is added
anywhere.

### The guard test

Following the house pattern of `src/__tests__/brandTextOpacity.test.ts` — a
tree walk plus a positive control over the real tree proving the walk can fail —
assert that the Tab-cycling algorithm has exactly one *copy*. Note the word:
this guard detects duplication of **this** implementation, and § "What the guard
does not detect" below says so to the implementer's face, because result 6 must
not be read as "no second focus trap can ever exist".

**The sweep.** `.ts`/`.tsx` files under `frontend/src`, skipping `__tests__/`
directories (the precedent's own boundary,
`brandTextOpacity.test.ts:96-111`). Skipping `__tests__/` is what keeps the
moved `focusTrap.test.ts` — which legitimately names `FOCUSABLE_SELECTOR` at
its lines 17 and 76 — and this guard file itself out of both counts.

**Two matchers, both concrete:**

- `M1` — the identifier `FOCUSABLE_SELECTOR` appears as a whole word.
- `M2` — a `querySelectorAll` call whose argument text mentions `tabindex`.
  "Within the same call's parentheses" is not expressible as a regex, and the
  call may carry a TypeScript generic parameter between the name and the paren
  (`focusTrap.ts:39` is `querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)`).
  Use exactly this pattern, case-insensitive, so two implementers write the
  same test:

  ```
  /querySelectorAll\s*(<[^>]*>)?\s*\([^)]*tabindex/i
  ```

  That is the shape a hand-rolled copy of this selector list takes.

  **`M2` deliberately does not match `focusTrap.ts:39` itself**, and must not be
  "repaired" until it does. That line is
  `querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)` — the argument is an
  *identifier*, so the argument text contains no `tabindex` and `M2` is silent
  there. That is correct: the canonical module is found by `M1`, and `M2` exists
  only to catch a copy that **inlines** the selector string. A future reader who
  makes `M2` match the canonical module will break assertion 1, which excludes
  `src/lib/focusTrap.ts` from the sweep for `M1`'s sake, not `M2`'s.

  The consequence to state plainly: **`M2` is unproven over the real tree.** The
  positive control (assertion 4) exercises `M1` only, because there is no file in
  the tree with an inlined `tabindex` selector to match. `M2` is a forbid-only
  matcher whose regex has never fired against a real file, so a typo in it would
  be invisible. It is kept because a false negative there costs nothing that
  `M1` does not already cover; it is not evidence of anything on its own.

**The assertions, with their exclusion sets stated separately — they differ:**

1. *No second copy.* Sweep excluding `src/lib/focusTrap.ts` **and**
   `__tests__/`: no file matches `M1` or `M2`, minus any entry listed in
   `focusTrapSingleImplementation.exceptions.json`.
2. *One suppression.* Sweep **including** `src/lib/focusTrap.ts`, excluding
   `__tests__/`: the literal `skipcq: JS-R1005` occurs exactly once in total,
   and the file it occurs in is `src/lib/focusTrap.ts`.
3. *The consumers really use it* (a forbid-only guard passes trivially if both
   dialogs lose the trap entirely): `src/hooks/useDialogFocus.ts` imports from
   `../lib/focusTrap`, and `ObraPrintDialog.tsx` and `TenantProfilePage.tsx`
   each reference `useDialogFocus`.
4. *Positive control, over the real tree, not over a synthetic string.* A
   matcher proven against an in-memory string says nothing about whether the
   walk opened a file, and a zero-file walk passes 1 and 2 for the wrong
   reason. So, following the precedent's
   `expect(files.length).toBeGreaterThan(20)`: the sweep's file list has more
   than 20 entries, and — the known single site — running matcher `M1` over the
   sweep **with** `src/lib/focusTrap.ts` included yields exactly one file,
   `src/lib/focusTrap.ts`. Those two halves are the load-bearing ones: the
   `>20` count proves the walk opened real files, and the exactly-one result
   proves `M1` can match. The filename-filter and no-`__tests__` checks may be
   kept for shape but are self-referential — they assert the walk against its
   own filter and can only fail on a walk bug, so neither is evidence that `M1`
   or `M2` works.

**What the guard does not detect**, stated in the test file as a comment so no
reader over-trusts it: a trap written as `if (event.key === "Tab")` with manual
`.focus()` calls and no `tabindex` selector; any third-party trap (Radix,
headlessui, `focus-trap`, a native `<dialog>`); a focusable-element selector
that enumerates tags without the word `tabindex`; a selector assembled from
fragments at runtime. **And anything under `__tests__/`** — the sweep's own
exclusion (which is what keeps the moved `focusTrap.test.ts` and this guard file
out of the counts) means a second trap, or a second `skipcq: JS-R1005`, placed
in a test helper there is invisible to assertions 1 and 2. It is a copy detector
for the specific module in non-test code, and that is all it claims.

**The exception route.** If a future task deliberately adopts a dialog library
or a second trap, it adds a row to
`frontend/src/__tests__/focusTrapSingleImplementation.exceptions.json` — the
sibling pattern of `themeTokenMigration.exceptions.json` — shaped
`{ "file", "matcher", "reason", "task" }`. The guard subtracts listed files from
assertion 1 and asserts every entry carries a non-empty `reason` and `task`, so
an exemption is a reviewable act with a paper trail rather than a deleted test.
The file ships as `[]`.

### Test criteria

- Hook unit tests: Escape invokes `onClose`; a non-Escape, non-Tab key does
  not; Tab at the last control moves focus to the first and Shift+Tab at the
  first moves to the last; mounting with `open` focuses the first control;
  unmounting (and flipping `open` to false) restores focus to the previously
  active element and removes the listener.
- Hook unit test for Decision 3b. **The test must be able to fail against the
  rejected `[open, onClose]` alternative**, and the obvious phrasings cannot:
  - "a later Escape invokes the new callback" passes against the alternative,
    because the teardown/setup pair installs a fresh handler closing over the
    fresh `onClose`. That assertion discriminates a hook that *ignores* later
    `onClose` values — a different bug — not the deps contract. It may be kept
    as a separate case for that different bug, but it does not test 3b.
  - "`document.activeElement` did not move" passes **vacuously** if focus
    happens to be on the panel's first control: the alternative's teardown runs
    `opener?.focus()` and its setup runs `focusableWithin(panel)[0]?.focus()`,
    so focus leaves and returns to the same node.

  Both 3b cases need a small test component rather than a bare `renderHook`:
  RTL's `renderHook` harness renders `null`, so there is no panel for
  `panelRef` to point at and nothing focusable to assert about. Render a tiny
  component that holds the `panelRef` div with at least two focusable controls
  inside it and calls the hook, and re-render *that*.

  So the premise has to be asserted first, and the test runs in this order:
  mount open with at least two focusable controls in the panel; move focus to a
  control that is **not** `focusableWithin(panel)[0]` and assert
  `document.activeElement` is that control by identity; re-render with a new
  `onClose` identity; assert `document.activeElement` is **still that same
  control** by identity. Under the rejected alternative the teardown/setup pair
  drags focus to the first control and this fails.
- Second observable for Decision 3b: **listener add/remove counts across the
  re-render.** Spy on `document.addEventListener` and
  `document.removeEventListener` *after* mounting open, counting only calls whose
  event name is `"keydown"`; re-render with a new `onClose` identity and no user
  interaction in between; assert **both deltas are 0**. This is the one
  observable that cannot pass both ways: under `[open]` the keydown effect's deps
  did not change, so nothing is torn down or re-installed; under `[open,
  onClose]` the deps did change, so React runs exactly one
  `removeEventListener("keydown", …)` and one `addEventListener("keydown", …)`
  and the deltas are 1 and 1. Note, rather than arrange, that the test does not
  run under `<StrictMode>`: `src/test/setup.ts` and `vitest.config.ts` set no
  `reactStrictMode` and register no document-level listeners, so a plain render
  is already outside it — there is nothing to switch off, only a wrapper not to
  add (its intentional double-invocation would contribute calls belonging to
  neither implementation). The test must restore the spies afterwards.

  Replacing the earlier "the re-render does not re-capture the opener"
  assertion, which was **not** discriminating and has been removed: under the
  rejected `[open, onClose]` alternative, the cleanup runs `opener?.focus()`
  *before* the fresh setup reads `document.activeElement`
  (`ObraPrintDialog.tsx:51-54` captures, `:68` restores), so the re-captured
  opener is the *same original opener* and a later Escape restores the correct
  node under both implementations.
- `TenantProfilePage` integration tests, driving the real page: open the dialog
  and assert `document.activeElement` is the panel's first control by identity
  (not merely "the dialog is in the DOM"); Escape closes it and no PATCH is
  issued; tabbing past the last control leaves `document.activeElement` inside
  `[data-testid="tenant-slug-confirm-panel"]`; the three exit paths each assert
  the node named in § Behaviour — Escape → the Save button, Cancel → the Save
  button, Confirm → `document.body`; Confirm still submits the changed slug
  exactly as today. The assertion form `expect(panel).not.toContainElement(...)`
  or any "focus is not inside the panel" phrasing is **forbidden** in these
  cases: the panel is unmounted, so it is vacuously true.
- The existing `ObraPrintDialog` and `focusTrap` test files pass unmodified in
  substance (only the import path changes), proving the extraction was
  behaviour-preserving.
- Assertions mutate what they claim to observe: a focus test asserts the
  *identity* of `document.activeElement` against the expected element.

## Expected Results

- [ ] The `confirming` dialog in `TenantProfilePage.tsx` closes on Escape via
      `useDialogFocus`, a new hook **modelled on** `alert-modal.tsx`'s document
      keydown effect and extracted from `ObraPrintDialog`'s; `alert-modal.tsx`
      is not modified and keeps its own effect, and no second Escape handler is
      added to `TenantProfilePage`.
- [ ] While the dialog is open, Tab and Shift+Tab cycle only among the panel's
      focusable elements, and a test asserts `document.activeElement` is still
      inside `[data-testid="tenant-slug-confirm-panel"]` after tabbing past the
      last control.
- [ ] Opening the dialog focuses the first control inside it, asserted by
      element identity. Closing restores focus to a node named per path, each
      asserted as `document.activeElement === <that node>`: Escape → the Save
      button, Cancel → the Save button, Confirm → `document.body` (the Save
      button is `disabled` while the mutation is pending, so `.focus()` on it is
      a no-op). No test asserts merely that focus is outside the panel. Escape
      and Cancel are the two cases that prove restoration; the Confirm case pins
      a known outcome and does not.
- [ ] `useDialogFocus` keeps `onClose` in a ref and its keydown effect depends
      on `[open]` alone, so a call site passing an inline arrow does not tear the
      effect down. Two hook tests prove it, **both of which fail against a
      `[open, onClose]` implementation**: (a) with focus moved to a panel control
      that is *not* the panel's first focusable element (asserted by identity
      first), a re-render with a new `onClose` identity leaves
      `document.activeElement` on that same control by identity; (b) with spies
      installed on `document.addEventListener` / `document.removeEventListener`
      after mount, counting only `"keydown"` calls, a re-render with a new
      `onClose` identity and no interaction in between adds **0** and removes
      **0** listeners (the rejected alternative removes 1 and adds 1). Both use
      a small test component holding the panel, not a bare `renderHook`, and
      neither runs under `<StrictMode>` (which the suite does not enable). Two
      phrasings may be asserted as extra cases but do **not** count towards this
      result, because they pass under `[open, onClose]` too: "a later Escape invokes the new callback", and "the
      re-render does not re-capture the opener" (the alternative's cleanup
      restores focus to the opener before its setup re-reads
      `document.activeElement`, so it re-captures the same node).
- [ ] The Tab trap is reused, not reimplemented: `focusTrap.ts` lives at
      `frontend/src/lib/focusTrap.ts` with its test at
      `frontend/src/lib/__tests__/focusTrap.test.ts`, its contents and its
      `// skipcq: JS-R1005` block byte-identical to the moved file, and
      `features/project-management/lib/focusTrap.ts` no longer exists.
- [ ] `ObraPrintDialog.tsx` holds no focus/keydown effect of its own — it calls
      `useDialogFocus`, and its docstring points at the hook for that behaviour
      — and its existing test file passes with no change in substance.
- [ ] `frontend/src/__tests__/focusTrapSingleImplementation.test.ts` passes and
      asserts all four: (1) no file under `frontend/src`, excluding
      `src/lib/focusTrap.ts` and all `__tests__/` directories, names
      `FOCUSABLE_SELECTOR` or matches
      `/querySelectorAll\s*(<[^>]*>)?\s*\([^)]*tabindex/i`, except files listed in
      `focusTrapSingleImplementation.exceptions.json` (which ships as `[]`);
      (2) `skipcq: JS-R1005` occurs exactly once in a sweep that **includes**
      `src/lib/focusTrap.ts` and excludes `__tests__/`, in that file; (3)
      `useDialogFocus.ts` imports `../lib/focusTrap` and both `ObraPrintDialog`
      and `TenantProfilePage` reference `useDialogFocus`; (4) a positive control
      over the real tree — more than 20 files swept, and `FOCUSABLE_SELECTOR`
      found in exactly one file when `src/lib/focusTrap.ts` is in the sweep. A
      comment in the file lists the shapes the walk cannot see (manual `Tab`
      handlers, third-party traps, tag-only selectors, and anything under
      `__tests__/`, which the sweep excludes).
- [ ] The dialog's Cancel and confirm buttons carry exactly
      `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring`
      — **option A, flush, which the operator chose** (answer `A` on questions
      entry `q-recovered-apras-98-1`, `answered_at` 2026-10-02T12:48:39.773Z,
      given with the 1.41:1 measurement stated in the question) — and carry
      **neither** `focus-visible:ring-offset-2` nor `focus-visible:ring-offset-card`,
      so a keyboard user sees where focus is in the form `alert-modal.tsx:115`
      already uses; no other class on either button changes, no raw palette class
      is introduced, and the theme-token migration guard still passes. The
      disjunction this result used to carry is resolved: there is one list and no
      alternative.
- [ ] The dialog is otherwise unchanged: same confirm and cancel actions, same
      translation keys (`tenantProfile.slugConfirm*`), same slug submitted.
- [ ] `npx tsc -b` exits 0, `npx vitest run --coverage` passes with coverage at
      or above 80 lines / 78 functions / 76 branches / 80 statements, and
      `npx eslint .` reports no more findings than the baseline the implementer
      measures on this branch before starting (roughly 375 errors across 64
      files — the recorded figure is approximate and the measured one governs).

## Out of Scope

- `AlertModal`'s own missing focus trap and its duplicate Escape effect.
- Generalising the moved module's docstring prose (Decision 1) **and rewording
  the now partly-stale `skipcq` comment prose** (Decision 2) — one later
  cosmetic edit covering both, so this rename stays byte-identical.
- Removing the `skipcq: JS-R1005` suppression itself (Decision 2).
- Restoring focus to the Save button after the save mutation settles
  (§ Behaviour, Confirm path).
