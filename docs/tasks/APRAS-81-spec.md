# APRAS-81 — Migrate project and asset management to semantic theme tokens

Child 4 of 8 of the APRAS-77 split, specified against the **amended** contract:
APRAS-78's three artefacts as extended by APRAS-79 / APRAS-80 and amended by
APRAS-88 at `c7c42fc`. This task **consumes** that contract and may not extend
it — with **one operator-authorised exception**, the scope sentence of §1f case
1, which this task **owns** and carries (see *The operator-authorised §1f case 1
amendment* below). Outside that one sentence: no row added or altered in
`docs/frontend/theme-token-mapping.md`, no new gap code, no token in
`frontend/src/index.css`, and §3b untouched. Every other call below is an
*application* of a published rule to a named call site.

Re-measured at `2c58a76` (after APRAS-90 at `a51b0f1` and APRAS-75 at
`2c58a76`); every figure below is measured from that tree and is stated as
*provenance*, never as the baseline an expected result is decided against.

## `BASE` — derived from the repository alone, never from a report and never from `origin`

This task and APRAS-83 are order-independent, so **no expected result may name a
literal sha**: `2c58a76` is the correct baseline only while APRAS-81 is the next
thing to land, and if APRAS-83 lands first, a range rooted at `2c58a76` sweeps
in APRAS-83's commits and files.

Every assertion below is therefore either **absolute** — a count filtered by
`task: "APRAS-81"`, a class string present or absent in the tree, a wall-time
ceiling — or anchored on `BASE`, which is **computed from the repository by
whoever is checking**, with no file outside version control involved:

> **`BASE` is the parent of this task's first commit:**
>
> ```
> git rev-parse "$(git log --format='%H %s' \
>   | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-81\):' | tail -1 | cut -d' ' -f1)^"
> ```
>
> and, for the content of any file immediately before this task,
> `PRE(<path>)` = `git show "$BASE:<path>"`.

The filter is exact because the project's commit convention (`CLAUDE.md`:
`<type>(<scope>): <summary>`, scope = the task id) puts `(APRAS-81):` in the
**subject** of every commit this task makes and in no other task's subject.
Matching the subject rather than the whole message is load-bearing: commit
*bodies* cite neighbouring ids, so `git log --grep=APRAS-80` matches `a51b0f1`,
which is an APRAS-90 commit.

**Why not `origin/master`, and why not the implementation report.** Integration
in this project happens on local `master`, which is currently 19 commits ahead
of `origin/master`; `git merge-base HEAD origin/master` therefore returns
`eba4cca`, a point 187 files — nine of them Alembic revisions or backend route
files — away from any child's branch point. No result below uses it. Nor does
any result read a sha, a count or a total out of the implementation report:
reports live under `.meridian/`, which is gitignored, so whoever checks these
results cannot open one.

The repository-wide "as measured today" figures — the eslint totals, the guard
suite's exception and pinned-file counts, its wall times — are **provenance
only**, and no result asserts a delta against them. Where a baseline was
genuinely needed the result states it absolutely instead: eslint is asserted per
touched file, exceptions and ledger rows by `task` filter, the guard's speed as
a fixed 2 s ceiling. Where an absolute number appears below with the words "at
`2c58a76`", it is provenance for the reasoning and is not the thing being
asserted.

Two directories, not one, because the operator scoped this child that way. They
are unusually complementary: `project-management` is a `dark:`-heavy slate/indigo
feature (331 occurrences, 140 of them `dark:`), `asset-management` is a
gray/blue feature with **zero** `dark:` occurrences (256). The two halves
exercise opposite halves of §1g.

## Scope

`frontend/src/features/project-management/components` — the eight files
`BudgetVsActualProgressBar`, `ConstructionTrackerPage`, `MilestoneFormModal`,
`MilestoneTimeline`, `ProjectFormModal`, `ProjectSummaryCard`,
`ProjectUpdateFeed`, `ProjectUpdateModal` — and
`frontend/src/features/asset-management/components` — the six files
`AssetFormModal`, `AssetMovementHistoryModal`, `AssetSummaryCards`,
`AssetTable`, `AssetsInventoryPage`, `StockMovementModal` — migrated from
hard-coded Tailwind palette classes to the tokens the table names, with every
class left behind logged in the ledger and excepted in the guard; then both
directory paths appended to `MIGRATED_DIRECTORIES`.

Plus the one operator-authorised amendment: the scope sentence of §1f case 1 in
`docs/frontend/theme-token-mapping.md`.

Not covered: either feature's `hooks/`, `utils/` or `__tests__/` (none of the
four files there contains a palette class), any other feature directory,
`index.css`, the backend, the `.dark` block, and any *further* amendment to the
mapping table — no row, no budget figure, no gap code — or to the ledger's rules
or the guard's grammar (§3b).

**No mockup.** This is a token substitution; every migrated pair is either
byte-identical in `:root` or a published, budgeted colour move already
tabulated. The visible changes are enumerated under *What this proves, and what
it misses*.

## The operator-authorised §1f case 1 amendment — owned here, consumed by APRAS-83

Every child of APRAS-77 is forbidden to amend APRAS-78's artefacts. The
operator has authorised **this one**, exactly as they authorised APRAS-85 to
widen §3b. It is the minimum that makes the answer above legal, and it is the
whole of what this task changes in the mapping table.

**What changes.** §1f case 1's rule — *if the element sits on the page it is
`bg-card`; if the element **is** the page it is `bg-background`* — is today
scoped by its own heading to `bg-white` / `text-white` / `border-white`. The
amendment extends that scope to a page root **whatever its source colour**, and
records that case 1 is consulted **before** the class's own §1b row. One
sentence, appended inside the Case 1 paragraph, in this shape:

> The second clause of the rule is **not** scoped to `bg-white`: an element that
> **is** the page takes `bg-background` whatever its source class, so a page
> root written `bg-slate-50` or `bg-gray-50` takes `bg-background` and **not**
> the `bg-muted` its §1b row would otherwise give it — case 1 is consulted
> before the row, and before case 2. (Operator ruling on APRAS-81 and APRAS-83;
> carried by APRAS-81.)

**The trailing parenthetical is a marker, not decoration.** The exact byte
string

```
(Operator ruling on APRAS-81 and APRAS-83; carried by APRAS-81.)
```

occurs nowhere else in the repository, so its **count** in
`docs/frontend/theme-token-mapping.md` is what distinguishes the three possible
outcomes, and it is what the expected result asserts — a substring count of the
rule's prose could not, because the rule restates wording that §1f case 1
already uses:

| Outcome | marker count | mapping-table diff `BASE..HEAD` |
| --- | --- | --- |
| **Carried** — APRAS-83 had not landed; this task appended the sentence | **1** | one added line inside the Case 1 paragraph |
| **Consumed** — APRAS-83 landed first; this task left the file alone | **1** | empty |
| **Double-carried** — both tasks appended it | 2 | one added line, but the file now states the ruling twice — **must FAIL** |

Whichever of the first two obtains, the §1f Case 1 paragraph must end with
**exactly one** sentence beginning `The second clause of the rule is` and
ending with the marker, and `grep -c -F` of the marker over the whole file must
print `1`. This is asserted on the file's **content**, not on the diff, precisely
so that consuming and carrying are both legal while carrying twice is not.

**What does not change, and a reviewer must confirm did not:** no table row is
added, removed or retargeted; no budget figure moves; no gap code is added or
redefined; §3b is untouched; §1b's `bg-slate-50` / `bg-gray-50` rows are
byte-identical; §1f cases 2 and 3 are byte-identical. `themeTokenCompile.test.ts`
therefore passes unmodified, because it asserts rows and no row moved.

**APRAS-83 consumes this amendment; it does not repeat it.** `finance/components/
FinanceDashboardPage.tsx:48` is the identical pattern
(`min-h-screen bg-slate-50 dark:bg-slate-950 …`) and the operator answered
`bg-background` there too. The two tasks are **order-independent** and each must
be implementable first:

- if **APRAS-81 lands first**, APRAS-83 finds the amended sentence already in the
  file, changes nothing in the mapping table, and sends
  `FinanceDashboardPage:48` to `bg-background` citing §1f case 1 as amended;
- if **APRAS-83 lands first**, it carries the *same sentence, verbatim*, and this
  task then finds it present and leaves the mapping table byte-unchanged.

**What APRAS-83's spec must say, verbatim, for the pair to be consistent.** Its
mapping-table expected result must be the mirror of this one — not a different
wording of the same idea, because the two are checked against the same file:

