# APRAS-97 — Code Review

**Task**: Give the language buttons a state a screen reader can hear
**Subject**: `git -C /Users/heitor/workspace/apras/.claude/worktrees/agent-a11c4915531a368ce diff --cached`
**Base**: `2cb0d48` (branch `worktree-agent-a11c4915531a368ce`, identical to local `master`)
**Diff size**: 2 files, +107 / −14 (`Navbar.tsx` +24/−14 in a single hunk; `Navbar.test.tsx` +83/−0)
**Reviewer scope**: static analysis, architecture, KISS/YAGNI/DRY, security, unit-test quality. No E2E, no QA verification against expected results.

**VERDICT: APPROVED**

---

## 1. Staged surface

```
M  frontend/src/features/user-administration/__tests__/Navbar.test.tsx
M  frontend/src/features/user-administration/components/Navbar.tsx
```

Exactly the two files named in the spec's *Files touched*, nothing else, and no
unstaged residue (`git diff --stat` empty before and after my work). The test
file is `+83 / −0` — **zero deletions**, which mechanically proves every
pre-existing case, including the six the spec requires to stay byte-identical,
is untouched. No need to take that on trust.

`Navbar.tsx` is a **single hunk** at `@@ -126,20 +126,30 @@`, entirely inside the
`LANGUAGES.map` callback. The hamburger (line 73) and the logout button
(164–169) are not in the diff, so result 4 and the Out-of-Scope clause hold.

## 2. Implementation

```tsx
{LANGUAGES.map((lang) => {
  const isActive = currentLang.startsWith(lang.code);
  return (
    <button
      key={lang.code}
      type="button"
      aria-pressed={isActive}
      onClick={() => i18n.changeLanguage(lang.code)}
      className={cn(
        "px-2.5 py-1 text-xs font-semibold transition-all",
        isActive
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
```

- **R3, one evaluation feeding both channels — satisfied literally.** `isActive`
  is a single `const` computed once per iteration and consumed by both the
  `cn(...)` ternary and the attribute. The expression
  `currentLang.startsWith(lang.code)` appears exactly once in the file; there is
  no second copy that could drift. This is the structural property R6 exists to
  protect, and it is present by construction rather than by coincidence.
- **The arrow body change is the minimum needed.** Converting the concise body
  to a block with a `return` is the only way to introduce a local binding, and
  it is what inflates the hunk to 24/14 — all 14 "deletions" are the same JSX
  re-indented one level. No gratuitous refactor rode along.
- **`aria-pressed` renders as `"true"`/`"false"`, not dropped.** React
  special-cases `aria-*` and `data-*`: a boolean is stringified rather than
  omitted the way a non-ARIA DOM boolean prop would be. Confirmed empirically,
  not by appeal to the docs — `toHaveAttribute("aria-pressed", "false")` on the
  EN button passes, which it could not if the attribute were absent.
- **`type="button"` is a literal**, twice in the rendered output (once per
  `LANGUAGES` entry), on the correct element.
- **No visual change.** The class list and the `cn` call are byte-identical to
  before, modulo indentation. No new class, no focus-ring touch.
- **Security**: no attack surface. `lang.code` comes from a module-level literal
  `LANGUAGES` table, nothing is interpolated into markup, no HTML is injected,
  no secret, no network, no user-controlled string reaches an attribute.
- **KISS/YAGNI/DRY**: clean. No helper extracted for a two-line derivation, no
  memo, no new type, no abstraction for a two-element list. The in-code comment
  explains *why* the single binding matters rather than restating what the line
  does — appropriate, and it is the one comment added.

## 3. Unit test quality — the mutations, applied rather than read

This repository's recorded defect is tests that pass while the behaviour they
name is absent (`docs/audits/APRAS-111-test-suite-audit.md`, 19+ instances). I
did not accept the developer's report of its mutation testing. I copied the
pristine `Navbar.tsx` to the scratchpad, applied each mutation, ran the suite,
recorded which cases reddened, restored from the copy and verified the restore
with `cmp`.

Baseline: `npx vitest run src/features/user-administration/__tests__/Navbar.test.tsx`
→ **34 passed (34)**, 30 pre-existing + 4 new.

### Mutation 1 — `aria-pressed={currentLang === lang.code}`

Equality instead of the shared `startsWith`. Class channel left intact, so the
colours still mark PT active while both buttons announce `"false"` under
`pt-BR`.

Result: **1 failed | 33 passed**, and the single failure is

```
× own markup, scoped to the banner > announces PT pressed for the regional tag pt-BR
  (Navbar.test.tsx:906)
```

