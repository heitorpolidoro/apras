# APRAS-98 — QA verification

**Task**: Give the slug-change dialog Escape and a focus trap
**Commit under test**: `2124432`, directly on top of `e1d19f2` (current `master`)
**Worktree**: `/Users/heitor/workspace/apras/.claude/worktrees/agent-a0968c01940cb4819`
**Branch**: `worktree-agent-a0968c01940cb4819`
**Date**: 2026-10-05

VERDICT: APPROVED

Everything below was observed in this worktree. The commit touches 9 paths,
685 insertions / 41 deletions, with two renames (`-M`), confirmed by
`git show HEAD -M --summary`.

Worktree left exactly as found: `HEAD` still `2124432`,
`git status --porcelain --untracked-files=all` empty, nothing staged, every
decoy deleted and verified gone. `git stash` was never invoked.

---

## R1 — Escape via a new `useDialogFocus`, modelled on `alert-modal.tsx`, `alert-modal` untouched, no second handler

**PASS**

- `frontend/src/hooks/useDialogFocus.ts` is a new file (`A` in
  `git diff HEAD~1 HEAD --raw`, blob `dd2c42f`). Its keydown effect is a
  document-level `addEventListener("keydown", handler)` with
  `event.key === "Escape"` → `onCloseRef.current()`, structurally the same shape
  as `frontend/src/components/ui/alert-modal.tsx:57-64`
  (`document.addEventListener("keydown", handler)` /
  `return () => document.removeEventListener("keydown", handler)`).
- `alert-modal.tsx` is **not** in the commit:
  `git diff HEAD~1 HEAD --name-only -- frontend/src/components/ui/alert-modal.tsx`
  returns nothing, and the file still carries its own effect (lines 57-64,
  verified by grep).
- `TenantProfilePage.tsx` adds **no** keydown handler of its own: grep for
  `keydown|Escape|onKeyDown` in that file returns only the three lines of the
  APRAS-98 comment block (111, 113, 115) and no code. The only wiring is
  `useDialogFocus(confirming, () => setConfirming(false), panelRef);`, called
  unconditionally above the `if (isPending || !data) return <Spinner />;` early
  return.
- The `confirming` dialog closes on Escape — proved live by the page test
  *"closes on Escape, sends nothing, and returns focus to the Save button"*,
  which passes and which reddens when the hook's restore is removed (see R3).
- Extraction from `ObraPrintDialog` confirmed: the diff deletes the component's
  entire 30-line effect verbatim and the hook's effect body is that same code
  with `onClose()` replaced by `onCloseRef.current()`.

## R2 — Tab / Shift+Tab cycle only within the panel, with an in-panel `activeElement` assertion

**PASS**

Page tests, in `TenantProfilePage.test.tsx`:

- *"keeps Tab inside the panel when it walks past the last control"* — focuses
  the confirm button (the last control), `await user.tab()`, then asserts both
  `expect(panel).toContainElement(document.activeElement as HTMLElement)` —
  `panel` being `screen.findByTestId("tenant-slug-confirm-panel")` — and
  `expect(document.activeElement).toBe(cancelButton())`. That is precisely the
  assertion R2 requires, plus identity.
- *"cycles Shift+Tab from the first control to the last"* — mirror case, same
  containment assertion.

**Mutation proof.** Removing the `else if (event.key === "Tab") { cycleTabWithin(...) }`
branch from the hook reddened exactly:

```
× TenantProfilePage > keeps Tab inside the panel when it walks past the last control
× TenantProfilePage > cycles Shift+Tab from the first control to the last
× ObraPrintDialog   > traps Tab inside the dialog, wrapping both ways
```

(3 failed / 36 passed). Restored and verified with `cmp`.

## R3 — Open focuses the first control by identity; each close path's restore target named and asserted by identity

**PASS**

- Open: *"moves focus to the panel's first control when the dialog opens"* reads
  the expected node off the panel (`panel.querySelector("button")`), pins it to
  `cancelButton()`, then asserts `document.activeElement` is that node.
