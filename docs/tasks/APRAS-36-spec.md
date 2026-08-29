# APRAS-36 — Raise frontend test coverage above the 75% functions gate

## Scope

`frontend/` fails its own coverage gate. `npm run test:coverage` exits 1 on the
**functions** threshold; statements, branches and lines pass. This task adds tests until
the functions threshold passes with headroom, without touching production behaviour.

The task also fixes one adjacent papercut it directly causes (ESLint linting the generated
`frontend/coverage/` artifacts) and closes the test blind spot QA found on APRAS-35 (the
whole suite passed while `/login` rendered nothing in a real browser, because no test boots
the real router and module graph).

**Not covered**: any production behaviour change, any backend change, any new feature, the
457 pre-existing ESLint errors under `src/`, and any change to the coverage thresholds
themselves.

## Baseline (measured on `master`, commit `4169bde`, working tree clean)

| Command | Result |
|---|---|
| `npx vitest run` | passes — 71 files, **769 tests** |
| `npm run test:coverage` | **exits 1** — `Coverage for functions (73.16%) does not meet global threshold (75%)` |
| `npm run build` | passes |

Coverage summary at baseline:

| Metric | Value | Threshold (`vitest.config.ts`) |
|---|---|---|
| Statements | 80.14% (3375/4211) | 75 |
| Branches | 76.00% (2014/2650) | 70 |
| Functions | **73.16% (1118/1528)** | **75** |
| Lines | 80.73% (3261/4039) | 75 |

75% of 1528 is 1146, so the gap is exactly **28 more covered functions**.

Top offenders by *uncovered function count* (from `coverage/coverage-summary.json`):

| Uncovered fns | File | Functions |
|---|---|---|
| 26 | `src/features/project-management/components/ConstructionTrackerPage.tsx` | 6/32 (18.8%) |
| 21 | `src/features/visitor-management/components/AuthorizationFormModal.tsx` | 3/24 (12.5%) |
| 18 | `src/api/finance.ts` | 0/18 |
| 16 | `src/features/project-management/hooks/useProjects.ts` | 12/28 |
| 13 | `src/features/document-management/components/DocumentCenterPage.tsx` | 9/22 |
| 12 | `src/api/announcements.ts` | 0/12 |
| 11 | `src/api/visitors.ts` | 0/11 |
| 10 | `src/api/projects.ts` | 0/10 |
| 9 | `src/api/documents.ts` | 0/9 |
| 9 | `src/features/user-administration/pages/ResetPasswordPage.tsx` | 0/9 |
| 7 | `src/api/accessControl.ts`, `src/api/lots.ts`, `src/api/residents.ts` | 0/7 each |
| 6 | `src/api/packages.ts`, `src/api/uploads.ts` | 0/6 each |

**Correction to the task's third expected result**: there is no `VisitorFormModal.tsx` in
the repo (`find frontend/src -name "VisitorFormModal*"` returns nothing). The
visitor-management file at 12.5% functions is `AuthorizationFormModal.tsx`. The expected
results below name the real file.

The single largest, cheapest, most mechanical block is the **ten `src/api/*.ts` modules
with 0% function coverage — 93 uncovered functions in total**. Every one of them is a thin
`apiClient` wrapper; they are uncovered because every hook test mocks the api module, so the
wrapper itself never executes. Covering them alone would clear the gate; the component work
below is what makes the delta worth having.

## Approach

Five work items. Items 1–3 are the bulk of the number; items 4–5 are the quality content.
No file under `src/` outside `__tests__/` directories may change, with the two explicit
exceptions named in item 1.

### 1. Stop ESLint from linting generated coverage artifacts

`eslint.config.js` has `globalIgnores(['dist'])` but not `coverage`, and ESLint 9 flat
config does not read `.gitignore`. After a coverage run, `npx eslint .` reports 462 problems
while `npx eslint src` reports 459 — the 3-problem delta is phantom
`Unused eslint-disable directive` warnings from `frontend/coverage/lcov-report/*.js`.

Change: `globalIgnores(['dist', 'coverage'])`. This and `vitest.config.ts` (item 5, if
needed) are the only non-test files this task may touch.

### 2. Contract tests for the ten zero-coverage `src/api/*.ts` modules

Add one test file per module under `src/api/__tests__/`, following the existing pattern in
`src/api/__tests__/voting.test.ts`:

```ts
vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
```

Files and their exported functions (every export listed here needs at least one test):

