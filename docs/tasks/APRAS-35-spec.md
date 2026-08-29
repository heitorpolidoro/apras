# APRAS-35 — Fix frontend TypeScript errors that break `npm run build` and the Vite dev app

## Scope

`frontend/` currently does not build. `npm run build` (`tsc -b && vite build`) fails with
**92 TypeScript errors across 37 files**, and even `vite build` alone (no type-check) fails
with rolldown `MISSING_EXPORT` errors. The same missing exports break the dev server at
runtime, so the SPA does not mount in a browser.

This task takes the frontend from 92 errors to **zero** and adds a CI guard so the build
cannot silently break again.

Why this went unnoticed: `.github/workflows/ci.yml` runs only `npm run test:coverage` for
the frontend. Vitest transpiles with esbuild and never type-checks, so all 769 tests pass
against code that does not compile. Adding `npm run build` to CI is part of this task.

**Not covered**: the 479 pre-existing ESLint errors (a separate cleanup), any backend
change, any new feature, and any behavioural redesign beyond the two genuine runtime bugs
called out in Groups C and D below.

## Baseline (measured on `master`, commit `d9ac704`)

| Command | Current result |
|---|---|
| `npm run build` | fails — 92 `error TS…` lines |
| `npx vite build` | fails — `MISSING_EXPORT` from `src/types/media_asset.ts` and `src/types/resident.ts` |
| `npx vitest run` | **passes** — 71 files, 769 tests |
| `npm run lint` | 484 problems (479 errors, 5 warnings) |

Error codes: 28×TS6133, 22×TS2322, 16×TS1484, 13×TS2741, 3×TS7006, 3×TS2339, 2×TS6196,
2×TS1294, 1×TS2345, 1×TS2305, 1×TS2304.

## Approach

Nine groups. Each is independent; do them in this order so later groups see fewer errors.

### Group A — repair the broken type declarations (3 errors)

1. `src/types/media_asset.ts:26` — `url: str;` → `url: string;` (TS2304; `str` is a Python
   type name that leaked into the TS port).
2. `src/types/resident.ts:1` and `src/types/package.ts:1` — `export enum` is not erasable
   syntax and violates `erasableSyntaxOnly` in `tsconfig.app.json` (TS1294). Convert both to
   the const-object pattern **already used everywhere else in this codebase**
   (`src/types/auth.ts` `UserRole`, `src/types/lot.ts` `LotStatus` / `LotAssociationType`):

   ```ts
   export const ResidentRelationship = {
     TITULAR: "TITULAR",
     // … same 6 members, same string values
   } as const;

   export type ResidentRelationship =
     (typeof ResidentRelationship)[keyof typeof ResidentRelationship];
   ```

   Same for `PackageStatus` (`AWAITING_PICKUP`, `PICKED_UP`). String values must not change —
   they are wire values from the backend.

   Both names stay dual value+type, so existing call sites keep working:
   `ResidentRelationship.TITULAR` (`ResidentFormModal.tsx`, `ResidentTable.tsx`,
   `ResidentsTab.test.tsx`), the `switch` in `ResidentTable.tsx:26-58`, and
   `PackageStatus.AWAITING_PICKUP` (`PackageStatusPage.tsx:78`). These remain **value**
   imports — do not convert them to `import type` in Group B.

### Group B — type-only imports (16× TS1484) — this is the dev-app breakage

`verbatimModuleSyntax` is on, so a value-style `import { SomeInterface }` is emitted verbatim
and the interface has no runtime export. `src/types/media_asset.ts` has *no* runtime exports
at all, which is exactly the browser error in the task description. Add the `type` keyword
(inline `import { type X }` for mixed imports, `import type { … }` when every specifier is a
type):