- Escape → Save button: `expect(document.activeElement).toBe(save)`.
- Cancel → Save button: `expect(document.activeElement).toBe(save)`.
- Confirm → `document.body`: `expect(document.activeElement).toBe(document.body)`,
  with the in-file comment stating it is *"Pinned, not credited"* and explaining
  the disabled-Save no-op.
- No "focus is outside the panel" phrasing exists: grep for
  `not.toContainElement`, `not.toBe(panel`, and `outside the panel` across both
  new test files returns nothing.

**Mutation proof.** Deleting `opener?.focus();` from the hook's cleanup reddened
exactly the two restoration cases and the hook's own restore case, and left the
Confirm case green:

```
× useDialogFocus      > restores focus to the opener and drops the listener when open goes false
× TenantProfilePage   > closes on Escape, sends nothing, and returns focus to the Save button
× TenantProfilePage   > returns focus to the Save button when Cancel closes the dialog
  (all three: expected <body>…</body> to be <button …>)
```

3 failed / 36 passed — the Confirm → `document.body` case stayed green, which is
exactly the documented behaviour: it pins a known outcome and does not prove the
restore. Restored and verified with `cmp`.

## R4 — `onClose` in a ref, keydown deps `[open]`, with two tests that fail against `[open, onClose]`

**PASS — this is the result the task exists for, and it holds.**

Implementation: `onCloseRef = React.useRef(onClose)`, synced in its own
`React.useEffect(..., [onClose])` (not a render-time assignment), and the keydown
effect closes with `}, [open]);` plus an
`// eslint-disable-next-line react-hooks/exhaustive-deps` carrying a written
justification.

**Mutation proof.** I changed `}, [open]);` to `}, [open, onClose]);` — leaving
the ref and its sync effect in place, so the mutation is the deps alone — and ran
`src/hooks/__tests__/useDialogFocus.test.tsx`:

```
 ❯ useDialogFocus.test.tsx (10 tests | 2 failed)
   × leaves focus on a non-first control across a re-render with a new onClose identity
     AssertionError: expected <button …> to be <button …> // Object.is equality
   × adds and removes no keydown listener across a re-render with a new onClose identity
     AssertionError: expected 1 to be +0 // Object.is equality
```

Both load-bearing cases fail, and **only** those two. Matching the requirement
literally:

- (a) *"leaves focus on a non-first control…"* asserts the premise first —
  `expect(focusableWithin(panel)[0]).not.toBe(middle)` and
  `expect(document.activeElement).toBe(middle)` — then re-renders with a new
  inline arrow and asserts `document.activeElement` is still `middle` by
  identity. Fails under `[open, onClose]`.
- (b) *"adds and removes no keydown listener…"* installs
  `vi.spyOn(document, "addEventListener"/"removeEventListener")` **after** mount,
  filters `mock.calls` to `type === "keydown"`, re-renders with a new arrow and
  no interaction, and asserts `0` removes and `0` adds. The mutated
  implementation produced `1`, matching the predicted "removes 1 and adds 1".

Both use the `Harness` component holding the real panel; grep confirms
`renderHook` appears only inside a comment explaining why it cannot be used.
Nothing in the file or in `src/test/` renders under `<StrictMode>` (grep clean).

**The excluded phrasings are not being credited.** Only one of the two is
present, as a third, separately-named case:
*"invokes the latest onClose on a later Escape (a different bug — not 3b)"* — and
it **passed** under the `[open, onClose]` mutation, confirming it does not
discriminate. The file's own docstring says so, and the case's name says so. The
second excluded phrasing ("the re-render does not re-capture the opener") does
not appear at all.

## R5 — the Tab trap moved, not reimplemented, byte-identical

**PASS**, by both required checks.

```
 rename frontend/src/{features/project-management => }/lib/focusTrap.ts (100%)
 rename frontend/src/{features/project-management => lib}/__tests__/focusTrap.test.ts (99%)
```

