# APRAS-87 — Raise the active-tab label contrast, which fails WCAG AA

## 0. The original premise no longer holds — establish that first

This task was written before APRAS-88 landed at `c7c42fc`. Its framing —
"the repair needs either a change to `frontend/src/index.css` or an amendment
to the table APRAS-78 published" — **is obsolete**. Both artefacts already
exist at HEAD:

- `frontend/src/index.css:52` declares `--primary-text: oklch(0.52 0.11 160)`
  (`:root`) and `:103` its `.dark` value; `:14` exposes it to Tailwind as
  `--color-primary-text`.
- `docs/frontend/theme-token-mapping.md` §1k (line 545) publishes the
  characters / graphical-object boundary: characters take `*-primary-text`
  at a 4.5:1 floor, graphical objects keep `*-primary` at 3:1.

**Re-derived at HEAD, by importing `frontend/src/lib/contrast.ts` and never
reimplementing it, on the emitted, rounded `oklch()` strings read out of
`src/index.css`:**

| Foreground | on `--background` | on `--card` | on `--muted`/`--accent`/`--secondary` |
| --- | --- | --- | --- |
| `--primary` `oklch(0.62 0.15 160)` → `#009f68` | **3.3091** | 3.4054 | 3.0427 |
| `--primary-text` `oklch(0.52 0.11 160)` → `#177c52` | **5.0622** | 5.2096 | 4.6547 |

**The DOM ancestry was re-traced at HEAD and still holds**, with one correction
to the figure note carried on the board: the details branch renders at
`LotsPage.tsx:93` inside `LotsPage.tsx:92` (`container mx-auto max-w-7xl px-4
py-8`, no fill), not at `LotsPage.tsx:123` — that line is the *list* branch's
container. The rest is unchanged: `LotDetailsView.tsx:165/176` → the tab nav at
`:158` (`border-b border-border`, no fill) → the component root at `:82`
(`space-y-6`, no fill) → `LotsPage.tsx:92/93` → `App.tsx:86`/`:112`
(`bg-background`). **No `bg-card` anywhere in the chain.** The surface is
`--background`; `3.3091` is the live figure.

**Therefore: no new token, no `index.css` change, no new table row, no gap
code.** The work is to *apply* a published rule to the call sites that predate
it. §5 states what this costs APRAS-81…85: **nothing to re-derive.**

## 1. Scope

**One deliverable: every shipped bare `text-primary` occurrence that §1k
classifies as *characters* becomes `text-primary-text`, tree-wide, and the
graphical ones are pinned as graphical so the distinction cannot rot.**

There are **48** bare `text-primary` occurrences under `frontend/src/`,
excluding `__tests__/` (matched as `text-primary` not followed by `[\w-]`, so
`text-primary-foreground` and `text-primary-text` are not counted). §1k's
question — *does this element paint glyphs of text?* — splits them
**29 characters / 19 graphical**. This task changes the 29 and leaves the 19.

**Explicitly not in scope:**

- Any change to `frontend/src/index.css`. The token exists and is correct.
- Any palette class (`text-indigo-*`, `text-emerald-*`, `slate-*`, …). Those
  belong to APRAS-80…85 and this task touches none of them, in any directory.
- Any new gap code, ledger row or `themeTokenMigration.exceptions.json` entry.
- `MIGRATED_DIRECTORIES` is **not** extended. Editing a bare token class in an
  unmigrated directory is not a migration and must not be recorded as one.
- The 1.4.11 graphical floor for the 19 graphical sites (`--primary` on
  `--accent` 3.0427, and far worse for a pale tenant brand). APRAS-88 §1k
  already names it as needing its own task; this task does not open it.
- Brand text at fractional opacity — there are **zero** `text-primary/N`,
  `text-indigo-N/M` and `text-emerald-N/M` occurrences in the tree at HEAD, so
  this task hands **nothing** to APRAS-90.
- Backend, Alembic, route registry: untouched.

## 2. The sweep — all 48 sites, classified

### 2a. Characters → `text-primary-text` (29 sites, all changed by this task)

