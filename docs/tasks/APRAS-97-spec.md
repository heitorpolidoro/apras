# APRAS-97 — Give the language buttons a state a screen reader can hear

## Scope

The PT/EN language switcher in
`frontend/src/features/user-administration/components/Navbar.tsx` conveys which
language is active through colour alone (`bg-primary text-primary-foreground`
against `text-muted-foreground`). A screen reader announces both buttons
identically. This task adds a **second, programmatic channel** for that same
state and gives the two buttons an explicit `type="button"`.

Nothing about the buttons' appearance changes, and the existing colour channel
stays exactly as it is — this task adds to it, it does not replace it.

In scope: `Navbar.tsx` (the language-button element only) and
`frontend/src/features/user-administration/__tests__/Navbar.test.tsx`.
Nothing else under `frontend/src/` changes.

### Where the elements are (as of `2cb0d48`)

| Lines | Element | `type="button"` today |
| --- | --- | --- |
| 73–81 | Mobile hamburger toggle (`onClick={toggleMobile}`, `aria-label={t("nav.openMenu")}`) | **yes** — already present, and **not** the element this task touches |
| 128–143 | `LANGUAGES.map(...)` → the two language buttons (`onClick={() => i18n.changeLanguage(lang.code)}`) | **no** — this is the element to change |
| 164–169 | Logout button (`onClick={logout}`) | no — deliberately **left alone**, see Out of Scope |

An implementer verifying result 1 against line 73 would be verifying the wrong
button. The only `type="button"` this task adds is on the element inside the
`LANGUAGES.map` callback, and it must appear twice in the rendered output
(once per language).

## Approach

### Decision: `aria-pressed` on two independent toggle buttons

Result 2 allows "an equivalent the WAI-ARIA authoring practices endorse". The
choice is made here rather than deferred:

- **Chosen — `aria-pressed` toggle buttons.** WAI-ARIA APG's *Button*
  pattern, toggle-button variant. A screen reader announces the active one as
  roughly "PT, toggle button, pressed" and the other as "EN, toggle button,
  not pressed". It requires no keyboard behaviour beyond what a plain
  `<button>` already has: each button is individually tabbable and activates
  on Enter/Space. The component's existing markup already satisfies that, so
  the attribute is the entire change.
- **Declined — `role="radiogroup"` + `aria-checked`.** The APG *Radio Group*
  pattern obliges the author to implement roving `tabindex` (one tab stop for
  the whole group) and arrow-key navigation between options. This component
  implements neither, and adding them is a behaviour change well outside a
  task whose premise is that nothing visible or interactive changes. A
  radiogroup that does not answer arrow keys is worse for a screen-reader user
  than two honest toggle buttons, because the announced role promises keyboard
  behaviour that is not there.
- **Declined — `aria-current`.** `aria-current` marks the current item within
  a set of *navigational* items — the page you are on, the step you are at. A
  language switcher mutates application state rather than navigating, and
  `aria-current` has no "false" announcement that pairs with the `"true"` one
  the way `aria-pressed` does; the inactive button would simply carry nothing,
  which is the asymmetry this task exists to remove.

### Behaviour required

1. Each of the two language buttons carries a literal `type="button"`.
2. Each carries `aria-pressed`, resolving to `"true"` on the button whose
   language is active and `"false"` on the other. Exactly one is `"true"` for
   any value of the resolved language that matches one of the two codes.
3. **One expression drives both channels.** The active-language test is
   `currentLang.startsWith(lang.code)` over
   `currentLang = i18n.resolvedLanguage ?? i18n.language` (line 31), which is
   what makes `"pt-BR"` render PT as active. `aria-pressed` must be fed from
   that **same** evaluation — computed once inside the `map` callback and
   consumed by both the `cn(...)` ternary and the attribute — so the colour and
   the announcement cannot disagree. Two independently written copies of the
   expression are not acceptable even while they happen to agree: the point is
   that a future edit to the matching rule cannot change one channel without
   the other.
4. No other element, attribute, class or comment in `Navbar.tsx` changes.

### Test criteria

