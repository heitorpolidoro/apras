# APRAS-97 — QA verification

**Task**: Give the language buttons a state a screen reader can hear
**Verified at**: worktree `/Users/heitor/workspace/apras/.claude/worktrees/agent-a11c4915531a368ce`,
branch `worktree-agent-a11c4915531a368ce`, HEAD `2cb0d48`, two staged files, no unstaged diff.

VERDICT: APPROVED

## Scope of the staged change

```
83	0	frontend/src/features/user-administration/__tests__/Navbar.test.tsx
24	14	frontend/src/features/user-administration/components/Navbar.tsx
```

The `Navbar.tsx` hunk is a single hunk at `@@ -126,20 +126,30 @@`, entirely inside the
`LANGUAGES.map` callback. The test file hunk is a pure addition (0 deletions).

## Expected Results Checked

- [x] **R1 — both language buttons carry a literal `type="button"`; hamburger not under test.**
  Verified by reading the staged `Navbar.tsx`. The `LANGUAGES.map` callback now returns a
  `<button>` with `type="button"` on its own line (file line 139). `grep -n 'type="button"'`
  returns exactly two hits: line 74 (the mobile hamburger, whose `<button` opens at line 73 —
  pre-existing, untouched by the diff) and line 139 (the language button). Because the attribute
  sits on the single element the `map` callback returns, both PT and EN carry it.

- [x] **R2 — `aria-pressed` driven by the *same single* evaluation as the colour pair.**
  Read the code. The callback body is now a block that begins:

  ```tsx
  const isActive = currentLang.startsWith(lang.code);
  return (
    <button
      key={lang.code}
      type="button"
      aria-pressed={isActive}
      ...
      className={cn(
        "px-2.5 py-1 text-xs font-semibold transition-all",
        isActive
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:text-foreground",
      )}
  ```

  `currentLang.startsWith(lang.code)` appears exactly once in the file (confirmed by reading the
  whole component); both `aria-pressed` and the ternary read the same `isActive` binding. This is a
  single evaluation, not two independent `startsWith` calls that happen to agree.
  `aria-pressed={isActive}` is a boolean, which React serialises to the string `"true"`/`"false"` —
  observed in the mutation runs below, where jsdom reported `aria-pressed="false"` / `"true"`.

- [x] **R3 — banner-scoped test asserts `type="button"` on PT and EN.**
  `it("gives both language buttons an explicit type of button")` uses `renderBanner(...)`, whose
  helper returns `within(screen.getByRole("banner"))`, and asserts
  `toHaveAttribute("type", "button")` on `getByRole("button", { name: "PT" })` and on `"EN"`.
  Both buttons, banner-scoped.

- [x] **R4 — both `aria-pressed` values asserted in the default `pt` fixture and swapped under
  `stubI18n({ language: "pt", resolvedLanguage: "en" })`; a hard-coded attribute fails.**
  Verified by mutation, not by a green suite. With the attribute hard-coded:

  ```tsx
  aria-pressed={true}
  ```

  `npx vitest run src/features/user-administration/__tests__/Navbar.test.tsx` →
  `Tests  3 failed | 31 passed (34)`, the three failures being:

  ```
  × announces PT pressed and EN not pressed with the default fixture
  × swaps the pressed state when resolvedLanguage is en
  × announces PT pressed for the regional tag pt-BR
  ```

  Nothing in the `aria-pressed` set survived the hard-code — i.e. no case asserts only the active
  button or only one of the pair. The default-fixture case dies on `en` expecting `"false"`; the
  `resolvedLanguage: "en"` case dies on `pt` expecting `"false"`.

- [x] **R5 — a case named for the regional tag fails when the attribute is derived from `===`.**
  Mutated `aria-pressed={isActive}` → `aria-pressed={currentLang === lang.code}` (leaving the colour
  ternary on `isActive`). Result: `Tests  1 failed | 33 passed (34)`, and the single failure is

  ```
  × announces PT pressed for the regional tag pt-BR
  ```

  with the assertion message

  ```
  expect(element).toHaveAttribute("aria-pressed", "true")
  - Expected   aria-pressed="true"
  + Received   aria-pressed="false"
  ❯ src/features/user-administration/__tests__/Navbar.test.tsx:906
      906|       expect(pt).toHaveAttribute("aria-pressed", "true");
  ```

  The failing case is the one whose own name claims that behaviour — not a neighbour — and it fails
  on the `aria-pressed` assertion, not incidentally on something else. The case uses
  `stubI18n({ language: "pt", resolvedLanguage: "pt-BR" })` and asserts PT `"true"` / EN `"false"`.