The variant prefix is preserved: `group-hover:text-primary` becomes
`group-hover:text-primary-text`. Only the token after the last `:` changes; no
other class on the line moves.

**Already-migrated directories (real code at HEAD, not a projection):**

| File : line | Element | Nearest painting ancestor |
| --- | --- | --- |
| `components/ui/alert-modal.tsx:41` | `info` variant `titleClass`, on the modal `<h3>` | `--card` |
| `components/ui/badge.tsx:10` | `default` variant, `bg-primary/10 text-primary` | `bg-primary/10` over `--card`/`--background` |
| `components/ui/button.tsx:19` | `link` variant, `text-primary underline-offset-4` | `--card` / `--background` |
| `features/lot-management/components/LotDetailsView.tsx:165` | active "Usuários" tab label | `--background` |
| `features/lot-management/components/LotDetailsView.tsx:176` | active "Moradores" tab label | `--background` |

**Not-yet-migrated directories.** These are **real classes in the tree today**,
not projections: they are bare token classes, so APRAS-81…85's palette-class
grammar never matches them and no sibling would ever change them (§5).

| File : line | Element |
| --- | --- |
| `features/user-administration/components/Navbar.tsx:155` | superuser role subtitle |
| `features/user-administration/components/Sidebar.tsx:111` | active nav item (icon **and** label from one `currentColor` — §1k "a mixed element counts as text") |
| `features/user-administration/components/Sidebar.tsx:125` | active nav item label `<span>` |
| `features/user-administration/components/Sidebar.tsx:160` | active Início item (mixed) |
| `features/user-administration/components/Sidebar.tsx:174` | active Início label `<span>` |
| `features/user-administration/components/Sidebar.tsx:295` | app wordmark |
| `features/user-administration/components/LoginForm.tsx:136` | "Esqueceu a senha?" link |
| `features/user-administration/pages/ForgotPasswordPage.tsx:38` | `APRAS` heading |
| `features/user-administration/pages/ForgotPasswordPage.tsx:92` | "Voltar ao Login" link |
| `features/user-administration/pages/LoginPage.tsx:73` | app-name heading |
| `features/user-administration/pages/LoginPage.tsx:119` | dev-login chip button label |
| `features/user-administration/pages/LoginPage.tsx:132` | signup link |
| `features/user-administration/pages/SignupPage.tsx:106` | app-name heading |
| `features/user-administration/pages/SignupPage.tsx:209` | login link |
| `features/user-administration/pages/ResetPasswordPage.tsx:74` | `APRAS` heading |
| `features/user-administration/pages/BrandedEntryPage.tsx:201` | tenant-name heading |
| `features/user-administration/pages/AcceptInvitationPage.tsx:210` | app-name heading |
| `features/task-management/components/TaskCard.tsx:113` | assignee initials |
| `features/task-management/components/TaskBoard.tsx:213` | drop hint `<p>` |
| `features/task-management/components/TaskList.tsx:106` | `group-hover:text-primary` on the task-title `<span>` |
| `features/task-management/components/AssigneePicker.tsx:166` | option initials |
| `features/dashboard/components/GeneralDashboardPage.tsx:124` | role chip |
| `features/dashboard/components/GeneralDashboardPage.tsx:170` | `group-hover:text-primary` on the card `<h3>` |
| `features/dashboard/components/GeneralDashboardPage.tsx:178` | "Acessar →" affordance |

### 2b. Graphical → keeps `text-primary` (19 sites, unchanged)

`components/ui/alert-modal.tsx:40` (`info` `iconClass`);
`features/visitor-management/components/GatekeeperDashboard.tsx:129,145,170,240,266,305`,
`VisitorAuthPage.tsx:58`, `QrScannerModal.tsx:61`, `AuthorizationQrModal.tsx:61`,
`AuthorizationFormModal.tsx:117` (ten self-closing icon components);
`features/lot-management/components/ResidentTable.tsx:191` (icon);
`features/lot-management/components/LinkUserAccountModal.tsx:107` (`<input
type="radio">` — renders no glyphs);
`features/user-administration/components/Sidebar.tsx:120,169` (icons);
`features/user-administration/components/PermissionMatrix.tsx:145` and
`pages/AdminUserDashboard.tsx:353` (`<input type="checkbox">`);
`features/dashboard/components/GeneralDashboardPage.tsx:135` (icon);
`features/purchase-management/components/PurchaseRequestsPage.tsx:178` (icon).

