# APRAS-85 — Migrate the remaining feature directories and close the guard

Child 8 of 8 of the APRAS-77 split — **the closer** — specified against the
**amended** contract: APRAS-78's three artefacts as extended by APRAS-79 /
APRAS-80 and amended by APRAS-88 at `c7c42fc`. Job (a) **consumes** that
contract and may not extend it: no row added to
`docs/frontend/theme-token-mapping.md`, no new gap code, no token in
`frontend/src/index.css`. Job (b) restructures **only** the guard's allow-list
machinery, which is the one thing the closer is licensed to replace.

Three distinct jobs, in this order:

- **(a)** migrate the last six feature directories — `infraction-management`,
  `task-management`, `dashboard`, `user-administration`,
  `space-reservation-management` and `assembly-voting`;
- **(b)** invert `frontend/src/__tests__/themeTokenMigration.test.ts` from an
  allow-list of pinned `MIGRATED_DIRECTORIES` into a **repo-wide deny** over
  every non-test `.ts`/`.tsx` under `frontend/src`, with the existing
  checked-in exceptions file as the single place listing deliberately
  unmigrated occurrences;
- **(c)** widen §3b's `prefix` production so the grammar also matches
  **side-qualified** border and divide utilities (`border-t-slate-400`,
  `divide-y-gray-100`, …), and re-scan the whole tree with it.

Job (c) is an **amendment to APRAS-78's published §3b**, and the operator has
authorised this child — and only this child, and only for the `prefix`
production — to make it. Its reason, recorded so no reviewer treats the
amendment as a scope breach: the closer's promise should be true without a
loose end, and with the old grammar "any new hard-coded palette class fails
CI" was only true of classes §3b happened to match.

After this child, any new hard-coded palette class anywhere in the frontend
fails CI by default.

## Scope

Job (a): the **thirty** non-test `.tsx` files under
`frontend/src/features/{infraction-management,task-management,dashboard,user-administration,space-reservation-management,assembly-voting}/`
that carry a palette class — out of 86 non-test source files in those six
trees — migrated to the tokens the table names, with every class left behind
logged in the ledger and excepted in the guard.

Job (b): `MIGRATED_DIRECTORIES`, `pinnedFiles()`'s default argument, the
`describe("MIGRATED_DIRECTORIES")` block, and the two hot spots inside
`violations()` that the repo-wide input makes quadratic.

Job (c): the `prefix` production of §3b in
`docs/frontend/theme-token-mapping.md` and the matching `PREFIX` constant in
the guard, plus the re-scan that widening implies. **Five** occurrences
tree-wide become newly visible, all of them in
`frontend/src/features/task-management/components/TaskBoard.tsx` — measured,
§"Job (c)".

Not covered: `index.css`, the backend, the `.dark` block, the mapping table's
rows, gap codes and tokens, the ledger's rules, every part of §3b other than
`prefix`, and every `hooks/`, `utils/`, `types/`,
`context/` and `access/` file in the six trees (all 103 non-test `.ts` files
under `frontend/src` contain **zero** grammar matches — measured, §"The
re-measurement").

**No mockup.** This is a token substitution plus a test-harness inversion;
there is no new UI.

## What is measured and what is projected — stated once, plainly

Only two classes of figure appear below.

- **Measured at `a8fc8ab`** (this HEAD) and **unaffected by siblings**:
  everything about job (a). APRAS-81, 82, 83 and 84 are specced and approved
  but **not yet implemented**, and their directories are **disjoint** from this
  child's six. Nothing they do adds, removes or edits a file or an occurrence
  in the thirty files below, so the 312 / 167 / 145 arithmetic is a
  measurement, not a forecast. **Job (c)'s widening is likewise disjoint
  from them**: re-scanned with the widened production, the five newly
  visible occurrences are all in this child's own `task-management`, and
  **no published count in APRAS-81, 82, 83 or 84 moves** — measured,
  §"Job (c)". The four known-gap classes' repo-wide total
  (§"The two known no-token gaps") is likewise a measurement that survives
  those four children, because every one of them is a gap that §1i forbids
  touching.
- **Projected after 81–84 land**, and labelled **(projected)** at every
  occurrence: the *repo-wide* residual — how many grammar matches and ledger
  rows exist under `frontend/src` once all eight children are done. Two
  numbers only: **1,197 remaining occurrences** and **882 exceptions entries**,
  derived as the sum of each child's own published kept-count
  (78: 24, 79: 211, 80: 113, 81: 276, 82: 129, 83: 190, 84: 109, 85: 145) and
  of each child's own published pair-count (78: 22, 79: 148, 80: 84, 81: 200,
  82: 77, 83: 145, 84: 80, 85: 126). Both are 5 higher than revision 2's
  figures, and both fives are job (c)'s.

**The implementer re-derives both projections rather than trusting them**, by
re-running the repo-wide scan at its own HEAD after 81–84 have merged. They
exist so a reviewer can tell a drift from a defect. **No expected result below
depends on either projected constant**: the repo-wide assertions are written
as *equalities between two things the test computes* (matches == ledger rows
== excused pairs), which are decidable whatever the sum turns out to be.

## The re-measurement

Measured now, at `a8fc8ab`, over the whole of `frontend/src` with the §3b
grammar **as job (c) widens it** — scale alternatives longest-first, both word
boundaries, opacity suffix, and `prefix` covering side-qualified `border-` /
`divide-` — excluding `__tests__/` directories and
`*.test.ts(x)`. **Nothing here is carried over from a sibling.**

| Figure | Value |
| --- | --- |
| Non-test `.ts`/`.tsx` under `frontend/src` | **260** files, of which **113** carry a grammar match |
| Of those 260, `.ts` (non-`.tsx`) files | **103**, carrying **zero** matches between them |
| Matches outside `src/features/` | **24**, all of them APRAS-78's already-excepted pilot residue in `src/components/ui/{alert-modal,alert,badge}.tsx` |
| Palette occurrences in this child's six directories | **312** — 307 under APRAS-78's published grammar plus job (c)'s 5: infraction 189, and 123 across the other five |
| Files with a match in the six | **30** (of 86 non-test source files there) |
| Distinct classes | 91 |
| Six-digit hex literals in a class context | **0** |
| `dark:`-prefixed | **24** (7.7%), against **288** non-`dark:` — all five of job (c)'s are non-`dark:` |

Per directory, and per file:

| Directory | Files w/ matches | Occ. | Per file |
| --- | --- | --- | --- |
| `infraction-management` (`components/` + `pages/`) | 10 | **189** | InfractionsPage 38, InfractionRulesPage 37, NewInfractionModal 25, InfractionDetailsView 18, NextStepPanel 16, MyInfractionsPage 16, CycleCloseModal 13, InfractionStageTimeline 13, AttachmentUploader 10, ContestationForm 3 |
| `task-management/components` | 6 | **35** | TaskBoard 15, TaskFilterBar 10, DueDateBadge 4, TaskDashboard 3, HighlightedText 2, AuditTimeline 1 |
| `dashboard/components` | 1 | **28** | GeneralDashboardPage 28 |
| `user-administration` (`components/` + `pages/`) | 10 | **50** | TenantsAdminPage 15, TenantProfilePage 8, InviteAdministratorDialog 6, TenantBrandColors 6, SimulationBanner 5, TenantInvitationsPanel 4, Navbar 2, AdminUserDashboard 2, PermissionMatrix 1, ContactInfoDashboard 1 |
| `space-reservation-management/components` | 2 | **9** | SpaceBookingPage 8, ReservableSpacesPage 1 |
| `assembly-voting/components` | 1 | **1** | AssemblyMinutesView 1 |

**The board's "reported 10 files / 189 occurrences" for `infraction-management`
is right, and it spans two subdirectories** — `components/` (7 files, 116) and
`pages/` (3 files, 73). `user-administration` likewise spans `components/`
(6 files, 24) and `pages/` (4 files, 26). This matters for job (b): both are
reached only because the repo-wide walk is **recursive**, which the
per-directory allow-list entries never were.

## Pairing a `dark:` class with its base

The settled rule: same class-context span, same utility prefix, same
non-`dark:` variant chain, nearest preceding. Applied mechanically, **every one
of the 24 `dark:` occurrences has a base, and every one of those bases is a
class this child keeps**. There is therefore **no `dark:` deletion in this
child at all** — §1g's first half never fires, and its second half fires 24
times.

## The disposition of all 312

| Disposition | n |
| --- | --- |
| Light class migrated to a token | **167** |
| `dark:` sibling of a migrated class, deleted (§1g) | **0** |
| Left untouched and logged | **145** (121 non-`dark:`, 24 `dark:`) |
| **Total** | **312** |

Both halves close independently: non-`dark:` 288 = 167 + 121, and `dark:`
24 = 0 + 24.

Per directory, as `migrated / deleted / logged`: `infraction-management`
160 / 0 / 29; `user-administration` 6 / 0 / 44; `assembly-voting` 1 / 0 / 0;
`task-management` 0 / 0 / 35; `dashboard` 0 / 0 / 28;
`space-reservation-management` 0 / 0 / 9.

Per file, `migrated / logged` — **fifteen files change and fifteen do not**:

| Changed | m / l | Unchanged (logged only) | l |
| --- | --- | --- | --- |
| `InfractionRulesPage.tsx` | 34 / 3 | `GeneralDashboardPage.tsx` | 28 |
| `InfractionsPage.tsx` | 32 / 6 | `TaskBoard.tsx` | 15 |
| `NewInfractionModal.tsx` | 21 / 4 | `TaskFilterBar.tsx` | 10 |
| `InfractionDetailsView.tsx` | 17 / 1 | `SpaceBookingPage.tsx` | 8 |
| `NextStepPanel.tsx` | 15 / 1 | `TenantProfilePage.tsx` | 8 |
| `MyInfractionsPage.tsx` | 12 / 4 | `TenantBrandColors.tsx` | 6 |
| `CycleCloseModal.tsx` | 10 / 3 | `SimulationBanner.tsx` | 5 |
| `AttachmentUploader.tsx` | 8 / 2 | `DueDateBadge.tsx` | 4 |
| `InfractionStageTimeline.tsx` | 8 / 5 | `TenantInvitationsPanel.tsx` | 4 |
| `ContestationForm.tsx` | 3 / 0 | `TaskDashboard.tsx` | 3 |
| `TenantsAdminPage.tsx` | 2 / 13 | `HighlightedText.tsx` | 2 |
| `InviteAdministratorDialog.tsx` | 2 / 4 | `Navbar.tsx` | 2 |
| `AdminUserDashboard.tsx` | 1 / 1 | `AuditTimeline.tsx` | 1 |
| `PermissionMatrix.tsx` | 1 / 0 | `ContactInfoDashboard.tsx` | 1 |
| `AssemblyMinutesView.tsx` | 1 / 0 | `ReservableSpacesPage.tsx` | 1 |

The 145 occupy **126** distinct `(file, class)` pairs — 25 in
`infraction-management`, 35 in `user-administration`, 33 in `task-management`,
26 in `dashboard`, 7 in `space-reservation-management`, 0 in `assembly-voting`
— which is the number of exceptions entries this task appends. Job (c)'s five
classes are all **new** pairs: none of the five occurs anywhere else in
`TaskBoard.tsx`, so they add 5 occurrences **and** 5 pairs.

## The gap codes, each counted from its own membership

| Code | Occ. | Derivation, enumerated |
| --- | --- | --- |
| `GAP-NO-TOKEN` | **53** | non-`dark:` **38**: `text-amber-700` 8, `bg-amber-50` 5, `text-amber-800` 4, `bg-amber-100` 3, `text-amber-600` 2, `text-amber-900` 2, and one each of `bg-amber-500/10` (of 2; the other is a swatch), `border-amber-500/20`, `border-amber-200`, `bg-amber-50/50`, `bg-amber-400`, `text-amber-950`, `border-amber-950/30`, `bg-amber-400/40`, `hover:bg-amber-400/70` — **33 amber** — plus `bg-sky-100` 1, `text-sky-800` 1, `bg-yellow-200` 1, `bg-blue-50/50` 1, `bg-green-50/50` 1. `33+5 = 38`. Plus **12** `dark:`: `dark:text-amber-400` 4 (of 5; the fifth is a swatch), and one each of `dark:text-amber-300`, `dark:bg-amber-500/20`, `dark:bg-amber-900/20`, `dark:bg-sky-500/20`, `dark:text-sky-300`, `dark:bg-yellow-500/40`, `dark:bg-blue-900/20`, `dark:bg-green-900/20`. `38 + 12 = 50`, **plus job (c)'s 3** — `border-t-blue-400`, `border-t-amber-500`, `border-t-green-400`, all non-`dark:`, so non-`dark:` becomes **41** and the code total **53** |
| `GAP-TINT` | **46** | non-`dark:` **42**: emerald **28** — `bg-emerald-50` 6, `text-emerald-800` 6, `text-emerald-700` 5, `text-emerald-900` 4, `border-emerald-200` 3, `border-emerald-300` 2, `bg-emerald-100` 1, `text-emerald-600` 1 — red **9** (`bg-red-50` 4, `text-red-700` 4 of 5, `bg-red-50/50` 1) and slate **5** (`bg-slate-100` 2, `text-slate-500` 2, `bg-slate-50/50` 1). `28+9+5 = 42`. Plus **2** `dark:`: `dark:bg-slate-900/20` and `dark:bg-red-900/20`, the two `TaskBoard` column tints whose base is slate or red. `42 + 2 = 44`, **plus job (c)'s 2** — `border-t-slate-400` and `border-t-red-400`, both non-`dark:` and both families that have a token, so non-`dark:` becomes **44** and the code total **46** |
| `GAP-SWATCH` | **24** | `GeneralDashboardPage.tsx` lines 33–83, the eight per-module identity colours, three classes each: `text-{blue,emerald,amber,indigo,purple,orange,green,rose}-500` 8, `dark:text-{…}-400` 8, `bg-{…}-500/10` 8. §1h code 2 verbatim ("category swatches"); see "Two judgement calls" below |
| `GAP-OVERLAY` | **10** | `bg-black/40` 3 (`CycleCloseModal:52`, `NewInfractionModal:166`, `TenantProfilePage:417`), `bg-black/50` 3 (`TaskDashboard:342`, `AdminUserDashboard:292`, `ContactInfoDashboard:175`), `hover:bg-black/10` 2 (`TaskDashboard:307`, `TaskFilterBar:216`) and their 2 `dark:hover:bg-white/10` siblings |
| `GAP-OUT-OF-BUDGET` | **7** | `text-gray-700` 7, all of them: `InfractionDetailsView:61`, `InfractionStageTimeline:49`, `InfractionRulesPage:238`, `InfractionsPage:269`, `:346`, `MyInfractionsPage:57`, `:63`. No `dark:` siblings |
| `GAP-BORDER-100` | **5** | `border-gray-100` 5, all of them: `InfractionStageTimeline:31`, `InfractionRulesPage:225`, `:276`, `InfractionsPage:262`, `:337`. No `dark:` siblings |

`53 + 46 + 24 + 10 + 7 + 5 = 145`. **Zero `GAP-NO-SURFACE`, zero
`GAP-UNLISTED`.** Cross-check from the other direction, code by code, as
`non-dark: / dark:`: NO-TOKEN 41 / 12, TINT 44 / 2, SWATCH 16 / 8, OVERLAY
8 / 2, OUT-OF-BUDGET 7 / 0, BORDER-100 5 / 0. The two columns sum to
`41+44+16+8+7+5 = 121` and `12+2+8+2 = 24`, matching the disposition table's
two halves exactly. The implementer regenerates this partition mechanically
and must arrive at the same twelve numbers.

There is no `GAP-NO-SURFACE` because both `text-white` occurrences sit on a
migrating `bg-emerald-700` (§"Every status set"), and no `border-white`,
`text-black` or `bg-white/N` occurs.

## Two judgement calls, named rather than buried

**1. `GeneralDashboardPage`'s eight colours are `GAP-SWATCH`; `TaskBoard`'s
five are not.** Both are lookup sets of one colour per enum member, and §1h's
precedence makes the difference visible rather than arbitrary:

- The dashboard's eight encode **module identity** — Tasks, Finance,
  Occurrences and so on. That is "a data-encoding colour: … category swatches"
  in code 2's own words, and it *must not follow the brand*: a tenant whose
  brand is emerald would otherwise see the Finance tile and the Tasks tile
  collapse into one colour. This is why `text-indigo-500`,
  `dark:text-indigo-400` and `bg-indigo-500/10` at lines 54–55 (three
  occurrences) **do not migrate** even though indigo is the named brand
  family — code 2 precedes every other code, and the classes are data, not
  brand.
- `TaskBoard`'s five encode **task status** (PENDING / IN_PROGRESS / BLOCKED /
  COMPLETED / CANCELED). That is the operator's status ruling, so each takes
  its family's code: slate and red `GAP-TINT`, blue, green and amber
  `GAP-NO-TOKEN`. Same outcome — the class is left untouched — different
  recorded label, which is exactly what §1h says the codes are for.

**2. Two emerald buttons migrate while the emerald panels around them stay.**
`InviteAdministratorDialog:114` and `TenantsAdminPage:290` are `<button
onClick>` elements reading `rounded-md bg-emerald-700 px-3 py-2 text-xs
font-semibold text-white`, each sitting **inside** a kept success panel
(`border-emerald-200 bg-emerald-50`). §1f case 3's single test — is the element
interactive? — migrates them, exactly as APRAS-78's pilot migrated
`button.tsx`'s `success` variant while keeping `alert-modal.tsx:28–30`'s
success *config*. Both members have a §1e/§1f row (`bg-emerald-700` →
`bg-primary`; `text-white` over `bg-primary` → `text-primary-foreground`) and
the resulting pair holds **5.7588:1**, so §1j's two clauses are satisfied.

**The span check cannot see this and a reviewer must.** The button's classes
live in their own `className` span, so the mechanical split-span check returns
nothing; the judgement that a dark-emerald primary button on a light-emerald
tint is correct is a **review duty on this diff**. By contrast
`TenantsAdminPage:272` and `:299` are *also* `<button>`s and **do not**
migrate: their `border-emerald-300` has no row at any scale, so triple-as-a-unit
freezes them with their `text-emerald-800`.

## Every status set in these directories

The triple rule is binding tree-wide: a status variant's class set migrates as
a **unit or not at all**, every member must have a row in §1b–1e, and the
resulting pair must hold ≥ 4.5:1. A ternary's, a `switch`'s or a lookup map's
branches are **one set**. There are **17** sets here, holding **96** of the 145
kept occurrences.