Exactly as claimed: one case, and it is the case whose **name** claims to check
the regional tag — not a neighbour. Note that the APRAS-91 case
`"treats the regional tag pt-BR as PT active"` stays green here, which is
correct: it only reads the colour channel, which this mutation does not move.
That is precisely the gap APRAS-97 closes, and the new case is the thing that
closes it.

### Mutation 2 — `aria-pressed={true}` hard-coded

Result: **3 failed | 31 passed**:

```
× announces PT pressed and EN not pressed with the default fixture
× swaps the pressed state when resolvedLanguage is en
× announces PT pressed for the regional tag pt-BR
```

Three, as claimed, and they are the three `aria-pressed` cases — every one of
them, because each asserts the `"false"` side on the inactive button in the same
case rather than only the `"true"` side on the active one. This is the exact
weakening the spec's *"An implementer who makes a required assertion pass by
weakening it"* paragraph warns about, and the cases are not weakened. The
`type="button"` case correctly stays green: it does not claim to check pressed
state.

### Mutation 3 (mine, not claimed) — drop `type="button"`

Result: **1 failed | 33 passed**:

```
× gives both language buttons an explicit type of button
```

One case, correctly named, and it reddens despite the mobile hamburger still
carrying `type="button"` — the `renderBanner` scoping genuinely isolates the
language buttons, so the assertion is not satisfiable by the wrong element. The
spec's warning about verifying result 1 against line 73 is answered.

### Mutation 4 (mine, not claimed) — decouple the two channels

I replaced the class ternary's `isActive` with an independent
`currentLang === lang.code`, leaving `aria-pressed={isActive}` alone. This is
the R6 scenario proper: colour says one thing, ARIA says another.

Result: **2 failed | 32 passed**:

```
× treats the regional tag pt-BR as PT active          (APRAS-91, colour channel)
× announces PT pressed for the regional tag pt-BR     (APRAS-97, both channels)
```

The new case reddens on its *colour* assertions while its `aria-pressed`
assertions still hold — which is exactly the "colour says EN, ARIA says PT"
report R6 was specified to produce. The co-located assertions are load-bearing,
not decorative.

**Restore verified.** After every mutation, `cmp` against the scratchpad copy
and against an independent earlier copy both returned clean, and
`git status --porcelain` / `git diff --stat` show the worktree exactly as I found
it: two staged files, no unstaged diff, nothing unstaged or committed.

### Test craftsmanship beyond the mutations

- All four cases live inside the existing `describe("own markup, scoped to the
  banner")` and use `renderBanner`, `stubI18n` and `classTokens`. No new mock,
  fixture or helper — DRY against the file's established vocabulary, as the spec
  required.
- Each case states its *scenario* in one place (the `stubI18n` call) and asserts
  both buttons. No case asserts a single button's single value.
- The comments say what mutation each case kills, which is the right thing for a
  comment to say in this repository.