### 2c. Every surface the 29 sites sit on, measured

Traced from the JSX, never assumed. Tinted surfaces are composited in sRGB
bytes from `oklchToHex`, then handed back through `hexToOklch` and measured by
`contrastRatio` — the module's own functions; the ratio arithmetic is not
reimplemented.

| Surface | painted | `--primary` | `--primary-text` |
| --- | --- | --- | --- |
| `--background` | `#fcfcfc` | 3.3091 | **5.0622** |
| `--card` | `#ffffff` | 3.4054 | **5.2096** |
| `--muted` = `--accent` = `--secondary` | | 3.0427 | **4.6547** |
| `bg-primary/10` over `--background` | `#e3f3ed` | 2.9691 | **4.5421** |
| `bg-primary/10` over `--card` | `#e6f5f0` | 3.0298 | **4.6350** |
| `bg-muted/30` over `--background` (auth page shell) | `#f7faf8` | 3.2408 | **4.9576** |
| `bg-primary/5` over `bg-muted/30` over `--background` | `#ebf5f1` | 3.0590 | **4.6796** |
| `bg-accent/40` over `--card` (dashboard card hover) | `#f7fbf9` | 3.2630 | **4.9917** |

Worst case **4.5421**, on `bg-primary/10` over `--background`. Every surface
clears 4.5:1 with `--primary-text` and fails it with `--primary`.

## 3. Files touched

- **The 17 `.tsx` files listed in §2a** — one or more class literals each:
  `text-primary` → `text-primary-text`, variant prefix preserved. Nothing else
  on the line changes.
- `docs/frontend/theme-token-mapping.md` — **one new paragraph inside §1k**
  (§5 states its coordination cost) saying that the character/graphical
  question also governs a bare `text-primary` that predates the migration, that
  a character site takes `text-primary-text`, and naming the guard below as
  where graphical sites are recorded. **No new row, no new gap code, no change
  to any existing row, no change to §1h's closed set of eight codes.**
- `frontend/src/__tests__/brandTextRole.test.ts` — **new**. Exports
  `GRAPHICAL_PRIMARY_SITES`, the §2b list as `{ file, element, why }` entries —
  **no line numbers**, because a sibling editing an unrelated line of the same
  file would otherwise shift them and turn a correct tree red. The guard asserts
  a **set equivalence**, in both directions: (a) it walks every `.tsx`/`.ts`
  under `frontend/src/` excluding `__tests__/` and `*.test.ts(x)` with
  `node:fs`, matching `text-primary(?![\w-])` including any variant prefix, and
  fails on any occurrence whose file is not declared or whose per-file
  occurrence count exceeds the declared entries for that file; and fails on any
  declared entry with no surviving occurrence. It asserts **no tree-wide
  total** — a sibling that migrates a palette-coloured icon to `text-primary`
  appends its entry and the guard stays green (§5). (b) measures
  `--primary-text` and `--primary` on the eight surfaces of §2c by **importing**
  `contrastRatio`, `parseOklch`, `oklchToHex` and `hexToOklch` from
  `src/lib/contrast.ts`. `// @vitest-environment node`, so `import.meta.url` is
  a `file:` URL.
- `frontend/src/features/lot-management/__tests__/lotManagementContrast.test.ts`
  — the single `PRE_EXISTING_SUB_AA` entry (owner `APRAS-87`) is **removed**,
  the `toHaveLength(1)` becomes `toHaveLength(0)`, and the two tab labels are
  re-asserted as repaired: `--primary-text` on `--background` is `5.0622` and
  at or above `MINIMUM_CONTRAST_RATIO`. The `ACTIVE_TAB_ON_CARD` history
  constant and its test are kept as-is — they document a corrected mistake.
