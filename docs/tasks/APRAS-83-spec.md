# APRAS-83 — Migrate finance, purchases and access control to semantic theme tokens

Child 6 of 8 of the APRAS-77 split, specified against the **amended** contract:
APRAS-78's three artefacts as extended by APRAS-79 / APRAS-80 and amended by
APRAS-88 at `c7c42fc`. This task **consumes** that contract and may not extend
it — with **one exception it does not own**: the operator-authorised scope
sentence of §1f case 1, which **APRAS-81 owns** and which this task
*consume-or-carries* (see *The §1f case 1 amendment, consumed not owned*
below). Outside that one sentence: no row added to
`docs/frontend/theme-token-mapping.md`, no new gap code, no token in
`frontend/src/index.css`. Every other call below is an *application* of a
published rule to a named call site.

This task and APRAS-81 are **order-independent**, so no expected result below
names a literal sha. Where a result needs the tree as it stood immediately
before this task, it uses **`BASE`**, computed from the repository alone:

> **`BASE` is the parent of this task's first commit:**
>
> ```
> git rev-parse "$(git log --format='%H %s' \
>   | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-83\):' | tail -1 | cut -d' ' -f1)^"
> ```
>
> and `PRE(<path>)` = `git show "$BASE:<path>"`.

The filter is exact because the project's commit convention puts `(APRAS-83):`
in the **subject** of every commit this task makes and in no other task's
subject; matching the subject rather than the whole message is load-bearing,
because sibling commit *bodies* cite neighbouring ids. `BASE` is never
`git merge-base HEAD origin/master` — integration runs on local `master`, which
is ahead of the remote — and never a sha read from an implementation report,
since reports live under the gitignored `.meridian/`. Every "as measured today"
figure quoted below is **provenance**, not a baseline any result asserts a
delta against.

Three directories, not one, because the operator scoped this child that way.
They are complementary: `finance` and `access-control` are `dark:`-heavy
slate/indigo features (192 and 162 occurrences, **all 162** of the trio's
`dark:` occurrences between them), `purchase-management` is a gray/amber
feature with **zero** `dark:` occurrences and **zero** indigo (180). The three
exercise both halves of §1g and both halves of §1f case 3.

## Scope

`frontend/src/features/finance/components` (ten files),
`frontend/src/features/purchase-management/components` (six) and
`frontend/src/features/access-control/components` (six) — twenty-two files —
migrated from hard-coded Tailwind palette classes to the tokens the table
names, with every class left behind logged in the ledger and excepted in the
guard; then the three directory paths appended to `MIGRATED_DIRECTORIES`.

Not covered: `finance/hooks/`, `purchase-management/hooks/`,
`purchase-management/utils/`, `access-control/hooks/` or any `__tests__/`
(none of the four non-component source files — `useAccessControl.ts`,
`usePurchaseRequests.ts`, `comparison.ts`, `formatters.ts` — contains a palette
class, and the guard's non-recursive directory walk does not reach them), any
other feature directory, `index.css`, the backend, the `.dark` block, and any
*further* amendment to the mapping table — no row, no budget figure, no gap
code — or to the ledger's rules or the guard's grammar (§3b). The single §1f
case 1 sentence below is consumed, and carried only if APRAS-81 has not landed
it first.

**Mockup:** `docs/tasks/APRAS-83-mock.html` records the operator's page-shell decision. This is a token substitution; every migrated pair is either
byte-identical in `:root` or a published, budgeted colour move already
tabulated. The visible changes are enumerated under *What this proves, and what
it misses*.

## The §1f case 1 amendment, consumed not owned

**APRAS-81's spec owns this amendment** (`docs/tasks/APRAS-81-spec.md`, *The
operator-authorised §1f case 1 amendment*). This task does **not** re-derive it,
does not restate its justification, and must not write it into
`docs/frontend/theme-token-mapping.md` a second time. The amendment extends §1f
case 1's second clause — *if the element **is** the page it is `bg-background`*
— beyond its `bg-white` / `text-white` / `border-white` scoping, and records that
case 1 is consulted **before** the class's own §1b row and before case 2.

The sentence, verbatim and byte-identical with APRAS-81's:

> The second clause of the rule is **not** scoped to `bg-white`: an element that
> **is** the page takes `bg-background` whatever its source class, so a page
> root written `bg-slate-50` or `bg-gray-50` takes `bg-background` and **not**
> the `bg-muted` its §1b row would otherwise give it — case 1 is consulted
> before the row, and before case 2. (Operator ruling on APRAS-81 and APRAS-83;
> carried by APRAS-81.)

The trailing parenthetical is a **marker**, not decoration: the exact byte string

```
(Operator ruling on APRAS-81 and APRAS-83; carried by APRAS-81.)
```

occurs nowhere else in the repository, so its **count** in
`docs/frontend/theme-token-mapping.md` is what distinguishes the outcomes, and
that count is what the expected result asserts.

**Either landing order is legal; carrying twice is not.**

- if **APRAS-81 lands first**, this task finds the sentence already present,
  changes **no line** of the mapping table, and sends
  `FinanceDashboardPage:48` to `bg-background` citing §1f case 1 as amended;
- if **this task lands first**, it appends that identical sentence, ending in
  that identical marker, inside the §1f Case 1 paragraph and nowhere else, and
  APRAS-81 then finds it present and leaves the file byte-unchanged.

After this task, whichever the order, `grep -c -F` of the marker over
`docs/frontend/theme-token-mapping.md` prints exactly `1`, and no line beginning
with `|` is added or removed anywhere in that file.

**What must not change, and a reviewer must confirm did not:** no table row is
added, removed or retargeted; no budget figure moves; no gap code is added or
redefined; §3b is untouched; §1b's `bg-slate-50` / `bg-gray-50` rows are
byte-identical; §1f cases 2 and 3 are byte-identical. `themeTokenCompile.test.ts`
therefore passes unmodified, because it asserts rows and no row moved.

## The re-measurement

Measured now, at `a8fc8ab`, over the twenty-two non-test `.tsx` files with the
§3b grammar exactly as the guard builds it (scale alternatives longest-first,
both word boundaries, opacity suffix). **Nothing here is carried over from a
sibling.**

| Figure | Value |
| --- | --- |
| Palette occurrences | **534** — the task's reported figure reproduces exactly |
| Files | **22** — reproduces exactly |
| Distinct classes | 104 |
| Six-digit hex literals anywhere in the 22 files | **0** |
| `dark:`-prefixed | **162** (30.3%), against **372** non-`dark:` |
| `finance/components` | 10 files, **192** occurrences, **83** `dark:` |
| `purchase-management/components` | 6 files, **180** occurrences, **0** `dark:` |
| `access-control/components` | 6 files, **162** occurrences, **79** `dark:` |
| Per file | QuoteComparisonTable 44, FacialTemplateSyncPanel 42, RegisterDeviceModal 38, CashBalanceCard 36, FinanceDashboardPage 33, PurchaseRequestDetailModal 33, DeviceTable 32, QuoteFormModal 31, PurchaseRequestsPage 26, SelectQuoteModal 24, GateMonitorPage 22, PurchaseRequestFormModal 22, BudgetVsActualTable 21, InvoicePreviewModal 20, TransactionFormModal 19, AccessEventFeed 18, StatementTable 16, BudgetLineFormModal 14, CategoryFormModal 14, CategoryTransactionDrilldown 13, AccessControlPage 10, StatementChart 6 |

## Pairing a `dark:` class with its base

The settled rule: a `dark:` occurrence pairs with the class in the **same
class-context span**, with the **same utility prefix**, the **same non-`dark:`
variant chain**, **nearest preceding**. A `dark:` sibling of a migrated class
is deleted (§1g); a `dark:` sibling of a kept class is left and logged under
its base's code.

Applied mechanically here, **every one of the 162 `dark:` occurrences has a
base**; there is no orphan.

The variant-chain clause is load-bearing at **seven** sites: the four
`text-slate-400 hover:text-slate-600 … dark:hover:text-slate-200` buttons
(`BudgetLineFormModal:60`, `CategoryFormModal:50`, `TransactionFormModal:74`,
`InvoicePreviewModal:56`), where the naive nearest-preceding base is the
resting `text-slate-400` and the chain-correct base is the `hover:` class; and
the three `dark:hover:bg-*` siblings at `InvoicePreviewModal:56`,
`RegisterDeviceModal:61` and `CategoryTransactionDrilldown:69`, whose
chain-correct bases are `hover:bg-slate-100`, `hover:bg-slate-100` and
`hover:bg-indigo-50` respectively. In all seven both candidates migrate, so the
disposition is unchanged — stated so a reviewer need not re-derive it. The
clause is applied from the start regardless; it is the rule, not a tiebreak.

## The disposition of all 534

| Disposition | n |
| --- | --- |
| Light class migrated to a token | **233** |
| `dark:` sibling of a migrated class, **deleted** (§1g) | **111** |
| Left untouched and logged | **190** (139 non-`dark:`, 51 `dark:`) |
| **Total** | **534** |

The two halves close independently: non-`dark:` 372 = 233 + 139, and `dark:`
162 = 111 + 51.

Per file, as `migrated / deleted / logged`:

| File | m / d / l |
| --- | --- |
| `BudgetLineFormModal.tsx` | 5 / 4 / 5 |
| `BudgetVsActualTable.tsx` | 9 / 6 / 6 |
| `CashBalanceCard.tsx` | 12 / 12 / 12 |
| `CategoryFormModal.tsx` | 5 / 4 / 5 |
| `CategoryTransactionDrilldown.tsx` | 5 / 4 / 4 |
| `FinanceDashboardPage.tsx` | 18 / 15 / 0 |
| `InvoicePreviewModal.tsx` | 13 / 7 / 0 |
| `StatementChart.tsx` | 2 / 2 / 2 |
| `StatementTable.tsx` | 3 / 3 / 10 |
| `TransactionFormModal.tsx` | 9 / 5 / 5 |
| `PurchaseRequestDetailModal.tsx` | 15 / 0 / 18 |
| `PurchaseRequestFormModal.tsx` | 11 / 0 / 11 |
| `PurchaseRequestsPage.tsx` | 23 / 0 / 3 |
| `QuoteComparisonTable.tsx` | 24 / 0 / 20 |
| `QuoteFormModal.tsx` | 20 / 0 / 11 |
| `SelectQuoteModal.tsx` | 9 / 0 / 15 |
| `AccessControlPage.tsx` | 5 / 5 / 0 |
| `AccessEventFeed.tsx` | 3 / 3 / 12 |
| `DeviceTable.tsx` | 8 / 8 / 16 |
| `FacialTemplateSyncPanel.tsx` | 11 / 11 / 20 |
| `GateMonitorPage.tsx` | 11 / 11 / 0 |
| `RegisterDeviceModal.tsx` | 12 / 11 / 15 |

Per directory: `finance` 81 / 62 / 49 = 192; `purchase-management`
102 / 0 / 78 = 180; `access-control` 50 / 49 / 63 = 162.

The 190 occupy **145** distinct `(file, class)` pairs — 37 in `finance`, 52 in
`purchase-management`, 56 in `access-control` — which is the number of
exceptions entries this task appends.

## The gap codes, each counted from its own membership

| Code | Occ. | Derivation, enumerated |
| --- | --- | --- |
| `GAP-TINT` | **83** | non-`dark:` **57**: `text-red-700` 8, `bg-red-50` 7, `border-red-200` 6, `text-emerald-700` 5, `text-emerald-600` **5** (of 6; `QuoteComparisonTable:300` migrates), `text-red-600` 4, `bg-emerald-50/40` 4, `bg-emerald-100` 3, `bg-red-100` 2, `bg-emerald-50` 2, `text-emerald-900` 2, and one each of `text-emerald-500`, `text-red-500` (of 7; the other six migrate), `bg-slate-100` (of 2), `text-slate-600` (of 2), `border-emerald-200`, `text-gray-900` (of 21), `bg-emerald-50/60`, `border-emerald-300`, `border-gray-200` (of 22). Plus **26** `dark:` siblings: `dark:text-red-400` 7, `dark:text-emerald-400` 6, `dark:bg-red-950/50` 4, `dark:bg-emerald-950/50` 3, `dark:border-red-900/50` 2, and one each of `dark:bg-slate-800` (of 5), `dark:text-slate-400` (of 27), `dark:bg-emerald-950`, `dark:bg-red-950`. `57 + 26 = 83` |
| `GAP-OUT-OF-BUDGET` | **33** | non-`dark:` **27**: `text-gray-700` 15 (all), `text-gray-800` 6 (all), `text-slate-800` 3 (all), `text-slate-700` 2 (all), `text-slate-300` 1 (all). Plus **6** `dark:`: `dark:text-slate-200` 3 (all), `dark:text-slate-300` 2 (all), `dark:text-slate-700` 1 (all). `27 + 6 = 33` |
| `GAP-BORDER-100` | **33** | non-`dark:` **18**: `border-slate-100` 13 (all), `border-gray-100` 3 (all), `divide-slate-100` 2 (all). Plus **15** `dark:`: `dark:border-slate-800` **13** (of 31; the other 18 pair with migrating `border-slate-200`/`border-slate-300`), `dark:divide-slate-800/80` 2 (all). `18 + 15 = 33` |
| `GAP-NO-TOKEN` | **29** | non-`dark:` **25**: `text-amber-600` 5, `text-amber-700` 4, `bg-amber-50` 4, `border-amber-200` 4, `text-amber-900` 3, `bg-amber-100` 2, `text-amber-800` 2, `text-sky-700` 1 — every amber and the single sky occurrence in the trio. Plus **4** `dark:`: `dark:bg-amber-950/50` 2, `dark:text-amber-400` 2. `25 + 4 = 29` |
| `GAP-OVERLAY` | **10** | `bg-black/50` 6 (`PurchaseRequestDetailModal:81`, `PurchaseRequestFormModal:165`, `PurchaseRequestsPage:331`, `:364`, `QuoteFormModal:265`, `SelectQuoteModal:75`), `bg-black/60` 3 (`BudgetLineFormModal:166`, `CategoryFormModal:110`, `TransactionFormModal:220`), `bg-black/40` 1 (`RegisterDeviceModal:48`). No `dark:` siblings |
| `GAP-SWATCH` | **2** | `StatementChart:53`'s `bg-emerald-500` and `:59`'s `bg-red-500` — the credit and debit **bars of a bar chart**, which is §1h code 2 verbatim ("chart series"). No `dark:` siblings |

`83 + 33 + 33 + 29 + 10 + 2 = 190`. **Zero `GAP-NO-SURFACE`, zero
`GAP-UNLISTED`.** Cross-check from the other direction: the codes hold
57 + 27 + 18 + 25 + 10 + 2 = **139** non-`dark:` and 26 + 6 + 15 + 4 = **51**
`dark:` occurrences, matching the disposition table's two halves.

There is no `GAP-NO-SURFACE` because both `text-white` occurrences sit on a
background that has a row (`FinanceDashboardPage:113` on `bg-indigo-600`,
`InvoicePreviewModal:47` on `bg-emerald-600`), and no `border-white` or
`text-black` occurs. This is the **first child to use `GAP-SWATCH`**, and it
uses it exactly where §1h code 2 defines it: two `<div>` bars whose height
encodes an amount and whose colour encodes its sign.

## Every status set in these directories

The triple rule is binding tree-wide: a status variant's class set migrates as
a **unit or not at all**, every member must have a row in §1b–1e, and the
resulting pair must hold ≥ 4.5:1. **A ternary's or a lookup map's branches are
one set**, exactly as APRAS-80 read its sets 2+3. There are **24** sets here,
holding **109** of the 190 kept occurrences.

| # | Set | Members | n | Code |
| --- | --- | --- | --- | --- |
| 1 | `AccessEventFeed:27,29` granted/denied glyph ternary | `text-emerald-500` (CheckCircle2) \| `text-red-500` (XCircle) | 2 | TINT |
| 2 | `AccessEventFeed:47,48` granted/denied badge ternary | emerald 2 + 2 `dark:` \| red 2 + 2 `dark:` | 8 | TINT |
| 3 | `DeviceTable:18,22,26` `StatusBadge` config map, 3 branches | emerald 2+2 `dark:`, slate 2+2 `dark:`, amber 2+2 `dark:` | 12 | TINT 8 / NO-TOKEN 4 |
| 4 | `FacialTemplateSyncPanel:8,9,10` SYNCED/PENDING/FAILED map | emerald 4, amber 4, red 4 | 12 | TINT 8 / NO-TOKEN 4 |
| 5 | `FacialTemplateSyncPanel:58` error alert | `border-red-200`, `bg-red-50`, `text-red-700` + 3 `dark:` | 6 | TINT |
| 6 | `RegisterDeviceModal:68` error alert | same six | 6 | TINT |
| 7 | `CashBalanceCard:40,41,47` income card | `bg-emerald-50`, `text-emerald-600` ×2 + 3 `dark:` | 6 | TINT |
| 8 | `CashBalanceCard:54,55,61` expense card | `bg-red-50`, `text-red-600` ×2 + 3 `dark:` | 6 | TINT |
| 9 | `BudgetVsActualTable:99` variance ternary | `text-red-600` \| `text-emerald-600` | 2 | TINT |
| 10 | `StatementTable:41,44` credit/debit columns | `text-emerald-600`, `text-red-600` + 2 `dark:` | 4 | TINT |
| 11 | `StatementChart:53,59` chart bars | `bg-emerald-500`, `bg-red-500` | 2 | SWATCH |
| 12 | `PurchaseRequestDetailModal:136–140` justification panel | `bg-amber-50`, `border-amber-200`, `text-amber-800`, `text-amber-900` | 4 | NO-TOKEN |
| 13 | `PurchaseRequestDetailModal:237–251` approved panel | `border-emerald-200`, `bg-emerald-50`, `text-emerald-600`, `text-emerald-900` ×2, `text-emerald-700` | 6 | TINT |
| 14 | `PurchaseRequestFormModal:184` red error triple | `bg-red-50`, `text-red-700`, `border-red-200` | 3 | TINT |
| 15 | `PurchaseRequestFormModal:281` amber warning triple | `border-amber-200`, `bg-amber-50`, `text-amber-800` | 3 | NO-TOKEN |
| 16 | `QuoteComparisonTable:337` lowest-price total ternary | `text-emerald-700` \| `text-gray-900` | 2 | TINT |
| 17 | `QuoteComparisonTable:386` red error triple | `border-red-200`, `bg-red-50`, `text-red-700` | 3 | TINT |
| 18 | `QuoteComparisonTable:406` lowest-price column head tint | `bg-emerald-50/60` | 1 | TINT |
| 19 | `QuoteComparisonTable:447,466,494` lowest-price cell tints | `bg-emerald-50/40` ×3 | 3 | TINT |
| 20 | `QuoteComparisonTable:527,528` lowest-price card ternary | `border-emerald-300`, `bg-emerald-50/40` \| `border-gray-200` | 3 | TINT |
| 21 | `QuoteFormModal:280` red error triple | `bg-red-50`, `text-red-700`, `border-red-200` | 3 | TINT |
| 22 | `SelectQuoteModal:88` red error triple | `bg-red-50`, `text-red-700`, `border-red-200` | 3 | TINT |
| 23 | `SelectQuoteModal:113,116,117` first warning panel | `border-amber-200`, `bg-amber-50`, `text-amber-600`, `text-amber-900` | 4 | NO-TOKEN |
| 24 | `SelectQuoteModal:140,143,144,159` second warning panel | `border-amber-200`, `bg-amber-50`, `text-amber-600`, `text-amber-900`, `text-amber-700` | 5 | NO-TOKEN |