- [x] **R6 — the two channels cannot disagree undetected.**
  Decoupled the class choice from the active flag while leaving the attribute correct: changed the
  `className` ternary condition to `!isActive`, keeping `aria-pressed={isActive}`. Result:
  `Tests  6 failed | 28 passed (34)`. The three new cases all failed, and the failing frames are
  the *colour* assertions, not the attribute ones:

  ```
  ❯ Navbar.test.tsx:869   (expect(classTokens(pt)).toContain("bg-primary"))
  ❯ Navbar.test.tsx:888   (expect(classTokens(en)).toContain("bg-primary"))
  ❯ Navbar.test.tsx:909   (expect(classTokens(pt)).toContain("bg-primary"))
  ```

  All three line numbers are inside the added block (which starts at line 831). So each new case
  asserts the `aria-pressed` pair *and* `bg-primary` / `text-primary-foreground` /
  `text-muted-foreground` on the same two elements, and a divergence between the channels is caught.
  (The three APRAS-91 colour cases at lines 782/799/811 failed too, as expected from an inverted
  colour ternary.)

- [x] **R7 — the four APRAS-91 cases are byte-identical.**
  `git diff --cached --numstat` reports `83 0` for the test file: zero deleted lines, so no existing
  case body can appear in a deletion hunk. Confirmed independently: the only `^-` line in
  `git diff --cached` for that file is the `--- a/...` header. The four named cases are present at
  lines 774, 789, 806 and 819 and all pass in the post-restore run.

- [x] **R8 — only the two intended files change, and only the language-button element in `Navbar.tsx`.**
  `git diff --cached --name-only` returns exactly:

  ```
  frontend/src/features/user-administration/__tests__/Navbar.test.tsx
  frontend/src/features/user-administration/components/Navbar.tsx
  ```

  Nothing else is staged, and `git diff` (unstaged) is empty. The `Navbar.tsx` diff is one hunk at
  `@@ -126,20 +126,30 @@`: the arrow-body `(lang) => (...)` becomes a block with an explicit
  `return`, `type="button"` and `aria-pressed={isActive}` are added, and `isActive` replaces the
  inline `startsWith` in the ternary. No other element, import, or line is touched.

- [x] **R9 — typecheck, coverage thresholds, lint baseline.** All run by me from the worktree's
  `frontend/`:

  - `npx tsc -b` → `TypeScript: No errors found`, exit `0`.
  - `npx vitest run --coverage` → exit `0`, `Test Files 188 passed (188)`, `Tests 2507 passed (2507)`.
    Coverage summary, against the required floors:

    | Metric | Observed | Floor | Result |
    |---|---|---|---|
    | Lines | 92.24% (6634/7192) | 80 | pass |
    | Functions | 87.84% (2335/2658) | 78 | pass |
    | Branches | 85.21% (3989/4681) | 76 | pass |
    | Statements | 91.51% (6949/7593) | 80 | pass |

    `Navbar.tsx` itself: 100% statements, 92.1% branches, 100% functions, 100% lines.
    No `ERROR: Coverage ... threshold` line in the output.
  - `npx eslint <the two files>` → `26 errors, 0 warnings in 1 files`, all
    `@typescript-eslint/no-explicit-any`, all in `Navbar.test.tsx`; `Navbar.tsx` reports 0. That is
    exactly the stated baseline. No new `any`: the count of `as any` / `: any` / `<any` in the test
    file is 26 both at `HEAD` and in the worktree, and the only added line containing the token
    `any` is prose inside a comment ("...satisfies any single-button assertion").

## Worktree left as found

Every mutation was taken on a scratchpad copy (`qa97/Navbar.pristine`, sha1 `405c85d6…`) and restored
with `cp` + `cmp` before the next one. Final state, checked after the last restore:

- `cmp` clean against both pristine copies (`BOTH_RESTORED_OK`).
- `git status --porcelain`: the same two `M ` (staged) entries, nothing else.
- `git diff --stat` (unstaged): empty.
- `git rev-parse --short HEAD`: `2cb0d48`. Nothing committed, nothing staged or unstaged by me.
- Post-restore confirmation run: `Test Files 1 passed (1)`, `Tests 34 passed (34)`.

## Blocking Findings

None.

## Suggestions

None.

VERDICT: APPROVED