| File | Line(s) | Specifiers |
|---|---|---|
| `src/api/uploads.ts` | 3,4,5 | `EntityType`, `MediaAssetRead`, `MediaAssetListResponse` |
| `src/features/lot-management/components/LinkUserAccountModal.tsx` | 6 | `ResidentDetail` |
| `src/features/lot-management/components/ResidentFormModal.tsx` | 5,6,8 | `ResidentCreatePayload`, `ResidentDetail`, `ResidentUpdatePayload` (keep `ResidentRelationship` on line 7 as a value) |
| `src/features/lot-management/components/ResidentsTab.tsx` | 14,15,16 | same three |
| `src/features/lot-management/components/ResidentTable.tsx` | 5 | `ResidentDetail` only (keep `ResidentRelationship` as a value) |
| `src/features/media-management/components/AvatarWithFallback.tsx` | 2 | `PhotoApprovalStatus` |
| `src/features/media-management/components/PhotoApprovalQueuePage.tsx` | 7 | `MediaAssetRead` |
| `src/features/media-management/components/PhotoUploadModal.tsx` | 2 | `EntityType` |
| `src/features/media-management/hooks/useMediaAssets.ts` | 10 | `EntityType` |
| `src/features/media-management/__tests__/MediaAssets.test.tsx` | 10 | `MediaAssetRead` |

### Group C — `useUsers()` return shape (3× TS2339, 3× TS7006) — real runtime bug

`src/hooks/useUsers.ts` returns a TanStack `UseQueryResult`, i.e. the user array is on
`.data`. Two components destructure a non-existent `users` property and then call
`users.filter(...)`, which throws `TypeError: Cannot read properties of undefined` in the
browser. The tests hide this because they mock the hook with the wrong shape.

- `src/features/lot-management/components/LinkUserAccountModal.tsx:24` and
  `src/features/lot-management/components/UserLotAssignmentModal.tsx:28` →
  `const { data: users = [], isLoading: … } = useUsers();` (keep each file's existing
  `isLoading` alias name). The `= []` default is required so `.filter` is safe while loading.
  The three implicit-`any` callback params (`LinkUserAccountModal.tsx:33,94`,
  `UserLotAssignmentModal.tsx:110`) then infer `User` and need no annotation.
- Fix the two mocks that encode the wrong shape:
  `src/features/lot-management/__tests__/LotsPage.test.tsx:118` and
  `src/features/lot-management/__tests__/ResidentsTab.test.tsx:82` — change
  `{ users: [...], isLoading: false, error: null }` to `{ data: [...], … }`. Do not change
  their assertions; both suites must still pass.

Do **not** change the signature of `useUsers` / `useAssignableUsers` — the task-management
consumers already read `.data` correctly.

### Group D — `ProjectRead` does not exist (1× TS2305)

`src/api/projects.ts` imports `ProjectRead` from `../types/project` and uses it at lines
38, 39, 46, 47 as the return type of `createProject` / `updateProject`. The frontend name for
the backend's `ProjectRead` schema (`backend/app/schemas/project.py:123`, the response model
of `POST /projects` and `PUT /projects/{id}`) is `ConstructionProject`
(`src/types/project.ts:5`) — the flat project without `milestones`/`updates`.

Remove `ProjectRead` from the import list and use `ConstructionProject` at all four sites.
Do not add a `ProjectRead` alias; one name per shape.

### Group E — missing Badge variants (2× TS2322)

`src/components/ui/badge.tsx` has no `destructive` or `warning` variant, but two
project-management components request them:

- `src/features/project-management/components/BudgetVsActualProgressBar.tsx:40` —
  `variant="destructive"` on the "Orçamento Estourado" badge.
- `src/features/project-management/components/ProjectUpdateFeed.tsx:90` —
  `variant="warning"` on the cost-impact badge.

Add both to the `cva` variant map, following the file's existing conventions (semantic
groups, Tailwind utility pairs like the `active`/`inactive` entries):

```ts
// Semantic
destructive: "bg-red-100 text-red-800",
warning: "bg-amber-100 text-amber-800",
```

Do not modify or reorder the existing variants, and do not change the two call sites — the
components' intent is correct; the primitive was incomplete.

### Group F — stale task fixtures (13× TS2741, 22× TS2322)

`TaskRead` (`src/features/task-management/types/index.ts:129`) requires
`visible_to: UserTypeRead[]`. `manager_visible` was removed from the type when `visible_to`
landed, but the test fixtures were never migrated. In each of the mock task literals below,
**replace** `manager_visible: false` with `visible_to: []`:

- `src/features/task-management/components/__tests__/TaskCard.test.tsx:26`
- `src/features/task-management/components/__tests__/TaskList.test.tsx:57,73`
- `src/features/task-management/components/__tests__/TaskBoard.test.tsx:56,72`
- `src/features/task-management/components/__tests__/TaskDashboard.test.tsx:97`
- `src/features/task-management/components/__tests__/TaskDetailsView.test.tsx:67`

(The last two currently compile but carry the same dead field; clean them in the same pass so
`manager_visible` disappears from `frontend/` entirely.) No assertion, render call, or test
name may change.

### Group G — unused symbols (28× TS6133, 2× TS6196)

Delete the unused binding in each case. Straight import deletions:

- `import React from "react"` (unused under `jsx: "react-jsx"`) in
  `access-control/__tests__/AccessControlPage.test.tsx:4`,
  `access-control/__tests__/GateMonitorPage.test.tsx:4`,
  `media-management/__tests__/MediaAssets.test.tsx:3`,
  `package-management/__tests__/PackageStatusPage.test.tsx:4`,
  `visitor-management/__tests__/AuthorizationQrModal.test.tsx:3`,
  `visitor-management/__tests__/GatekeeperDashboard.test.tsx:4`,
  `visitor-management/__tests__/QrScannerModal.test.tsx:3`,
  `visitor-management/__tests__/VisitorAuthPage.test.tsx:4` (all paths under
  `src/features/`).
- Unused `lucide-react` icons: `LinkUserAccountModal.tsx:3` (`UserIcon`),
  `LotDetailsView.tsx:3` (`UserIcon`, `Shield`), `LotsPage.tsx:3` (`Filter`),
  `document-management/components/DocumentCenterPage.tsx:8` (`Filter`),
  `visitor-management/components/VisitorAuthPage.tsx:3` (`Filter`),
  `visitor-management/components/AccessLogTimeline.tsx:3` (`User`),
  `visitor-management/components/AuthorizationFormModal.tsx:3` (`Calendar`).
- Unused test imports: `document-management/__tests__/DocumentCenter.test.tsx:6,8,9,10`
  (`FolderTreeSidebar`, `PDFViewerModal`, `DocumentUploadModal`, `FolderFormModal`) and `:13`
  (type `AssociationDocument`, TS6196); `occurrence-management/__tests__/OccurrenceBook.test.tsx:7`
  (`NewOccurrenceModal`) and `:11` (type `Occurrence`, TS6196);
  `visitor-management/__tests__/QrScannerModal.test.tsx:1` (`screen`).

Three that need judgement rather than deletion:

- `src/features/lot-management/hooks/useResidents.ts:68,91,113,135` — `lotId` is destructured
  in each `mutationFn` but only read as `variables.lotId` inside `onSuccess`. Remove `lotId`
  from the **destructuring pattern** only; it must stay in the parameter's type literal and
  in every `onSuccess` `queryClient.invalidateQueries` key. Cache invalidation behaviour must
  not change.
- `src/features/media-management/components/PhotoApprovalQueuePage.tsx:10` — `setPage` is
  never called because no pagination control was ever rendered. Narrow the declaration to
  `const [page] = useState(1);`. Building the pagination UI is **out of scope**.
- `src/features/document-management/components/DocumentCenterPage.tsx:53` — drop the unused
  `isLoadingFolders` alias, keeping `const { data: folders = [] } = useDocumentFolders();`.

### Group H — heterogeneous `it.each` hook table (1× TS2345)

`src/features/assembly-voting/hooks/__tests__/useVoting.test.ts:83-95` — `it.each` infers a
union of four differently-typed `UseQueryResult` factories, which `renderHook` rejects. Hoist
the table into an explicitly typed constant whose element type covers only what the test body
reads (`result.current.isSuccess`):

```ts
const queryHookCases: Array<[string, () => { isSuccess: boolean }]> = [
  ["/votes/vote-1/my-ballot", () => useMyBallot("vote-1")],
  ["/votes/vote-1/eligible-lots", () => useEligibleLots("vote-1")],
  ["/votes/vote-1/tally", () => useTally("vote-1")],
  ["/lots/lot-1/voter-eligibility", () => useLotVoterEligibility("lot-1")],
];

it.each(queryHookCases)("fetches %s", async (url, hook) => { /* body unchanged */ });
```