- `frontend/src/features/user-administration/__tests__/Sidebar.test.tsx` (lines
  143, 154) and `.../Navbar.test.tsx` (159, 186, 241) — these use
  `expect(el.className).toContain("text-primary")`, a **substring** match that
  `text-primary-text` satisfies vacuously. Each becomes a **whitespace-split
  class-token** assertion: the token list contains `text-primary-text` and does
  **not** contain `text-primary`.

## 4. Test criteria

1. `npx tsc -b` exits 0.
2. `npx vitest run` passes, with coverage at or above 80 lines / 78 functions /
   76 branches / 80 statements.
3. `brandTextRole.test.ts` fails if any of the 29 sites is reverted, and fails
   if **any** new graphical site appears without a `GRAPHICAL_PRIMARY_SITES`
   entry — whatever the resulting total. It must **not** assert a fixed count.
4. ESLint diff-scoped: no new error or warning beyond the 375 + 2 baseline.
5. No file under `backend/` changes; no Alembic revision is added; no route
   registry entry changes.

## 5. What this costs APRAS-81…85 — the coordination statement

**Nothing to re-derive.** The reason is structural, not a promise:

- **No token and no mapping-table *row* changes.** §1k's nine palette-class
  rows, their Budget columns, their ΔE figures and `--primary-text`'s value are
  byte-identical after this task. Every ratio those five specs publish
  (`4.6547`, `5.2096`, `5.0622`, …) is re-measured above and unchanged.
- **The 29 sites are bare token classes.** The §3b guard grammar matches
  Tailwind *palette* classes, so none of the 29 is in any sibling's inventory;
  the five specs enumerate their sites file-by-line and no line overlaps a §2a
  line.
- **The one obligation added is mechanical and small.** A sibling migrating a
  `text-indigo-*` *icon* to `text-primary` creates a new graphical site, which
  `brandTextRole.test.ts` requires be appended to `GRAPHICAL_PRIMARY_SITES` —
  one line per site, from data the sibling's spec already lists explicitly
  under its own "§1k applied" section. No re-measurement, no re-classification:
  the sibling's spec has already answered §1k's question for each site. This
  is stated here rather than discovered by the first sibling to go red.
- **Merge order is free — and the results are written so that it is true.**
  If a sibling lands first, this task's guard is seeded from the tree at its
  own implementation time; if this task lands first, the sibling appends.
  Neither ordering changes any figure. Crucially, **no expected result and no
  assertion states a tree-wide total of graphical sites**: the guard is a set
  equivalence (every match is declared, every declaration is matched) plus a
  **floor** — the 19 sites of §2b must still be declared and still carry bare
  `text-primary`. A sibling can only *add* to the set, never remove from the
  floor, because the sibling grammar matches palette classes and never a bare
  token class. Entries carry no line numbers, so a sibling's edits to an
  unrelated line of the same file cannot invalidate them.

## 6. Mockup — yes, and why

`docs/tasks/APRAS-87-mock.html`. APRAS-88 declined a mock because it shipped a
stylesheet value and no call site. This task is the inverse: it changes the
**rendered appearance of 29 call sites** across tabs, sidebar, badges, links
and headings, and the operator's decision is a visual one — whether the darker
`#177c52` still reads as the brand on an active tab and an active sidebar item.
The mock renders both tokens side by side at the real call-site shapes, with
each pair's measured ratio, so the trade is visible rather than argued.

## Expected Results

- [ ] 1. Both active-tab branches in
      `frontend/src/features/lot-management/components/LotDetailsView.tsx`
      (the `activeTab === "users"` and `activeTab === "residents"` ternaries)
      read the literal `border-primary text-primary-text`, and neither class
      list contains `text-primary` as a whitespace-split token.