> §1f case 1's page-root extension is owned by APRAS-81 and is carried by
> whichever of APRAS-81 / APRAS-83 lands first. If the marker
> `(Operator ruling on APRAS-81 and APRAS-83; carried by APRAS-81.)` is already
> present in `docs/frontend/theme-token-mapping.md` when this task starts, this
> task changes **no line** of that file; if it is absent, this task appends the
> identical sentence, ending in that identical marker, inside the §1f Case 1
> paragraph and nowhere else. Either way `grep -c -F` of the marker over the
> file prints **exactly `1`** after this task, the file contains no added or
> removed line beginning with `|` in `BASE..HEAD` — `BASE` derived by the same
> repository-only rule this spec states above, with `(APRAS-83):` in place of
> `(APRAS-81):` — and `FinanceDashboardPage.tsx:48` takes `bg-background`.

APRAS-83 must adopt the same `BASE` convention this spec defines above — its
own branch point, computed as the parent of its own first commit from the
repository, never from `origin/master` and never from a report — and must not
baseline any assertion on a literal sha either, for the symmetric
reason: if APRAS-81 lands first, a range rooted at `2c58a76` sweeps in
APRAS-81's fourteen files and its ledger and exceptions edits, and APRAS-83's
path-scope and repository-total results would fail through no act of APRAS-83.

