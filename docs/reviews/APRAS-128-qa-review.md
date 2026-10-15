VERDICT: APPROVED

# APRAS-128 QA review (reopened: decision 8, "Cards")

Scope of this round: decision 8 and the expected result "Every unit on both
pages is a card with the package title and, for a bundle, the list of its
features; bundles are titled from `modules.bundles` in pt and en, and a test
asserts the bundle card lists its members." Plus a re-run of the frontend
gates against the staged change (`git diff --cached`). The other expected
results shipped and passed QA earlier and were not re-verified.

## Expected Results Checked

- [x] Every unit on `/admin/modules` and `/subscription` is a card with the
  package title and, for a bundle, the list of its features; bundles titled
  from `modules.bundles` in pt and en; a test asserts the bundle card lists its
  members.
  - **Rendering (temporary probe test, deleted afterwards).** I rendered the real
    `TenantModulesPage` and `SubscriptionPage` with a real `i18next` instance
    (en and pt resources from the locale files) in place of the suite's pt-only
    `t` mock, with mocked API responses:
    - Tenant page, en: the visitors bundle checkbox's accessible name is
      "Visitors and gate". Its card (`label.rounded-lg.border.bg-card.p-3.shadow-sm`)
      lists `<li>` Visitors / Visitor authorizations / Gatehouse, and the title
      span is `font-semibold`. Reservations reads "Reservations and spaces"
      with the list Reservations / Reservable spaces. Finance (no bundle) is a
      card with no list. Core `users` is a disabled card with the "core" badge.
      Every checkbox on the page sits inside a `rounded-lg` card label.
      Each of the 10 group fieldsets wraps its cards in a `div.grid`, so 10
      grids in all.
    - Tenant page, pt: "Visitantes e portaria" with Visitantes / Autorizações
      de visita / Portaria, and "Reservas e espaços". All other checks the same
      as en.
    - Subscription page, en/pt: "Assets and inventory" / "Patrimônio e
      estoque" with the summed price "15 BRL" and the list Assets, Inventory /
      Patrimônio, Estoque. The "Tasks and categories" bundle lists its two
      members. The single `documents` card has no list. The not-in-plan row
      (`subscription-row-finance`) has no checkbox but is still styled as a
      card (`rounded-lg border bg-card p-3`).
    - Fallback: a bundle key with no translation (`zz_unknown`) is titled
      "Tasks + Categories" (members joined by " + ") under real i18next.
  - **Locale keys.** `modules.bundles` in both `en.json` and `pt.json` has
    exactly the four keys `tasks`, `reservations`, `assets`, `visitors`. These
    match the `MODULE_BUNDLES` keys in `backend/app/core/permissions.py:921`.
  - **Test asserts members.** `ModuleBundles.test.tsx` (TenantModulesPage)
    checks that the bundle card's `<li>` texts equal `[Tarefas, Categorias]`.
    Mutation check: I temporarily replaced `features.length > 1 &&` with
    `false &&` in `ModuleCard.tsx`, and the test failed with
    `AssertionError: expected [] to deeply equal [ 'Tarefas', 'Categorias' ]`.
    I then restored the file from a backup. `git diff -- ModuleCard.tsx`
    (worktree vs index) was empty afterwards.
  - **Built output.** `npm run build` writes `dist/assets/index-*.js`, which
    contains "Patrimônio e estoque" and "Visitors and gate". The CSS contains
    `sm\:grid-cols-2`.

- [x] Frontend gates still pass with the staged change:
  - `npx vitest run --coverage`: 202 files and 2721 tests passed.
    Statements 91.75%, branches 85.57%, functions 88.05%, lines 92.47%. All
    are above the 75% gate.
  - `npx tsc -b`: exit 0.
  - `npm run lint`: 375 problems (373 errors, 2 warnings), exit 1. This is the
    existing baseline, not a regression. ESLint is per-file, and running
    `npx eslint` on the four changed TS/TSX files (ModuleCard.tsx,
    SubscriptionPage.tsx, TenantModulesPage.tsx, ModuleBundles.test.tsx) gives
    "No issues found". I could not lint a HEAD copy for a direct comparison
    because `git archive` was denied. Earlier QA reports in docs/reviews
    record 370 and 372, so the baseline has grown through other commits, not
    this one.
  - `npm run build`: built successfully, with only the existing chunk-size
    warning.

## Blocking Findings

None.

## Suggestions

- The test setup's `t` mock (`src/test/setup.ts`) ignores `defaultValue`, so
  the suite never exercises the " + " fallback title. It only passed under real
  i18next in my probe. A small test with an untranslated bundle key would lock
  it in.
- The SubscriptionPage bundle test checks the bundle's title and price but not
  its feature list. Only the TenantModulesPage test checks the list. That meets
  the expected result as worded ("a test"), but a matching assertion on the
  subscription card would cover the second page too.
- The English title "Visitors and gate" leaves out authorizations. The card's
  feature list shows all three members, so this is copy-only.

## Notes

- The git state was left as found. The temporary probe test was deleted and
  `ModuleCard.tsx` was restored byte-identical to the index. The only new file
  is this report.