- [ ] 2. **Ordering-independent graphical inventory.** A scan of every
      `.tsx`/`.ts` under `frontend/src/`, excluding `__tests__/` and
      `*.test.ts(x)`, for `text-primary(?![\w-])` yields a set of occurrences
      that is **exactly equivalent** to the entries of
      `GRAPHICAL_PRIMARY_SITES` in
      `frontend/src/__tests__/brandTextRole.test.ts`: every occurrence found is
      declared, and every declaration matches a surviving occurrence. No fixed
      tree-wide total is asserted anywhere. That set contains **at least** the
      19 sites of §2b, named by file and element: `alert-modal.tsx` (`info`
      `iconClass`); `GatekeeperDashboard.tsx` (six icons);
      `VisitorAuthPage.tsx`, `QrScannerModal.tsx`, `AuthorizationQrModal.tsx`,
      `AuthorizationFormModal.tsx` (one icon each); `ResidentTable.tsx` (icon);
      `LinkUserAccountModal.tsx` (`<input type="radio">`); `Sidebar.tsx` (two
      nav icons); `PermissionMatrix.tsx` and `AdminUserDashboard.tsx`
      (`<input type="checkbox">` each); `GeneralDashboardPage.tsx` (icon);
      `PurchaseRequestsPage.tsx` (icon). Entries carry no line numbers.
- [ ] 3. At least the 29 character sites of §2a carry `text-primary-text` with
      their variant prefix preserved (`group-hover:text-primary-text` where the
      original was `group-hover:text-primary`), across at least these files:
      `alert-modal.tsx`, `badge.tsx`, `button.tsx`, `LotDetailsView.tsx`,
      `Navbar.tsx`, `Sidebar.tsx`, `LoginForm.tsx`, `ForgotPasswordPage.tsx`,
      `LoginPage.tsx`, `SignupPage.tsx`, `ResetPasswordPage.tsx`,
      `BrandedEntryPage.tsx`, `AcceptInvitationPage.tsx`, `TaskCard.tsx`,
      `TaskBoard.tsx`, `TaskList.tsx`, `AssigneePicker.tsx`,
      `GeneralDashboardPage.tsx`.
- [ ] 4. `brandTextRole.test.ts` measures `--primary-text` at or above 4.5:1 on
      all eight surfaces of §2c — `--background` 5.0622, `--card` 5.2096,
      `--muted`/`--accent`/`--secondary` 4.6547, `bg-primary/10` over
      `--background` 4.5421, `bg-primary/10` over `--card` 4.6350,
      `bg-muted/30` over `--background` 4.9576, `bg-primary/5` over
      `bg-muted/30` over `--background` 4.6796, `bg-accent/40` over `--card`
      4.9917 — by **importing** `contrastRatio`, `parseOklch`, `oklchToHex` and
      `hexToOklch` from `frontend/src/lib/contrast.ts`, reimplementing none of
      them.
- [ ] 5. `frontend/src/index.css` is byte-unchanged; no file under `backend/`
      changes; no Alembic revision is added;
      `frontend/src/features/user-administration/access/routeAccess.ts` is
      unmodified.
- [ ] 6. `docs/frontend/theme-token-mapping.md` gains exactly one new paragraph
      inside §1k extending the character/graphical question to bare
      `text-primary` classes that predate the migration, with **no** new table
      row, no change to any existing row, and §1h still naming exactly eight gap
      codes.
- [ ] 7. `frontend/src/__tests__/brandTextRole.test.ts` exists, carries
      `// @vitest-environment node`, exports `GRAPHICAL_PRIMARY_SITES`, and
      passes under `npx vitest run`.
- [ ] 8. `frontend/src/features/user-administration/__tests__/Sidebar.test.tsx`
      and `.../Navbar.test.tsx` contain no
      `expect(...className).toContain("text-primary")` substring assertion; the
      five affected assertions check a whitespace-split class-token list that
      contains `text-primary-text` and does not contain `text-primary`.
- [ ] 9. In `frontend/`: `npx tsc -b` exits 0; `npx vitest run` passes with
      coverage at or above 80 lines / 78 functions / 76 branches / 80
      statements; `npx eslint .` reports no more than the 375 errors and 2
      warnings baseline. `lotManagementContrast.test.ts` has `PRE_EXISTING_SUB_AA`
      empty with `toHaveLength(0)` and both tab labels asserted at or above
      `MINIMUM_CONTRAST_RATIO`.
- [ ] 10. `docs/tasks/APRAS-87-mock.html` exists and renders both tokens
      side by side at the real call-site shapes with each pair's measured
      ratio.
