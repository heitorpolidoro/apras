# APRAS-77 — Migrate hard-coded palette classes to semantic theme tokens (umbrella: integration and verification)

## Scope

APRAS-77 was split; children APRAS-78..85 are done and own all migration work. This umbrella has no migration of its own. Its remaining work is to verify, across all migrated directories, the four umbrella results, and to close the gaps found while reading the current tree (at 9339346).

Findings from reading the children's specs, `themeTokenMigration.test.ts`, `TenantBrandReach.test.tsx`, `themeTokenCompile.test.ts` and `docs/frontend/unmapped-colours.md`:

- **Result 3 (grep pin): already satisfied, and stronger than asked.** APRAS-85 inverted the guard to a repo-wide deny (`SCANNED_ROOTS = ["src/**"]`), so every non-test `.ts`/`.tsx` under `frontend/src` is covered, with exact `(file, class)` exceptions cross-checked against the ledger. Only one regression assertion is added (below).
- **Result 4 (unmapped colours listed): already satisfied.** `docs/frontend/unmapped-colours.md` holds one row per kept occurrence, the guard ties each exception to a ledger row, and no child added a one-off token to `index.css` (APRAS-88's `--primary-text` was a published table amendment). Verification only.
- **Result 1 (brand re-themes, asserted against the tenant token): partially satisfied.** Verified at HEAD: `TenantBrandReach.test.tsx` has blocks for the pilot and APRAS-81, 82, 83, 84 and 85, but the APRAS-85 block imports only `infraction-management` components, and there is no block for APRAS-79 or APRAS-80. Seven `src/features` directories therefore have no brand-reach assertion: `lot-management`, `visitor-management`, `task-management`, `dashboard`, `user-administration`, `space-reservation-management`, `assembly-voting`. (`TenantBrandReach.test.tsx` already `vi.mock`s `user-administration/context/AuthContext` and `visitor-management/hooks/usePackages`; extend that pattern for any hook the chosen component calls.)
- **Result 2 (byte-identical default colours): not true as worded, and cannot be made true.** The operator-approved mapping table (`docs/frontend/theme-token-mapping.md`) deliberately maps some classes to tokens with a published, budgeted ΔL/ΔE (e.g. `text-emerald-500` → `text-primary-text` at ΔE 18.60, `bg-slate-300` → `bg-primary` at ΔE 29.21), and `themeTokenCompile.test.ts` pins those numbers. The achievable, already-tested claim is: every default-theme colour change is bounded by the published budget, and nothing changes outside the table. This task records that reconciliation instead of inventing a byte-identity test that would fail; the report must tell the operator.

Not covered: any new migration, new token or gap code, change to the mapping table, or visual regression tooling (the repo has none).

## Approach

Behavior: every migrated directory is provably covered by a brand-reach assertion, and each umbrella result maps onto named passing tests.

Files touched:
- `frontend/src/components/__tests__/TenantBrandReach.test.tsx` — append one `describe` per directory below (seven `it` blocks minimum, one per row), in the existing shape: render the component beside `TenantBrandTheme`, `await waitFor(() => expect(brandedPrimary()).toBe(THEME.light.primary))`, then assert the whitespace-split class tokens of the rendered markup contain the tenant-bound token(s) named, never a colour literal. Mock data-fetching hooks the way the file already does.

  | Directory | Component rendered | Token asserted present |
  |---|---|---|
  | `lot-management` | `components/ResidentTable` (props-only) | `text-primary` (link icon) |
  | `visitor-management` | `components/AuthorizationQrModal` | `text-primary` (QR icon) |
  | `task-management` | `components/AuditTimeline` (mock `useTaskHistory`) | `bg-primary` (timeline dot) |
  | `dashboard` | `components/GeneralDashboardPage` (mock its data hook) | `text-primary-text` and `text-primary` |
  | `user-administration` | `components/PermissionMatrix` (props-only) | `text-primary` (checkbox) |
  | `space-reservation-management` | `components/ReservableSpacesPage` (mock `useReservableSpaces`) | `bg-primary` via its `Button` primitive's default variant |
  | `assembly-voting` | `components/AssemblyMinutesView` (mock `useAssemblyMinutes`) | `bg-primary` via its `Button` primitive's default variant |

  If a row's token is not emitted in the rendered state the developer reaches, they pick another tenant-bound token (`primary` family) that component does carry and name it in the test; the directory and component stay as listed.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — append one `describe` ("APRAS-77 umbrella") with one test: for every directory returned by `readdirSync("src/features")` (excluding `__tests__`; today 20 directories), at least one file in `pinnedFiles()` starts with `src/features/<dir>/`. The set is derived, not hand-listed, so a new feature directory is covered automatically. It does NOT re-assert that `SCANNED_ROOTS` equals `["src/**"]`: the existing test "is exactly the single recursive src entry" already pins that. Edit nothing above the new block.
- `docs/frontend/unmapped-colours.md` — no change expected; edit only if the cross-check finds a missing row.

Test criteria: each new brand-reach test fails if its component's token class is swapped back to a palette class; the umbrella test fails if a feature directory has no pinned file.

Report duty (not a test, not an Expected Result): the task report lists ledger totals per gap code and states that no colour received a one-off token.

## Expected Results
- [ ] `TenantBrandReach.test.tsx` has a passing test for each of the seven directories in the Approach table, asserting a tenant-bound token on the named component and never a colour literal.
- [ ] A new `themeTokenMigration.test.ts` test passes only if every directory under `src/features` (excluding `__tests__`) contributes at least one pinned file.
- [ ] `themeTokenMigration.test.ts` reports no violation, so a palette class reintroduced anywhere under `frontend/src` fails the suite.
- [ ] `themeTokenCompile.test.ts` passes, pinning every default-theme colour change to its published ΔL/ΔE budget.
- [ ] `git diff -- frontend/src/index.css` is empty.

## Out of Scope
New migrations, new tokens or gap codes, table amendments, visual regression tooling, and a literal byte-identity test (it contradicts the approved table).