- `git diff --raw -M` line: `:100644 100644 11dca67 11dca67 R100` — the same
  blob id on both sides. `git rev-parse HEAD~1:.../project-management/lib/focusTrap.ts`
  and `HEAD:frontend/src/lib/focusTrap.ts` both return
  `11dca67dd81e43a992c390c1c54865d86b51df13`.
- Independent checksum: `git cat-file blob HEAD~1:<old path> | shasum -a 256`
  and `shasum -a 256 frontend/src/lib/focusTrap.ts` both give
  `81c8d6ba8bd5befd60354a238f2e3658b7a5d451626455eab510fe65220df82a`.
- `skipcq: JS-R1005` block present, `grep -c` → 1, and byte-identical by the
  above.
- `frontend/src/features/project-management/lib/` now contains only
  `obraPrintDocument.ts` — `focusTrap.ts` is gone.
- Test at `frontend/src/lib/__tests__/focusTrap.test.ts`; its single-line change
  (`R099`, 2 +-) is the import path, which R5 permits — the byte-identity claim
  is on `focusTrap.ts`.

## R6 — `ObraPrintDialog` holds no focus/keydown effect; docstring points at the hook; its test unchanged in substance

**PASS**

- The diff removes the whole `React.useEffect` (opener capture, first-focus,
  keydown handler, add/removeEventListener, restore) and replaces it with
  `useDialogFocus(open, onClose, panelRef);` — 13 insertions / 37 deletions.
  Nothing focus- or keydown-related remains; the component only supplies
  `panelRef`.
- Docstring now reads: *"None of that keyboard behaviour is implemented here.
  The component delegates all of it — Escape, the `Tab` trap and the focus
  restore — to `src/hooks/useDialogFocus.ts` (APRAS-98)…"*
- `ObraPrintDialog.test.tsx` is **not** in the commit's file list at all — no
  change at all, let alone in substance — and it passes: 10 tests green. It is
  also a live regression net for the delegation: it reddened under the Tab-trap
  mutation in R2.

## R7 — `focusTrapSingleImplementation.test.ts` passes and all four assertions hold, with the forbidding ones proved to redden

**PASS**

The file passes (5 tests) and implements all four:

1. Sweep of `.ts`/`.tsx` under `src/`, excluding `__tests__/` directories,
   filtering out `CANONICAL = "src/lib/focusTrap.ts"` and any file listed in
   `focusTrapSingleImplementation.exceptions.json`; matchers
   `M1 = /\bFOCUSABLE_SELECTOR\b/` and
   `M2 = /querySelectorAll\s*(<[^>]*>)?\s*\([^)]*tabindex/i` — the regex exactly
   as specified. The exceptions file ships as `[]` (verified: file content is
   `[]`).
2. `skipcq: JS-R1005` sweep that **includes** the canonical module and excludes
   `__tests__/`; asserts the hit list equals `[CANONICAL]` *and* that the
   occurrence count inside it is 1.
3. `useDialogFocus.ts` contains `"../lib/focusTrap"`; `ObraPrintDialog.tsx` and
   `TenantProfilePage.tsx` each contain `useDialogFocus`.
4. Positive control: `expect(files.length).toBeGreaterThan(20)` and, with the
   canonical module in the sweep, `M1` hits exactly `[CANONICAL]`.

A comment block at the top of the file lists what the walk cannot see: a trap
with no `tabindex` selector, third-party traps, tag-enumerating selectors,
run-time-assembled selectors, and anything under `__tests__/`. It also notes
honestly that `M2` has never fired against a real file.

**Decoy proofs — every forbidding assertion was watched to fail.**