All new cases go in the existing
`describe("own markup, scoped to the banner")` block of `Navbar.test.tsx`,
using the `renderBanner` helper, the `stubI18n` helper and the banner-scoped
`getByRole("button", { name: "PT" | "EN" })` lookups already established
there. No new mock, fixture or helper is needed.

Required cases:

- **`type="button"` on both language buttons.** Assert
  `toHaveAttribute("type", "button")` on the PT and the EN button. Scoped to
  the banner, so the hamburger at line 73 cannot satisfy it.
- **Both `aria-pressed` values, in the default fixture.** With setup's
  `language: "pt"` and no `resolvedLanguage`: PT is `"true"` **and** EN is
  `"false"`, asserted in the same case.
- **The swap.** With `stubI18n({ language: "pt", resolvedLanguage: "en" })`:
  PT is `"false"` **and** EN is `"true"`, asserted in the same case.
- **The regional tag.** With
  `stubI18n({ language: "pt", resolvedLanguage: "pt-BR" })`: PT is `"true"`,
  EN is `"false"`. This is the case that catches a divergence between the two
  channels: an `aria-pressed` written as an equality check
  (`currentLang === lang.code`) instead of the shared `startsWith` evaluation
  leaves both buttons `"false"` here while the colours still mark PT active.
- **The two channels agreeing.** At least one of the `aria-pressed` cases must
  also assert the colour pair on the same two rendered elements — the active
  button's `bg-primary` / `text-primary-foreground` and the inactive one's
  `text-muted-foreground`, read through `classTokens` — so that a single
  failing case is enough to report "colour says PT, ARIA says EN".

#### The mutation these cases must fail

A test that asserts only `aria-pressed="true"` on the active button passes
unchanged against a component that hard-codes `aria-pressed="true"` on both
buttons, or on the first one, with no reference to the language at all. The
case list above is specified so that each of those mutations is caught:

| Mutation | Case that fails |
| --- | --- |
| `aria-pressed="true"` hard-coded on both | default fixture — EN is not `"false"` |
| `aria-pressed="true"` on the first button only (PT) | the swap — EN is not `"true"` |
| `aria-pressed` derived from `===` rather than the shared `startsWith` | the regional tag — PT is not `"true"` |
| `aria-pressed` derived from `i18n.language` instead of `currentLang` | the swap — PT is not `"false"` |

An implementer who makes a required assertion pass by weakening it (asserting
only the active value, or only one of the two buttons) has removed the reason
the case exists.

### The existing tests do not need rewriting — verified, not assumed

During APRAS-91 a reviewer applied exactly this change — `type="button"` plus
`aria-pressed={currentLang.startsWith(lang.code)}` on both language buttons —
and ran the suite: all 30 cases in `Navbar.test.tsx` passed untouched. The
APRAS-91 cases were written so as not to entrench this gap, and that was
confirmed empirically rather than inferred, which matters in this repository
because it has a recorded species of test whose assertions forbid a legitimate
improvement.

Concretely, these cases must still pass **byte-identical**, none of them
edited by this task:

- `"marks PT active and EN inactive with the default fixture"`
- `"marks EN active from resolvedLanguage even while language is still pt"`
- `"treats the regional tag pt-BR as PT active"`
- `"calls changeLanguage exactly once with 'en' when EN is clicked"`
- `"exposes exactly one link in the banner, the appName logo pointing at /"`
- `"renders hamburger toggle button on mobile and desktop collapse button in sidebar"`

If any of these needs editing to accommodate the change, the implementation has
gone beyond this task's scope — that is the signal to stop, not to adjust the
test.

### Files touched

- `frontend/src/features/user-administration/components/Navbar.tsx` — add
  `type="button"` and `aria-pressed` to the language button inside the
  `LANGUAGES.map` callback (lines 128–143), deriving the active flag once and
  reusing it in the existing `cn(...)` ternary. No other edit in the file.
- `frontend/src/features/user-administration/__tests__/Navbar.test.tsx` — add
  the cases above to the `"own markup, scoped to the banner"` block. Existing
  cases untouched.

### Gates

Run from `frontend/`:

- `npx tsc -b` exits 0.
- `npx vitest run --coverage` passes, with the thresholds configured in
  `frontend/vitest.config.ts`: **lines 80, functions 78, branches 76,
  statements 80**. Do not restate different figures.
- ESLint: `npm run lint` carries roughly **375 pre-existing errors across 64
  files** repo-wide, so the gate is "no more than the baseline the implementer
  measures", never zero. Measure it on the two touched files before and after:
  at `2cb0d48` that is **0 errors in `Navbar.tsx` and 26 in `Navbar.test.tsx`,
  all `@typescript-eslint/no-explicit-any`** from pre-existing cases. New test
  code must introduce no `any` — the helpers in this file
  (`renderBanner(directorUser())`, `stubI18n`) make casts unnecessary.

### No mockup

No HTML mock accompanies this spec. The buttons look exactly the same before
and after, so a mock would show an unchanged pair of buttons, and the one
decision in the task (which ARIA pattern) is a technical call with a
keyboard-behaviour consequence, decided above rather than put to the operator.
Nothing here is a visual choice.

## Expected Results

- [ ] Both language buttons rendered by the `LANGUAGES.map` callback in
      `Navbar.tsx` carry a literal `type="button"`; the hamburger at line 73
      already had one and is not the element under test.
- [ ] Each language button carries `aria-pressed`, `"true"` on the active
      language and `"false"` on the other, driven by the same single
      evaluation of `currentLang.startsWith(lang.code)` that drives the
      `bg-primary` / `text-muted-foreground` classes.
- [ ] A banner-scoped test asserts `type="button"` on the PT and the EN button.
- [ ] A banner-scoped test asserts both `aria-pressed` values in the default
      `pt` fixture (PT `"true"`, EN `"false"`) and another asserts the swap
      under `stubI18n({ language: "pt", resolvedLanguage: "en" })` (PT
      `"false"`, EN `"true"`), so an `aria-pressed` hard-coded on one or both
      buttons fails.
- [ ] A banner-scoped test asserts PT `"true"` / EN `"false"` under
      `stubI18n({ language: "pt", resolvedLanguage: "pt-BR" })`, so an
      `aria-pressed` derived from `===` instead of `startsWith` fails.
- [ ] At least one new case asserts the `aria-pressed` pair and the
      `bg-primary` / `text-primary-foreground` / `text-muted-foreground`
      classes on the same two elements, so the two channels cannot disagree
      undetected.
- [ ] The APRAS-91 cases listed in this spec still pass unedited, including
      `"marks PT active and EN inactive with the default fixture"`,
      `"marks EN active from resolvedLanguage even while language is still pt"`,
      `"treats the regional tag pt-BR as PT active"` and
      `"calls changeLanguage exactly once with 'en' when EN is clicked"`.
- [ ] No file under `frontend/src/` other than
      `features/user-administration/components/Navbar.tsx` and
      `features/user-administration/__tests__/Navbar.test.tsx` changes, and in
      `Navbar.tsx` only the language-button element changes.
- [ ] From `frontend/`: `npx tsc -b` exits 0; `npx vitest run --coverage`
      passes at or above lines 80 / functions 78 / branches 76 /
      statements 80; ESLint on the two touched files reports no more than the
      measured baseline (0 in `Navbar.tsx`, 26 pre-existing
      `no-explicit-any` in `Navbar.test.tsx`), with no new `any`.

## Out of Scope

- The logout button (lines 164–169) has no `type="button"` either. It is left
  alone: result 4 forbids changing any other element in the file. A separate
  task may sweep remaining buttons.
- The buttons' accessible names stay the bare `"PT"` / `"EN"` label text. A
  fuller name ("Português", "Switch to English") would be an i18n change with
  new translation keys, and would break the `getByRole("button", { name:
  "PT" })` lookups the existing cases rely on.
- No `role="radiogroup"`, no roving `tabindex`, no arrow-key navigation.
- No visual change: no new class, no focus-ring change, no layout change.
- No change to the language-switching behaviour itself
  (`i18n.changeLanguage`), to `src/test/setup.ts`, or to the coverage
  thresholds.