| # | Set | Members | n | Code |
| --- | --- | --- | --- | --- |
| 1 | `AttachmentUploader:181` error tint | `bg-red-50`, `text-red-700` | 2 | TINT |
| 2 | `CycleCloseModal:104` error tint | `bg-red-50`, `text-red-700` | 2 | TINT |
| 3 | `NewInfractionModal:336` error tint | `bg-red-50`, `text-red-700` | 2 | TINT |
| 4 | `InfractionsPage:355` error tint | `bg-red-50`, `text-red-700` | 2 | TINT |
| 5 | `InfractionStageTimeline:57` overridden badge | `bg-amber-100`, `text-amber-800` | 2 | NO-TOKEN |
| 6 | `MyInfractionsPage:67` warning tint | `bg-amber-50`, `text-amber-800` | 2 | NO-TOKEN |
| 7 | `DueDateBadge:18,19` today/tomorrow map | `text-amber-700` ×2 + 2 `dark:` | 4 | NO-TOKEN |
| 8 | `TaskBoard:75–100` column map, 5 branches | `bg-{slate,blue,amber,green,red}-50/50` + 5 `dark:` + `border-t-{slate,blue,amber,green,red}-{400,400,500,400,400}` (job (c)) | 15 | TINT 6 / NO-TOKEN 9 |
| 9 | `TaskFilterBar:146` priority chip | `bg-amber-100`, `text-amber-800`, `dark:bg-amber-500/20`, `dark:text-amber-300` | 4 | NO-TOKEN |
| 10 | `TaskFilterBar:166` assignee chip | `bg-sky-100`, `text-sky-800`, `dark:bg-sky-500/20`, `dark:text-sky-300` | 4 | NO-TOKEN |
| 11 | `GeneralDashboardPage:33–83` module colour map, 8 branches | 24 classes | 24 | SWATCH |
| 12 | `GeneralDashboardPage:116` preview badge | `bg-amber-500/10`, `text-amber-700`, `dark:text-amber-400`, `border-amber-500/20` | 4 | NO-TOKEN |
| 13 | `SpaceBookingPage:16,18,22,24` `statusBadgeClass`, 4 palette branches | `bg-emerald-100`+`text-emerald-700`, `bg-amber-100`+`text-amber-700`, `bg-slate-100`+`text-slate-500` ×2 | 8 | TINT 6 / NO-TOKEN 2 |
| 14 | `InviteAdministratorDialog:99,101,104` success panel | `border-emerald-200`, `bg-emerald-50`, `text-emerald-900` ×2 | 4 | TINT |
| 15 | `TenantsAdminPage:257–299` success panel | `border-emerald-200`, `bg-emerald-50`, `text-emerald-900` ×2, `text-emerald-800` ×5, `border-emerald-300` ×2 | 11 | TINT |
| 16 | `TenantProfilePage:364` warning panel | `border-amber-200`, `bg-amber-50`, `text-amber-900` | 3 | NO-TOKEN |
| 17 | `TenantBrandColors:599` success panel | `border-emerald-200`, `bg-emerald-50`, `text-emerald-800` | 3 | TINT |