`2+8+12+12+6+6+6+6+2+4+2+4+6+3+3+2+3+1+3+3+3+3+4+5 = 109`, of which **83** are
`GAP-TINT` (matching the code's total exactly, so every `GAP-TINT` occurrence
in this child belongs to a set), **24** `GAP-NO-TOKEN` and **2** `GAP-SWATCH`.
The remaining 81 kept occurrences are the 33 `GAP-OUT-OF-BUDGET`, the 33
`GAP-BORDER-100`, the 10 `GAP-OVERLAY` and **five free-standing
`GAP-NO-TOKEN`** classes that belong to no set (`PurchaseRequestsPage:294`
`text-amber-600`, `QuoteComparisonTable:198` `text-amber-700`, `:231`
`text-sky-700`, `QuoteFormModal:553` `text-amber-600`, `SelectQuoteModal:188`
`text-amber-600`). `24 + 5 = 29`, the code's total.

**The rowless member of each.** Sets 3, 4, 12, 15, 23 and 24 are blocked by
`amber`, which has no row at any scale; sets 5, 6, 14, 17, 21 and 22 are red
tint triples, which §1j makes `GAP-TINT` by name; sets 2, 7, 8, 10 and 13 are
blocked by `bg-emerald-50` / `bg-emerald-100` / `bg-red-50` / `bg-red-100`,
none of which has a §1b row for its role, and set 13 additionally by
`text-emerald-900`. Sets 1, 9, 16, 18, 19 and 20 are the operator's status
ruling applied through **§1f case 3**: every emerald in them is a
non-interactive status glyph, a lowest-price tint or a badge, so it stays
regardless of its row, and its ternary partner stays with it. Set 11 is the
only `GAP-SWATCH`.

**Four consequences worth stating once.**

1. **Three neutral classes that have rows are kept because their ternary
   partner is a status colour** — `QuoteComparisonTable:337`'s `text-gray-900`
   (set 16), `:528`'s `border-gray-200` (set 20), and `DeviceTable:22`'s
   `bg-slate-100 text-slate-600` pair with its two `dark:` siblings (set 3,
   the OFFLINE branch, which is neutral by design). This is APRAS-82 set 3's
   precedent applied four times, and it is the reason the ledger carries a
   `text-gray-900`, a `border-gray-200`, a `bg-slate-100` and a
   `text-slate-600` entry in files where the same classes also migrate
   elsewhere. It is named as a **review duty**, not hidden in a count.