Any equivalent typing is acceptable as long as all four cases still run, the four URL
assertions are unchanged, and no `any` / `@ts-expect-error` is introduced.

### Group I — CI regression guard

In `.github/workflows/ci.yml`, `frontend` job, add a step between "Install dependencies" and
"Run tests with coverage":

```yaml
    - name: Type-check and build
      run: |
        cd frontend
        npm run build
```

Placing it before the test step makes a compile break fail fast. Do not touch the backend
job, the coverage upload, or the SonarCloud job.

## Constraints

- **No suppressions.** No new `any`, `as any`, `@ts-ignore`, `@ts-expect-error`, or
  `eslint-disable`, and no loosening of `tsconfig.app.json` / `tsconfig.node.json` (in
  particular `erasableSyntaxOnly`, `verbatimModuleSyntax`, `noUnusedLocals`,
  `noUnusedParameters` must all stay on). Excluding `__tests__` from `include` is likewise not
  an acceptable fix — the stale fixtures in Group F are real drift worth catching.
- **No behaviour change** except the two genuine bugs (Group C's `undefined.filter` crash and
  Group D's wrong response type) and the two newly available Badge variants.
- The 71 test files / 769 tests must all still pass, and `npm run test:coverage` must still
  clear its thresholds (lines/functions/statements 75%, branches 70%).
- No new locale keys; no `en.json` / `pt.json` changes are needed anywhere in this task.

## Expected Results

- [ ] `cd frontend && npm run build` exits 0 and prints no line matching `error TS`.
- [ ] `cd frontend && npx tsc -b --force` exits 0 with empty output.
- [ ] `cd frontend && npx vite build` exits 0 and emits no `MISSING_EXPORT` diagnostic.
- [ ] With `npm run dev` running, loading the app at `/login` renders the login form and the
      browser console shows no `does not provide an export named` error (previously:
      `The requested module '/src/types/resident.ts' does not provide an export named 'ResidentDetail'`).
- [ ] `grep -n "str" frontend/src/types/media_asset.ts` shows no `url: str`; the field is
      `url: string`.
- [ ] `grep -rn "^export enum" frontend/src` returns no matches; `ResidentRelationship` and
      `PackageStatus` are `as const` objects with matching union types, and their string
      values are unchanged.
- [ ] `grep -rn "manager_visible" frontend/src` returns no matches.
- [ ] `cd frontend && npx vitest run` reports 71 passed test files and 769 passed tests, 0
      failed.
- [ ] `cd frontend && npm run test:coverage` exits 0 (all four coverage thresholds met).
- [ ] `cd frontend && npm run lint` reports no more than the 479 pre-existing errors — the
      count must go down or stay equal, never up.
- [ ] `.github/workflows/ci.yml` contains a step in the `frontend` job that runs
      `npm run build`, and the CI run for the PR shows that step passing.
- [ ] `src/api/projects.ts` imports no `ProjectRead`; `createProject` and `updateProject` are
      typed `Promise<ConstructionProject>`.
- [ ] `useUsers()` is consumed as `data` (not `users`) in `LinkUserAccountModal.tsx` and
      `UserLotAssignmentModal.tsx`, and the mocks in `LotsPage.test.tsx` and
      `ResidentsTab.test.tsx` return `{ data: [...] }`.
- [ ] `badgeVariants` in `src/components/ui/badge.tsx` includes `destructive` and `warning`;
      all previously existing variants are unchanged.

## Out of Scope

- The 479 pre-existing ESLint errors (`no-explicit-any`, `react-hooks/set-state-in-effect`,
  etc.) beyond the ~30 unused-variable errors that Group G removes as a side effect.
- Pagination UI for `PhotoApprovalQueuePage`.
- Any redesign of the `useUsers` hook's public API.
- Backend, Alembic, or schema changes.
- Adding a lint gate to CI (only the build gate is added here).