`2+2+2+2+2+2+4+15+4+4+24+4+8+4+11+3+3 = 96`. Set 13's `bg-destructive/10
text-destructive` REJECTED branch is **already tokens today** and matches no
grammar; the set is nonetheless frozen as a unit, and that branch is named here
so a reviewer does not read it as half a migration.

**The rowless member of each.** Sets 5–10, 12, 16 and the amber halves of 8 and
13 are blocked by `amber`, `sky`, `yellow`, `blue` or `green`, none of which has
a row at any scale. Sets 1–4 are red tint triples, which §1j makes `GAP-TINT`
by name. Sets 14, 15 and 17 are blocked by `bg-emerald-50` (no §1b row for its
role) and, in 15, additionally by `border-emerald-300`. Set 11 is the sole
`GAP-SWATCH`. Set 13's slate branches are neutral by design and stay with their
emerald and amber siblings — APRAS-83's set-3 precedent applied once more.

The remaining 49 kept occurrences are the 7 `GAP-OUT-OF-BUDGET`, the 5
`GAP-BORDER-100`, the 10 `GAP-OVERLAY` and **27 free-standing** classes
belonging to no set: `SimulationBanner`'s five amber, `TenantBrandColors:469`
and `:552`, `TenantProfilePage:225` and `:397`, `TenantInvitationsPanel:24` and
`:26` (4), `TenantsAdminPage:53` (2), `Navbar:153` (2),
`ReservableSpacesPage:243`, `AuditTimeline:111`, `HighlightedText:62` (2),
`InfractionStageTimeline:99`, `NewInfractionModal:260` and `NextStepPanel:62`.
`5+3+4+4+2+2+1+1+2+1+1+1 = 27`, and `96+7+5+10+27 = 145`.

**The proof there is no eighteenth set.** A split span is a class-context span
— as the guard's exported `classContexts()` computes it, not a line — holding
both a migrated occurrence and a kept `GAP-TINT` occurrence. Run mechanically
over all 312 occurrences grouped by `(file, span)`, that check returns
**exactly zero** spans. Job (c)'s five sit in a `headerColorClass` **object
property**, not in a `className` / `cn` / `cva` argument, so `classContexts()`
returns no span containing them and they cannot create a mixed span; the
palette grammar still finds them because it is applied to the whole source and
only the hex pattern is span-restricted. This is the first child in the split to return zero
rather than one. Three spans mix a migrated occurrence with a kept occurrence
under a *different* code and are expected, not counted:
`InfractionsPage:262` (`border-gray-100` beside a migrating `hover:bg-gray-50`),
`InfractionsPage:269` and `MyInfractionsPage:57` (`text-gray-700` beside a
migrating `bg-gray-100`). The implementer must re-run the check and get the
same zero and the same three.

## Behaviour — the substitutions

Every substitution is a table row applied verbatim.

- `text-gray-500` ×64 → **`text-muted-foreground`**.
- `border-gray-200` ×41 → **`border-border`** — §1c's row, which governs even
  where the element is a raw `<input>`/`<select>`/`<textarea>` border.
- `text-gray-900` ×23 → **`text-foreground`**.
- `bg-white` ×18 → **`bg-card`** — §1f case 1, settled below. Zero take
  `bg-background`, zero take `bg-popover`.
- `text-indigo-600` ×5 → **`text-primary-text`** — §1k, settled below.
- `bg-gray-100` ×3 → `bg-muted` (resting chips at `InfractionRulesPage:245`,
  `InfractionsPage:269`, `MyInfractionsPage:57`).
- `text-gray-400` ×2 → `text-muted-foreground`; `text-gray-600` ×2 →
  `text-muted-foreground`; `border-gray-300` ×2 → `border-input`
  (`PermissionMatrix:145`, `AdminUserDashboard:353`, both checkbox borders);
  `bg-emerald-700` ×2 → `bg-primary`; `text-white` ×2 →
  `text-primary-foreground`.
- `bg-gray-50` ×1 → `bg-muted` (`NewInfractionModal:207`, a resting read-only
  field); `hover:bg-gray-50` ×1 → `hover:bg-accent` (`InfractionsPage:262`, an
  interaction fill) — §1f case 2, the only two neutral-fill sites where the
  choice arises.
- `text-red-700` ×1 → **`text-destructive`** (`NextStepPanel:82`, a
  free-standing error message on a `bg-white` card with no red surface — §1j's
  "free-standing red takes the §1e row"). The other four `text-red-700` are
  inside sets 1–4 and stay.

`64 + 41 + 23 + 18 + 5 + 3 + 2 + 2 + 2 + 2 + 2 + 1 + 1 + 1 = 167`, reading the
bullets in order, with no occurrence counted twice.

**Zero `dark:` siblings are deleted**, and **zero opacity modifiers are created
or carried over on a migrated class**: every migrated class here is
opacity-free, and every `/N` in the six directories belongs to a kept class.
**No `text-primary/N` and no `text-primary-text/N` is produced**, so this child
creates no APRAS-90 site.

## §1k applied — which brand classes are characters

§1k asks one question per call site, from the JSX, with no measurement: *does
this element paint glyphs of text?* Traced at every site, not assumed.

**Characters — take `*-primary-text`, floor 4.5:1 (5 occurrences).** All five
are the anchor or router-link that is the app's "open the source / open the
attachment" affordance, each with visible text content and `underline`:

| Site | Element | Surface | After |
| --- | --- | --- | --- |
| `AttachmentUploader:208` | `<a href={url}>` rendering the URL | hosting card/modal → `--card` | **5.2096** |
| `InfractionDetailsView:66` | `<Link to=…>` "source occurrence" | `bg-white` card → `--card` | **5.2096** |
| `InfractionDetailsView:90` | `<a href={url}>` attachment | `bg-white` card → `--card` | **5.2096** |
| `InfractionStageTimeline:89` | `<a href={url}>` attachment | `bg-white` card → `--card` | **5.2096** |
| `NewInfractionModal:179` | `<Link to=…>` "source occurrence" | `bg-white` modal → `--card` | **5.2096** |

`AttachmentUploader` is a leaf rendered by `NewInfractionModal:326` (inside its
`bg-white` modal) and by `ContestationForm:59`, itself rendered by
`MyInfractionsPage:78` inside that page's `bg-white` card. Both hosts migrate
to `bg-card`, so the surface is `--card` on every path.

**Graphical — keeps `*-primary`, floor 3:1 (0 occurrences).** This child
produces **no** `text-primary` and no non-`text-` brand utility at all: the
only other indigo in the six directories is `GeneralDashboardPage`'s swatch
pair, which does not migrate. The child is therefore the split's purest
exercise of §1k's *character* branch and its cleanest confirmation of
APRAS-88's amendment — **`text-primary` must not appear anywhere in the diff.**

## The context-dependent cases, settled at the real call sites

**The verification tests cannot detect a wrong choice in any of these.** They
are a **human review duty on this diff**.

**§1f case 1 — `bg-white` ×18 all take `bg-card`.** Seventeen are
`infraction-management` panels (`rounded-xl border border-gray-200 bg-white
p-4|p-6`) or modal bodies (`CycleCloseModal:55`, `NewInfractionModal:169`); the
eighteenth is `AssemblyMinutesView:78`'s embedded minutes viewer
(`w-full h-[60vh] rounded-md border border-border/60 bg-white`), a surface that
sits **on** the page. None of the six trees' page roots carries `bg-white` —
they are bare `<div className="space-y-4|space-y-6">` shells under `App.tsx`'s
`min-h-screen bg-background` — so **zero** take `bg-background`, and no site
has popover semantics, so **zero** take `bg-popover`.

**Raw form controls take `bg-card`'s sibling ruling, and none arises.** There
is no `bg-white` on an `<input>`, `<select>` or `<textarea>` in these thirty
files, so APRAS-80's accepted `bg-card`-for-raw-fills precedent is **not
exercised here**. It is named so a reviewer knows its absence is a measurement,
not an oversight; the divergence from `components/ui/`'s `bg-background` stays
**recorded, not resolved**.

**§1f case 2 — `bg-muted` versus `bg-accent`.** Four resting fills take
`bg-muted` (`NewInfractionModal:207`, `InfractionRulesPage:245`,
`InfractionsPage:269`, `MyInfractionsPage:57`); one interaction fill takes
`hover:bg-accent` (`InfractionsPage:262`, the infraction row button). No other
neutral fill at 50/100/200 occurs.

**§1f case 3 — emerald 500–700.** The band holds **3** occurrences here, all
`bg-emerald-700`: two migrate (the interactive success buttons above) and one
— `AuditTimeline:111`'s `text-emerald-600` "new value" in a read-only audit
diff — is not in the band's fill role but is a non-interactive status glyph
text and stays `GAP-TINT`.

**No interaction distinction is lost.** No resting/hover pair in these six
directories maps both halves to the same token, so unlike APRAS-83 this child
leaves no redundant class behind and creates no §1i-blocked repair.

## Contrast, re-derived by importing `frontend/src/lib/contrast.ts`

Measured by importing `contrastRatio`, `parseOklch` and `hexToOklch` from
`frontend/src/lib/contrast.ts` — **never reimplemented** — with token values
read from `src/index.css` and palette values from
`node_modules/tailwindcss/theme.css` (Tailwind 4's OKLCH palette, whose
lightness is a percentage and must be divided by 100 before `parseOklch` sees
it). The measurement reproduces APRAS-78's, APRAS-80's, APRAS-83's and
APRAS-88's published figures to the digit (`--primary-foreground` on
`--primary` 5.7588, `--muted-foreground` on `--card` 5.2249 and on `--muted`
4.6684, `--primary-text` on `--card` 5.2096, `--foreground` on `--card`
19.8801, `--destructive` on `--card` 4.8073, `text-gray-700` on `--muted`
9.2081), which is the check that it is the same measurement.

| Pair | Background | Today | After |
| --- | --- | --- | --- |
| Headings `text-gray-900` → `text-foreground` | `--card` | 17.7467 | **19.8801** |
| `text-gray-900` on `bg-gray-50` → `text-foreground` on `bg-muted` | `--muted` | 17.0010 | **17.7626** |
| Secondary text `text-gray-500` ×64 → `text-muted-foreground` | `--card` | 4.8357 | **5.2249** |
| `text-gray-600` ×2 → `text-muted-foreground` | `--card` | 7.5608 | **5.2249** |
| `text-gray-600` on `bg-gray-100` → on `bg-muted` | `--muted` | 6.8711 | **4.6684** |
| **`text-gray-400` ×2 → `text-muted-foreground`** | `--card` | **2.6023** | **5.2249** — repairs an AA failure at 2 sites |
| **Links `text-indigo-600` ×5 → `text-primary-text`** | `--card` | 6.4414 | **5.2096** |
| Success buttons `text-white` on `bg-emerald-700` → `text-primary-foreground` on `bg-primary` | `--primary` | 5.4381 | **5.7588** |
| Error message `text-red-700` → `text-destructive` | `--card` | 6.5373 | **4.8073** |

**No full-opacity text pair this task produces falls below 4.5:1.** The
tightest is `--muted-foreground` on `--muted` at 4.6684; the tightest pair the
task *creates* is `--destructive` on `--card` at 4.8073.

### Kept pairs whose surface moves, measured so nobody attributes them later

A kept foreground can sit on a migrated background. There are exactly two such
pairs, both `text-gray-700` on a chip whose `bg-gray-100` becomes `bg-muted`
(`InfractionsPage:269`, `MyInfractionsPage:57`): **9.3658 → 9.2081**, far above
AA. Every other kept class sits on a surface this task does not touch. **This
migration therefore converts no passing pair into a failing one, text or
graphical, and this child names no follow-up site.**

### Declared sub-AA or unmeasurable, none of them introduced by this task

All are pre-existing, all kept verbatim, all inside a status set:
`text-slate-500` on `bg-slate-100` **4.3481** (`SpaceBookingPage:22,24`, set
13), `text-amber-600` on white **3.1884** (`Navbar:153`,
`ReservableSpacesPage:243`), `text-emerald-600` on white **3.7194**
(`AuditTimeline:111`), `text-amber-700` on `bg-amber-100` 4.5273 (set 13),
`text-amber-700` on `bg-amber-50` 4.8611, `text-emerald-700` on `bg-emerald-50`
5.1582 and on `bg-emerald-100` 4.7907, `text-emerald-800` on `bg-emerald-50`
7.2679, `text-emerald-900` on `bg-emerald-50` 9.1968, `text-red-700` on
`bg-red-50` 5.9842, `text-amber-950` on `bg-amber-400` 8.7247, `text-sky-800`
on `bg-sky-100` 6.5925, `text-amber-800` on `bg-amber-50` 6.8748 and on
`bg-amber-100` 6.4027, `text-amber-900` on `bg-amber-50` 8.7680.
**No APRAS-90 site exists in these six directories**: this child produces no
`text-primary-text/N` and no `text-primary/N`.

---

# Job (b) — inverting the guard

## What changes, and what is deliberately left alone

Re-read against the file as it stands at `a8fc8ab`: 979 lines, **50 tests in
925 ms**, `MIGRATED_DIRECTORIES` holding three entries, `pinnedFiles()`
returning **26** files, the exceptions file holding **254** entries.

**1. `MIGRATED_DIRECTORIES` is retired and replaced.** It becomes

```
export const SCANNED_ROOTS: readonly string[] = ["src/**"];
```

Everything the allow-list needed is already there: `pinnedFiles()` honours the
`/**` recursion marker, `collect()` skips `__tests__` directories, `isSource()`
skips `*.test.ts(x)`, and every exceptions entry is already `src/`-relative —
which is what APRAS-78 §3d designed for and what
`it("uses src/-relative paths, so APRAS-85's inversion is a one-line change")`
has been asserting for seven children.

**2. `pinnedFiles()` and `PINNED` keep their exported names and meanings.**
Only `pinnedFiles()`'s **default argument** changes, from `MIGRATED_DIRECTORIES`
to `SCANNED_ROOTS`. This is not cosmetic conservatism: every sibling's
ledger-arithmetic block filters `PINNED` by a directory prefix, and several
call `pinnedFiles([entry])` directly. Keeping both names is what lets those
blocks stand **byte-for-byte unedited**.

**3. `describe("MIGRATED_DIRECTORIES")` is retired**, not rewritten in place,
and replaced by an appended `describe("SCANNED_ROOTS — the repo-wide deny")`.
Its three tests asserted *membership of an allow-list* and *that PINNED
contains nothing outside the pinned roots* — precisely the properties the
inversion abolishes. The replacement asserts the opposite and stronger
properties:

- `SCANNED_ROOTS` is exactly `["src/**"]`, and the module exports no
  `MIGRATED_DIRECTORIES` binding;
- `pinnedFiles()` equals an independently computed recursive walk of
  `frontend/src` for non-test `.ts`/`.tsx`, **260 files** at the time of
  writing, and the assertion is written as the equality, not as the literal;
- it **contains** at least one file no child ever migrated and that carries no
  palette class — `src/App.tsx` and `src/lib/contrast.ts` — and at least one
  file from a **nested** directory the old allow-list could not reach
  (`src/features/infraction-management/pages/InfractionsPage.tsx`);
- it contains no `__tests__/` path and no `*.test.ts(x)`.

**4. All eight per-child ledger-arithmetic `describe` blocks are KEPT,
unedited.** The decision, stated rather than implied, because these assertions
are the audit trail of the whole migration and retiring them silently would be
the one thing nobody could review afterwards:

| Block | Disposition | Why |
| --- | --- | --- |
| `describe("the pilot's own ledger arithmetic")` (APRAS-78) | **kept, unedited** | scoped by `startsWith("src/components/ui/")` over `LEDGER` and `PINNED`; both stay supersets |
| `describe("APRAS-79's ledger arithmetic")` | **kept, unedited** | same shape, scoped to `lot-management/components/` |
| `describe("APRAS-80's ledger arithmetic")` | **kept, unedited** | same, `visitor-management/components/` |
| APRAS-81's, 82's, 83's, 84's blocks | **kept, unedited** | same, their own directories; they land before this child and this child must not touch them |
| — | **appended** | `describe("APRAS-85's ledger arithmetic")`, same shape, scoped to the six directories |

This is safe for a mechanical reason that must be verified rather than
assumed: **none of the fourteen already-migrated directories contains a
subdirectory** (measured: zero non-`__tests__` subdirectories under each), so
the recursive walk returns exactly the same file set for every existing
`startsWith(DIRECTORY)` filter as the non-recursive walk did. Every
`toHaveLength` in those blocks therefore holds unchanged. **If a sibling has
since added a subdirectory, that block's count would move, and the implementer
must report it rather than edit the block.**

**5. `violations()` gains two purely mechanical optimisations, no assertion
changed.** The repo-wide input makes the existing shape quadratic where it was
merely large:

- the scan memo is **hoisted to module scope**, keyed on
  `file + "\0" + source` — a pure function of its arguments, so every
  mutated-argument test still bites;
- `files.find((candidate) => candidate.file === entry.file)` inside the
  exception loop is replaced by a `Map<string, string>` built once per call,
  turning `O(exceptions × files)` into `O(exceptions + files)`.

The arithmetic that forces this: `it("fails when any single exception is
removed")` calls `violations()` once per exception. Today that is 254 calls ×
26 files and takes ~880 ms. **(projected)** after all eight children it is 882
calls × 260 files, which is 3.5× the calls and 10× the per-call work — roughly
**30 s** unchanged, against a per-test budget of 2 s. With both optimisations
the per-call cost falls to `O(exceptions + files + matches)` ≈ 2,300 operations
and the whole loop to ≈ 2 M, comfortably inside budget. **The decidable
requirement is that every individual test in the file finishes under 2 s and
the file as a whole under 10 s**, reported by
`npx vitest run … --reporter=verbose`.

**6. Nothing else in the guard changes except §3b's `PREFIX`, which job (c)
widens.** `GAP_CODES`,
`classContexts()`, `matchesIn()`, `readLedger()`, the exceptions file's four
keys and its four rules, and `describe("the §3b grammar")`,
`describe("the guard")` and `describe("the exceptions file")` are untouched.
The new matcher cases the board asks for are added in a **new appended
`describe("the closed guard")`**, and job (c)'s widened-grammar cases in a
**new appended `describe("the widened prefix")`** — neither by editing
APRAS-78's `describe("the §3b grammar")` block, whose fourteen existing
match / no-match cases were re-run against the widened production and all
still hold (`border-2` in particular still does not match).

## The exceptions file after the inversion

Unchanged in path, shape and rules. What changes is its **reach**: the
ledger→exception direction of rule 4 currently begins
`if (!pinned.has(file)) continue;`, which silently skips every ledger row in a
not-yet-migrated directory. Once `PINNED` is every file under `src`, that
`continue` never fires for a `src/` row, and **rule 4 becomes total without a
line of new logic**. The new `describe` asserts this directly: the number of
ledger rows whose `file` resolves under `src/` equals the number that have a
matching exceptions entry, and the skipped count is **0**.

## The two known no-token gaps, repo-wide

`text-slate-700` / `text-gray-700` (`GAP-OUT-OF-BUDGET`, ΔE 17.93 / 17.81) and
`border-slate-100` / `border-gray-100` (`GAP-BORDER-100`, ΔE 4.95 / 4.83) are
left untouched by every child, this one included. Measured now over all 260
files: `text-gray-700` **73**, `text-slate-700` **69**, `border-slate-100`
**41**, `border-gray-100` **12** — **195** bare occurrences, plus one `dark:`
variant of the four. Because every child leaves them alone and §1i forbids
deleting a class, this figure is a **measurement that survives 81–84**, and the
closed guard requires each of the 195 to carry both a ledger row and an
exceptions entry. It does **not** require a particular gap code for them:
§1h's precedence puts an occurrence of one of these four classes under
`GAP-SWATCH` or `GAP-TINT` wherever it sits inside a swatch or a status set,
and sibling specs already do exactly that in a handful of places.

---

# Job (c) — widening §3b's `prefix`, the one amendment this child may make

## The amendment, stated as a diff of the published text

The operator authorised this, and only this, and only here. **No mapping row,
no gap code and no token changes.** Two pieces of
`docs/frontend/theme-token-mapping.md` §3b change and nothing else does.

**1. The `prefix` production.** Quoted out of the file at
`docs/frontend/theme-token-mapping.md:632-633`, the production reads **today**,
verbatim, across two lines:

```
prefix   = (?:bg|text|border|ring|outline|divide|placeholder|caret|accent|
              decoration|shadow|fill|stroke|from|via|to)
```

That is an alternation of **sixteen** keywords, in this order: `bg`, `text`,
`border`, `ring`, `outline`, `divide`, `placeholder`, `caret`, `accent`,
`decoration`, `shadow`, `fill`, `stroke`, `from`, `via`, `to`. The guard's
`PREFIX` constant at
`frontend/src/__tests__/themeTokenMigration.test.ts:55` carries the same
sixteen on one line.

It becomes:

```
prefix   = (?:bg|text|border(?:-[trblxyse])?|ring|outline|
              divide(?:-[trblxyse])?|placeholder|caret|accent|
              decoration|shadow|fill|stroke|from|via|to)
```

The two blocks differ in **exactly** two ways and in no other: `border` gains
the suffix `(?:-[trblxyse])?` and `divide` gains the same suffix. The
alternation set is unchanged — the same sixteen keywords, in the same order,
none added, **none removed**; `accent` in particular is present before and
after, and the amendment is not licensed to drop it or any other alternative.
Only the line wrapping moves, to keep the block inside the document's width.
The guard's `PREFIX` constant is edited to the same production, so the document
and the code stay one grammar; the implementer edits the existing line in place
rather than retyping the production from this spec.

**2. The prose that states the grammar's coverage.** §3b's "Two details are
load-bearing" list gains a **third** item recording that the side qualifier is
optional and applies to `border` and `divide` **only** — `bg-t-slate-400` and
`ring-t-blue-500` are not Tailwind classes and must not match — that the
qualifier is exactly one letter, so `border-tr-slate-400` does not match, and
that the amendment was made by APRAS-85 under an operator authorisation
recorded on that task. The same item records that §1j's appendix was generated
with the **pre-amendment** grammar and is therefore 5 occurrences short of the
widened one, the five being named below; §1j itself is **not** edited, because
it publishes APRAS-78's baseline and rewriting a baseline is worse than
annotating it.

Everything else in §3b — `variants`, `family`, `scale`, `opacity`, the
`palette` assembly, the boundary lookarounds, the hex pattern, §3c and §3d —
is byte-unchanged.

## What the widened grammar catches that the old one missed — measured

Re-scanned at this HEAD over every non-test `.ts`/`.tsx` under `frontend/src`,
old production against new, comparing match sets by `(offset, text)`:
**exactly five** occurrences are newly caught, and they are all in one file.

| File | Line | Class | Status branch | Code |
| --- | --- | --- | --- | --- |
| `task-management/components/TaskBoard.tsx` | 76 | `border-t-slate-400` | `PENDING` | `GAP-TINT` |
| ″ | 82 | `border-t-blue-400` | `IN_PROGRESS` | `GAP-NO-TOKEN` |
| ″ | 88 | `border-t-amber-500` | `BLOCKED` | `GAP-NO-TOKEN` |
| ″ | 94 | `border-t-green-400` | `COMPLETED` | `GAP-NO-TOKEN` |
| ″ | 100 | `border-t-red-400` | `CANCELED` | `GAP-TINT` |

**Zero `divide-` side-qualified occurrences exist**, and zero `border-x-`,
`border-y-`, `border-b-`, `border-l-`, `border-r-`, `border-s-` and
`border-e-` — the whole tree, not only the six directories. The board's
expectation of five is confirmed exactly.

**The codes follow §1h's precedence, not the stripe's role.** Blue, amber and
green have no token at any scale, so code 3 catches them first; slate and red
have tokens deliberately withheld from a status colour, so code 4 catches
those two. This is the same split set 8's tints already carry, which is why
set 8 remains **one** set of fifteen rather than becoming two.

## Why the five are kept, not migrated

They are the five branches of `TaskBoard`'s column map — one colour per
`TaskStatus` member — so §1h's status-set unit rule governs them exactly as it
governs the `bg-*-50/50` tints in the same object literal. A set migrates as a
unit or not at all, three of the five families have no row at any scale, and
the operator's status-colour ruling forbids binding a status to the brand.
**Job (c) makes them visible to the guard; it does not make them migratable.**
What changes is bookkeeping: five occurrences that needed no ledger row and no
exceptions entry before now need both.

## Over-reach — what the widened production must still refuse

The widening is a real risk of catching non-classes, so the control test pins
both directions. Verified against the widened production while writing this
spec: `border-t-slate-400`, `divide-y-gray-100`, `border-x-slate-200`,
`border-s-red-500`, `border-e-white` and `dark:hover:border-b-amber-500/40`
each match **whole**; and `bg-t-slate-400`, `text-x-gray-500`,
`ring-t-blue-500` (side qualifiers on prefixes that never take one),
`border-tr-slate-400` (a two-letter qualifier), `border-t-2`,
`divide-y-reverse`, `border-collapse`, `border-t-slate-4000`,
`border-t-mauve-400`, `xborder-t-red-500` and `order-t-red-500` each match
**not at all**. The last two are the boundary lookarounds still doing their
job after the widening, which is the specific thing a widened alternation can
break.

**And the alternation set itself is pinned, not only its edges.** A widening
written as a rewritten alternation can silently *lose* an alternative, and
neither the newly-caught count nor the over-reach list above would notice: an
alternative absent from both productions is absent from their set difference.
So the control test enumerates the sixteen prefixes by name and asserts each
still matches a representative class whole — `bg-slate-800`, `text-gray-500`,
`border-slate-100`, `ring-blue-500`, `outline-gray-300`, `divide-gray-200`,
`placeholder-gray-400`, `caret-slate-500`, **`accent-indigo-600`**,
`decoration-sky-500`, `shadow-slate-900`, `fill-emerald-600`,
`stroke-rose-500`, `from-blue-500`, `via-purple-500`, `to-pink-500` — and the
re-scan compares the two match sets in **both** directions, asserting the
old-only set is empty as well as measuring the widened-only set at five.
`accent-indigo-600` earns its emphasis: the tree's one `accent` palette
occurrence (`media-management/components/AvatarCropEditor.tsx:81`) is migrated
away by APRAS-84 before this child runs, so a dropped `accent` alternative
would move no count anywhere.

## What this proves, and what it misses

**Proved.** Every substitution is a §1b–1e row, and `themeTokenCompile.test.ts`
already asserts each row's ΔL/ΔE from the compiled stylesheet to ±0.1. After
the inversion the guard certifies something no earlier child could: that
**every** grammar match anywhere under `frontend/src` is either gone or present
in **both** the ledger and the exceptions file, and that a palette class
reintroduced into a file **no child ever migrated** fails CI.

**Not proved, stated plainly.**

- No Playwright, no Storybook, no Chromatic, no Percy, and jsdom does not run
  the Tailwind pipeline: **no pixel and no computed-style proof**. Compiling
  Tailwind over a fixture proves the table is truthful and that no unlisted
  substitution slipped in; it does **not** prove the right row was chosen at
  the right call site.
- **The three §1f cases and every §1k verdict are invisible to every test
  here.** `bg-card` vs `bg-background`, and `bg-muted` vs `bg-accent`, are
  byte-identical in `:root`; `text-primary` vs `text-primary-text` is two legal
  classes. A **review duty on this diff**, and the sites to start from are the
  two migrating emerald buttons inside kept emerald panels, the five links
  taking `text-primary-text`, `AssemblyMinutesView:78`'s viewer taking
  `bg-card`, and `InfractionsPage:262`'s `hover:bg-accent`.
- **The grammar's one measured blind spot is closed by job (c), so the claim
  needs no qualifier.** `border-t-*`, `border-x-*`, `divide-y-*` and every
  other *side-qualified* border or divide utility used to sit outside §3b's
  `prefix-family-scale` production. After job (c) they are inside it, the five
  occurrences that existed are ledgered and excepted, and the claim this child
  makes is unqualified: *any new hard-coded palette class anywhere in the
  frontend fails CI by default.* What remains outside the grammar is named
  rather than hidden: arbitrary values (`bg-[#1e293b]` is caught by the hex
  pattern only inside a class context, and `bg-[oklch(...)]` is caught by
  neither), CSS-in-JS and inline `style` props, and palette classes assembled
  at runtime from fragments.
- The rendering *does* move where the table says it moves: the 2 `text-gray-400`
  sites darken by ~17 L points, the 5 links shift from indigo hue 277 to
  emerald hue 160, `text-gray-600` lightens at 2 sites, and the 2 success
  buttons go from white-on-emerald-700 to dark-on-`--primary`.
- **The guard cannot enforce per-site completeness**, because the exceptions
  file carries no line number. Only one class in this child is both migrated
  and kept, and never inside one file: `text-red-700` migrates at
  `NextStepPanel.tsx:82` and is kept in four *other* files, so no single file
  excuses a class it also migrates, and the per-file exception sets are
  therefore exact. The disposition table (167 / 0 / 145 with the
  per-file split), the seventeen-set inventory and the §1k site table are what
  a reviewer must check the diff against.

## Files touched

- The **fifteen** changed `.tsx` files listed in the disposition table.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — `SCANNED_ROOTS`
  replacing `MIGRATED_DIRECTORIES`, `pinnedFiles()`'s default argument, the two
  `violations()` optimisations, the `PREFIX` constant widened per job (c),
  `describe("MIGRATED_DIRECTORIES")` retired, and
  three appended blocks: `describe("SCANNED_ROOTS — the repo-wide deny")`,
  `describe("the widened prefix")` and
  `describe("APRAS-85's ledger arithmetic")`. No other child's block edited,
  and APRAS-78's `describe("the §3b grammar")` block unedited.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — **126** new
  entries, `src/`-relative, `task` `APRAS-85`.
- `docs/frontend/unmapped-colours.md` — **145** appended rows, one per kept
  occurrence, sorted by file then line, plus a closing `APRAS-85 total`
  paragraph in the shape APRAS-78/79/80 use. Nothing already in the file is
  rewritten.
- `frontend/src/features/__tests__/remainingFeaturesContrast.test.ts` — new.
- `frontend/src/components/__tests__/TenantBrandReach.test.tsx` — extended with
  `InfractionStageTimeline` and `NextStepPanel`, both props-only.
- `docs/frontend/theme-token-mapping.md` — **job (c)'s amendment, and nothing
  else**: the `prefix` line of §3b's grammar block, plus the prose in §3b that
  states the grammar's coverage. No mapping row, no gap code, no token, no
  other section.
- `docs/tasks/APRAS-85-spec.md` — this file.

`frontend/src/index.css` is **not** touched, and every section of
`docs/frontend/theme-token-mapping.md` other than §3b is byte-unchanged.

## Test criteria

1. `npx vitest run src/__tests__/themeTokenMigration.test.ts` green with the
   repo-wide deny: zero unexcused grammar matches across all 260 files, no
   stale exception, no unknown code, ledger parity total in both directions,
   every preceding child's block passing untouched, and this child's block's
   145.
2. The new contrast test asserts, by **importing** `contrastRatio`,
   `parseOklch` and `hexToOklch` from `src/lib/contrast.ts`, that every
   foreground/background pair this task changes holds ≥
   `MINIMUM_CONTRAST_RATIO`, and that every pair it leaves below 4.5 appears in
   an explicit in-file list carrying its measured before/after ratio. Ratios to
   ±0.001 against the tables above, each against its declared background. Token
   values from `src/index.css`, palette values from
   `node_modules/tailwindcss/theme.css`; no colour literal hard-coded.
3. The **62** existing suites under
   `src/features/{infraction-management,user-administration,dashboard}/__tests__/`
   — **594** tests — pass **unmodified**. Measured now: none of them asserts on
   a class name, so none proves a colour.
4. `npx tsc -b` clean.
5. `npx vitest run --coverage` meets exactly **80 lines / 78 functions / 76
   branches / 80 statements**.
6. `npx eslint` diff-scoped. Re-measured now: the repository carries **375
   errors + 2 warnings across 64 files**, and **the thirty files in scope carry
   zero errors and zero warnings**. (The six trees do hold 6 errors across 4
   files — `AuthContext.tsx` 2, `ResetPasswordPage.tsx` 2,
   `SimulationContext.tsx` 1, `ForgotPasswordPage.tsx` 1 — none of which this
   task touches, because none carries a palette class.)
7. `git diff --exit-code frontend/src/index.css` succeeds;
   `docs/frontend/theme-token-mapping.md`'s diff is confined to §3b; no backend file,
   no Alembic revision, no route-registry entry in the diff; the `.dark` block
   stays unapplied.

## Out of scope

Adding `--success` / `--warning` / `--info` tokens; migrating any `amber`,
`sky`, `yellow`, `blue`, `green`, `purple`, `orange` or `rose` occurrence —
**including the five job (c) newly reveals, which are kept and ledgered, not
migrated**; widening §3b's `family`, `scale`, `variants` or `opacity`
productions, or teaching the guard arbitrary values, inline styles or
runtime-assembled classes; APRAS-90's sub-AA
repair tree; enabling the `.dark` block; visual-regression or computed-style
infrastructure; removing the now-duplicate `success` button variant; any
amendment to APRAS-78's mapping table rows, gap codes, tokens or ledger rules,
or to any part of §3b other than `prefix`; and any
backend, migration or route-registry change.

## The operator question, asked and answered

**Asked:** §3b's grammar does not match side-qualified border utilities
(`border-t-slate-400` and friends), so "any new hard-coded palette class fails
CI" was only true of classes matching §3b. Authorise a follow-up task to widen
`prefix` and re-scan, or accept the blind spot as permanent?

**Answered — option B: widen the grammar inside APRAS-85 itself**, because the
closer's promise should be true without a loose end. That answer is job (c),
and it is the sole authorisation any child of APRAS-77 has to amend APRAS-78's
artefacts. It extends to the `prefix` production and the §3b prose that states
the grammar's coverage, and to nothing else.

## The working tree the implementer will find

Another task's uncommitted work (APRAS-75) sits in the tree today:
`frontend/src/App.tsx`, the i18n locale files, `frontend/src/features/public-site/**`
and `docs/tasks/APRAS-75-*`. **It is out of bounds for this child** — do not
stage it, do not migrate it, do not edit it.

It is not, however, invisible to a repo-wide deny. Measured now,
`frontend/src/features/public-site/pages/LandingPage.tsx` carries **8** grammar
matches — `bg-blue-100`, `text-blue-700`, `bg-red-100`, `text-red-700`,
`bg-green-100`, `text-green-700`, `bg-orange-100`, `text-orange-700`, one
occurrence each — and `frontend/src/features/public-site/` contains no other
file with a match. So:

- **If APRAS-75 has not landed when this child runs**, that file is not in the
  tree and nothing is owed.
- **If APRAS-75 has landed**, the inverted guard will fail on its occurrences,
  and **APRAS-75 owes them, not this child**: whichever of the two lands
  second adds the ledger rows and exceptions entries for that file, under the
  code §1h's precedence assigns (all four families — blue, red, green, orange —
  are status/identity tints; blue, green and orange have no token, so
  `GAP-NO-TOKEN`, and red has one withheld, so `GAP-TINT`), and reports the
  count it added rather than folding it into any figure this spec publishes.

**Every count in this spec is measured over the six directories this child
owns and is unaffected either way.** The repo-wide assertions are written as
equalities the test computes, not as literals, precisely so that a neighbouring
file arriving or not arriving cannot falsify them. The implementer reports the
`public-site` disposition in its own words; it does not silently patch a
number.

## Expected Results

- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts` passes with the guard inverted to a repo-wide deny: the module exports `SCANNED_ROOTS` equal to exactly `["src/**"]`, exports **no** binding named `MIGRATED_DIRECTORIES` and contains no `describe("MIGRATED_DIRECTORIES")`, `pinnedFiles()` returns every non-test `.ts`/`.tsx` file under `frontend/src` (260 at `a8fc8ab`, asserted as an equality against an independently computed recursive walk and not as a literal), and `violations(PINNED, EXCEPTIONS, LEDGER)` returns `[]`.
- [ ] `pinnedFiles()` contains `src/App.tsx` and `src/lib/contrast.ts` — files no child ever migrated, which carry zero grammar matches — and `src/features/infraction-management/pages/InfractionsPage.tsx`, a file in a nested subdirectory that no per-directory allow-list entry ever reached; and it contains no path whose segments include `__tests__` and no path matching `*.test.ts` or `*.test.tsx`.
- [ ] The guard's `§3b` prefix production is widened to cover side-qualified border and divide utilities, and a test asserts both directions of the widening on literal inputs. **Matched whole** (the match equals the whole input, not a prefix of it): `border-t-slate-400`, `divide-y-gray-100`, `border-x-slate-200`, `border-s-red-500`, `border-e-white` and `dark:hover:border-b-amber-500/40`. **Not matched at all** (zero matches): `bg-t-slate-400`, `text-x-gray-500` and `ring-t-blue-500` — a side qualifier on a prefix that never takes one — `border-tr-slate-400` — a two-letter qualifier — and `border-t-2`, `divide-y-reverse`, `border-collapse`, `border-t-slate-4000`, `border-t-mauve-400`, `xborder-t-red-500` and `order-t-red-500`. **No alternative is lost**: the same block enumerates the sixteen prefix alternatives by name — `bg`, `text`, `border`, `ring`, `outline`, `divide`, `placeholder`, `caret`, `accent`, `decoration`, `shadow`, `fill`, `stroke`, `from`, `via`, `to` — and asserts that `paletteGrammar()` matches each of `bg-slate-800`, `text-gray-500`, `border-slate-100`, `ring-blue-500`, `outline-gray-300`, `divide-gray-200`, `placeholder-gray-400`, `caret-slate-500`, `accent-indigo-600`, `decoration-sky-500`, `shadow-slate-900`, `fill-emerald-600`, `stroke-rose-500`, `from-blue-500`, `via-purple-500` and `to-pink-500` **whole**, the match equalling the whole input and not a prefix of it, so an alternative dropped while rewriting the production fails this test whichever one it is. These cases live in a newly appended `describe` block; APRAS-78's own `describe("the §3b grammar")` block is present with its assertions unedited and all of them still pass, `git diff` showing no line removed or changed inside it.
- [ ] A test mutates one entry of `PINNED` that belongs to a file no child ever migrated — `src/App.tsx` — by appending each of `bg-slate-800`, `hover:dark:bg-slate-800/40`, `text-gray-500`, `bg-white` and `text-black` in turn, and a `className` containing the literal `#1e293b`, and asserts `violations()` reports a message naming that text in each of the six cases; the same six inputs are asserted to be matched whole by `paletteGrammar()` (or, for `#1e293b`, by `matchesIn` inside a class context), with the match equal to the whole input string and not a prefix of it.
- [ ] `docs/frontend/theme-token-mapping.md` is modified **only** inside §3b: its `prefix` production now admits an optional single-letter side qualifier from `t`, `r`, `b`, `l`, `x`, `y`, `s`, `e` on `border` and on `divide` and on no other prefix **while removing no alternative**: the widened production's alternation set is exactly the sixteen keywords the pre-amendment production listed — `bg`, `text`, `border`, `ring`, `outline`, `divide`, `placeholder`, `caret`, `accent`, `decoration`, `shadow`, `fill`, `stroke`, `from`, `via`, `to` — with none added and none dropped, so the only textual difference between the pre- and post-amendment blocks is the suffix `(?:-[trblxyse])?` appearing after `border` and after `divide` (plus line re-wrapping), and `accent-indigo-600` still matches whole under both the document's production and the guard's `PREFIX`; and §3b's load-bearing-details prose gains an item recording that the qualifier is exactly one letter, that it applies to `border` and `divide` only, that APRAS-85 made the amendment under an operator authorisation recorded on that task, and that §1j's appendix was generated with the pre-amendment grammar and is therefore 5 occurrences short of the widened one. `git diff docs/frontend/theme-token-mapping.md` shows no changed line outside §3b: no row added, removed or edited in §1b, §1c, §1d, §1e or §1j's appendix, no change to the set of eight gap codes in §1h, no token added anywhere, and §3c and §3d byte-unchanged. The production text in the document and the `PREFIX` constant in `frontend/src/__tests__/themeTokenMigration.test.ts` describe the same grammar.
- [ ] Re-scanning every non-test `.ts`/`.tsx` file under `frontend/src` with the widened production and with the pre-amendment production, and comparing the two match sets by `(file, offset, matched text)`, yields **zero** occurrences present only in the **pre-amendment** set — the old-only difference is empty, so the amendment lost no alternative and narrowed nothing — and **exactly five** occurrences present only in the widened set, and they are exactly `border-t-slate-400` at `frontend/src/features/task-management/components/TaskBoard.tsx:76`, `border-t-blue-400` at `:82`, `border-t-amber-500` at `:88`, `border-t-green-400` at `:94` and `border-t-red-400` at `:100`. Zero newly caught occurrences exist anywhere else in `frontend/src`, in particular zero under `features/asset-management`, `features/project-management`, `features/document-management`, `features/occurrence-management`, `features/access-control`, `features/finance`, `features/purchase-management`, `features/announcement-feed`, `features/feedback-management`, `features/media-management` and `features/package-management` — the directories APRAS-81, 82, 83 and 84 publish counts for — and zero `divide-`, `border-x-`, `border-y-`, `border-b-`, `border-l-`, `border-r-`, `border-s-` or `border-e-` side-qualified occurrences anywhere.
- [ ] The five newly visible occurrences are **kept verbatim and ledgered, not migrated**: after the change `TaskBoard.tsx` still contains the literal strings `border-t-slate-400`, `border-t-blue-400`, `border-t-amber-500`, `border-t-green-400` and `border-t-red-400`, one each, and each has one row in `docs/frontend/unmapped-colours.md` whose `task` is `APRAS-85` and one entry in `themeTokenMigration.exceptions.json` whose `task` is `APRAS-85`, coded `GAP-TINT` for `border-t-slate-400` and `border-t-red-400` and `GAP-NO-TOKEN` for `border-t-blue-400`, `border-t-amber-500` and `border-t-green-400`.
- [ ] `frontend/src/__tests__/themeTokenMigration.exceptions.json` remains the single checked-in list of deliberately unmigrated occurrences: every entry has exactly the keys `file`, `class`, `code`, `task`, every `file` is `src/`-relative, every `code` is one of the eight in §1h, and a test asserts that the number of ledger rows in `docs/frontend/unmapped-colours.md` whose `file` resolves under `src/` and which have **no** matching exceptions entry is exactly **0**, and that the number of exceptions entries with no matching ledger row is exactly **0**.
- [ ] `describe("the pilot's own ledger arithmetic")` (APRAS-78) and the ledger-arithmetic `describe` blocks of APRAS-79, APRAS-80, APRAS-81, APRAS-82, APRAS-83 and APRAS-84 are present in the file with their assertions **unedited** and all pass; `git diff` on `frontend/src/__tests__/themeTokenMigration.test.ts` shows no line removed or changed inside any of those seven blocks; and no ledger row or exceptions entry whose `task` is not `APRAS-85` is modified.
- [ ] Re-measuring the thirty files with a grammar match under `frontend/src/features/{infraction-management,task-management,dashboard,user-administration,space-reservation-management,assembly-voting}/` with the widened §3b grammar accounts for all 312 baseline occurrences as 167 migrated + 0 deleted `dark:` siblings + 145 left and logged, with both halves closing independently (288 non-`dark:` = 167 + 121; 24 `dark:` = 0 + 24); after the change those six trees together retain exactly 145 grammar matches and zero six-digit hex literals in a class context, `infraction-management` retaining 29, `user-administration` 44, `task-management` 35, `dashboard` 28, `space-reservation-management` 9 and `assembly-voting` 0.
- [ ] `docs/frontend/unmapped-colours.md` gains 145 rows whose `task` cell is `APRAS-85` — 53 `GAP-NO-TOKEN`, 46 `GAP-TINT`, 24 `GAP-SWATCH`, 10 `GAP-OVERLAY`, 7 `GAP-OUT-OF-BUDGET`, 5 `GAP-BORDER-100`, and zero `GAP-NO-SURFACE`, zero `GAP-UNLISTED` — each with a `why` of at most 120 characters that does not contain the string `GAP-`; and `themeTokenMigration.exceptions.json` gains exactly 126 entries whose `task` is `APRAS-85` (25 naming an `infraction-management` file, 35 a `user-administration` file, 33 a `task-management` file, 26 a `dashboard` file, 7 a `space-reservation-management` file, 0 an `assembly-voting` file).
- [ ] Exactly five brand-text occurrences carry `text-primary-text` and they are exactly these `<a>`/`<Link>` elements, each of which previously read `text-indigo-600 underline`: `AttachmentUploader.tsx`'s attachment-URL anchor, `InfractionDetailsView.tsx`'s source-occurrence link and its attachment anchor, `InfractionStageTimeline.tsx`'s attachment anchor, and `NewInfractionModal.tsx`'s source-occurrence link. Across the whole diff the class token `text-primary` appears **zero** times, and no `-primary-text` token appears on any `bg-`, `border-`, `ring-`, `divide-`, `outline-`, `fill-`, `stroke-` or `accent-` utility.
- [ ] After the change, no `indigo` class of any prefix, with or without a `dark:`, `hover:` or `file:` variant, remains anywhere under `frontend/src/features/infraction-management/`, and exactly three remain under `frontend/src/features/dashboard/`, counting `dark:`-prefixed classes as separate occurrences exactly as the first clause does — `text-indigo-500` and `dark:text-indigo-400` at `GeneralDashboardPage.tsx` line 54 and `bg-indigo-500/10` at line 55 — all three logged under `GAP-SWATCH` because they encode module identity and must not follow the tenant brand.
- [ ] `frontend/src/features/__tests__/remainingFeaturesContrast.test.ts` passes, importing `contrastRatio`, `parseOklch` and `hexToOklch` from `src/lib/contrast.ts` and reading every colour from `src/index.css` and `node_modules/tailwindcss/theme.css` with no hard-coded colour literal, asserting to ±0.001 that `--primary-text` on `--card` is 5.2096, `--muted-foreground` on `--card` 5.2249 and on `--muted` 4.6684, `--foreground` on `--card` 19.8801 and on `--muted` 17.7626, `--primary-foreground` on `--primary` 5.7588, and `--destructive` on `--card` 4.8073 — and that each of those six exceeds 4.5.
- [ ] The same test records each changed pair's before/after ratio and asserts no pair moves from ≥ 4.5 to < 4.5: `text-gray-900` on white 17.7467 → 19.8801; `text-gray-500` on white 4.8357 → 5.2249; `text-gray-600` on white 7.5608 → 5.2249 and on `bg-gray-100` 6.8711 → 4.6684; `text-gray-400` on white 2.6023 → 5.2249, recorded as **repairing** a pre-existing AA failure at 2 sites; `text-indigo-600` on white 6.4414 → 5.2096; `text-white` on `bg-emerald-700` 5.4381 → 5.7588; `text-red-700` on white 6.5373 → 4.8073; and the only kept foreground on a migrated surface, `text-gray-700` on `bg-gray-100` 9.3658 → on `--muted` 9.2081.
- [ ] The same test declares, in an explicit in-file list, every pair below 4.5:1 that this task leaves untouched and did not introduce — `text-slate-500` on `bg-slate-100` 4.3481, `text-amber-600` on white 3.1884, `text-emerald-600` on white 3.7194 — each recorded as failing **before** this task as well as after, and asserts that the task introduces no other sub-4.5 pair.
- [ ] All seventeen status sets retain their original class strings verbatim: the four red error tints at `AttachmentUploader.tsx:181`, `CycleCloseModal.tsx:104`, `NewInfractionModal.tsx:336` and `InfractionsPage.tsx:355` (2 classes each); `InfractionStageTimeline.tsx:57` (2); `MyInfractionsPage.tsx:67` (2); `DueDateBadge.tsx:18,19` (4); `TaskBoard.tsx`'s five-branch column map (15 — the five `bg-*-50/50` tints, their five `dark:` siblings and the five `border-t-*` header stripes the widened grammar newly reveals); `TaskFilterBar.tsx:146` (4) and `:166` (4); `GeneralDashboardPage.tsx`'s eight-branch module map (24) and its preview badge at `:116` (4); `SpaceBookingPage.tsx`'s `statusBadgeClass` palette branches (8); `InviteAdministratorDialog.tsx:99,101,104` (4); `TenantsAdminPage.tsx:257–299` (11); `TenantProfilePage.tsx:364` (3); and `TenantBrandColors.tsx:599` (3) — 96 classes in all, each with a ledger row.
- [ ] Exactly two occurrences migrate out of a kept emerald panel, and they are exactly `InviteAdministratorDialog.tsx`'s and `TenantsAdminPage.tsx`'s success-panel `<button>`s, each of whose `bg-emerald-700 … text-white` becomes `bg-primary … text-primary-foreground`; `TenantsAdminPage.tsx`'s two other `<button>`s still read `border-emerald-300` with `text-emerald-800`, unchanged, because `border-emerald-300` has no row at any scale; and after the change the six trees contain exactly zero `bg-emerald-700` and zero `text-white`.
- [ ] Grouping every grammar match in the thirty files by `(file, class-context span)` — using the guard's own exported `classContexts()`, not by line — yields **zero** spans holding both a migrated occurrence and a kept `GAP-TINT` occurrence, and exactly three spans holding a migrated occurrence beside a kept occurrence under another code: `InfractionsPage.tsx:262` (`border-gray-100`), `InfractionsPage.tsx:269` (`text-gray-700`) and `MyInfractionsPage.tsx:57` (`text-gray-700`). Of the 312 occurrences, the five `border-t-*` stripes fall inside **no** class-context span at all, because they are values of a `headerColorClass` object property rather than arguments of `className`, `cn` or `cva`; the test asserts that they are nonetheless reported by `matchesIn`, so the palette grammar is shown to run over the whole source and not only over spans.
- [ ] The two known no-token gaps are untouched repo-wide and fully recorded: after the change, `frontend/src` still carries 73 `text-gray-700`, 69 `text-slate-700`, 41 `border-slate-100` and 12 `border-gray-100` — 195 occurrences (re-measured at the implementer's HEAD; the figure is unchanged by APRAS-81 through APRAS-84, all of which leave these four classes alone) — and every one of them has both a row in `docs/frontend/unmapped-colours.md` and a matching entry in `themeTokenMigration.exceptions.json`. No gap code is asserted for these rows: §1h's precedence legitimately codes some of them `GAP-SWATCH` or `GAP-TINT` when they sit inside a swatch or a status set, so the requirement is the existence of the row and the entry, not their code.
- [ ] The total number of widened-grammar matches over every non-test `.ts`/`.tsx` file under `frontend/src` equals the total number of ledger rows in `docs/frontend/unmapped-colours.md` whose `file` resolves under `src/`, and equals the number of `(file, class)` pairs covered by `themeTokenMigration.exceptions.json` expanded per occurrence; the guard asserts these equalities itself rather than against a literal constant (for orientation only, the projected value once APRAS-81 through APRAS-84 have landed is 1,197 matches over 882 exceptions entries; a mismatch against the projection is reported, not asserted). If `frontend/src/features/public-site/` exists in the tree at the implementer's HEAD — APRAS-75's uncommitted work, out of bounds for this child — its occurrences are reported with their count and disposition in the implementation report rather than folded into any figure above.
- [ ] `frontend/src/components/__tests__/TenantBrandReach.test.tsx` passes with two added cases that mount `InfractionStageTimeline` and `NextStepPanel` under the mocked `useTenantProfile`, assert `getComputedStyle(document.documentElement).getPropertyValue("--primary")` equals the mocked theme's value, and assert, **per component**, over the **whitespace-split class tokens of the FULL rendered markup** — every `class` value in the mounted output split on `/\s+/`, explicitly **including the tokens contributed by any `components/ui/` primitive the component renders at its actual variant** — that the token set is exactly as follows. Splitting is strict, so `bg-accent`, `hover:bg-accent` and `hover:bg-accent/80` are three distinct tokens and none matches another; no substring matching anywhere in this test. `InfractionStageTimeline`, mounted with one `STAGE` entry carrying an `actor`, a `note`, one `attachment_urls` element, `fine_amount: null`, `defense_due_on: null` and `suggestion_followed: true`, renders **no** `components/ui/` primitive, so its set is entirely its own: it contains `text-primary-text`, `text-foreground`, `text-muted-foreground` and the kept `border-gray-100` and `text-gray-700`, and contains none of the tokens `text-primary`, `bg-primary`, `bg-card`, `bg-muted`, `bg-accent`, `border-border`, `border-input`, `text-primary-foreground`, `text-destructive`, `bg-amber-100`, `text-amber-800` or `text-amber-700`. `NextStepPanel`, mounted with a `nextStep` whose `reason` is neither `"NO_POLICY"` nor `"CLAMPED"`, whose `fine_amount` is a number and whose `fine_amount_unavailable_reason` is `null`, renders `ui/button` twice — once **variantless, which therefore takes `buttonVariants`' `default` variant**, and once at `outline` — so it contains `bg-card`, `border-border`, `text-foreground` and `text-muted-foreground` from its own markup, `bg-primary`, `text-primary-foreground` and `hover:bg-primary/90` contributed by the `default` variant, and `border-input`, `bg-background`, `hover:bg-accent` and `hover:text-accent-foreground` contributed by the `outline` variant, and contains none of the tokens `text-primary`, `text-primary-text`, `bg-accent`, `bg-muted`, `text-destructive`, `text-amber-700` or `text-red-700`. Never a colour literal is asserted anywhere in the test.
- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts --reporter=verbose` reports every individual test finishing under 2 s and the file as a whole under 10 s, including `it("fails when any single exception is removed")`, which at `a8fc8ab` measures ~880 ms against 254 exceptions and 26 pinned files and runs against every exception and all 260 files after this task; the scan memo inside `violations()` is at module scope and keyed on the file path together with its source text, and the exception loop resolves a file's source through a `Map` built once per call rather than through `Array.prototype.find`.
- [ ] The 62 existing suites under `frontend/src/features/infraction-management/__tests__/`, `frontend/src/features/user-administration/__tests__/` and `frontend/src/features/dashboard/__tests__/` — 594 tests in total — pass without modification.
- [ ] `npx tsc -b` completes with no error.
- [ ] `npx vitest run --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint` over the fifteen changed `.tsx` files reports zero errors and zero warnings, exactly as it does today, and the repository total stays at 375 errors + 2 warnings across 64 files.
- [ ] `git diff --exit-code frontend/src/index.css` succeeds, the `.dark` block in `frontend/src/index.css` is still never applied, and — after the developer has staged its own paths with `git add` — `git diff --name-only --cached` contains no file under `backend/`, no Alembic revision, no route-registry change, no file under `frontend/src/components/ui/`, no file under `frontend/src/features/public-site/`, not `frontend/src/App.tsx` and no file under `frontend/src/i18n/`, and no path outside this set of twenty-four: the fifteen changed `.tsx` files (`AttachmentUploader.tsx`, `ContestationForm.tsx`, `CycleCloseModal.tsx`, `InfractionDetailsView.tsx`, `InfractionStageTimeline.tsx`, `NewInfractionModal.tsx`, `NextStepPanel.tsx`, `InfractionRulesPage.tsx`, `InfractionsPage.tsx`, `MyInfractionsPage.tsx`, `InviteAdministratorDialog.tsx`, `PermissionMatrix.tsx`, `AdminUserDashboard.tsx`, `TenantsAdminPage.tsx`, `AssemblyMinutesView.tsx`), `frontend/src/__tests__/themeTokenMigration.test.ts`, `frontend/src/__tests__/themeTokenMigration.exceptions.json`, `frontend/src/components/__tests__/TenantBrandReach.test.tsx`, `frontend/src/features/__tests__/remainingFeaturesContrast.test.ts`, `frontend/src/__tests__/brandTextRole.test.ts`, `docs/frontend/unmapped-colours.md`, `docs/frontend/theme-token-mapping.md`, `docs/tasks/APRAS-85-spec.md` and `docs/tasks/APRAS-85-mock.html` (the mock only if this task produces one). `frontend/src/__tests__/brandTextRole.test.ts` is APRAS-87's graphical-site guard (landed at `0815915`, after this spec was written): it reconciles a live scan of bare `text-primary` against a declared set of graphical sites, per file and in both directions, so a migration that moves an icon onto `text-primary` must append its declaration there or the guard fails. Any change to it must be a pure append inside `GRAPHICAL_PRIMARY_SITES` — no existing declaration removed or weakened, and no change to that file's surfaces, ratios or imports. If this task's migration adds no bare `text-primary`, the file is absent from the staged set instead. `frontend/src/features/task-management/components/TaskBoard.tsx` is **not** in the staged set: its five newly visible classes are kept verbatim.