2. **`emerald` splits within this PR, correctly, at three places.**
   `InvoicePreviewModal:58`'s download `<a>` carries `bg-emerald-600
   hover:bg-emerald-700 text-white` — an **interactive fill**, so §1f case 3
   migrates it to the primary triple, exactly as APRAS-78's pilot migrated
   `button.tsx`'s `success` variant. `QuoteComparisonTable:300`'s `<Award/>`
   inside a `<Button variant="ghost" title={…chooseQuote}>` is likewise
   **interactive** — it is the only colour that control carries, and its
   accessible name states what it does — so it migrates to `text-primary`
   (graphical under §1k, an icon with no children). Every other emerald in the
   trio is a status tint, a status glyph or a lowest-price highlight and stays.
   A reviewer should check precisely these two migrating sites against sets 1,
   7, 9, 10, 13, 16, 18, 19 and 20.
3. **Red splits too, and the rule is §1j's, not a new one.** Six `text-red-500`
   `<Trash2/>` icons — `PurchaseRequestFormModal:353`,
   `PurchaseRequestsPage:303`, `QuoteComparisonTable:283`, `:319`,
   `QuoteFormModal:489`, `:596` — are **free-standing destructive controls**
   and take `text-destructive` per §1e; the seventh, `AccessEventFeed:29`, is
   the denied half of a status ternary and stays (set 1). Every other red is
   inside a tint triple or a status badge.
4. **`purchase-management` contains no `indigo` class at all.** Its only
   brand-family occurrence is set 2's exception above, and
   `PurchaseRequestsPage:198` already reads `bg-primary text-primary-foreground`
   today. So the whole of this child's indigo work lives in `finance` and
   `access-control`.

**The proof there is no twenty-fifth set.** A split span is a class-context
span — as `classContexts()` in the guard computes it, not a line — holding both
a migrated occurrence and a kept `GAP-TINT` occurrence. Run mechanically over
all 534 occurrences grouped by `(file, span)`, that check returns **exactly
one** span: `QuoteComparisonTable.tsx` lines 405–406, where the migrating
`border-gray-200` of the column head sits beside set 18's kept
`bg-emerald-50/60`. That is **not** a split set — every column head carries
that border, and only the lowest-price one carries the tint — and it is the
same shape APRAS-80 recorded at `VisitorAuthPage:144`. The implementer must
re-run the check and get the same single span. (Spans that mix a migrated
occurrence with a kept occurrence under any *other* code are expected and are
not counted.)

## Behaviour — the substitutions

Every substitution is a table row applied verbatim.

- `bg-white` ×27 → **`bg-card`** — §1f case 1, settled below. **None of the 27**
  takes `bg-background` and none takes `bg-popover`: no `bg-white` element in
  these twenty-two files *is* the page. (The one `bg-background` this task
  writes comes from `bg-slate-50` at the page root, below, not from any
  `bg-white`.)
- `bg-slate-950/70` ×1 → `bg-foreground/70` (`InvoicePreviewModal:29`) — §1b's
  `bg-slate-950` row (ΔE 4.69, `noted`), *not* `GAP-OVERLAY`; settled below.
- `border-gray-200` ×21 (of 22) + `border-slate-200` ×18 → `border-border`.
- `border-slate-300` ×4 + `border-gray-300` ×1 → `border-input`.
- `text-slate-900` ×21 + `text-gray-900` ×20 (of 21) → `text-foreground`.
- To `text-muted-foreground` ×78: `text-slate-500` 25, `text-gray-500` 20,
  `text-gray-600` 13, `text-slate-400` 8, `text-gray-400` 7, `text-slate-600` 1
  (of 2), plus `hover:text-slate-600` 4 → `hover:text-muted-foreground`.
- **The page root ×1 → `bg-background`** — `FinanceDashboardPage:48`'s
  `bg-slate-50`, under §1f case 1 as amended. It is the **only**
  `bg-background` this task writes.
- Neutral fills ×11: resting `bg-gray-50` 4, `bg-slate-50` **2 of 3** (the third
  is the page root above), `bg-slate-100` 1 (of 2) → `bg-muted`; interaction
  `hover:bg-slate-100` 2, `hover:bg-slate-50` 1, `hover:bg-gray-100` 1 →
  `hover:bg-accent` — §1f case 2, settled below.
- **Indigo ×19, split by §1k** — see the next section: 2 → `*-primary-text`,
  17 → `primary` / `accent` / `border`.
- Emerald ×3: `bg-emerald-600` and `hover:bg-emerald-700`
  (`InvoicePreviewModal:47`) → `bg-primary` and `hover:bg-primary/90`, and
  `text-emerald-600` (`QuoteComparisonTable:300`) → `text-primary` — §1f case
  3's interactive branch.
- `text-red-500` ×6 → `text-destructive` — the six `<Trash2/>` controls.
- `text-white` ×2 → `text-primary-foreground`. Both sit on a migrating
  `bg-indigo-600` / `bg-emerald-600`, so there is no `GAP-NO-SURFACE`.

`27 + 1 + 39 + 5 + 41 + 78 + 1 + 11 + 19 + 3 + 6 + 2 = 233`, reading the bullets
in order, with no occurrence counted twice. The total is **unchanged** by the
operator's `bg-background` ruling: the page root was already one of the 233
migrated occurrences and only its target moved, so the disposition table
(233 / 111 / 190), every per-file and per-directory row, all six gap-code
counts, the 145 exception pairs and the 190 ledger rows are **all unchanged** —
the ledger and the exceptions record what is *kept*, and nothing kept changed.

No occurrence is counted twice: the indigo bullet's 19 already
includes the variant-carrying brand utilities `file:bg-indigo-50`,
`file:text-indigo-700`, `hover:file:bg-indigo-100`, `hover:bg-indigo-50` and
`hover:bg-indigo-700`, and no other bullet contains an indigo class.

**Opacity modifiers are carried over verbatim**, never dropped and never
rounded to a different `N`: `bg-slate-950/70` → `bg-foreground/70`,
`hover:bg-indigo-700` → `hover:bg-primary/90`, and `hover:bg-emerald-700` →
`hover:bg-primary/90`, per §1i's named target. §1i measures such a target
against the base token with the alpha declared **unmeasured**. **No
`text-primary/N` and no `text-primary-text/N` is produced anywhere**, so this
child creates no APRAS-90 site.

Each of the 233 takes its `dark:` sibling with it where it has one: **111
deletions**, 62 in `finance` and 49 in `access-control`. All 102 of
`purchase-management`'s migrations carry no `dark:` sibling at all, because
that directory has none.

## §1k applied — which brand classes are characters

§1k asks one question per call site, from the JSX, with no measurement: *does
this element paint glyphs of text?* Traced at every site, not assumed.

**Characters — take `*-primary-text`, floor 4.5:1 (2 occurrences).**

| Site | Class → target | Why it is text | Surface | After |
| --- | --- | --- | --- | --- |
| `DeviceTable:103` | `text-indigo-700` → `text-primary-text` | `<div>` rendering `{revealedKey.key}`, the regenerated device key | `bg-indigo-50` → `--accent` | **4.6547** |
| `TransactionFormModal:189` | `file:text-indigo-700` → `file:text-primary-text` | the `file:` variant paints the file-selector button, which renders the browser's own label characters | `file:bg-indigo-50` → `--accent` | **4.6547** |

`DeviceTable:103`'s `dark:text-indigo-300` sibling is deleted with it;
`TransactionFormModal:189` has no `dark:` sibling.

**Graphical — keeps `*-primary`, floor 3:1 (17 indigo + 1 emerald).** Nine of
the indigo are `text-`-prefixed classes on an element that paints no glyphs and
eight are non-`text-` utilities, which §1k makes graphical always; the emerald
is a `text-` icon.

The ten `text-`-prefixed graphical sites, by surface:

| Surface | Sites | `--primary` on it |
| --- | --- | --- |
| `--card` (6) | `GateMonitorPage:44` `<Icon/>` in a `bg-white` device chip; `FacialTemplateSyncPanel:40` `<ScanFace/>` in the `bg-white` panel heading; `RegisterDeviceModal:53` `<ScanFace/>` in the `bg-white` modal; `FinanceDashboardPage:52` `<Wallet/>` in the `bg-white` header card; `InvoicePreviewModal:38` `<FileText/>` (`text-indigo-500`) in the `bg-white` modal; `QuoteComparisonTable:300` `<Award/>` (`text-emerald-600`) in a column head | 3.4054 |
| `--background` (2) | `AccessControlPage:34` `<ScanFace/>` and `GateMonitorPage:27` `<Radio/>`, both in a page header that carries **no** background class, so the surface is `App.tsx:122`'s `min-h-screen bg-background` | **3.3091** |
| `--accent` (1) | `CashBalanceCard:24` `<Wallet/>` inside the `bg-indigo-50` tile | **3.0427** |
| `--muted` / `--accent` (1) | `CategoryTransactionDrilldown:69` a `<button>` whose only child is `<FileText/>`, resting on `BudgetVsActualTable:112`'s `bg-slate-50` cell and hovering to `bg-accent` | **3.0427** |

The eight non-`text-` indigo utilities: `bg-indigo-50` ×2 → `bg-accent`,
`border-indigo-200` ×1 → `border-border`, `hover:bg-indigo-50` ×1 →
`hover:bg-accent`, `file:bg-indigo-50` ×1 → `file:bg-accent`,
`hover:file:bg-indigo-100` ×1 → `hover:file:bg-accent`, `bg-indigo-600` ×1 →
`bg-primary`, `hover:bg-indigo-700` ×1 → `hover:bg-primary/90`. That is
`2+1+1+1+1+1+1 = 8`; with the two `file:`/`hover:file:` counted once each the
non-`text-` indigo total is **8**, which with the nine `text-` indigo graphical
sites and the two `*-primary-text` sites gives **19** migrating indigo
occurrences in all, `dark:` siblings excluded.

## The context-dependent cases, settled at the real call sites

**The verification tests cannot detect a wrong choice in any of these.** They
are a **human review duty on this diff**.

**§1f case 1 — `bg-white` ×27 all take `bg-card`.** No `bg-white` in these
twenty-two files is a page shell: the two full-bleed roots are
`FinanceDashboardPage:48` (`min-h-screen bg-slate-50`, handled below) and the
bare `<div className="space-y-6">` roots of `AccessControlPage:30`,
`GateMonitorPage:24` and `PurchaseRequestsPage`, none of which carries
`bg-white`. None of the 27 is a floating layer with popover semantics, so none
takes `bg-popover`. **Four** of the twenty-seven are **raw
`<select>`/`<input>` fills** (`FinanceDashboardPage:73`,
`FacialTemplateSyncPanel:50`, `RegisterDeviceModal:82`, `:93`). They take
**`bg-card`**, following APRAS-80's already-accepted precedent, even though
`components/ui/`'s primitives use `bg-background`; the two are byte-identical
in `:root` and diverge only under a tenant theme. The divergence is
**recorded, not resolved** here.

**The page shell that is not `bg-white` — `bg-background`, by operator
ruling.** `FinanceDashboardPage:48` reads `min-h-screen bg-slate-50
dark:bg-slate-950`: the element **is** the page. An earlier revision of this
spec sent it to `bg-muted`, because §1f case 1's "if the element *is* the page,
it is `bg-background`" was textually scoped to `bg-white` / `text-white` /
`border-white` and `bg-slate-50`'s §1b row offers only `bg-muted` / §1f case 2.
The operator was asked and answered **`bg-background`**, and the amendment above
makes case 1 the rule consulted **first**: it is consulted before the class's
§1b row and before case 2, wins, and the shell therefore takes
**`bg-background`**. `bg-slate-50`'s §1b row is **not** amended and not
retargeted; it simply is not reached at a page root.

Measured, so the move is not taken on faith, by importing
`frontend/src/lib/contrast.ts` and reading `bg-slate-50`
(`oklch(98.4% 0.003 247.858)`) from `node_modules/tailwindcss/theme.css` and
`--background` (`oklch(0.99 0 0)`) from `src/index.css`: ΔL **0.60**, ΔE
**0.67** — a *smaller* move than the ΔL 2.40 / ΔE 2.61 the `bg-muted` row would
have given it. This is a measurement, **not a table row**.

**What the answer changes under a tenant theme**, which no contrast figure
shows: `background` is derived as a fixed neutral, **not placed at the tenant
hue**, while `muted` is `(0.96, 0.01)` **at the tenant's hue**
(`backend/app/core/branding.py:_neutral_family`). `bg-background` therefore keeps
the finance canvas hue-free for every tenant, where `bg-muted` would have tinted
it with the brand.

**No measured pair moves with it.** Traced from the JSX, *nothing paints directly
on `FinanceDashboardPage:48`*: its children are the `bg-white` header card at
`:49`, `CashBalanceCard` (three `bg-white` tiles), the two `bg-white` panels at
`:124` and `:132`, and three modals. Every foreground inside the page sits on
`--card`, `--accent` or a status tint, none on the shell. So the contrast tables
below are **identical** whether the shell takes `bg-muted` or `bg-background`,
and the ratios that *were* computed against `--muted` — the table-head text, the
kept `text-gray-700` / `text-slate-800`, and
`CategoryTransactionDrilldown:79`'s `text-slate-300` — all belong to
`BudgetVsActualTable:112`, `FacialTemplateSyncPanel:64`,
`InvoicePreviewModal:63` and the four gray panels, which still migrate to
`bg-muted` and are untouched by this ruling. **Named here so a reviewer decides
it deliberately rather than discovering it.**

**The one genuinely arguable site class: `bg-slate-950/70` ×1**
(`InvoicePreviewModal:29`), the PDF preview scrim. `GAP-OVERLAY` (§1h code 1)
is defined for `bg-black` and `bg-white` *only*, and `bg-slate-950` **has** a
§1b row (`bg-foreground`, ΔL 1.10, ΔE 4.69, `noted`), so the contract requires
migration to `bg-foreground/70`. The ten `bg-black/N` scrims in the same trio
*are* code 1 and stay. That the same UI element resolves two different ways in
one PR — here at a ratio of one to ten — is a consequence of the published
codes, not a defect of this child; naming it here is the alternative to
silently inventing a ninth code. **The inheritance it creates is stated rather
than hidden:** `--foreground` inverts in the `.dark` block, so whoever enables
`.dark` inherits one scrim that would paint near-white. `.dark` is never
applied today, so nothing changes now.

**§1f case 2 — `bg-muted` versus `bg-accent`.** **Seven** resting fills take
`bg-muted` — the page shell is **not** among them, having been resolved by case
1 before case 2 was reached: `BudgetVsActualTable:112`'s
expanded-row cell, `InvoicePreviewModal:63`'s viewer stage,
`FacialTemplateSyncPanel:64`'s summary panel, and the four gray panels at
`PurchaseRequestDetailModal:271`, `PurchaseRequestFormModal:295`,
`QuoteFormModal:497` and `SelectQuoteModal:93`. Four interaction fills take
`hover:bg-accent`: `InvoicePreviewModal:56`, `RegisterDeviceModal:61`,
`BudgetVsActualTable:73` and `PurchaseRequestsPage:199`. Separately, the four
brand tints (`bg-indigo-50` ×2, `file:bg-indigo-50`, `hover:bg-indigo-50`,
`hover:file:bg-indigo-100`) take `accent` under §1e's own row, not under case 2.

**§1f case 3 — emerald 500–700.** The band holds **15** occurrences here
(`emerald-500` 2, `emerald-600` 7, `emerald-700` 6).
**Three migrate** — `InvoicePreviewModal:47`'s `bg-emerald-600
hover:bg-emerald-700` interactive fill and `QuoteComparisonTable:300`'s Award
control glyph — and **twelve stay**, distributed across the status sets as the
gap-code table above records them. That table is authoritative for this band;
no expected result depends on the figures in this paragraph.

**The one tab ternary that is not a status set.** `PurchaseRequestsPage:198,199`
switches a tab between `bg-primary text-primary-foreground` (already tokens
today) and `text-gray-600 hover:bg-gray-100`. Selected-versus-unselected is not
a status variant, and the selected half is already migrated, so the inactive
half migrates normally to `text-muted-foreground hover:bg-accent`. Named as a
review duty because it is the one ternary in the trio that the unit rule does
**not** freeze.

## Contrast, re-derived by importing `frontend/src/lib/contrast.ts`

Measured by importing `contrastRatio`, `parseOklch` and `hexToOklch` from
`frontend/src/lib/contrast.ts` — never reimplemented — with token values read
from `src/index.css` and palette values read from
`node_modules/tailwindcss/theme.css` (**Tailwind 4's OKLCH palette**, whose
lightness is written as a percentage and must be divided by 100 before
`parseOklch` sees it). The measurement reproduces APRAS-78's, APRAS-80's and
APRAS-88's published figures to the digit (`--primary-foreground` on
`--primary` 5.7588, `--muted-foreground` on `--muted` 4.6684, `--primary-text`
on `--card` 5.2096 and on `--accent` 4.6547, `--primary` on `--card` 3.4054, on
`--background` 3.3091), which is the check that it is the same measurement.

| Pair | Background | Today | After |
| --- | --- | --- | --- |
| Headings `text-slate-900` / `text-gray-900` → `text-foreground` | `--card` | 17.8448 / 17.7467 | **19.8801** |
| Page headings `text-slate-900` → `text-foreground` | `--background` | 17.3401 | **19.3178** |
| Secondary text `text-slate-500` / `text-gray-500` → `text-muted-foreground` | `--card` | 4.7670 / 4.8357 | **5.2249** |
| `text-slate-600` / `text-gray-600` → `text-muted-foreground` | `--card` | 7.5635 / 7.5608 | **5.2249** |
| Table-head text `text-slate-500` on `bg-slate-50`, `text-gray-500` on `bg-gray-50` → on `bg-muted` | `--muted` | 4.5540 / 4.6325 | **4.6684** |
| **`text-slate-400` ×8 / `text-gray-400` ×7 → `text-muted-foreground`** | `--card` | 2.6282 / 2.6023 | **5.2249** — repairs an AA failure at 15 sites |
| Primary button `text-white` on `bg-indigo-600` → `text-primary-foreground` on `bg-primary` | `--primary` | 6.4414 | **5.7588** |
| Download link `text-white` on `bg-emerald-600` → `text-primary-foreground` on `bg-primary` | `--primary` | 3.7194 | **5.7588** — repairs an AA failure at 1 site |
| **Device-key chip `text-indigo-700` → `text-primary-text`** | `--accent` | 7.2164 | **4.6547** |
| **File-input button `file:text-indigo-700` → `file:text-primary-text`** | `--accent` | 7.2164 | **4.6547** |
| Brand icons `text-indigo-600` / `text-indigo-500` → `text-primary` (graphical, floor 3) | `--card` | 6.4414 / 4.5587 | **3.4054** |
| Page-header brand icons `text-indigo-600` → `text-primary` (graphical) | `--background` | 6.2592 | **3.3091** |
| Tile and inline brand glyphs → `text-primary` (graphical) | `--accent` / `--muted` | 5.7621 / 6.1536 | **3.0427** |
| Award control glyph `text-emerald-600` → `text-primary` (graphical) | `--card` | 3.7194 | **3.4054** |
| Delete-control glyphs `text-red-500` → `text-destructive` (graphical) ×6 | `--card` | 3.8199 | **4.8073** |

**No full-opacity text pair this task produces falls below 4.5:1.** The tightest
are `--primary-text` on `--accent` at 4.6547 and `--muted-foreground` on
`--muted` at 4.6684.

### Kept pairs whose *surface* moves, measured so nobody attributes them later

A kept foreground can sit on a migrated background. Every such **text** pair
stays far above AA, so **this migration converts no passing text pair into a
failing one**: `text-gray-700` on `bg-gray-50` → on `--muted` 9.8728 →
**9.2081** (`PurchaseRequestDetailModal:274`, `QuoteFormModal:498`);
`text-slate-800` on `bg-slate-50` → on `--muted` 14.0024 → **13.0962**
(`BudgetVsActualTable:85` under the row's migrated hover fill); and
`text-slate-700`, `text-slate-800`, `text-gray-700` and `text-gray-800` on
`bg-white` → `--card` are **unchanged to the digit** (10.3442, 14.6574,
10.3058, 14.6846), because `--card` is `oklch(1 0 0)` and `bg-white` is `#fff`.