| Test file | Module | Exports |
|---|---|---|
| `finance.test.ts` | `api/finance.ts` | `getCategories`, `createCategory`, `updateCategory`, `getBudgetLines`, `createBudgetLine`, `updateBudgetLine`, `deleteBudgetLine`, `getTransactions`, `getTransactionById`, `createTransaction`, `updateTransaction`, `deleteTransaction`, `uploadInvoice`, `deleteInvoice`, `getCashBalance`, `getStatement`, `getBudgetVsActual`, `getCategoryTransactions` |
| `announcements.test.ts` | `api/announcements.ts` | `getAnnouncements`, `getAnnouncementById`, `createAnnouncement`, `updateAnnouncement`, `deleteAnnouncement`, `uploadAnnouncementMedia`, `deleteAnnouncementMedia`, `getAnnouncementComments`, `addAnnouncementComment`, `deleteAnnouncementComment`, `markAnnouncementRead`, `getAnnouncementReadReceipts` |
| `visitors.test.ts` | `api/visitors.ts` | `searchVisitors`, `createVisitor`, `getVisitor`, `updateVisitor`, `getLotAuthorizations`, `createLotAuthorization`, `getAuthorization`, `revokeAuthorization`, `checkInVisitor`, `checkOutVisitor`, `getAccessLogs` |
| `projects.test.ts` | `api/projects.ts` | `getProjects`, `getProjectDetail`, `createProject`, `updateProject`, `deleteProject`, `createMilestone`, `updateMilestone`, `deleteMilestone`, `createProjectUpdate`, `deleteProjectUpdate` |
| `documents.test.ts` | `api/documents.ts` | `getDocumentFolders`, `createDocumentFolder`, `updateDocumentFolder`, `deleteDocumentFolder`, `getDocuments`, `createDocument`, `createDocumentVersion`, `downloadDocument`, `deleteDocument` |
| `lots.test.ts` | `api/lots.ts` | `getLots`, `createLot`, `getLotDetail`, `updateLot`, `deleteLot`, `linkUserLot`, `unlinkUserLot` |
| `residents.test.ts` | `api/residents.ts` | `getLotResidents`, `createResident`, `getResidentDetail`, `updateResident`, `deleteResident`, `linkResidentUser`, `unlinkResidentUser` |
| `accessControl.test.ts` | `api/accessControl.ts` | `createDevice`, `listDevices`, `updateDeviceStatus`, `regenerateDeviceKey`, `syncFacialTemplate`, `getFacialTemplate`, `getAccessEvents` |
| `packages.test.ts` | `api/packages.ts` | `createPackage`, `getPackagesForLot`, `getPackageQueue`, `getPackage`, `markPackagePickedUp`, `getMyPackageLots` |
| `uploads.test.ts` | `api/uploads.ts` | `uploadPhoto`, `getPendingPhotos`, `approvePhoto`, `rejectPhoto`, `deletePhoto`, `getPhotoMetadata` |

These are **contract tests, not coverage filler**. Each test must assert all three of:

1. the HTTP verb and the **exact path string**, including interpolated path params
   (e.g. `` `/finance/budget-vs-actual/${categoryId}/transactions` ``);
2. the request payload / `params` object as passed to `apiClient`, including the
   snake_case query-param names the backend expects (`fiscal_year`, `start_date`,
   `end_date`, `as_of`, `skip`, `limit`, `include_inactive`, …) and any
   optional-param branch the wrapper builds conditionally;
3. the resolved value, proving the wrapper unwraps `response.data`.

Multipart wrappers get one extra assertion each: `uploadInvoice` (`api/finance.ts`),
`uploadAnnouncementMedia` (`api/announcements.ts`) and `uploadPhoto` (`api/uploads.ts`)
must be asserted to send a `FormData` body carrying the file under the field name the
wrapper uses, with the `multipart/form-data` header where the wrapper sets one.

This is the class of bug the tests exist to catch: a wrong path segment or a renamed query
param currently reaches production silently, because every consumer test mocks the module.

### 3. Real-router smoke test (`src/__tests__/AppRouting.smoke.test.tsx`)

`src/__tests__/App.test.tsx` renders `<App />` and asserts only `expect(document.body).toBeDefined()`,
which is true even when the app renders nothing — that is why 769 tests passed while
`/login` was blank in the browser. Add a smoke test that boots the **real** `App` (real
`BrowserRouter`, real `AuthProvider`/`SimulationProvider`, real page modules) and asserts
real controls appear.

Rules that give the test its value — a reviewer must be able to check them by reading the file:

- It imports `App` from `../App` and renders it inside a `QueryClientProvider` only.
- It contains **no `vi.mock()` of any module under `src/features/**`, `src/api/**` (other
  than `src/api/client`), or `react-router-dom`**. The global `react-i18next` mock from
  `src/test/setup.ts` still applies; that is fine.
- It navigates with `window.history.pushState({}, "", "<path>")` before each render, since
  `App` mounts a `BrowserRouter`.

Cases:

| Route | Assertion |
|---|---|
| `/login` | email field, password field and a submit button are all present (≥ 3 form controls) |
| `/signup` | the signup form renders its inputs and submit button |
| `/forgot-password` | the email input and submit button render |
| `/reset-password?token=test-token` | the two password inputs (`Nova Senha`, `Confirmar Nova Senha`) and the submit button render |
| `/reset-password` (no `token` query param) | no password input and no submit button; the `Link inválido` alert modal is shown |
| `/dashboard` while unauthenticated | lands on the login form (exercises `ProtectedRoute` + `Navigate` through the real graph) |

Queries must target actual form elements (`getByLabelText`, `getByRole("textbox")`,
`getByRole("button", { name: … })`), never `document.body`. The test must fail if a page
renders an empty tree.

`ResetPasswordPage` reads the token in a `useEffect` (`searchParams.get("token")` into state)
and gates the whole form behind `const isTokenMissing = !token`, so:

- the token **must** be supplied in the pushed URL's query string
  (`window.history.pushState({}, "", "/reset-password?token=test-token")`) — with no token the
  page renders only the `Link inválido` `AlertModal` and there is nothing to submit;
- the form appears only after the effect has run, so use `await screen.findByLabelText(…)`
  (or `findByRole`) rather than a synchronous `getBy*` for that case;
- password inputs are `type="password"` and therefore **not** matched by
  `getByRole("textbox")` — query them by their labels (`Nova Senha`,
  `Confirmar Nova Senha`) via `getByLabelText`/`findByLabelText`.

The token-missing case is asserted as the negative: `queryByLabelText("Nova Senha")` is
`null` and the `Link inválido` text is present. Neither case may edit `ResetPasswordPage.tsx`.

Note the empty-render failure mode is not hypothetical: `ForgotPasswordPage.tsx` (5.3%
statements) and `ResetPasswordPage.tsx` (2.5% statements, 0/9 functions) are two production
auth pages with essentially no coverage today.

### 4. Dedicated tests for the two worst components

Both are named in the task's own expected results; both are ordinary state-and-handler
components, so their uncovered functions are event handlers.

**`src/features/visitor-management/components/AuthorizationFormModal.tsx` (3/24 functions).**
Test file `src/features/visitor-management/__tests__/AuthorizationFormModal.test.tsx`,
mocking `../hooks/useVisitors` (`useVisitors`, `useCreateVisitor`). Cover at minimum:
- returns `null` when `isOpen` is false, renders the form when true;
- `handleToggleDay` / `handleToggleShift` — toggling a day/shift off removes it from the
  submitted payload, toggling it back on restores it;
- the "create new visitor" path: submitting with an empty name shows the
  `residents.validationNameRequired` message and does **not** call `onSubmit`; a successful
  `createVisitorMutation.mutateAsync` feeds the new visitor's `id` into the `onSubmit` payload;
- the mutation-rejects path: the error message from `err.response.data.detail` is displayed
  and `onSubmit` is not called;
- the "existing visitor" path: selecting a visitor submits that `visitor_id`;
- `onClose` fires from the close control.

**`src/features/project-management/components/ConstructionTrackerPage.tsx` (6/32 functions).**
Extend `src/features/project-management/__tests__/ProjectsFeature.test.tsx` (it already
mounts this page with `vi.mock('../../../api/projects')` and a mocked `useEffectiveIdentity`)
or add a sibling file. Cover the untriggered handlers: `handleSaveProject` (create *and*
edit), `handleConfirmDeleteProject`, `handleSaveMilestone` (create *and* edit),
`handleConfirmDeleteMilestone`, `handleSaveUpdate`, `handleConfirmDeleteUpdate`, the
`statusFilter` change, and project selection. Assert the correct `api/projects` function is
called with the expected id/payload — not merely that a modal opened.

RBAC assertion to keep alongside: with `role` mocked as a non-managing role, the
create/edit/delete controls are absent.

### 5. Verify, do not move, the gate

Re-run `npm run test:coverage` and confirm the reported functions percentage. The task is
done when functions is **≥ 78%** — i.e. the gate passes with real headroom, not by one
rounding tick. Reaching ~80% is expected if items 2–4 are done as written (93 + ~11 + ~14
newly covered functions on a 1528 denominator).