- Planted `frontend/src/lib/qaDecoyM1.ts` (`export const FOCUSABLE_SELECTOR = …`)
  and `frontend/src/lib/qaDecoyM2.ts` with an inlined
  `querySelectorAll<HTMLElement>(` followed by a **line break** and then
  `'button:not([tabindex="-1"]), [tabindex]:not([tabindex="-1"])'`:

  ```
  × has no second copy of the algorithm outside src/lib/focusTrap.ts
    expected [ 'src/lib/qaDecoyM1.ts (M1)', 'src/lib/qaDecoyM2.ts (M2)' ] to deeply equal []
  × proves the sweep and M1 work against the real tree
    + "src/lib/qaDecoyM1.ts"
  ```

  Assertion 1 reddens on both matchers, and `M2` does match across a line break
  (the `[^)]*` class is newline-permissive). Both decoys deleted; `ls | grep -i decoy`
  returns nothing and `git status --porcelain` is empty.
- Planted `frontend/src/lib/qaDecoySkipcq.ts` containing `// skipcq: JS-R1005`:

  ```
  × carries the JS-R1005 suppression exactly once, in the canonical module
    + "src/lib/qaDecoySkipcq.ts"
  ```

  Assertion 2 reddens. Decoy deleted and verified gone.
- Assertion 3: replacing `useDialogFocus` with `zzQaTrapGone` throughout
  `TenantProfilePage.tsx` reddened it
  (`expected 'import React, …' to contain 'useDialogFocus'`). Note my first
  attempt — renaming to `useDialogFocusRenamedByQA` — did **not** redden it,
  because the assertion is a substring `toContain`; that is a mild weakness of
  the assertion, recorded as a suggestion, not a blocker, since the requirement
  is only that both dialogs *reference* `useDialogFocus`. File restored and
  `cmp`-verified.

## R8 — exactly the three focus-ring classes, no `ring-offset`, nothing else changed, theme guard green

**PASS**

The diff's only class change on the two buttons appends
`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring` and
nothing else:

- Cancel: `rounded-md border border-input px-4 py-2 text-sm font-medium text-foreground` + the ring
- Confirm: `rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground` + the ring

Neither `focus-visible:ring-offset-2` nor `focus-visible:ring-offset-card`
appears. The page test *"gives both dialog controls the house focus ring, flush
with no offset"* asserts the **whole** `className` string for each button
(`toBe`, not `toContain`), which pins "no other class changes" from the other
side, and additionally asserts
`expect(control.className).not.toMatch(/focus-visible:ring-offset/)` for both.

No raw palette class is introduced: grepping the added lines for
`(bg|text|border|ring)-(red|blue|green|gray|slate|zinc|white|black|yellow|amber)…`
returns nothing; every class used is a theme token.

Theme-token migration guard: `themeTokenMigration.test.ts`,
`themeTokenCompile.test.ts` and `themeContrast.test.ts` run green — 3 files,
271 tests passed.

## R9 — the dialog is otherwise unchanged

**PASS**

The full diff of `TenantProfilePage.tsx` is: one import, one `panelRef`, one
comment block, one `useDialogFocus(...)` call, `ref`/`data-testid` on the panel
div, and the two class strings. Specifically unchanged:

- `onClick={() => setConfirming(false)}` on Cancel, `onClick={submit}` on
  Confirm — both untouched in the diff.
- Translation keys `tenantProfile.slugConfirmCancel`, `slugConfirmCta`,
  `slugConfirmTitle`/body (via `tenant-slug-confirm-title`) — all unchanged.
- Slug submitted: the Confirm test asserts
  `apiClient.patch` called with `{ name: PROFILE.name, slug: "solar-da-serra" }`,
  commented *"Unchanged from before this task: the same slug, in the same body."*
  The Escape and Cancel tests assert `apiClient.patch` was **not** called.

## R10 — typecheck, coverage, lint

**PASS** on all three clauses.