**One kept pair does drop, and it is graphical and already failing.**
`CategoryTransactionDrilldown:79`'s `text-slate-300` `<FileX2/>` glyph sits on
`BudgetVsActualTable:112`'s `bg-slate-50` cell, which migrates to `--muted`:
**1.4181 → 1.3263**. It is an icon, so the applicable floor is 1.4.11's 3:1,
and it fails that floor **today, before this task**. §1i forbids repairing it in
place (the class may be swapped, never added or removed) — `text-slate-300` has
no row at all, it is `GAP-OUT-OF-BUDGET` — and the tree-wide repair is
APRAS-90's. It is named here rather than left for a reviewer to find.

### Declared sub-AA or unmeasurable, none of them introduced by this task

1. `--primary` on `--accent` / `--muted` is **3.0427** at two graphical sites
   (`CashBalanceCard:24`, `CategoryTransactionDrilldown:69`) and on
   `--background` **3.3091** at two more (`AccessControlPage:34`,
   `GateMonitorPage:27`). Those clear 1.4.11 by 0.043 and 0.309 and, for a pale
   tenant brand, do not clear it at all. §1k routes them there deliberately;
   this is APRAS-68 behaviour predating APRAS-77 and this child must not be read
   as having introduced the numbers.
2. `--primary` on the kept `bg-emerald-50/60` tint is **3.2301** at
   `QuoteComparisonTable:300` when that column is the lowest-price one (3.4054
   otherwise); today the same glyph measures 3.5279 there. Graphical, above 3
   both ways.
3. Unchanged pre-existing failures, all kept verbatim and all inside a status
   set or an out-of-budget gap: `text-slate-300` on `--muted` **1.3263** (above),
   `text-emerald-600` on `--card` 3.7194 and on `bg-emerald-50` **3.5279**,
   `text-emerald-500` on `--card` **2.5032**, `text-red-500` on `--card`
   **3.8199** (`AccessEventFeed:29` only), `text-amber-600` on `bg-amber-50`
   **3.0755**, `text-amber-700` on `bg-amber-50` 4.8611 and on `bg-amber-100`
   4.5273, `text-emerald-700` on `bg-emerald-50` 5.1582 and on `bg-emerald-100`
   4.7907, `text-red-700` on `bg-red-50` 5.9842 and on `bg-red-100` 5.3552,
   `text-red-600` on `bg-red-50` **4.4506** (`CashBalanceCard:55`, a
   pre-existing AA failure §1j already records).
4. **No APRAS-90 site exists in these three directories.** APRAS-90 owns brand
   text carrying an opacity modifier over a brand tint; this child produces no
   `text-primary-text/N` and no `text-primary/N` anywhere. The one opacity
   modifier it carries over (`/70`) and the two it creates (`/90`) are all
   background utilities.

### The consequence the table forces and §1i forbids repairing

Four call sites lose an interaction distinction, because both members of a
`resting`/`hover` pair map to the same token: `text-slate-400
hover:text-slate-600` → `text-muted-foreground hover:text-muted-foreground` at
`BudgetLineFormModal:60`, `CategoryFormModal:50`, `TransactionFormModal:74` and
`InvoicePreviewModal:56`.

§1i forbids deleting the now-redundant class — that is a markup change, not a
colour change — so each substitution is made in place and the redundancy is
left. It is a published consequence of §1d's rows, not a defect of this child,
and it is the natural companion follow-up to APRAS-90.

## The guard suite — what changes

Re-read against the file as it stands at `a8fc8ab`, where
`MIGRATED_DIRECTORIES` holds three entries and `pinnedFiles()` returns 26 files:

1. `MIGRATED_DIRECTORIES` gains **three** entries —
   `"src/features/finance/components"`,
   `"src/features/purchase-management/components"` and
   `"src/features/access-control/components"`. APRAS-78's comment says each
   sibling appends exactly one; this child's operator-given scope is three
   directories, so it appends three and says so in the comment.
2. `describe("MIGRATED_DIRECTORIES")`'s two tests each gain **three**
   assertions, in the shape already there
   (`…/finance/components/CashBalanceCard.tsx`,
   `…/purchase-management/components/QuoteComparisonTable.tsx` and
   `…/access-control/components/DeviceTable.tsx` for the pinned-files test).