`vitest.config.ts` may be touched **only** to *raise* a threshold to ratchet in the gain
(optional, and only if the final measured value clears the new number by ≥ 2 points).
Lowering any threshold, widening `coverage.exclude`, or adding `/* v8 ignore */` comments to
production files is an automatic fail of this task.

## Expected Results

- [ ] `cd frontend && npm run test:coverage` exits 0; its printed summary shows
      `Functions : >= 78%` (baseline 73.16%, gate 75%) and no `ERROR: Coverage for …` line.
- [ ] The same run reports statements ≥ 80%, branches ≥ 76% and lines ≥ 80% — no metric
      regresses below its baseline (80.14 / 76.00 / 80.73).
- [ ] `frontend/coverage/coverage-summary.json` reports **≥ 90% functions** for each of
      `src/api/finance.ts`, `announcements.ts`, `visitors.ts`, `projects.ts`, `documents.ts`,
      `lots.ts`, `residents.ts`, `accessControl.ts`, `packages.ts`, `uploads.ts` (all 0%
      at baseline), and every exported function of those ten modules is exercised by a named
      test asserting HTTP verb, exact path, payload/params and unwrapped return value.
- [ ] `frontend/coverage/coverage-summary.json` reports ≥ 60% functions for
      `src/features/visitor-management/components/AuthorizationFormModal.tsx` (12.5% at
      baseline — this is the file the task description called `VisitorFormModal.tsx`, which
      does not exist in the repo) and ≥ 60% functions for
      `src/features/project-management/components/ConstructionTrackerPage.tsx` (18.8% at
      baseline).
- [ ] A new test `frontend/src/__tests__/AppRouting.smoke.test.tsx` renders the real `App`
      (real `BrowserRouter` and page modules; no `vi.mock` of anything under `src/features/**`,
      of `react-router-dom`, or of any `src/api/*` module except `src/api/client`) and asserts
      that `/login`, `/signup`, `/forgot-password` and `/reset-password?token=test-token`
      (token query param required — `ResetPasswordPage` renders no form without it) each
      render their real form inputs and submit button; that `/reset-password` with **no**
      token renders no password input and shows the `Link inválido` alert; and that
      `/dashboard` while unauthenticated lands on the login form. Deleting the body of
      `LoginPage`'s returned JSX makes this test fail.
- [ ] `cd frontend && npx vitest run` passes with **> 769 tests** and 0 skipped/`.todo`; no
      pre-existing test is deleted, renamed away, or weakened.
- [ ] `cd frontend && npm run build` (`tsc -b && vite build`) still exits 0 with the new
      test files in the type-check graph.
- [ ] After a coverage run, `cd frontend && npx eslint .` reports **zero** findings whose
      path is under `frontend/coverage/` (baseline: 3 phantom
      `Unused eslint-disable directive` warnings), achieved by adding `coverage` to
      `globalIgnores` in `frontend/eslint.config.js`; the `src/` error count does not
      increase (baseline 457 errors), and `npx eslint` on the files added by this task is clean.
- [ ] No production source file changed: `git diff --name-only master -- frontend/` lists
      only files under a `__tests__/` directory plus `frontend/eslint.config.js` (and at most
      `frontend/vitest.config.ts`, and only with thresholds raised, never lowered). The
      assertion is deliberately scoped to `frontend/`: the branch is expected to also carry
      `docs/**` (this spec, `docs/suggestions-log.md`) and `.meridian/tasks.json`, per this
      repo's commit convention. `coverage.exclude` in `vitest.config.ts` is unchanged and no
      `v8 ignore` comment is added to any file under `frontend/src/` outside `__tests__/`.

## Out of Scope

- The 457 pre-existing ESLint errors under `frontend/src/` (mostly `no-explicit-any`).
- Backend coverage (its own 90% gate, unaffected).
- Any refactor of the components under test — if a handler is hard to test, test it as it is
  and note the friction; do not restructure production code in this task.
- Adding `npm run lint` to `.github/workflows/ci.yml` (CI runs `npm run build` +
  `npm run test:coverage`; making lint blocking is a separate task, and impossible today
  with 457 standing errors).
- Coverage for the remaining mid-range files (`DocumentCenterPage.tsx`, `useProjects.ts`,
  `WebcamCaptureDialog.tsx`, `AvatarCropEditor.tsx`, …) beyond whatever the work above
  incidentally lifts.