- **No new `any`.** The sole occurrence of the token `any` in the 83 added lines
  is the English word in a prose comment ("satisfies any single-button
  assertion"). ESLint on the two files reports **26 errors, all
  `@typescript-eslint/no-explicit-any`, all in `Navbar.test.tsx`, 0 in
  `Navbar.tsx`** — identical to the baseline the spec records at `2cb0d48`. Zero
  new lint.

## 4. Gates re-run independently

| Gate | Result |
| --- | --- |
| `npx tsc -b` | exit 0, "No errors found" |
| `npx vitest run --coverage` (whole suite) | **188 files passed, 2507 tests passed** |
| Coverage vs. thresholds (lines 80 / functions 78 / branches 76 / statements 80) | lines 92.24, functions 87.84, branches 85.21, statements 91.51 — all above |
| ESLint, two touched files | 26 pre-existing `no-explicit-any`, 0 new |

## 5. The three escalated judgements

### (1) The fast-forward from `25e9dc6` to `2cb0d48`

**Right call, and the only correct one.** The spec is written "as of `2cb0d48`",
names line numbers from that tree, mandates `renderBanner` / `stubI18n` / the
banner-scoped describe block, and lists six APRAS-91 cases that must pass
unedited. At `25e9dc6` none of those exist, so implementing the spec there
would have meant either inventing parallel helpers (contradicting "No new mock,
fixture or helper is needed") or not implementing the spec. Escalating rather
than silently rebasing was also right — the worktree's base is not the
developer's to choose unilaterally.

Consequences, checked rather than assumed:

- It was a **true fast-forward**: `HEAD`, `worktree-agent-a11c4915531a368ce` and
  the main checkout's `master` are all exactly
  `2cb0d489360522f7c4f02267a23bd54e3bbf0b69`. No merge commit, no divergence, no
  foreign commit riding in. The eventual commit will be linear on `master`.
- `npm ci` was **contained**: `frontend/node_modules` in the worktree is a real
  directory, not a symlink into the main checkout, and
  `frontend/package.json` / `frontend/package-lock.json` are both clean in
  `git status`. Nothing leaked into the main checkout or other worktrees.
- The one residual risk is that `2cb0d48` is **local-only, not pushed**. Nothing
  in this change depends on it being pushed, but while it is unpushed it is
  rewritable, and a rewrite would orphan this work's base. See *Suggestions*.

### (2) Leaving `prettier --check` red on `Navbar.test.tsx`

**Right call.** I verified the "already failed at `2cb0d48`" claim against the
pristine `HEAD` blob rather than taking it:

```
git show HEAD:…/Navbar.test.tsx | npx prettier --stdin-filepath …
```

`HEAD` already disagrees at **six hunks, lines 174, 265, 329, 655, 721 and
811**. Running the same comparison against the staged file yields the
**identical six hunks at the identical line numbers** — the 83 added lines
introduce **zero** new prettier disagreements. `Navbar.tsx` passes
`prettier --check` cleanly.

The hunk at 811 sits inside `"treats the regional tag pt-BR as PT active"`,
one of the six cases the spec requires byte-identical, so `prettier --write`
would have broken a stated requirement in order to satisfy a check that is not a
gate: `frontend/package.json` has no `format` or `prettier` script, and
`grep -rn prettier .github/workflows/` returns nothing. Prettier is not wired
into CI at all here. Formatting pre-existing lines in an accessibility task
would also have buried a 24-line change under formatting noise. Leaving it is
correct on all three counts.

### (3) R6 in all three `aria-pressed` cases rather than "at least one"

**Acceptable, mildly generous, and I would not ask for it to be trimmed.**

The three colour blocks are not copies: each pins a different active language,
so each asserts a different token on a different element. The honest caveat is
that the APRAS-91 cases already cover the colour channel for these same three
fixtures, so as *colour coverage* the additions are redundant. What is not
redundant is the **co-location**: only by reading both channels off the same two
`getByRole` handles in one case can a failure report "colour says PT, ARIA says
EN" instead of two unrelated reds in two files' worth of output. Mutation 4
above demonstrates that pay-off concretely.

Of the three, the `resolvedLanguage: "en"` case is the most redundant and the
`pt-BR` case has the most teeth. The cost is roughly twelve assertion lines that
cannot go stale independently of the component. That is a good trade in a
repository whose recorded failure mode is under-assertion, and I would rather
review one case too many than one too few. One small asymmetry, non-blocking:
the default-fixture and swap cases add `not.toContain("bg-primary")` on the
inactive button while the `pt-BR` case does not.

## 6. Architecture and conventions

Nothing here crosses a module boundary: the change is confined to one component
in `features/user-administration` and its co-located test. It reuses the
project's `cn` helper and the existing `classTokens` test utility, follows the
file's `describe`/`it` naming style and its comment conventions, and adds no
dependency. The ARIA pattern decision (`aria-pressed` toggle buttons over
`role="radiogroup"`) was made in the spec and is implemented as specified,
including the deliberate absence of roving `tabindex` — correct, since the
component has no arrow-key handling and announcing a radiogroup role would
promise keyboard behaviour that does not exist.

## Suggestions

- `2cb0d48` is on local `master` but **not pushed**. Nothing in APRAS-97 depends
  on that, but while it is unpushed it is rewritable, and rewriting it would
  orphan this change's base. Push `master` before (or right after) landing
  APRAS-97, and in the meantime do not rebase or amend `2cb0d48`.
- `Navbar.test.tsx` has six pre-existing `prettier --check` disagreements and 26
  pre-existing `@typescript-eslint/no-explicit-any` errors, several of them
  avoidable now that `directorUser()` and `renderBanner` exist. Both are worth a
  dedicated cleanup task — and the formatting one is worth doing *before* any
  future task adds cases to this file, so the next author is not forced into the
  same choice between `--write` and a byte-identical-cases requirement. Neither
  belongs in APRAS-97.
- The `pt-BR` case could add `expect(classTokens(en)).not.toContain("bg-primary")`
  for symmetry with the other two cases. Cosmetic.
- The logout button (lines 164–169) still has no `type="button"`, correctly left
  alone by this spec. The sweep task the Out of Scope section anticipates is
  worth creating so it is not forgotten.

---

**VERDICT: APPROVED**

Blocking findings: **None.**