3. A new **appended, directory-scoped** `describe("APRAS-83's ledger
   arithmetic")`, in the shape APRAS-79 and APRAS-80 established: the 22 pinned
   files split 10 / 6 / 6 by directory, the 190 ledger rows, the 145 exception
   pairs, the six gap-code counts, the twenty-four status sets still whole, and
   the single split span. **No child's existing block is edited**; APRAS-78's,
   APRAS-79's, APRAS-80's and — if they have landed first — APRAS-81's and
   APRAS-82's must still pass untouched.
4. **Performance.** Measured now at `a8fc8ab`: the suite runs **50 tests in
   932 ms**, `pinnedFiles()` returns **26** files, the exceptions file holds
   **254** entries (APRAS-78 22 + APRAS-79 148 + APRAS-80 84), and
   `it("fails when any single exception is removed")` alone takes **882 ms**,
   i.e. 254 × 26 = 6,604 scans at 0.1336 ms each. After this child (145 more
   exceptions, 22 more files) that test runs 399 × 48 = **19,152** scans,
   ≈**2.6 s**, over the 2 s trigger APRAS-80 named — and far over it if
   APRAS-81 and APRAS-82 have landed first (676 × 73 = 49,348 scans, ≈6.6 s).
   The memo inside `violations()` is a **function-local** `Map` today, so it is
   rebuilt on each of the hundreds of mutated-argument calls. APRAS-81 is the
   child assigned the module-scope hoist; if it has landed, this child verifies
   the hoist still holds with the larger input and changes nothing, and if it
   has not, this child performs it — keyed on `file + "\0" + source`, a pure
   function of its arguments so the mutated-argument tests keep biting, with no
   assertion changed either way. The decidable requirement is that **every
   individual test in the file finishes under 2 s**.

## Files touched

- The ten `frontend/src/features/finance/components/*.tsx`, the six
  `frontend/src/features/purchase-management/components/*.tsx` and the six
  `frontend/src/features/access-control/components/*.tsx`, per the
  `migrated / deleted / logged` table.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — the three directory
  entries, six assertions, the module-scope memo hoist if not already present,
  and the new scoped `describe`.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — **145** new
  entries, `src/`-relative, `task` `APRAS-83`.
- `docs/frontend/unmapped-colours.md` — **190** appended rows, one per kept
  occurrence, sorted by file then line, plus a closing `APRAS-83 total`
  paragraph in the shape APRAS-78/79/80 use. Nothing already in the file is
  rewritten.
- `docs/frontend/theme-token-mapping.md` — **conditionally**: one sentence
  appended inside §1f case 1's paragraph if, and only if, APRAS-81 has not
  already landed it. Nothing else in the file changes, and no line beginning
  with `|` is added, removed or edited. If the marker is already present, this
  file is not touched at all.
- `frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts` — new.
- `frontend/src/components/__tests__/TenantBrandReach.test.tsx` — extended with
  one migrated component from each directory: `CashBalanceCard`,
  `SelectQuoteModal` and `DeviceTable`, all three props-only so none needs a
  query client, each asserted against the tenant token and never against a
  colour literal.

## Test criteria

1. `npx vitest run src/__tests__/themeTokenMigration.test.ts` green with all
   three directories pinned: zero unexcused grammar matches across the 22
   files, no stale exception, no unknown code, ledger parity in both
   directions, the preceding children's blocks untouched, and this block's 190.
2. The new contrast test asserts, by **importing** `contrastRatio`,
   `parseOklch` and `hexToOklch` from `src/lib/contrast.ts`, that every
   foreground/background pair this task changes either holds ≥
   `MINIMUM_CONTRAST_RATIO` or appears in an explicit in-file list of declared
   sub-AA / graphical pairs carrying its measured before/after ratio. Ratios to
   ±0.001 against the tables above, each against its declared background. Token
   values from `src/index.css`, palette values from
   `node_modules/tailwindcss/theme.css`; no colour literal hard-coded.
   Graphical pairs are asserted against the 3:1 floor, text pairs against 4.5.
3. The fourteen existing suites under the three `__tests__/` directories — 175
   tests — pass **unmodified**. None asserts on a class name, so none proves a
   colour.
4. `npx tsc -b` clean.
5. `npx vitest run --coverage` meets exactly **80 lines / 78 functions / 76
   branches / 80 statements**.
6. `npx eslint` diff-scoped. Re-measured now: the repository carries **375
   errors + 2 warnings across 64 files**, and **the 22 touched files carry 2
   errors and 0 warnings across 2 files** (`FacialTemplateSyncPanel.tsx` 1,
   `RegisterDeviceModal.tsx` 1; `finance` and `purchase-management` contribute
   zero).
7. `git diff --exit-code frontend/src/index.css` succeeds; the only possible
   change to `docs/frontend/theme-token-mapping.md` is the single §1f case 1
   sentence, appended only if APRAS-81 has not already landed it, with no table
   row touched; `themeTokenCompile.test.ts`, `themeContrast.test.ts` and
   `brandTextOpacity.test.ts` pass unmodified; no backend file, no Alembic
   revision, no route-registry entry in the diff; the `.dark` block stays
   unapplied.

## What this proves, and what it misses

**Proved.** Every substitution is a §1b–1e row, and `themeTokenCompile.test.ts`
already asserts each row's ΔL/ΔE from the compiled stylesheet to ±0.1. The
guard certifies nothing was dropped or silently substituted: each of the 534 is
either gone from the file or present in **both** the ledger and the exceptions
file. The contrast test certifies the pairs that change.

**Not proved, stated plainly.**

- No Playwright, no Storybook, no Chromatic, no Percy, and jsdom does not run
  the Tailwind pipeline: **no pixel and no computed-style proof**. Compiling
  Tailwind over a fixture proves the table is truthful and that no unlisted
  substitution slipped in; it does **not** prove the right row was chosen at
  the right call site.
- **The three §1f cases and every §1k verdict are invisible to every test
  here**, with one exception. `bg-card` vs `bg-background` on a *card*, and
  `bg-muted` vs `bg-accent`, are byte-identical in `:root`; `text-primary` vs
  `text-primary-text` on an icon is two legal classes. A **review duty on this
  diff**, and the four sites to start from are `InvoicePreviewModal:29`'s
  scrim, `InvoicePreviewModal:47` versus the kept emerald sets,
  `QuoteComparisonTable:300`'s Award glyph, and the four neutrals kept by sets
  3, 16 and 20. The exception is the **page shell**: `--background` (0.99) and
  `--muted` (0.96) are different colours with different tenant behaviour
  (`_LIGHT_BACKGROUND` is a fixed neutral, `_LIGHT_MUTED` is placed at the
  tenant hue — `backend/app/core/branding.py:_neutral_family`), so the
  operator's choice at `FinanceDashboardPage:48` is asserted **by class name**
  in the expected results and a wrong target there fails a test rather than only
  a review.
- The rendering *does* move where the table says it moves: 15 `text-*-400`
  sites darken by ~17 L points, the indigo hue shift at 19 sites (plus 12
  deleted `dark:` indigo siblings), `text-*-600` lightening at 18 sites, the
  two primary fills going dark-on-emerald, the Award glyph becoming brand, the
  six delete glyphs moving from `red-500` to `--destructive`, and the four
  hover-distinction losses named above.
- The **111 deleted `dark:` siblings** change nothing today, because `.dark` is
  never applied. What changes is what the future dark-mode task inherits,
  alongside the 51 `dark:` classes kept — **all 162 of them live in `finance`
  and `access-control`**, which are the only directories in this trio that have
  any — plus the one `bg-foreground/70` scrim named above.
- **The guard cannot enforce per-site completeness**, because the exceptions
  file carries no line number. `QuoteComparisonTable.tsx` is the worst case:
  `border-gray-200`, `text-gray-900` and `text-emerald-600` are each migrated
  at one site and kept at another in that one file, and once excused an
  unmigrated occurrence anywhere in it passes. `DeviceTable.tsx` has the same
  shape for `bg-slate-100` and `text-slate-600`, and `AccessEventFeed.tsx` for
  `text-red-500`. The disposition table (233 / 111 / 190 with the per-file
  split), the twenty-four-set inventory and the §1k site table are what a
  reviewer must check the diff against.

## Out of scope

Adding `--success` / `--warning` / `--info` tokens; migrating any `amber` or
`sky` occurrence; APRAS-90's sub-AA repair tree; deleting the now-redundant
`hover:` classes; repairing `CategoryTransactionDrilldown:79`'s pre-existing
1.4.11 failure; the 1.4.11 graphical floor for pale tenant brands; enabling the
`.dark` block; visual-regression infrastructure; any other feature directory;
the six `user-administration/pages/` page roots already written `bg-muted/30`,
which are tokens and so outside APRAS-77 entirely; and any amendment to
APRAS-78's mapping table, ledger rules or grammar **other than** the single §1f
case 1 sentence owned by APRAS-81, which this task consumes and carries only if
APRAS-81 has not landed it first.

## Expected Results