- `npx tsc -b` → `TypeScript: No errors found`, exit **0**.
- `npx vitest run --coverage` → exit **0**, **190 test files / 2529 tests
  passed**, 0 failed.

  | metric | measured | threshold |
  |---|---|---|
  | Lines | **92.24%** (6641/7199) | 80 |
  | Functions | **87.86%** (2338/2661) | 78 |
  | Branches | **85.21%** (3989/4681) | 76 |
  | Statements | **91.52%** (6957/7601) | 80 |

  The thresholds in `vitest.config.ts` are exactly the four R10 names
  (80/78/76/80), so exit 0 is itself the gate passing.

- Lint, measured both ways rather than inferred. Baseline: `git archive e1d19f2`
  extracted to a scratchpad directory, `node_modules` symlinked from the
  worktree, then the worktree's own `eslint` binary run over it.

  | tree | result |
  |---|---|
  | base `e1d19f2` | **372 problems (370 errors, 2 warnings)**, exit 1 |
  | HEAD `2124432` | **372 problems (370 errors, 2 warnings)**, exit 1 |

  Equal, so "no more findings than the baseline" holds. I also diffed the two
  reports with the differing root prefixes stripped: the only differences are
  whitespace column padding (the two trees have different longest path lengths).
  No finding in any new or changed file — grep for
  `useDialogFocus|focusTrap|TenantProfilePage` in the HEAD report returns
  nothing. The pre-existing 372 are inherited debt, unchanged by this task.

---

## Blocking Findings

None.

## Suggestions

1. **R7 assertion 3 is a substring check.** `expect(source).toContain("useDialogFocus")`
   survives a rename to any identifier that *contains* that substring — I
   observed it stay green against `useDialogFocusRenamedByQA`. Anchoring it to
   the import specifier (as assertion 3 already does for the hook, with
   `'"../lib/focusTrap"'`) would close that hole. Non-blocking: the requirement
   is only that the dialogs reference the hook, and the real failure mode
   (dropping the trap entirely) is caught.
2. **`M2` remains unexercised against the real tree**, as the file itself
   admits. My decoy run is the first evidence it fires at all, including across
   a line break. Worth noting that evidence somewhere durable — a committed
   negative-control fixture under `__tests__/` (excluded from the sweep) would
   turn "never fired" into a standing proof without weakening assertion 1.
3. **Inherited lint debt is large** (370 errors at the base). Nothing this task
   caused, and the relative gate is met exactly, but a 372-problem baseline makes
   "no new findings" hard to see at a glance in CI.

---

## Verification log (mutations, all restored)

| # | Mutation | Expected to redden | Observed |
|---|---|---|---|
| 1 | hook keydown deps `[open]` → `[open, onClose]` | R4 (a) and (b), and only those | both failed (`expected <button> to be <button>`; `expected 1 to be +0`); the "later Escape" case stayed green |
| 2 | delete `opener?.focus()` from cleanup | R3 Escape + Cancel, not Confirm | Escape, Cancel and the hook's own restore case failed; Confirm → `document.body` stayed green |
| 3 | delete the `Tab` branch from the handler | R2 cases | both page Tab cases + `ObraPrintDialog`'s trap case failed |
| 4 | decoy `src/lib/qaDecoyM1.ts` naming `FOCUSABLE_SELECTOR` | R7 assertion 1 (M1) + positive control | both failed, naming the decoy |
| 5 | decoy `src/lib/qaDecoyM2.ts`, inlined `querySelectorAll` + `[tabindex]` across a line break | R7 assertion 1 (M2) | failed, reported as `(M2)` |
| 6 | decoy `src/lib/qaDecoySkipcq.ts` with `skipcq: JS-R1005` | R7 assertion 2 | failed, naming the decoy |
| 7 | strip `useDialogFocus` from `TenantProfilePage.tsx` | R7 assertion 3 | failed |

Each mutated file was copied to the scratchpad first, restored afterwards, and
the restore verified with `cmp`; each decoy was deleted and its absence verified
by `ls` and `git status`. Final state: `HEAD` = `2124432`,
`git status --porcelain --untracked-files=all` empty.

VERDICT: APPROVED
