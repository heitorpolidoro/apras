VERDICT: APPROVED

# APRAS-128 code review, round 2 (reopened scope: decision 8 "Cards")

Scope reviewed: the staged diff only (`git diff --cached`), 8 files, +156/-75:
`access/ModuleCard.tsx` (new), `pages/SubscriptionPage.tsx`, `pages/TenantModulesPage.tsx`,
`__tests__/ModuleBundles.test.tsx`, `i18n/locales/{pt,en}.json`, and `docs/tasks/APRAS-128-{spec.md,mock.html}`.
The working tree has no unstaged changes to these files, so the index is self-consistent.
The untracked `backend/scripts/sync_obras_from_drive.py` and `sync-obras.sh` are not staged, which is correct.

## Blocking Findings
None.

## Suggestions
- The bundle title logic is written twice, with slightly different inputs:
  `SubscriptionPage.tsx` uses `t(\`modules.bundles.${unit[0].bundle}\`, { defaultValue: features.join(" + ") })` and
  `TenantModulesPage.tsx` uses `unit.length > 1 ? t(\`modules.bundles.${bundleOf(unit[0])}\`, ...) : features[0]`.
  A small `packageTitle(t, bundleKey, features)` helper in `access/moduleGroups.ts` (or next to `ModuleCard`) would keep
  the fallback rule in one place. This is minor, since both copies are short and correct.
- No test pins the "list only for a bundle" rule (`features.length > 1` in `ModuleCard.tsx`). If that changed to `> 0`,
  every single-module card would list itself and no test would fail. One assertion that a single-module card
  (for example `finance`) has no `li` would cover it. Also optional: a test for the " + " fallback when a bundle key has no
  `modules.bundles` entry.
- `ModuleCard` sets both `htmlFor={id}` and wraps the input inside the `<label>`. That is redundant but harmless. Dropping
  `htmlFor` (implicit association) or keeping it are both fine.
- The SubscriptionPage test for the `assets` bundle could assert the card's features too, so both pages are covered.
  The spec asks for one test, and the TenantModulesPage test meets that.

## Evidence

### Spec compliance (decision 8, last expected result)
- Every unit is a card. On `/admin/modules`, every unit (bundle or single) renders `ModuleCard`. On `/subscription`,
  in-plan units render `ModuleCard`, and read-only rows (not in plan / override / unmanaged) get the same card styling on
  their `div`. Units are laid out in `grid gap-2 sm:grid-cols-2` under the unchanged `fieldset`/`legend` group headings.
  This matches "two columns from `sm` up".
- Title: bold (`font-semibold`). Bundles use `modules.bundles.<key>` with the " + " fallback, and single modules use their own name.
- The feature list shows only when `features.length > 1`, so only bundles list their members, in `<ul><li>`.
- The checkbox's accessible name is `aria-label={title}`, kept explicit so the badge and price stay out of the name. The
  rationale comment moved into `ModuleCard`.
- i18n: `modules.bundles` has `tasks`, `reservations`, `assets` and `visitors` in both pt and en. These match the
  `MODULE_BUNDLES` keys in `backend/app/core/permissions.py:921-926` exactly.
- Test: `ModuleBundles.test.tsx` now finds the bundle checkbox by `pt.modules.bundles.tasks` ("Tarefas e categorias").
  That name differs from the fallback "Tarefas + Categorias", so the test would fail if the i18n lookup broke. It also
  asserts that the card's `li` texts equal `[name("tasks"), name("categories")]`. If the bundle key were missing,
  `bundleLabel` would return `undefined` and the role query would match several checkboxes and throw, so the test fails
  loudly rather than passing vacuously.
- Spec and mock: decision 8 and the expected result were added, and the mock was updated to package cards with pt titles
  consistent with the new keys.

### Architecture / KISS
- `ModuleCard` is a presentational component in `access/`, next to `moduleGroups.ts`, with no state and no data
  fetching. The props are minimal, and `children` takes the trailing details (core badge, price), so neither page
  needed special cases.
- Toggle, disabled and checked semantics are unchanged from the shipped round: `toggle(unit)`, `unit.every(isChecked)`,
  `disabled` from core / `can_contract`.

### Security
- No new inputs, network calls or HTML injection. All text goes through React and i18n.

### Checks run
- `npx vitest run src/features/user-administration`: 53 files, 549 tests passed.
- `npx eslint` on the four changed TS/TSX files: exit 0.
- `npx tsc --noEmit -p tsconfig.app.json`: exit 0.
- Prettier `--check` flags `TenantModulesPage.tsx`, but the HEAD version already fails it and prettier is not wired
  into `package.json` or CI. This is pre-existing and not counted against this diff.