- [ ] `frontend/src/features/finance/components/FinanceDashboardPage.tsx`'s root element — the `min-h-screen` `<div>` the component returns, today `className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 sm:p-6 lg:p-8 space-y-6"` — carries the whitespace-split class token `bg-background` and carries none of `bg-slate-50`, `bg-muted`, `bg-card` or `dark:bg-slate-950`; the token `bg-background` appears in exactly one class string across the twenty-two migrated `.tsx` files, and the roots of `AccessControlPage.tsx`, `GateMonitorPage.tsx` and `PurchaseRequestsPage.tsx` are unchanged, since each declares no background class at all.
- [ ] §1f case 1's page-root extension is owned by APRAS-81 and is carried by whichever of APRAS-81 / APRAS-83 lands first. If the marker `(Operator ruling on APRAS-81 and APRAS-83; carried by APRAS-81.)` is already present in `docs/frontend/theme-token-mapping.md` when this task starts, this task changes **no line** of that file; if it is absent, this task appends the identical sentence, ending in that identical marker, inside the §1f Case 1 paragraph and nowhere else. Either way `grep -c -F '(Operator ruling on APRAS-81 and APRAS-83; carried by APRAS-81.)' docs/frontend/theme-token-mapping.md` prints **exactly `1`** after this task — so a file carrying the ruling twice FAILS this result — exactly one sentence in the §1f Case 1 paragraph begins `The second clause of the rule is`, the file contains no added or removed line beginning with `|` in `BASE..HEAD` (`BASE` = `git rev-parse "$(git log --format='%H %s' | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-83\):' | tail -1 | cut -d' ' -f1)^"`, the parent of this task's first commit, computed from the repository alone — never `git merge-base HEAD origin/master`, never a sha read from an implementation report, never the literal `a8fc8ab`), and `FinanceDashboardPage.tsx:48` takes `bg-background`. `git diff BASE..HEAD -- docs/frontend/theme-token-mapping.md` is either empty (consumed) or exactly one added line inside the §1f Case 1 paragraph (carried), and in neither case contains any change outside that paragraph, to §1b's `bg-slate-50` or `bg-gray-50` rows, to §1f cases 2 and 3, to §1h's gap codes, or to §3b.
- [ ] `npx vitest run src/__tests__/themeTokenCompile.test.ts src/__tests__/themeContrast.test.ts src/__tests__/brandTextOpacity.test.ts` passes with all three files unmodified — no commit whose subject matches `[a-z]+\(APRAS-83\):` touches any of the three — the compile test because no mapping-table row moved, and APRAS-90's repository-wide brand-text-opacity sweep because this task writes no `text-primary/N` and no `text-primary-text/N` anywhere.
- [ ] Of the 233 migrated occurrences, exactly **1** becomes `bg-background` (the page root above) and exactly **11** become `bg-muted` / `bg-accent` neutral fills — resting `bg-gray-50` ×4 (`PurchaseRequestDetailModal.tsx:271`, `PurchaseRequestFormModal.tsx:295`, `QuoteFormModal.tsx:497`, `SelectQuoteModal.tsx:93`), `bg-slate-50` ×2 (`BudgetVsActualTable.tsx:112`, `FacialTemplateSyncPanel.tsx:64`) and `bg-slate-100` ×1 (`InvoicePreviewModal.tsx:63`) → `bg-muted`, and `hover:bg-slate-100` ×2, `hover:bg-slate-50` ×1, `hover:bg-gray-100` ×1 → `hover:bg-accent` — with the twelve bullet groups summing 27 + 1 + 39 + 5 + 41 + 78 + 1 + 11 + 19 + 3 + 6 + 2 = 233; `bg-muted` appears in exactly 7 class strings across the twenty-two files and `bg-background` in exactly 1. Each "becomes" is read against that file's pre-task content, `git show "$BASE:<path>"`, with `BASE` derived by the repository-only rule above.
- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts` passes with `MIGRATED_DIRECTORIES` containing all three of `"src/features/finance/components"`, `"src/features/purchase-management/components"` and `"src/features/access-control/components"`, `pinnedFiles()` returning those directories' 10, 6 and 6 source files respectively, and `violations(PINNED, EXCEPTIONS, LEDGER)` returning `[]`.
- [ ] Re-measuring the twenty-two files `frontend/src/features/{finance,purchase-management,access-control}/components/*.tsx` with the guard's §3b grammar accounts for all 534 baseline occurrences as 233 migrated + 111 deleted `dark:` siblings + 190 left and logged, with both halves closing independently (372 non-`dark:` = 233 + 139; 162 `dark:` = 111 + 51); after the change the twenty-two files together retain exactly 190 grammar matches and zero six-digit hex literals, `finance` retaining 49, `purchase-management` 78 and `access-control` 63.
- [ ] `docs/frontend/unmapped-colours.md` gains 190 rows whose `task` cell is `APRAS-83` — 83 `GAP-TINT`, 33 `GAP-OUT-OF-BUDGET`, 33 `GAP-BORDER-100`, 29 `GAP-NO-TOKEN`, 10 `GAP-OVERLAY`, 2 `GAP-SWATCH`, and zero `GAP-NO-SURFACE`, zero `GAP-UNLISTED` — and `frontend/src/__tests__/themeTokenMigration.exceptions.json` gains exactly 145 entries whose `task` is `APRAS-83` (37 naming a `finance` file, 52 a `purchase-management` file, 56 an `access-control` file), with the guard's ledger-parity check passing in both directions.
- [ ] Exactly two brand-text occurrences carry a `-primary-text` token, at exactly these sites and no others: `DeviceTable.tsx`'s revealed device-key chip, whose `text-indigo-700` becomes `text-primary-text`, and `TransactionFormModal.tsx`'s file input, whose `file:text-indigo-700` becomes `file:text-primary-text`; no `-primary-text` appears on any `bg-`, `border-`, `ring-`, `divide-`, `outline-`, `fill-`, `stroke-` or `accent-` utility anywhere in the diff.
- [ ] Nine `text-`-prefixed indigo occurrences become `text-primary` because the element carrying them paints no glyphs — `AccessControlPage.tsx` ×1, `FacialTemplateSyncPanel.tsx` ×1, `GateMonitorPage.tsx` ×2, `RegisterDeviceModal.tsx` ×1, `CashBalanceCard.tsx` ×1, `CategoryTransactionDrilldown.tsx` ×1, `FinanceDashboardPage.tsx` ×1, `InvoicePreviewModal.tsx` ×1 (the last being `text-indigo-500`) — and no `indigo` class of any prefix, with or without a `dark:`, `hover:` or `file:` variant, remains anywhere in the twenty-two files.
- [ ] `frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts` passes, importing `contrastRatio`, `parseOklch` and `hexToOklch` from `src/lib/contrast.ts` and reading every colour from `src/index.css` and `node_modules/tailwindcss/theme.css` with no hard-coded colour literal, asserting to ±0.001 that `--primary-text` on `--accent` is 4.6547, `--muted-foreground` on `--card` 5.2249 and on `--muted` 4.6684, `--foreground` on `--card` 19.8801 and on `--background` 19.3178, `--primary-foreground` on `--primary` 5.7588, `--destructive` on `--card` 4.8073, and — against the 3:1 graphical floor — `--primary` on `--card` 3.4054, on `--background` 3.3091 and on `--accent`/`--muted` 3.0427.
- [ ] The same test declares, in an explicit in-file list with before/after ratios, every pair this task leaves or puts below 4.5:1: the graphical `--primary` at 3.0427 on `--accent`/`--muted` (2 sites) and 3.3091 on `--background` (2 sites); `CategoryTransactionDrilldown.tsx`'s kept `text-slate-300` glyph moving 1.4181 → 1.3263 as its `bg-slate-50` host cell becomes `bg-muted`, recorded as failing the 3:1 floor **before** this task as well as after; and the kept status pairs `text-emerald-600` on `bg-emerald-50` 3.5279, `text-emerald-500` on white 2.5032, `text-red-500` on white 3.8199, `text-red-600` on `bg-red-50` 4.4506, `text-amber-600` on `bg-amber-50` 3.0755 and `text-amber-700` on `bg-amber-50` 4.8611.
- [ ] The same test asserts that every kept **text** foreground sitting on a migrated background still clears 4.5:1: `text-gray-700` on `--muted` 9.2081 (from 9.8728 on `bg-gray-50`), `text-slate-800` on `--muted` 13.0962 (from 14.0024 on `bg-slate-50`), and `text-slate-700` 10.3442, `text-slate-800` 14.6574, `text-gray-700` 10.3058 and `text-gray-800` 14.6846 unchanged on `--card`.
- [ ] Grouping every grammar match in the twenty-two files by `(file, class-context span)` — using the guard's own exported `classContexts()`, not by line — yields exactly **one** span holding both a migrated occurrence and a kept `GAP-TINT` occurrence: the span covering `QuoteComparisonTable.tsx` lines 405–406, where the migrating `border-gray-200` sits beside the kept `bg-emerald-50/60`; and no other.
- [ ] All twenty-four status sets retain their original class strings verbatim: the three branches of `DeviceTable.tsx`'s `StatusBadge` config map (12 classes) and the three of `FacialTemplateSyncPanel.tsx`'s sync-status map (12), `AccessEventFeed.tsx`'s two ternaries (2 and 8), the two alert triples at `FacialTemplateSyncPanel.tsx:58` and `RegisterDeviceModal.tsx:68` (6 each), `CashBalanceCard.tsx`'s income and expense cards (6 each), `BudgetVsActualTable.tsx:99` (2), `StatementTable.tsx:41,44` (4), `StatementChart.tsx:53,59` (2), `PurchaseRequestDetailModal.tsx`'s justification (4) and approved (6) panels, the four red error triples at `PurchaseRequestFormModal.tsx:184`, `QuoteComparisonTable.tsx:386`, `QuoteFormModal.tsx:280` and `SelectQuoteModal.tsx:88` (3 each), the amber triple at `PurchaseRequestFormModal.tsx:281` (3), `QuoteComparisonTable.tsx`'s lowest-price total ternary (2), its three `bg-emerald-50/40` cell tints and one `bg-emerald-50/60` head tint (4) and its lowest-price card ternary (3), and `SelectQuoteModal.tsx`'s two warning panels (4 and 5) — 109 classes in all, each with a ledger row.
- [ ] `InvoicePreviewModal.tsx` contains no `emerald` class at all — its download link reads `bg-primary hover:bg-primary/90 text-primary-foreground` — and `QuoteComparisonTable.tsx`'s `<Award/>` glyph reads `text-primary`, while every other emerald occurrence in the twenty-two files is unchanged; `text-destructive` appears at exactly six sites, all `<Trash2/>` glyphs, in `PurchaseRequestFormModal.tsx` ×1, `PurchaseRequestsPage.tsx` ×1, `QuoteComparisonTable.tsx` ×2 and `QuoteFormModal.tsx` ×2, and `AccessEventFeed.tsx` still reads `text-red-500` on its `<XCircle/>`.
- [ ] Every opacity modifier present in the baseline is carried over unchanged on migrated classes: `bg-slate-950/70` → `bg-foreground/70` (×1, `InvoicePreviewModal.tsx`), `hover:bg-indigo-700` → `hover:bg-primary/90` (×1, `FinanceDashboardPage.tsx`) and `hover:bg-emerald-700` → `hover:bg-primary/90` (×1, `InvoicePreviewModal.tsx`); the ten `bg-black/40`, `bg-black/50` and `bg-black/60` scrims are unchanged and logged under `GAP-OVERLAY`; the five kept `bg-emerald-50/40` and `bg-emerald-50/60` tints are unchanged; and the diff contains no `text-primary/N` and no `text-primary-text/N` anywhere.
- [ ] No `dark:` sibling of a migrated base survives: across the sixteen `finance` and `access-control` files exactly 51 `dark:` classes remain, all of them ledger-logged and consisting only of `dark:border-slate-800` ×13, `dark:text-red-400` ×7, `dark:text-emerald-400` ×6, `dark:bg-red-950/50` ×4, `dark:bg-emerald-950/50` ×3, `dark:text-slate-200` ×3, `dark:divide-slate-800/80` ×2, `dark:bg-amber-950/50` ×2, `dark:text-amber-400` ×2, `dark:border-red-900/50` ×2, `dark:text-slate-300` ×2, and one each of `dark:bg-slate-800`, `dark:text-slate-400`, `dark:bg-emerald-950`, `dark:bg-red-950` and `dark:text-slate-700`; no `dark:bg-slate-900`, `dark:text-white`, `dark:text-slate-100`, `dark:text-indigo-400`, `dark:text-indigo-300`, `dark:border-slate-700`, `dark:border-indigo-900/50`, `dark:bg-indigo-950`, `dark:bg-indigo-950/40`, `dark:bg-slate-950`, `dark:bg-slate-900/60`, `dark:bg-slate-800/40`, `dark:hover:text-slate-200`, `dark:hover:bg-slate-800`, `dark:hover:bg-slate-800/50` or `dark:hover:bg-indigo-950` remains anywhere; and the six `purchase-management` files contain zero `dark:` occurrences before and after.
- [ ] `describe("the pilot's own ledger arithmetic")` and the equivalent blocks for every sibling already present in the file still pass with their assertions unedited, and no ledger row or exceptions entry belonging to another task is modified.
- [ ] `frontend/src/components/__tests__/TenantBrandReach.test.tsx` passes with three added cases that mount `CashBalanceCard` (with a balance and `isLoading={false}`), `SelectQuoteModal` (with `isOpen` and a quote) and `DeviceTable` (with one `ONLINE` device and an `onRegenerateKey` that resolves a key, after clicking its regenerate button so the key chip renders) under the mocked `useTenantProfile`, assert `getComputedStyle(document.documentElement).getPropertyValue("--primary")` equals the mocked theme's value, and assert, **per component**, over the **whitespace-split class tokens of the FULL rendered markup** — every `class` value in the mounted output split on `/\s+/`, explicitly **including the tokens contributed by any `components/ui/` primitive the component renders**, not only the tokens written in the component's own source — that the token set is exactly as follows. Splitting is strict, so `bg-accent`, `hover:bg-accent` and `hover:bg-accent/80` are three distinct tokens and none matches another; no substring matching anywhere in this test. `CashBalanceCard` renders **no** `components/ui/` primitive, so its set is entirely its own: contains `bg-card`, `border-border`, `bg-accent`, `text-primary`, `text-muted-foreground` and `text-foreground`, and contains none of the tokens `text-primary-text`, `bg-primary`, `text-primary-foreground`, `text-destructive` or `bg-muted`. `SelectQuoteModal` renders `ui/button` (a `ghost` close button, an `outline` cancel button, and a **variantless submit button that therefore takes `buttonVariants`' `default` variant**) and `ui/textarea`: contains `bg-card`, `border-border`, `bg-muted`, `text-foreground` and `text-muted-foreground` from its own markup, and contains `bg-primary` and `text-primary-foreground` **contributed by the already-migrated `ui/button` `default` variant**, and contains none of the tokens `text-primary`, `text-primary-text`, `bg-accent` or `text-destructive`. `DeviceTable` renders `ui/button` at the `outline` variant only, which contributes `border-input`, `bg-background`, `hover:bg-accent` and `hover:text-accent-foreground` and no token on either list below: contains `text-primary-text`, `bg-accent`, `border-border`, `text-foreground` and `text-muted-foreground`, and contains none of the tokens `text-primary`, `bg-primary`, `bg-card`, `bg-muted`, `text-primary-foreground` or `text-destructive`. Never a colour literal is asserted anywhere in the test.
- [ ] `git diff --exit-code frontend/src/index.css` succeeds, and the set of paths this task's own commits touch — `git log --format='%H %s' | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-83\):' | cut -d' ' -f1 | xargs -n1 git show --pretty=format: --name-only | sort -u`, which needs no branch point, no range and no report, and which is exactly this task's set regardless of which of APRAS-81 / APRAS-83 landed first — contains no backend file, no Alembic revision, no route-registry change, no file under `frontend/src/components/ui/`, `frontend/src/features/lot-management/`, `frontend/src/features/visitor-management/`, `frontend/src/features/document-management/`, `frontend/src/features/occurrence-management/`, `frontend/src/features/project-management/` or `frontend/src/features/asset-management/`, and no path outside this set of thirty-one: the twenty-two `.tsx` under the three component directories, `frontend/src/__tests__/themeTokenMigration.test.ts`, `frontend/src/__tests__/themeTokenMigration.exceptions.json`, `frontend/src/__tests__/brandTextRole.test.ts`, `frontend/src/components/__tests__/TenantBrandReach.test.tsx`, `frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts`, `docs/frontend/unmapped-colours.md`, `docs/tasks/APRAS-83-spec.md`, `docs/tasks/APRAS-83-mock.html` and `docs/frontend/theme-token-mapping.md` (the last appearing only under the *carried* outcome, and absent under the *consumed* one, which makes the set thirty under consumption). `brandTextRole.test.ts` is APRAS-87's guard (`0815915`), which postdates this spec: it reconciles a live scan of bare `text-primary` against a declared set of graphical sites, so a migration that moves an icon onto `text-primary` must append its declaration there or the guard fails. This task's change to it must be a pure append inside `GRAPHICAL_PRIMARY_SITES` — no existing declaration removed or weakened, and no change to that file's surfaces, ratios or imports. The untracked `docs/tasks/APRAS-8*` spec and mock files the working tree already carries belong to other tasks and must never be staged by this one.
- [ ] `npx tsc -b` completes with no error.
- [ ] `npx vitest run --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint` over the twenty-two touched component files reports at most the 2 errors and 0 warnings across 2 files present today (`FacialTemplateSyncPanel.tsx` 1 error, `RegisterDeviceModal.tsx` 1 error, and zero in all ten `finance` and all six `purchase-management` files), and `npx eslint` over the four other linted files this task touches — `frontend/src/__tests__/themeTokenMigration.test.ts`, `frontend/src/components/__tests__/TenantBrandReach.test.tsx`, `frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts` and `frontend/src/__tests__/themeTokenMigration.exceptions.json` where linted — reports 0 errors and 0 warnings. No repository-wide total is asserted and none is needed: those are the only linted files this task changes, so no repository total can move through an act of APRAS-83 nor be moved into this result by a sibling landing first. (Provenance at `a8fc8ab`: 375 errors + 2 warnings across 64 files repository-wide.)
- [ ] The fourteen existing suites in `frontend/src/features/finance/__tests__/`, `frontend/src/features/purchase-management/__tests__/` and `frontend/src/features/access-control/__tests__/` — 175 tests in total — pass without modification.
- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts --reporter=verbose` reports every individual test finishing under 2 s, including `it("fails when any single exception is removed")`, which this task takes to 145 more exceptions over 22 more pinned files than whatever the totals read at `BASE` (provenance at `a8fc8ab`: 882 ms against 254 exceptions over 26 pinned files — provenance only, asserted as the fixed 2 s ceiling and not as a delta); the scan memo inside `violations()` is at module scope, keyed on the file path and its source text.