The expected results of both tasks are then satisfiable under either order (see
the mapping-table result below, which is phrased *consume-or-carry* and pins the
marker's cardinality).

**No other sibling is affected.** Measured across every remaining sibling
directory at `2c58a76`, the only elements that *are* a page are:
`ConstructionTrackerPage:198` (this task), `FinanceDashboardPage:48`
(APRAS-83), and six in APRAS-85's `user-administration/pages/` — `LoginPage:70`,
`ForgotPasswordPage:35`, `ResetPasswordPage:71`, `BrandedEntryPage:190`,
`SignupPage:103`, `AcceptInvitationPage:207` — each of which already reads
`min-h-screen … bg-muted/30`. `bg-muted/30` is **a token, not a palette class**,
so it produces no §3b match, sits in no ledger and no exceptions entry, and is
outside APRAS-77's migration entirely. **No published count in APRAS-82,
APRAS-84 or APRAS-85 moves**, and none of the three needs revising for this
amendment. That those six page roots read `bg-muted/30` rather than
`bg-background/30` is a pre-existing inconsistency with the amended rule; it is
recorded here and is **out of scope** for every child of APRAS-77, because §1i
forbids a migration child from touching a class that is already a token.

## The re-measurement

Measured now over the fourteen non-test `.tsx` files with the §3b grammar
exactly as the guard builds it (scale alternatives longest-first, both word
boundaries, opacity suffix):

| Figure | Value |
| --- | --- |
| Palette occurrences | **587** — the task's reported figure reproduces exactly |
| Files | **14** — reproduces exactly |
| Distinct classes | 140 |
| Six-digit hex literals inside a class context | **0** |
| `dark:`-prefixed | **140** (23.9%), against **447** non-`dark:` |
| `project-management/components` | 8 files, **331** occurrences, 140 `dark:` |
| `asset-management/components` | 6 files, **256** occurrences, **0** `dark:` |
| Per file | ConstructionTrackerPage 81, AssetTable 72, ProjectSummaryCard 65, MilestoneTimeline 62, AssetFormModal 54, BudgetVsActualProgressBar 42, AssetsInventoryPage 42, ProjectUpdateFeed 39, AssetMovementHistoryModal 35, StockMovementModal 27, AssetSummaryCards 26, MilestoneFormModal 14, ProjectFormModal 14, ProjectUpdateModal 14 |

`hooks/useProjects.ts`, `hooks/useAssets.ts` and `utils/currency.ts` are pinned
by the directory walk only if they sit **in** a pinned directory; they do not,
so the guard pins exactly the 14 `.tsx` above.

## Pairing a `dark:` class with its base

The settled rule: a `dark:` occurrence pairs with the class in the **same
class-context span**, with the **same utility prefix**, the **same non-`dark:`
variant chain**, **nearest preceding**. A `dark:` sibling of a migrated class
is deleted (§1g); a `dark:` sibling of a kept class is left and logged under its
base's code.

Applied mechanically here, **every one of the 140 `dark:` occurrences has a
base**; there is no orphan.

The variant-chain clause is load-bearing at **three** sites, all of the shape
`text-slate-400 hover:text-slate-600 dark:hover:text-slate-200`
(`MilestoneFormModal:81`, `ProjectFormModal:107`, `ProjectUpdateModal:67`):
the naive nearest-preceding base is `text-slate-400`, the chain-correct base is
`hover:text-slate-600`. Both migrate, so the disposition is unchanged — stated
so a reviewer need not re-derive it. A fourth site,
`ConstructionTrackerPage:427` `dark:hover:bg-slate-800`, pairs with
`hover:bg-slate-50` rather than `bg-white` for the same reason, again with no
change of disposition.

## The disposition of all 587

| Disposition | n |
| --- | --- |
| Light class migrated to a token | **228** |
| `dark:` sibling of a migrated class, **deleted** (§1g) | **83** |
| Left untouched and logged | **276** (219 non-`dark:`, 57 `dark:`) |
| **Total** | **587** |

The two halves close independently: non-`dark:` 447 = 228 + 219, and `dark:`
140 = 83 + 57.

Per file, as `migrated / deleted / logged`:

| File | m / d / l |
| --- | --- |
| `BudgetVsActualProgressBar.tsx` | 10 / 10 / 22 |
| `ConstructionTrackerPage.tsx` | 33 / 24 / 24 |
| `MilestoneFormModal.tsx` | 5 / 4 / 5 |
| `MilestoneTimeline.tsx` | 22 / 14 / 26 |
| `ProjectFormModal.tsx` | 5 / 4 / 5 |
| `ProjectSummaryCard.tsx` | 16 / 11 / 38 |
| `ProjectUpdateFeed.tsx` | 19 / 12 / 8 |
| `ProjectUpdateModal.tsx` | 5 / 4 / 5 |
| `AssetFormModal.tsx` | 19 / 0 / 35 |
| `AssetMovementHistoryModal.tsx` | 19 / 0 / 16 |
| `AssetSummaryCards.tsx` | 15 / 0 / 11 |
| `AssetTable.tsx` | 26 / 0 / 46 |
| `AssetsInventoryPage.tsx` | 22 / 0 / 20 |
| `StockMovementModal.tsx` | 12 / 0 / 15 |

Per directory: `project-management` 115 / 83 / 133 = 331;
`asset-management` 113 / 0 / 143 = 256.

The 276 occupy **200** distinct `(file, class)` pairs, which is the number of
exceptions entries this task appends.

## The gap codes, each counted from its own membership

| Code | Occ. | Derivation |
| --- | --- | --- |
| `GAP-NO-TOKEN` | **87** | `focus:ring-blue-500` 20 (the operator note's "21 focus rings stay blue" — **20 of the 21 are in these two directories**), plus every `blue`, `amber` and `orange` occurrence outside the category map: **blue 36** (56 blue occurrences in all, less the 20 rings), **amber 28** (31 in all, less the 3 in `AssetTable:52`'s `FERRAMENTAS` swatch branch, which are `GAP-SWATCH`), **orange 3** (`AssetTable:39`'s condition branch). `20 + 36 + 28 + 3 = 87` |
| `GAP-TINT` | **77** | the status sets enumerated below: 12 + 14 + 11 + 16 + 9 + 6 + 3 + 3 + 3, counted per file |
| `GAP-OUT-OF-BUDGET` | **51** | `text-gray-700` 19 (of 20; `AssetTable:62`'s is `GAP-SWATCH`) + `text-slate-700` 7 (all) + `text-slate-800` **6** (of 8; `MilestoneTimeline:42` and `ProjectSummaryCard:23` are the slate badges of sets 1–2 and are `GAP-TINT`) + `text-gray-800` 3 (of 4; `AssetTable:43`'s is set 11's gray branch, `GAP-TINT`) + `text-slate-300` 1 + `hover:text-red-400` 1 (§1h's published `text-red-400` row, ΔE 13.45) = **37** non-`dark:`, plus their **14** `dark:` siblings (`dark:text-slate-300` **6** — of 8, the other 2 being the sets 1–2 badges' and so inside `GAP-TINT` — `dark:text-slate-200` 7, `dark:text-slate-600` 1). `37 + 14 = 51` |
| `GAP-BORDER-100` | **23** | `border-slate-100` 11 + `border-gray-100` 1 = 12, plus 11 `dark:border-slate-800` siblings (`AssetFormModal:212`'s `border-gray-100` has no `dark:` sibling) |
| `GAP-SWATCH` | **21** | `AssetTable.tsx`'s `getCategoryBadgeClass` map only — 7 branches × 3 classes; see below |
| `GAP-OVERLAY` | **11** | `bg-black/50` **×5** (`ProjectSummaryCard:89`, `AssetFormModal:132`, `AssetsInventoryPage:330`, `AssetMovementHistoryModal:59`, `StockMovementModal:87`), `bg-black/60` ×4, `bg-black/80` ×1, `hover:bg-black` ×1 — modal scrims and the photo-lightbox chrome; no `dark:` siblings. `5 + 4 + 1 + 1 = 11` |
| `GAP-NO-SURFACE` | **6** | `text-white` over a background with no row: `ProjectSummaryCard:94,103` and `ProjectUpdateFeed:133` over `bg-black/*` scrims, `AssetFormModal:427`, `AssetsInventoryPage:168`, `StockMovementModal:193` over `bg-blue-600` |

`87 + 77 + 51 + 23 + 21 + 11 + 6 = 276`. **Zero `GAP-UNLISTED`.** Cross-check
from the other direction: the codes hold 219 non-`dark:` and 57 `dark:`
occurrences, matching the disposition table's two halves.

## Every status set in these directories, and the one swatch map

The triple rule is binding tree-wide: a status variant's class set migrates as a
**unit or not at all**, every member must have a row in §1b–1e, and the
resulting pair must hold ≥ 4.5:1. **A ternary's branches are one set**, exactly
as APRAS-80 read its sets 2+3 — the branches are the same property of the same
element in two states, so the rule is applied to the whole ternary.

| # | Set | Members | n | Code |
| --- | --- | --- | --- | --- |
| 1 | `MilestoneTimeline:28,35,42` column badges | DONE emerald 6, IN_PROGRESS blue 6, NEXT_STEPS slate 6 | 18 | TINT 12 / NO-TOKEN 6 |
| 2 | `ProjectSummaryCard:23,28,33,38` `STATUS_BADGES` | slate 6, blue 6, amber 6, emerald 6 | 24 | TINT 12 / NO-TOKEN 12 |
| 3 | `ProjectSummaryCard:170–174` budget-bar fill ternary | `bg-red-500` / `bg-emerald-500` | 2 | TINT |
| 4 | `BudgetVsActualProgressBar:23,25,27` `progressColor` | `bg-emerald-500`, `bg-red-500`, `bg-amber-500` | 3 | TINT 2 / NO-TOKEN 1 |
| 5 | `BudgetVsActualProgressBar:77–81` executed-value ternary | `text-red-600` + `dark:text-red-400` \| `text-slate-800` + `dark:text-slate-200` | 4 | TINT 2 / OUT-OF-BUDGET 2 |
| 6 | `BudgetVsActualProgressBar:92–96` remaining-value ternary | `text-red-600` + `dark:` \| `text-emerald-600` + `dark:` | 4 | TINT |
| 7 | `BudgetVsActualProgressBar:34,46` budget glyphs | `text-emerald-600` + `dark:text-emerald-400`; `text-emerald-600` | 3 | TINT |
| 8 | `ConstructionTrackerPage:271` report-success alert | `border-emerald-200`, `bg-emerald-50`, `text-emerald-800` + 3 `dark:` | 6 | TINT |
| 9 | `ConstructionTrackerPage:272` report-error alert | `border-red-200`, `bg-red-50`, `text-red-800` + 3 `dark:` | 6 | TINT |
| 10 | `ConstructionTrackerPage:317` delete-project control | `text-red-600`, `border-red-200`, `hover:bg-red-50`, `dark:hover:bg-red-950` | 4 | TINT |
| 11 | `AssetTable:32–43` `getConditionBadgeClass` | 6 branches × 3 (emerald, blue, amber, orange, red, gray) | 18 | TINT 9 / NO-TOKEN 9 |
| 12 | `AssetTable:162,164` low-stock badge | `bg-amber-100`, `text-amber-800`, `text-amber-600` | 3 | NO-TOKEN |
| 13 | `AssetMovementHistoryModal:27–49` movement-type badges | 4 branches × 3 (emerald, blue, amber, red) | 12 | TINT 6 / NO-TOKEN 6 |
| 14 | `AssetFormModal:152` / `StockMovementModal:113` error alerts | `bg-red-50`, `text-red-700`, `border-red-200` each | 6 | TINT |
| 15 | `AssetSummaryCards:37,61,66,69,73,84,88` metric tiles | blue tile 2, low-stock amber 4 (`border-amber-300`, `bg-amber-50/20`, `text-amber-700`, `text-amber-900`), amber tile 2, emerald value 1, emerald tile 2 | 11 | NO-TOKEN 8 / TINT 3 |
| 16 | `AssetsInventoryPage:149,189–234` header tile and tab strip | `bg-blue-50`/`text-blue-600` tile 2, three `bg-blue-50 text-blue-700` active tabs 6, `bg-amber-50 text-amber-700` 2, `text-amber-500` 1, `bg-amber-200 text-amber-900` 2, `bg-blue-600 hover:bg-blue-700` 2 | 15 | NO-TOKEN |

**The rowless member of each.** Sets 1–2 and 11 are blocked by
`bg-emerald-100` / `bg-slate-100`-with-`text-slate-800` / `bg-red-100` /
`text-emerald-800` / `border-emerald-200`, none of which has a §1b–1e row for
its role. Sets 8, 9, 10 and 14 are blocked by `bg-emerald-50` / `bg-red-50` /
`border-red-200` / `hover:bg-red-50` — APRAS-80's sets 4/5/11 unchanged. Sets
3, 4, 6 and 7 are the operator's status ruling applied through **§1f case 3**:
every emerald in them is a **non-interactive** status glyph, fill or figure, so
it stays regardless of its row, and its ternary partner stays with it. Sets 5
and 12–16 contain an `amber`/`blue`/`orange` or `text-*-[78]00` member with no
row at all.

**Consequence worth stating once: no emerald and no `text-red-*` occurrence in
these two directories migrates.** `text-emerald-500` does not occur, so §1a's
fourth named move is not exercised here; the five `text-emerald-600`, one
`text-emerald-700`, five `text-emerald-800` and six emerald surfaces are all
inside sets above. The only red that moves is `hover:text-red-600` ×3, which is
free-standing (see below).

**The one swatch map.** `AssetTable.tsx:47–63` `getCategoryBadgeClass` maps an
asset **category** — `ELETRONICOS`, `FERRAMENTAS`, `MOBILIARIO`, `SEGURANCA`,
`LIMPEZA`, `MANUTENCAO`, default — onto seven colours. That is §1h code 2
`GAP-SWATCH` verbatim ("category swatches. Must not follow the brand"), and
code 2 outranks codes 3 and 4. It matters: without it,
`bg-indigo-50 text-indigo-700 border-indigo-200` (MANUTENCAO) and
`bg-gray-50 text-gray-700 border-gray-200` (default) would each be split by
their class-level rows and the seven-colour category scale would lose two of
its seven hues to the brand. **`getConditionBadgeClass` at `:29–45` is *not* a
swatch**: condition is a record's status, so it takes codes 4 / 3 by family,
exactly as `badge.tsx`'s variants did in the pilot. Both codes forbid migration,
so only the recorded label differs.

**The proof there is no further split set.** A split set is a class-context span
holding both a migrated occurrence and a kept `GAP-TINT` occurrence. Run
mechanically over all 587 occurrences grouped by `(file, span)`, that check
returns **zero** spans. It must still return zero after the change. (Spans that
mix a migrated occurrence with a kept occurrence under any *other* code are
expected and are not counted — e.g. `ConstructionTrackerPage:426–427`'s filter
chip, where `text-slate-700` is `GAP-OUT-OF-BUDGET` beside four migrating
classes, and `AssetsInventoryPage:189–194`'s tabs, where a `GAP-NO-TOKEN` blue
active branch sits beside a migrating gray inactive branch.)

## Behaviour — the substitutions

Every substitution is a table row applied verbatim.

- `bg-white` ×27 → **`bg-card`** — §1f case 1, settled below. **None of the 27**
  takes `bg-background` and none takes `bg-popover`: no `bg-white` element in
  these fourteen files *is* the page. (The one `bg-background` this task writes
  comes from `bg-slate-50` at the page root, below, not from any `bg-white`.)
- `border-gray-200` ×19 + `border-slate-200` ×15 → `border-border`;
  `border-slate-200/80` ×2 → `border-border/80`; `border-gray-200/60` ×1 →
  `border-border/60`; `divide-gray-200` ×1 → `divide-border`.
- `border-gray-300` ×20 + `border-slate-300` ×1 → `border-input`.
- `text-slate-900` ×12 + `text-gray-900` ×11 → `text-foreground`.
- To `text-muted-foreground` ×65: `text-slate-500` 12, `text-gray-600` 12,
  `text-slate-400` 11, `text-gray-500` 11, `text-gray-400` 8, `text-slate-600`
  5, plus `hover:text-slate-600` 3 and `hover:text-gray-600` 3 →
  `hover:text-muted-foreground`.
- **The page root ×1 → `bg-background`** — `ConstructionTrackerPage:198`'s
  `bg-slate-50`, under §1f case 1 as amended by this task. It is the **only**
  `bg-background` this task writes.
- Neutral fills ×20: resting `bg-slate-50` **6 of 7** (the seventh is the page
  root above), `bg-slate-100` 4, `bg-gray-50` 2,
  `bg-slate-200` 1, `bg-gray-100` 1 → `bg-muted`; interaction
  `hover:bg-gray-100` 4, `hover:bg-slate-50` 1 → `hover:bg-accent`,
  `hover:bg-gray-50/75` 1 → `hover:bg-accent/75` — §1f case 2, settled below.
- `bg-slate-900` ×1 → `bg-foreground` (`ProjectUpdateFeed:130`, the photo
  lightbox panel; §1b row, ΔE 8.20 `noted`; it carries no text).
- **Indigo ×25, split by §1k** — see the next section: 2 → `*-primary-text`,
  23 → `primary` / `accent` / `border`.
- `text-white` ×4 → `text-primary-foreground`; the other six are
  `GAP-NO-SURFACE`.
- `hover:text-red-600` ×3 → `hover:text-destructive` — the free-standing
  destructive controls only (`AssetTable:211`, `MilestoneTimeline:136`,
  `ProjectUpdateFeed:92`), each an icon-only `<button>`/`<Button>` on a neutral
  surface, which is exactly §1j's "a destructive control".

`27 + 38 + 21 + 23 + 65 + 1 + 20 + 1 + 25 + 4 + 3 = 228`, reading the bullets in
order: `bg-card`, border/divide, `border-input`, `text-foreground`,
`text-muted-foreground`, `bg-background` (the page root), neutral fills,
`bg-foreground`, indigo, `text-white`, red. The total is **unchanged** by the
operator's answer: the page root was already one of the 228 migrated
occurrences; only its target moved, from `bg-muted` to `bg-background`. For the
same reason the disposition table (228 / 83 / 276), every per-file and
per-directory row, all seven gap-code counts, the 200 exception pairs and the
276 ledger rows are **all unchanged** — the ledger and exceptions record what is
*kept*, and nothing kept changed.

**Opacity modifiers are carried over verbatim**, never dropped and never rounded
to a different `N`: `border-slate-200/80` → `border-border/80`,
`border-gray-200/60` → `border-border/60`, `hover:bg-gray-50/75` →
`hover:bg-accent/75`, and `hover:bg-indigo-700` → `hover:bg-primary/90` per
§1i's named target. §1i measures such a target against the base token with the
alpha declared **unmeasured**.

Each of the 228 takes its `dark:` sibling with it: **83 deletions**. All 113 of
`asset-management`'s migrations carry no `dark:` sibling at all, because that
directory has none.

## §1k applied — which brand classes are characters

§1k asks one question per call site, from the JSX, with no measurement: *does
this element paint glyphs of text?* Traced at every site, not assumed.

**Characters — take `text-primary-text`, floor 4.5:1 (2 occurrences).**

| Site | Class → target | Why it is text | Surface | Today → after |
| --- | --- | --- | --- | --- |
| `ConstructionTrackerPage:353` | `text-indigo-700` → `text-primary-text` | `<div>` whose child is `{t("projects.card.physicalProgress", …)}` | `bg-indigo-50` → `--accent` | 7.2164 → **4.6547** |
| `ConstructionTrackerPage:356` | `text-indigo-900` → `text-primary-text` | `<div>` whose child is `{selectedProjectDetail.physical_progress_pct}%` | `--accent` | 10.2604 → **4.6547** |

Both `dark:` siblings (`dark:text-indigo-300`, `dark:text-indigo-100`) are
deleted with them.

**Graphical — keeps `*-primary`, floor 3:1 (19 occurrences).** Ten are
`text-`-prefixed brand classes on an element that paints no glyphs; nine are
non-`text-` utilities, which §1k makes graphical always.

| Site | Element | Surface traced from the JSX | `--primary` on it |
| --- | --- | --- | --- |
| `MilestoneTimeline:60` | `<ListOrdered …/>`, self-closing | card `bg-white` → `--card` | 3.4054 |
| `ProjectUpdateFeed:31` | `<Camera …/>` | card → `--card` | 3.4054 |
| `ConstructionTrackerPage:203` | `<HardHat …/>` | header card → `--card` | 3.4054 |
| `AssetMovementHistoryModal:64` | `<Clock …/>` inside an `<h2>` that renders text — §1k is asked of *the element carrying the class* | modal panel → `--card` | 3.4054 |
| `AssetSummaryCards:52` | `<Archive/>` in a `bg-indigo-50` tile | `bg-indigo-50` → `--accent` | **3.0427** |
| `ConstructionTrackerPage:283`, `:438` | `<RefreshCw … animate-spin/>` | page shell `bg-slate-50` → **`--background`** | **3.3091** |
| `MilestoneTimeline:127` `hover:text-indigo-600` | `<button>` whose only child is `<Edit2/>` | card → `--card` | 3.4054 |
| `AssetTable:191` `hover:text-indigo-600` | `<Button>` whose only child is `<History/>` | card → `--card` | 3.4054 |
| `ProjectSummaryCard:94` `hover:text-indigo-300` | `<button>` whose only child is `<Edit2/>` | `bg-black/50` scrim over a cover photo — **no token, unmeasurable** | declared |

The nine non-`text-` indigo utilities: `bg-indigo-600` ×6 → `bg-primary`
(three `<Button>` fills, two progress-bar fills, one filter chip),
`hover:bg-indigo-700` ×3 → `hover:bg-primary/90`, plus the tint surfaces
`bg-indigo-50` ×2 and `bg-indigo-200` ×1 → `bg-accent`, and
`border-indigo-100` ×1 → `border-border`, which takes its explicit §1e row over
`GAP-BORDER-100` per the appendix's † note. `6 + 3 + 2 + 1 + 1 = 13`, which with the ten
`text-` graphical sites gives **23** graphical. With the two `text-primary-text`
sites that is **25** migrating indigo occurrences in all, `dark:` siblings
excluded: `text-indigo-600` 7, `bg-indigo-600` 6, `hover:bg-indigo-700` 3,
`bg-indigo-50` 2, `hover:text-indigo-600` 2, `bg-indigo-200` 1,
`border-indigo-100` 1, `hover:text-indigo-300` 1, `text-indigo-700` 1,
`text-indigo-900` 1.

## The context-dependent cases, settled at the real call sites

**The verification tests cannot detect a wrong choice in any of these.** They
are a **human review duty on this diff**.

**§1f case 1 — `bg-white` ×27 all take `bg-card`.** Sixteen are card, panel or
modal surfaces; eleven are the repeated `bg-white … border border-gray-200`
card shell in `asset-management`. **Zero raw `<input>`/`<select>`/`<textarea>`
in these 14 files declares a background class at all**, so APRAS-80's
already-accepted precedent (raw form-control fills take `bg-card`, while
`components/ui/` primitives use `bg-background`; the two are byte-identical in
`:root` and diverge only under a tenant theme) is **not exercised here**. It is
recorded, not resolved.

**The page root, `ConstructionTrackerPage:198` — `bg-background`, by operator
ruling.** The root is `min-h-screen bg-slate-50 dark:bg-slate-950`: the element
**is** the page. Revision 2 of this spec sent it to `bg-muted`, because §1f case
1's rule is textually scoped to `bg-white` / `text-white` / `border-white` and
`bg-slate-50`'s §1b row offers only `bg-muted` / §1f case 2. The operator was
asked and answered **`bg-background`**. It therefore takes `bg-background`,
under the amendment this task carries and the next section states.

Measured, so the move is not taken on faith: `bg-slate-50` is
`oklch(98.4% 0.003 247.858)` and `--background` is `oklch(0.99 0 0)` — ΔL
**0.60**, ΔE **0.67**, a *smaller* move than the 2.61 the `bg-muted` row would
have given it. This is a measurement, **not a new table row**: no row is added
and `bg-slate-50`'s existing row is left byte-identical, because a page root is
now resolved by §1f case 1 before its §1b row is consulted.

**What the answer changes under a tenant theme**, which no contrast figure
shows: `background` is derived as `snap_to_gamut(OklchColor(0.99, 0.0, 0.0))` —
a fixed neutral, **not placed at the tenant hue** — while `muted` is
`_at(_LIGHT_MUTED, hue)`, i.e. `(0.96, 0.01)` **at the tenant's hue**
(`backend/app/core/branding.py:_neutral_family`, lines 609–612). The operator's
`bg-background` therefore keeps the whole page canvas hue-free for every tenant,
where `bg-muted` would have tinted it with the brand. Under the default theme
the two differ only in lightness, 0.99 against 0.96.

**§1f case 2 — `bg-muted` versus `bg-accent`.** Fourteen resting fills take
`bg-muted` (the page shell is no longer among them): the three metric panels at
`BudgetVsActualProgressBar:63,72,87` and its progress track at `:53`; the
column and card surfaces at `MilestoneTimeline:86`, `ProjectUpdateFeed:49,61`
and its photo placeholder at `:111`; `ProjectSummaryCard:66,150,168`; the
`<thead>` at `AssetTable:86`, the mono asset-tag chip at `:118`, and the
movement card at `AssetMovementHistoryModal:98`. Six interaction fills take
`bg-accent`: the four inactive tabs' `hover:bg-gray-100` at
`AssetsInventoryPage:193,205,217,229`, `ConstructionTrackerPage:427`'s
`hover:bg-slate-50`, and `AssetTable:112`'s `hover:bg-gray-50/75` →
`hover:bg-accent/75`.

**§1f case 3 — emerald 500–700.** The band holds **9** non-`dark:` occurrences
here and **none migrates**: every one is a non-interactive status glyph, badge
text, figure or progress fill inside sets 1–4, 6, 7, 11, 13 and 15. This
directory pair contains no interactive emerald fill, so the pilot's
`bg-emerald-600 → bg-primary` move is not exercised.

## Contrast, re-derived by importing `frontend/src/lib/contrast.ts`

Measured by importing `contrastRatio` and `parseOklch` from
`frontend/src/lib/contrast.ts` — never reimplemented — with token values read
from `src/index.css` and palette values read from
`node_modules/tailwindcss/theme.css` (**Tailwind 4's OKLCH palette**). The
measurement reproduces APRAS-78's and APRAS-80's published figures to the digit
(`--primary-foreground` on `--primary` 5.7588, `--muted-foreground` on `--muted`
4.6684, `--primary-text` on `--card` 5.2096, `text-red-700` on `bg-red-50`
5.9842), which is the check that it is the same measurement.

| Pair | Background | Today | After |
| --- | --- | --- | --- |
| Headings `text-slate-900` / `text-gray-900` → `text-foreground` | `--card` | 17.8448 / 17.7467 | **19.8801** |
| Secondary text `text-slate-500` / `text-gray-500` → `text-muted-foreground` | `--card` | 4.7670 / 4.8357 | **5.2249** |
| `text-gray-600` → `text-muted-foreground` | `--card` | 7.5608 | **5.2249** |
| Table head/panel text `text-slate-500` on `bg-slate-50` → on `bg-muted` | `--muted` | 4.5540 | **4.6684** |
| Asset-tag chip `text-gray-600` on `bg-gray-100` → on `bg-muted` | `--muted` | 6.8711 | **4.6684** |
| **`text-slate-400` / `text-gray-400` → `text-muted-foreground`** ×19 | `--card` | 2.6282 / 2.6023 | **5.2249** — repairs an AA failure at 19 sites |
| Primary buttons `text-white` on `bg-indigo-600` → `text-primary-foreground` on `bg-primary` | `--primary` | 6.4414 | **5.7588** |
| **Gauge label `text-indigo-700` → `text-primary-text`** | `--accent` | 7.2164 | **4.6547** |
| **Gauge figure `text-indigo-900` → `text-primary-text`** | `--accent` | 10.2604 | **4.6547** |
| Brand icons `text-indigo-600` → `text-primary` (graphical, floor 3) | `--card` | 6.4414 | **3.4054** |
| **Spinners → `text-primary` on the page root** (graphical, floor 3) | `--background` | 6.1536 | **3.3091** |
| Tile glyph `AssetSummaryCards:52` → `text-primary` (graphical, floor 3) | `--accent` | 5.7621 | **3.0427** |
| Progress fill `bg-indigo-600` → `bg-primary` on `bg-slate-100` → `bg-muted` (graphical) | `--muted` | 5.8754 | **3.0427** |
| Delete icon `hover:text-red-600` → `hover:text-destructive` (graphical, floor 3) | `--card` / `--muted` | 4.8619 / 4.6446 | **4.8073 / 4.2953** |

**No full-opacity text pair this task produces falls below 4.5:1.** The tightest
is `--primary-text` on `--accent` at 4.6547 and `--muted-foreground` on
`--muted` at 4.6684.

### Kept pairs whose *surface* moves, measured so nobody attributes them later

A kept foreground can sit on a migrated background. All four such pairs stay far
above AA, so **this migration converts no passing pair into a failing one**:
`text-slate-700` on `bg-slate-50` → on `--muted` 9.8820 → **9.2424**;
`text-gray-700` on `bg-gray-50` → **9.2081** (from 9.8728); `text-slate-800`
14.0024 → **13.0962**; `text-gray-800` on `bg-gray-100` → `--muted` 13.3451 →
**13.1205**.

The three kept status **fills** whose track migrates move by at most 0.0712.
Two were already below the 3:1 graphical floor before this task and one,
`bg-red-500`, was above it and stays above it: `bg-emerald-500` 2.2832
→ **2.2366**, `bg-red-500` 3.4842 → **3.4130**, `bg-amber-500` 1.9567 →
**1.9167**, each against `bg-slate-100` → `--muted`. Pre-existing, declared,
not repaired here.

### Declared sub-AA or unmeasurable, none of them introduced by this task

1. `--destructive` on `--muted` is **4.2953** — below 4.5 but comfortably over
   the 1.4.11 graphical floor of 3:1, and the only site is
   `ProjectUpdateFeed:92`, an **icon-only** delete `<button>` in a
   `bg-slate-50` → `bg-muted` card. Today the same icon measures 4.6446,
   which is `red-600` on `slate-50` — the literal the site carries, not
   `--destructive` on `slate-50` (4.5925).
   Graphical, so it passes; named rather than hidden.
2. `--primary` on `--accent` / `--muted` is **3.0427** at **two** sites
   (`AssetSummaryCards:52`'s tile glyph on `--accent`, and
   `ConstructionTrackerPage:359/361`'s progress fill on `--muted`). It clears
   1.4.11 by 0.043 and, for a pale tenant brand, does not clear it at all. §1k
   routes it there deliberately and records it as APRAS-68 behaviour predating
   APRAS-77; this child changes the class and must not be read as having
   introduced the number. The **two spinners** at
   `ConstructionTrackerPage:283,438` were in this list in revision 2, when the
   page root was going to `bg-muted`; with the operator's `bg-background` they
   measure **3.3091** instead and clear the graphical floor by 0.309. That is
   the one figure the operator's answer improves.
3. `ProjectSummaryCard:94`'s `hover:text-primary` sits on a `bg-black/50` scrim
   over a user-uploaded cover photo. **Unmeasurable by construction** — the
   background carries no token and no fixed colour. Declared, not asserted.
4. Unchanged pre-existing failures, all kept verbatim: `text-amber-600` on
   `bg-amber-100` **2.8643** (three status glyphs), `text-emerald-600` on
   `bg-emerald-50` **3.5279**, `text-slate-300` on `--card` **1.4844** (the
   empty-state `<Building2/>`), and the three progress fills above.
5. **No APRAS-90 site exists in these two directories.** APRAS-90 owns brand
   text carrying an opacity modifier over a brand tint; this child produces no
   `text-primary-text/N` and no `text-primary/N` anywhere. The three opacity
   modifiers it does carry over (`/80`, `/75`, `/60`) are all border or
   background utilities.

### The consequence the table forces and §1i forbids repairing

Three ghost close-buttons carry `text-slate-400 hover:text-slate-600`
(`MilestoneFormModal:81`, `ProjectFormModal:107`, `ProjectUpdateModal:67`) and
three carry `text-gray-400 hover:text-gray-600` (`AssetFormModal:144`,
`AssetMovementHistoryModal:78`, `StockMovementModal:105`). Both classes in each
pair map to `text-muted-foreground`, so after the migration the class list reads
`text-muted-foreground hover:text-muted-foreground` and **the hover darkening
disappears**. §1i forbids deleting the now-redundant class — that is a markup
change, not a colour change — so the substitution is made in place and the
redundancy is left. It is a published consequence of §1d's rows, not a defect of
this child, and it is the natural companion follow-up to APRAS-90.

## The guard suite — what changes

Re-read against the file as it stood at `2c58a76`. The counts in item 4 are
**provenance**: if a sibling lands before this task, the exception and
pinned-file totals at `BASE` will be larger, which makes the memo hoist more
necessary, never less. The decidable requirement is the wall-time ceiling, not
the totals.

1. `MIGRATED_DIRECTORIES` gains **two** entries —
   `"src/features/project-management/components"` and
   `"src/features/asset-management/components"`. APRAS-78's comment says each
   sibling appends exactly one; this child's operator-given scope is two
   directories, so it appends two and says so in the comment.
2. `describe("MIGRATED_DIRECTORIES")`'s two tests each gain **two** `toContain`
   assertions, matching the three already there
   (`…/project-management/components/ConstructionTrackerPage.tsx` and
   `…/asset-management/components/AssetTable.tsx` for the pinned-files test).
3. A new **appended, directory-scoped** `describe("APRAS-81's ledger
   arithmetic")`, in the shape APRAS-79 and APRAS-80 established: the 14 pinned
   files split 8 / 6 by directory, the 276 ledger rows, the 200 exception pairs,
   the seven gap-code counts, and the sixteen status sets still whole plus the
   swatch map still whole. **No child's existing block is edited.**
4. **The memo hoist APRAS-80 conditionally assigned to this child.** Re-measured
   now at `2c58a76`: the suite runs **50 tests in 1.18 s**, `pinnedFiles()`
   returns **26** files (`src/components/ui` 9, `lot-management/components` 9,
   `visitor-management/components` 8), the exceptions file holds **254** entries
   (APRAS-78 22 + APRAS-79 148 + APRAS-80 84), and
   `it("fails when any single exception is removed")` alone takes
   **863 ms** (883 ms at `a8fc8ab`; neither APRAS-90 nor APRAS-75 touched this
   file). This child adds **200** exceptions and **14** pinned files to whatever those
   totals read at `BASE`; from the `2c58a76` provenance that is **454**
   exceptions over **40** files —
   `O(exceptions × files)` goes 254 × 26 = 6,604 → 454 × 40 = 18,160 scans,
   ×2.75, i.e. ≈**2.4 s** for that single test at today's 0.131 ms per scan,
   over APRAS-80's stated 2 s trigger. (The ≈2.8 s figure of revision 1 rested
   on an 18-file count carried over from APRAS-80's pre-merge tree; the
   conclusion is unchanged, the arithmetic is not.) So this child **must** hoist
   the scan memo out of `violations()` to module scope, keyed on
   `file + "\0" + source`. It stays a pure function of its arguments, so the
   mutated-argument tests keep biting, and no assertion changes. The implementer
   reports the measured wall time after the hoist; the decidable requirement is
   that every individual test in the file finishes under 2 s.

## Files touched

- The eight `frontend/src/features/project-management/components/*.tsx` and the
  six `frontend/src/features/asset-management/components/*.tsx`, per the
  `migrated / deleted / logged` table.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — the two directory
  entries, four `toContain`, the module-scope memo hoist, and the new scoped
  `describe`.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — **200** new
  entries, `src/`-relative, `task` `APRAS-81`.
- `docs/frontend/unmapped-colours.md` — **276** appended rows, one per kept
  occurrence, sorted by file then line, plus a closing `APRAS-81 total`
  paragraph in the shape APRAS-78/79/80 use. Nothing already in the file is
  rewritten.
- `docs/frontend/theme-token-mapping.md` — **one sentence appended inside §1f
  case 1's paragraph**, the operator-authorised amendment; nothing else in the
  file changes, and no line beginning with `|` is added, removed or edited. If
  APRAS-83 has already landed the identical sentence, this file is not touched
  at all.
- `frontend/src/features/__tests__/projectAssetContrast.test.ts` — new.
- `frontend/src/components/__tests__/TenantBrandReach.test.tsx` — extended with
  one migrated component from each directory: `MilestoneTimeline` (renders
  `bg-primary hover:bg-primary/90 text-primary-foreground` and `text-primary`)
  and `AssetSummaryCards` (renders `bg-accent` and `text-primary`), each
  asserted against the tenant token and never against a colour literal.

## Test criteria

1. `npx vitest run src/__tests__/themeTokenMigration.test.ts` green with both
   directories pinned: zero unexcused grammar matches across the 14 files, no
   stale exception, no unknown code, ledger parity in both directions, the
   pilot's 24, APRAS-79's 211 and APRAS-80's 113 untouched, and this block's
   276.
2. The new contrast test asserts, by **importing** `contrastRatio` and
   `parseOklch` from `src/lib/contrast.ts`, that every foreground/background
   pair this task changes either holds ≥ `MINIMUM_CONTRAST_RATIO` or appears in
   an explicit in-file list of declared sub-AA / unmeasurable pairs carrying its
   measured before/after ratio. Ratios to ±0.001 against the tables above, each
   against its declared background. Token values from `src/index.css`, palette
   values from `node_modules/tailwindcss/theme.css`; no colour literal
   hard-coded. Graphical pairs are asserted against the 3:1 floor, text pairs
   against 4.5.
3. The nine existing suites under the two `__tests__/` directories pass
   **unmodified**. None asserts on a class name, so none proves a colour.
4. `npx tsc -b` clean.
5. `npx vitest run --coverage` meets exactly **80 lines / 78 functions / 76
   branches / 80 statements**.
6. `npx eslint` diff-scoped. **The 14 touched files carry 2 errors across 2
   files** (`AssetFormModal.tsx` 1, `StockMovementModal.tsx` 1) — a property of
   those fourteen files, which no sibling touches, so it is stable under either
   landing order. The other three linted files this task touches
   (`themeTokenMigration.test.ts`, `TenantBrandReach.test.tsx` and the new
   `projectAssetContrast.test.ts`) report **0 errors and 0 warnings**, as the
   first two do today. No repository-wide total is asserted, and none is needed:
   this task changes no other linted file, so no repository total can move.
   (Provenance: 375 errors + 2 warnings across 64 files at `2c58a76`.)
7. `git diff --exit-code frontend/src/index.css` succeeds; the only change to
   `docs/frontend/theme-token-mapping.md` is the §1f case 1 sentence, with no
   table row touched; `themeTokenCompile.test.ts` and `themeContrast.test.ts`
   pass unmodified; `brandTextOpacity.test.ts` (APRAS-90's repo-wide sweep)
   passes against the migrated tree; no backend file, no Alembic revision, no
   route-registry entry in the diff; the `.dark` block stays unapplied.

## What this proves, and what it misses

**Proved.** Every substitution is a §1b–1e row, and `themeTokenCompile.test.ts`
already asserts each row's ΔL/ΔE from the compiled stylesheet to ±0.1. The guard
certifies nothing was dropped or silently substituted: each of the 587 is either
gone from the file or present in **both** the ledger and the exceptions file.
The contrast test certifies the pairs that change.

**Not proved, stated plainly.**

- No Playwright, no Storybook, no Chromatic, no Percy, and jsdom does not run
  the Tailwind pipeline: **no pixel and no computed-style proof**.
- **The three §1f cases and every §1k verdict are invisible to every test
  here**, with one exception. `bg-card` vs `bg-background` on a *card*, and
  `bg-muted` vs `bg-accent`, are byte-identical in `:root`; `text-primary` vs
  `text-primary-text` on an icon is two legal classes. A **review duty on this
  diff**. The exception is the page root: `--background` (0.99) and `--muted`
  (0.96) are **different** colours with different tenant behaviour
  (`_LIGHT_BACKGROUND` is a fixed neutral, `_LIGHT_MUTED` is placed at the
  tenant hue — `backend/app/core/branding.py:_neutral_family`), so the operator's
  choice is asserted by class name in the expected results and a wrong target
  there fails a test rather than only a review.
- The rendering *does* move where the table says it moves: 19 `text-*-400`
  sites, the indigo hue shift at 25 (plus 8 deleted `dark:` indigo siblings), `text-*-600` lightening at 17, and the six
  hover-darkening losses named above.
- The **83 deleted `dark:` siblings** change nothing today, because `.dark` is
  never applied. What changes is what the future dark-mode task inherits,
  alongside the 57 `dark:` classes kept — 53 of which live in
  `project-management`, which is the only directory in this pair that has any.
- **The guard cannot enforce per-site completeness**, because the exceptions
  file carries no line number. `AssetTable.tsx` is the worst case: `bg-gray-50`,
  `text-gray-700`, `border-gray-200`, `bg-gray-100` and `text-gray-800` are each
  migrated at one site and kept at another in that one file, and once excused an
  unmigrated occurrence anywhere in it passes. The disposition table
  (228 / 83 / 276 with the per-file split), the sixteen-set inventory, the
  swatch map and the §1k site table are what a reviewer must check the diff
  against.

## Out of scope

Adding `--success` / `--warning` / `--info` tokens; migrating the 20
`focus:ring-blue-500` focus rings (the operator note's open question);
APRAS-90's sub-AA repair tree; deleting the now-redundant
`hover:text-muted-foreground` classes; the 1.4.11 graphical floor for pale
tenant brands; enabling the `.dark` block; visual-regression infrastructure; any
other feature directory; the six `user-administration/pages/` page roots already
written `bg-muted/30`; and any amendment to APRAS-78's mapping table, ledger
rules or grammar **other than** the single operator-authorised §1f case 1
sentence this task carries.

## Expected Results

- [ ] `frontend/src/features/project-management/components/ConstructionTrackerPage.tsx`'s root element — the `min-h-screen` `<div>` returned by `ConstructionTrackerPage`, today `className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 sm:p-6 lg:p-8 space-y-6"` — carries the whitespace-split class token `bg-background` and carries neither `bg-slate-50`, `bg-muted`, `bg-card` nor `dark:bg-slate-950`; `bg-background` appears in exactly one class string across the fourteen migrated `.tsx` files, and `frontend/src/features/asset-management/components/AssetsInventoryPage.tsx`'s root (`container mx-auto px-4 py-8 max-w-7xl space-y-6`) is unchanged, since it declares no background class and is not the page.
- [ ] `docs/frontend/theme-token-mapping.md` contains, inside the `**Case 1 —` paragraph of §1f and before the `**Case 2 —` paragraph, a sentence stating that the "if the element **is** the page it is `bg-background`" clause applies whatever the source class, so that a page root written `bg-slate-50` or `bg-gray-50` takes `bg-background` rather than the `bg-muted` its §1b row gives it, and that §1f case 1 is consulted before that row and before case 2, ending with the marker `(Operator ruling on APRAS-81 and APRAS-83; carried by APRAS-81.)` — placed there either because this task appended it, or because APRAS-83 landed the identical sentence first and this task left the file untouched. **`grep -c -F '(Operator ruling on APRAS-81 and APRAS-83; carried by APRAS-81.)' docs/frontend/theme-token-mapping.md` prints exactly `1`**, so that a file carrying the ruling twice — one sentence from APRAS-83 and a second from this task — FAILS this result, and exactly one sentence in the §1f Case 1 paragraph begins `The second clause of the rule is`. Whichever the case, `git diff BASE..HEAD -- docs/frontend/theme-token-mapping.md` (`BASE` = `git rev-parse "$(git log --format='%H %s' | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-81\):' | tail -1 | cut -d' ' -f1)^"`, the parent of this task's first commit, computed from the repository alone; the project's `<type>(APRAS-81): …` commit-subject convention makes that filter exact, and it deliberately matches subjects rather than whole messages, since sibling commit *bodies* cite neighbouring ids. `BASE` is never `git merge-base HEAD origin/master` — integration runs on local `master`, which is ahead of the remote, so that merge-base resolves 187 files and nine backend/Alembic/route files away from any child's branch point — is never a sha read from an implementation report, since reports live under the gitignored `.meridian/`, and is not the literal `2c58a76` unless this task lands next) is either empty (consumed) or a single added line inside the §1f Case 1 paragraph (carried), and in neither case contains an added or removed line beginning with `|`, any change outside the §1f Case 1 paragraph, or any change to §1b's `bg-slate-50` or `bg-gray-50` rows, to §1f cases 2 and 3, to §1h's gap codes, or to §3b.
- [ ] `npx vitest run src/__tests__/themeTokenCompile.test.ts src/__tests__/themeContrast.test.ts src/__tests__/brandTextOpacity.test.ts` passes with all three files unmodified — no commit whose subject matches `[a-z]+\(APRAS-81\):` touches any of the three, which is how "unmodified" is checked here — the compile test because no mapping-table row moved, and APRAS-90's repo-wide brand-text-opacity sweep because this task writes no `text-primary/N` and no `text-primary-text/N` anywhere.
- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts` passes with `MIGRATED_DIRECTORIES` containing both `"src/features/project-management/components"` and `"src/features/asset-management/components"`, `pinnedFiles()` returning those directories' 8 and 6 source files respectively, and `violations(PINNED, EXCEPTIONS, LEDGER)` returning `[]`.
- [ ] Re-measuring the fourteen files `frontend/src/features/{project-management,asset-management}/components/*.tsx` with the guard's §3b grammar accounts for all 587 occurrences those fourteen files carry before this task — read as `git show "$BASE:<path>"` for each of the fourteen, where `BASE` = `git rev-parse "$(git log --format='%H %s' | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-81\):' | tail -1 | cut -d' ' -f1)^"`, the parent of this task's first commit, computed from the repository alone — never `git merge-base HEAD origin/master`, never a sha from a report — as 228 migrated + 83 deleted `dark:` siblings + 276 left and logged, with both halves closing independently (447 non-`dark:` = 228 + 219; 140 `dark:` = 83 + 57), and the fourteen files together retain exactly 276 grammar matches and zero six-digit hex literals inside a class context.
- [ ] Of the 228 migrated occurrences, exactly 1 becomes `bg-background` (the page root above), 20 become `bg-muted` / `bg-accent` neutral fills — resting `bg-slate-50` ×6, `bg-slate-100` ×4, `bg-gray-50` ×2, `bg-slate-200` ×1, `bg-gray-100` ×1 → `bg-muted`, and `hover:bg-gray-100` ×4, `hover:bg-slate-50` ×1 → `hover:bg-accent`, `hover:bg-gray-50/75` ×1 → `hover:bg-accent/75` — and 27 become `bg-card` (every `bg-white`), the eleven bullet groups summing 27 + 38 + 21 + 23 + 65 + 1 + 20 + 1 + 25 + 4 + 3 = 228; each "becomes" is read against that same file's pre-task content, `git show "$BASE:<path>"`, where `BASE` = `git rev-parse "$(git log --format='%H %s' | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-81\):' | tail -1 | cut -d' ' -f1)^"`, the parent of this task's first commit, computed from the repository alone — never `git merge-base HEAD origin/master`, never a sha from a report.
- [ ] `docs/frontend/unmapped-colours.md` gains 276 rows whose `task` cell is `APRAS-81` — 87 `GAP-NO-TOKEN`, 77 `GAP-TINT`, 51 `GAP-OUT-OF-BUDGET`, 23 `GAP-BORDER-100`, 21 `GAP-SWATCH`, 11 `GAP-OVERLAY`, 6 `GAP-NO-SURFACE` and zero `GAP-UNLISTED` — and `frontend/src/__tests__/themeTokenMigration.exceptions.json` gains exactly 200 entries whose `task` is `APRAS-81`, with the guard's ledger-parity check passing in both directions.
- [ ] Exactly two brand-text sites carry `text-primary-text` — `ConstructionTrackerPage.tsx`'s physical-progress gauge label (was `text-indigo-700`) and its percentage figure (was `text-indigo-900`) — and no `text-primary-text` appears on any non-`text-` utility anywhere in the diff; the ten icon-only brand sites carry `text-primary` / `hover:text-primary` (`MilestoneTimeline.tsx` ×2, `ProjectUpdateFeed.tsx` ×1, `ConstructionTrackerPage.tsx` ×3, `AssetMovementHistoryModal.tsx` ×1, `AssetSummaryCards.tsx` ×1, `AssetTable.tsx` ×1, `ProjectSummaryCard.tsx` ×1).
- [ ] `frontend/src/features/__tests__/projectAssetContrast.test.ts` passes, importing `contrastRatio` and `parseOklch` from `src/lib/contrast.ts` and reading every colour from `src/index.css` and `node_modules/tailwindcss/theme.css` with no hard-coded colour literal, asserting to ±0.001 that `--primary-text` on `--accent` is 4.6547, `--muted-foreground` on `--card` 5.2249 and on `--muted` 4.6684, `--foreground` on `--card` 19.8801, `--primary-foreground` on `--primary` 5.7588, `--destructive` on `--card` 4.8073, and — against the 3:1 graphical floor — `--primary` on `--card` 3.4054, on `--muted`/`--accent` 3.0427, and **on `--background` 3.3091** (the two `ConstructionTrackerPage` spinners, which sit on the page root and so are measured against `--background`, not `--muted`); and declaring in an explicit in-file list, with before/after ratios, the sub-AA or unmeasurable pairs `--destructive` on `--muted` 4.2953 (icon-only), `hover:text-primary` over a `bg-black/50` scrim (unmeasurable), `text-amber-600` on `bg-amber-100` 2.8643, `text-emerald-600` on `bg-emerald-50` 3.5279, `text-slate-300` on `--card` 1.4844, and the three kept progress fills `bg-emerald-500` 2.2832 → 2.2366, `bg-red-500` 3.4842 → 3.4130 and `bg-amber-500` 1.9567 → 1.9167.
- [ ] The same test asserts that every kept foreground sitting on a migrated background still clears 4.5:1: `text-slate-700` on `--muted` 9.2424, `text-gray-700` on `--muted` 9.2081, `text-slate-800` on `--muted` 13.0962 and `text-gray-800` on `--muted` 13.1205 — i.e. no pair that passes AA today fails AA after the change — and that no kept foreground is measured against `--background`, because no text sits directly on `ConstructionTrackerPage`'s page root: its only descendants painting on it are the two spinner icons.
- [ ] Grouping every grammar match in the fourteen files by `(file, class-context span)` yields **zero** spans that hold both a migrated occurrence and a kept occurrence whose ledger gap code is `GAP-TINT`; and all seven branches of `AssetTable.tsx`'s `getCategoryBadgeClass` (including its `bg-indigo-50 text-indigo-700 border-indigo-200` and `bg-gray-50 text-gray-700 border-gray-200` branches) retain their original classes under code `GAP-SWATCH`, as do all six branches of `getConditionBadgeClass` and all four `STATUS_BADGES` / three `COLUMNS` badge strings in `ProjectSummaryCard.tsx` and `MilestoneTimeline.tsx`.
- [ ] No emerald class and no `text-red-*` class migrates anywhere in the fourteen files: `bg-emerald-500`, `bg-emerald-50`, `bg-emerald-100`, `text-emerald-600`, `text-emerald-700`, `text-emerald-800`, `border-emerald-200`, `bg-red-50`, `bg-red-100`, `bg-red-500`, `text-red-600`, `text-red-700`, `text-red-800` and `border-red-200` all still appear with their original text and each has a ledger row; the only red that moves is `hover:text-red-600` → `hover:text-destructive` at exactly three sites, in `AssetTable.tsx`, `MilestoneTimeline.tsx` and `ProjectUpdateFeed.tsx`.
- [ ] No `dark:` sibling of a migrated base survives in the eight `project-management` files: zero `dark:bg-slate-900`, `dark:bg-slate-950`, `dark:bg-slate-800/40`, `dark:bg-slate-800/60`, `dark:text-slate-100`, `dark:text-slate-400`, `dark:text-slate-500`, `dark:text-indigo-400`, `dark:text-indigo-300`, `dark:text-indigo-100`, `dark:bg-indigo-950/50`, `dark:bg-indigo-800`, `dark:border-indigo-900`, `dark:hover:text-slate-200` or `dark:hover:bg-slate-800` remains, and none appears in the ledger; the six `asset-management` files contain zero `dark:` occurrences before and after.
- [ ] Every opacity modifier is carried over verbatim — none dropped, none rounded to a different `N` — which the fourteen migrated files show absolutely: they contain `border-border/80` ×2, `border-border/60` ×1, `hover:bg-accent/75` ×1 and `hover:bg-primary/90` ×3, and contain **zero** occurrences of `border-slate-200/80`, `border-gray-200/60`, `hover:bg-gray-50/75` and `hover:bg-indigo-700`, and zero occurrences of any `text-primary/N` or `text-primary-text/N`.
- [ ] `describe("the pilot's own ledger arithmetic")`, `describe("APRAS-79's ledger arithmetic")` and `describe("APRAS-80's ledger arithmetic")` still pass with their assertions unedited (the literals 24, 211/148 and 113/84 still present in the file), and no APRAS-78, APRAS-79 or APRAS-80 ledger row or exceptions entry is modified, which is checkable by filter with no baseline at all: `docs/frontend/unmapped-colours.md` holds exactly 24 rows whose task cell is `APRAS-78`, 211 whose task cell is `APRAS-79` and 113 whose task cell is `APRAS-80`, and `frontend/src/__tests__/themeTokenMigration.exceptions.json` holds exactly 22 entries whose `task` is `APRAS-78`, 148 whose `task` is `APRAS-79` and 84 whose `task` is `APRAS-80` — counts unaffected by whichever sibling lands first.
- [ ] `git diff --exit-code frontend/src/index.css` succeeds, and the set of paths this task's own commits touch — `git log --format='%H %s' | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-81\):' | cut -d' ' -f1 | xargs -n1 git show --pretty=format: --name-only | sort -u`, which needs no branch point, no range and no report: the project's `<type>(APRAS-81): …` commit-subject convention puts this task's id in the subject of each of its commits and in no sibling's, so the set is exactly this task's regardless of which of APRAS-81 / APRAS-83 landed first, and it ignores the working tree and the index — contains no backend file, no Alembic revision, no route-registry change, no file under `frontend/src/components/ui/`, `frontend/src/features/lot-management/` or `frontend/src/features/visitor-management/`, and no path outside this set of twenty-three: the fourteen `.tsx` under the two component directories, `frontend/src/__tests__/themeTokenMigration.test.ts`, `frontend/src/__tests__/themeTokenMigration.exceptions.json`, `frontend/src/__tests__/brandTextRole.test.ts`, `frontend/src/components/__tests__/TenantBrandReach.test.tsx`, `frontend/src/features/__tests__/projectAssetContrast.test.ts`, `docs/frontend/unmapped-colours.md`, `docs/frontend/theme-token-mapping.md`, `docs/tasks/APRAS-81-spec.md` and `docs/tasks/APRAS-81-mock.html`. `brandTextRole.test.ts` is APRAS-87's guard (`0815915`), which postdates this spec: it reconciles a live scan of bare `text-primary` against a declared set of graphical sites, so a migration that moves an icon onto `text-primary` must append its declaration there or the guard fails. This task's change to it must be a pure append inside `GRAPHICAL_PRIMARY_SITES` — no existing declaration removed or weakened, and no change to that file's surfaces, ratios or imports. (The untracked `docs/tasks/APRAS-82…APRAS-87` spec and mock files the working tree already carries belong to other tasks; APRAS-81 must not stage or commit them, so they never appear in that list.)
- [ ] `frontend/src/components/__tests__/TenantBrandReach.test.tsx` passes with two added cases that mount `MilestoneTimeline` and `AssetSummaryCards` under the mocked `useTenantProfile`, assert `getComputedStyle(document.documentElement).getPropertyValue("--primary")` equals the mocked theme's value, and assert the rendered markup contains, per component, the class strings it actually produces — `MilestoneTimeline` `bg-primary`, `hover:bg-primary/90`, `text-primary-foreground` and `text-primary`; `AssetSummaryCards` `bg-accent` and `text-primary` (its single brand call site, `AssetSummaryCards.tsx:52`, is a tile, so it yields no `bg-primary` and the case must not assert one) — never a colour literal.
- [ ] `npx tsc -b` completes with no error.
- [ ] `npx vitest run --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint` over the fourteen touched component files reports at most **2 errors and 0 warnings**, in at most the two files that carry them today (`AssetFormModal.tsx` 1, `StockMovementModal.tsx` 1), and `npx eslint` over the three other linted files this task touches — `frontend/src/__tests__/themeTokenMigration.test.ts`, `frontend/src/components/__tests__/TenantBrandReach.test.tsx` and the new `frontend/src/features/__tests__/projectAssetContrast.test.ts` — reports **0 errors and 0 warnings**. No repository-wide total is asserted and none is needed: those seventeen are the only linted files this task changes, so a repository total can neither grow through an act of APRAS-81 nor be moved by a sibling into this result. (Provenance: the 14 component files measure exactly 2 errors / 0 warnings at `2c58a76`, and the first two test files 0 / 0; repository-wide, 375 errors + 2 warnings across 64 files.)
- [ ] The nine existing suites in `frontend/src/features/project-management/__tests__/` and `frontend/src/features/asset-management/__tests__/` pass, and no commit whose subject matches `[a-z]+\(APRAS-81\):` touches any file under either `__tests__/` directory, so they pass unmodified.
- [ ] The scan memo inside `violations()` in `frontend/src/__tests__/themeTokenMigration.test.ts` is hoisted to module scope, keyed on the file path and its source text, and `npx vitest run src/__tests__/themeTokenMigration.test.ts --reporter=verbose` reports every individual test finishing under 2 s — including `it("fails when any single exception is removed")` — with `frontend/src/__tests__/themeTokenMigration.exceptions.json` holding exactly 200 entries whose `task` is `APRAS-81` and `pinnedFiles()` returning, among its results, all fourteen `.tsx` files of this task's two component directories — both absolute by filter, so neither needs a baseline and neither moves when a sibling lands first. (Provenance at `2c58a76`: that test measures 863 ms against 254 exceptions over 26 pinned files, and this task would take it to 454 over 40.)
