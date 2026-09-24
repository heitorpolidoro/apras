# APRAS-82 — Migrate document and occurrence management to semantic theme tokens

Child 5 of 8 of the APRAS-77 split, specified against the **amended** contract:
APRAS-78's three artefacts as extended by APRAS-79 / APRAS-80 / APRAS-81 and
amended by APRAS-88 at `c7c42fc`. This task **consumes** that contract and may
not extend it: no row added to `docs/frontend/theme-token-mapping.md`, no new
gap code, no token in `frontend/src/index.css`. Every call below is an
*application* of a published rule to a named call site.

Two directories, not one, because the operator scoped this child that way. They
are complementary in exactly the way APRAS-81's pair was:
`document-management` is a `dark:`-heavy slate/indigo feature (247 occurrences,
**all 100** of the pair's `dark:` occurrences), `occurrence-management` is a
gray/indigo feature with **zero** `dark:` occurrences (200). The two halves
exercise opposite halves of §1g.

## Scope

`frontend/src/features/document-management/components` — the six files
`DocumentCenterPage`, `DocumentGridTable`, `DocumentUploadModal`,
`FolderFormModal`, `FolderTreeSidebar`, `PDFViewerModal` — and
`frontend/src/features/occurrence-management/components` — the five files
`NewOccurrenceModal`, `OccurrenceBookPage`, `OccurrenceDetailsView`,
`OccurrenceTable`, `OccurrenceTimelineLog` — migrated from hard-coded Tailwind
palette classes to the tokens the table names, with every class left behind
logged in the ledger and excepted in the guard; then both directory paths
appended to `MIGRATED_DIRECTORIES`.

Not covered: either feature's `hooks/` or `__tests__/` (neither
`hooks/useDocuments.ts` nor `hooks/useOccurrences.ts` contains a palette
class, and the guard's directory walk does not reach them), any other feature
directory, `index.css`, the backend, the `.dark` block, and any amendment to
the mapping table, the ledger's rules or the guard's grammar.

**No mockup.** This is a token substitution; every migrated pair is either
byte-identical in `:root` or a published, budgeted colour move already
tabulated. The visible changes are enumerated under *What this proves, and what
it misses*.

## The re-measurement

Measured now, at `a8fc8ab`, over the eleven non-test `.tsx` files with the §3b
grammar exactly as the guard builds it (scale alternatives longest-first, both
word boundaries, opacity suffix). **Nothing here is carried over from a
sibling.**

| Figure | Value |
| --- | --- |
| Palette occurrences | **447** — the task's reported figure reproduces exactly |
| Files | **11** — reproduces exactly |
| Distinct classes | 102 |
| Six-digit hex literals anywhere in the eleven files | **0** |
| `dark:`-prefixed | **100** (22.4%), against **347** non-`dark:` |
| `document-management/components` | 6 files, **247** occurrences, **100** `dark:` |
| `occurrence-management/components` | 5 files, **200** occurrences, **0** `dark:` |
| Per file | DocumentGridTable 62, OccurrenceDetailsView 57, OccurrenceTable 51, DocumentUploadModal 48, FolderFormModal 47, FolderTreeSidebar 44, NewOccurrenceModal 39, OccurrenceBookPage 27, OccurrenceTimelineLog 26, DocumentCenterPage 24, PDFViewerModal 22 |

## Pairing a `dark:` class with its base

The settled rule: a `dark:` occurrence pairs with the class in the **same
class-context span**, with the **same utility prefix**, the **same non-`dark:`
variant chain**, **nearest preceding**. A `dark:` sibling of a migrated class
is deleted (§1g); a `dark:` sibling of a kept class is left and logged under
its base's code.

Applied mechanically here, **every one of the 100 `dark:` occurrences has a
base**; there is no orphan.

The variant-chain clause is load-bearing at **six** sites, all of the shape
`text-slate-400 hover:text-slate-600 … dark:hover:text-slate-200`
(`DocumentUploadModal:134`, `FolderFormModal:116`, `FolderTreeSidebar:60`,
`PDFViewerModal:66`) and `hover:text-indigo-600 … dark:hover:text-indigo-400`
(`FolderTreeSidebar:93`, `:107`): the naive nearest-preceding base is the
resting `text-slate-400`, the chain-correct base is the `hover:` class. In all
six both candidates migrate, so the disposition is unchanged — stated so a
reviewer need not re-derive it. The clause is applied from the start
regardless; it is the rule, not a tiebreak.

## The disposition of all 447

| Disposition | n |
| --- | --- |
| Light class migrated to a token | **240** |
| `dark:` sibling of a migrated class, **deleted** (§1g) | **78** |
| Left untouched and logged | **129** (107 non-`dark:`, 22 `dark:`) |
| **Total** | **447** |

The two halves close independently: non-`dark:` 347 = 240 + 107, and `dark:`
100 = 78 + 22.

Per file, as `migrated / deleted / logged`:

| File | m / d / l |
| --- | --- |
| `DocumentCenterPage.tsx` | 16 / 8 / 0 |
| `DocumentGridTable.tsx` | 27 / 21 / 14 |
| `DocumentUploadModal.tsx` | 21 / 13 / 14 |
| `FolderFormModal.tsx` | 24 / 13 / 10 |
| `FolderTreeSidebar.tsx` | 23 / 15 / 6 |
| `PDFViewerModal.tsx` | 14 / 8 / 0 |
| `NewOccurrenceModal.tsx` | 25 / 0 / 14 |
| `OccurrenceBookPage.tsx` | 22 / 0 / 5 |
| `OccurrenceDetailsView.tsx` | 31 / 0 / 26 |
| `OccurrenceTable.tsx` | 20 / 0 / 31 |
| `OccurrenceTimelineLog.tsx` | 17 / 0 / 9 |

Per directory: `document-management` 125 / 78 / 44 = 247;
`occurrence-management` 115 / 0 / 85 = 200.

The 129 occupy **77** distinct `(file, class)` pairs — 22 in
`document-management`, 55 in `occurrence-management` — which is the number of
exceptions entries this task appends.

## The gap codes, each counted from its own membership

| Code | Occ. | Derivation, enumerated |
| --- | --- | --- |
| `GAP-OUT-OF-BUDGET` | **69** | non-`dark:` **52**: `text-gray-800` 20 (all of them), `text-slate-700` 15 (all), `text-gray-700` **15** (of 17; `OccurrenceTable:32` and `:45`'s are inside the badge maps and are `GAP-TINT`), `text-slate-800` 1 (`DocumentGridTable:39`), `text-slate-300` 1 (`DocumentGridTable:38`). Plus **17** `dark:` siblings: `dark:text-slate-300` **15** (of 16; `DocumentGridTable:89`'s pairs with a migrating `text-slate-600` and is deleted), `dark:text-slate-600` 1, `dark:text-slate-200` 1. `52 + 17 = 69` |
| `GAP-TINT` | **30** | the status sets enumerated below: 9 + 2 + 2 + 2 + 6 + 5 + 4, counted per set |
| `GAP-NO-TOKEN` | **24** | `OccurrenceTable`'s status map, amber 3 + blue 3 + rose 3 = 9; its priority map, rose 2 + orange 2 + sky 2 = 6; `OccurrenceTimelineLog:67`'s internal-note badge, amber 3; `DocumentGridTable:166`'s delete-button hover, rose 2 + 2 `dark:` = 4; `FolderTreeSidebar:121`'s delete-button hover, rose 1 + 1 `dark:` = 2. `9 + 6 + 3 + 4 + 2 = 24` |
| `GAP-OVERLAY` | **3** | `bg-black/40` ×3 — `NewOccurrenceModal:55`, `OccurrenceDetailsView:39`, `OccurrenceDetailsView:61`. No `dark:` siblings |
| `GAP-BORDER-100` | **3** | `ring-gray-100` 1 (`OccurrenceTimelineLog:57`), `border-gray-100` 1 (`:58`), `divide-gray-100` 1 (`OccurrenceTable:86`). No `dark:` siblings |

`69 + 30 + 24 + 3 + 3 = 129`. **Zero `GAP-SWATCH`, zero `GAP-NO-SURFACE`, zero
`GAP-UNLISTED`.** Cross-check from the other direction: the codes hold
52 + 28 + 21 + 3 + 3 = **107** non-`dark:` and 17 + 2 + 3 = **22** `dark:`
occurrences, matching the disposition table's two halves.

There is no `GAP-SWATCH` because neither directory colours a **category**: the
occurrence *category* is rendered as a single neutral chip
(`OccurrenceTable:93`, one `bg-gray-100 text-gray-800 … border-gray-200` for
every category) and as `<option>` text, never as a per-category hue. There is
no `GAP-NO-SURFACE` because all eight `text-white` occurrences sit on a
background that does have a row (seven on `bg-indigo-600`, one on
`bg-emerald-600`), and the one `border-white` sits on a card.

## Every status set in these directories

The triple rule is binding tree-wide: a status variant's class set migrates as
a **unit or not at all**, every member must have a row in §1b–1e, and the
resulting pair must hold ≥ 4.5:1. **A ternary's or a `switch`'s branches are
one set**, exactly as APRAS-80 read its sets 2+3 and APRAS-81 its sets 1, 2 and
11 — the branches are the same property of the same element in different
states, so the rule is applied to the whole construct, never branch by branch.

| # | Set | Members | n | Code |
| --- | --- | --- | --- | --- |
| 1 | `OccurrenceTable:22–32` `getStatusBadgeClass`, 6 branches × 3 | amber 3, blue 3, indigo 3, emerald 3, rose 3, gray 3 | 18 | TINT 9 (indigo, emerald, gray) / NO-TOKEN 9 (amber, blue, rose) |
| 2 | `OccurrenceTable:39–45` `getPriorityBadgeClass`, 4 branches × 2 | rose 2, orange 2, sky 2, gray 2 | 8 | TINT 2 (gray) / NO-TOKEN 6 |
| 3 | `OccurrenceTable:100,102` visibility glyph ternary | `text-emerald-600` (Globe) \| `text-gray-400` (Lock) | 2 | TINT |
| 4 | `NewOccurrenceModal:158` visibility glyph ternary | `text-emerald-600` (Globe) \| `text-gray-500` (Lock) | 2 | TINT |
| 5 | `OccurrenceDetailsView:71,76` visibility badge ternary | `text-emerald-700`/`bg-emerald-50`/`border-emerald-200` \| `text-gray-600`/`bg-gray-100`/`border-gray-200` | 6 | TINT |
| 6 | `OccurrenceDetailsView:160–165` resolution-notes panel | `bg-emerald-50`, `border-emerald-200`, `text-emerald-900`, `text-emerald-600`, `text-emerald-800` | 5 | TINT |
| 7 | `DocumentGridTable:143` download-button hover | `hover:text-emerald-600`, `hover:bg-emerald-50` + 2 `dark:` | 4 | TINT |
| 8 | `OccurrenceTimelineLog:67` internal-note badge | `text-amber-700`, `bg-amber-50`, `border-amber-200` | 3 | NO-TOKEN |
| 9 | `DocumentGridTable:166` delete-button hover | `hover:text-rose-600`, `hover:bg-rose-50` + 2 `dark:` | 4 | NO-TOKEN |
| 10 | `FolderTreeSidebar:121` delete-button hover | `hover:text-rose-600` + 1 `dark:` | 2 | NO-TOKEN |

**The rowless member of each.** Sets 1 and 2 are blocked by their `amber`,
`blue`, `rose`, `orange` and `sky` branches, none of which has a row at any
scale, and by `text-gray-700` / `text-gray-800`; had they been read
branch-by-branch, the indigo branch of set 1 would have migrated on its own and
split a six-colour status scale, which the unit rule exists to prevent. Sets 5
and 6 are blocked by `bg-emerald-50`, which has no §1b row for its role, and
set 6 additionally by `text-emerald-900`. Sets 3, 4 and 7 are the operator's
status ruling applied through **§1f case 3**: every emerald in them is a
non-interactive status glyph or the tint behind one, so it stays regardless of
its row, and its ternary partner stays with it. Sets 8–10 are `amber` and
`rose`, families with no token at all.

**Three consequences worth stating once.**

1. **Two gray classes that have rows are kept because their ternary partner is
   an emerald status glyph** — `OccurrenceTable:102`'s `text-gray-400` and
   `NewOccurrenceModal:158`'s `text-gray-500` (sets 3 and 4). This is APRAS-81
   set 5's precedent applied to a case where the neutral branch *does* have a
   row, and it is the reason the ledger carries a `text-gray-400` and a
   `text-gray-500` entry in files where the same classes also migrate
   elsewhere. It is named as a **review duty**, not hidden in a count.
2. **`emerald` splits within one PR, correctly.** `PDFViewerModal:58`'s
   download `<button>` carries `bg-emerald-600 hover:bg-emerald-700 text-white`
   — an **interactive fill**, so §1f case 3 migrates it to the primary triple,
   exactly as APRAS-78's pilot migrated `button.tsx`'s `success` variant.
   `DocumentGridTable:143`'s download **icon button** carries
   `hover:text-emerald-600 hover:bg-emerald-50`, whose surface member has no
   row, so set 7 stays whole. The two verdicts are consistent and both are
   forced; a reviewer should check precisely this pair.
3. **No red occurs at all.** Neither directory contains a single `red-*` class;
   the destructive affordances are `rose`, which has no token, so **no
   `text-destructive` appears anywhere in this diff**.

**The proof there is no eleventh set.** A split span is a class-context span
holding both a migrated occurrence and a kept `GAP-TINT` occurrence. Run
mechanically over all 447 occurrences grouped by `(file, span)`, that check
returns **exactly one** span: `DocumentGridTable:143`, which holds the
migrating resting colour `text-slate-500` beside set 7's four kept classes.
That is **not** a split set — the button's resting foreground is neutral and
takes its §1d row, while the button's *hover* pair is the emerald unit — and it
is the same shape APRAS-80 recorded at `VisitorAuthPage:144`. The implementer
must re-run the check and get the same single span. (Spans that mix a migrated
occurrence with a kept occurrence under any *other* code are expected and are
not counted — e.g. `OccurrenceTable:93`'s category chip, where `text-gray-800`
is `GAP-OUT-OF-BUDGET` beside two migrating neutrals.)

## Behaviour — the substitutions

Every substitution is a table row applied verbatim.

- `bg-white` ×24 → **`bg-card`**, and `focus:bg-white` ×4 → **`focus:bg-card`**
  — §1f case 1, settled below. Zero take `bg-background`, zero take
  `bg-popover`.
- `border-white` ×1 → `border-card` (`OccurrenceTimelineLog:57`, the timeline
  dot's ring against the card).
- `bg-slate-950/70` ×3 → `bg-foreground/70` — §1b's `bg-slate-950` row
  (ΔE 4.69, `noted`), *not* `GAP-OVERLAY`; settled below.
- `border-slate-200` ×13 + `border-gray-200` ×5 → `border-border`;
  `divide-slate-200` ×1 → `divide-border`.
- `border-slate-300` ×6 → `border-input`.
- `text-slate-900` ×11 + `text-gray-900` ×6 → `text-foreground`.
- To `text-muted-foreground` ×54: `text-slate-500` 14, `text-gray-500` 13,
  `text-slate-400` 11, `text-gray-400` 7, `text-slate-600` 2, `text-gray-600`
  1, plus `hover:text-slate-600` 4 and `hover:text-gray-600` 2 →
  `hover:text-muted-foreground`.
- Neutral fills ×29: resting `bg-gray-50` 10, `bg-slate-100` 3, `bg-slate-50`
  2, `bg-gray-100` 2 → `bg-muted`; interaction `hover:bg-slate-100` 5,
  `hover:bg-gray-100` 4, `hover:bg-gray-200` 1 → `hover:bg-accent`, and
  `hover:bg-slate-50/80` 1, `hover:bg-gray-50/80` 1 → `hover:bg-accent/80` —
  §1f case 2, settled below.
- **Indigo ×73, split by §1k** — see the next section: 12 → `*-primary-text`,
  61 → `primary` / `accent` / `border` / `ring`.
- Emerald ×2 → `bg-primary` and `hover:bg-primary/90` (`PDFViewerModal:58`) —
  §1f case 3's interactive branch.
- `text-white` ×8 → `text-primary-foreground`. All eight sit on a migrating
  `bg-indigo-600` or `bg-emerald-600`, so there is no `GAP-NO-SURFACE`.

`28 + 1 + 3 + 19 + 6 + 17 + 54 + 29 + 73 + 2 + 8 = 240`, reading the bullets in
order.

**Opacity modifiers are carried over verbatim**, never dropped and never
rounded to a different `N`: `bg-slate-950/70` → `bg-foreground/70` ×3,
`hover:bg-slate-50/80` → `hover:bg-accent/80`, `hover:bg-gray-50/80` →
`hover:bg-accent/80`, and `hover:bg-indigo-700` → `hover:bg-primary/90` ×7 plus
`hover:bg-emerald-700` → `hover:bg-primary/90` ×1, per §1i's named target. §1i
measures such a target against the base token with the alpha declared
**unmeasured**. **No `text-primary/N` and no `text-primary-text/N` is produced
anywhere**, so this child creates no APRAS-90 site.

Each of the 240 takes its `dark:` sibling with it where it has one: **78
deletions**, all of them in `document-management`. All 115 of
`occurrence-management`'s migrations carry no `dark:` sibling at all, because
that directory has none.

## §1k applied — which brand classes are characters

§1k asks one question per call site, from the JSX, with no measurement: *does
this element paint glyphs of text?* Traced at every site, not assumed.

**Characters — take `*-primary-text`, floor 4.5:1 (12 occurrences).**

| Site | Class → target | Why it is text | Surface | After |
| --- | --- | --- | --- | --- |
| `FolderTreeSidebar:46` | `text-indigo-700` → `text-primary-text` | selected tree row `<div>` whose subtree renders `{folder.name}` | `bg-indigo-50` → `--accent` | **4.6547** |
| `FolderTreeSidebar:187` | `text-indigo-700` → `text-primary-text` | selected "all documents" row, renders `{t(…)}` | `bg-indigo-50` → `--accent` | **4.6547** |
| `FolderTreeSidebar:174` | `text-indigo-600` → `text-primary-text` | `<button>` rendering `<FolderPlus/>` **and** `<span>{t(…)}</span>` — §1k's mixed element wins for text | card → `--card` | **5.2096** |
| `FolderTreeSidebar:174` | `hover:text-indigo-700` → `hover:text-primary-text` | same element | `--card` | **5.2096** |
| `OccurrenceTable:89` | `text-indigo-600` → `text-primary-text` | `<td>` rendering `{item.protocol_number}` | card → `--card` | **5.2096** |
| `OccurrenceTable:134` | `text-indigo-600` → `text-primary-text` | `<button>` rendering `<Eye/>` and the "Ver Detalhes" label — mixed | `bg-indigo-50` → `--accent` | **4.6547** |
| `OccurrenceTable:134` | `hover:text-indigo-800` → `hover:text-primary-text` | same element | `hover:bg-indigo-100` → `--accent` | **4.6547** |
| `OccurrenceTimelineLog:74` | `text-indigo-700` → `text-primary-text` | `<div>` rendering the status transition string | `bg-gray-50` → `--muted` | **4.6547** |
| `OccurrenceDetailsView:67` | `text-indigo-600` → `text-primary-text` | `<span>` rendering `{occurrence.protocol_number}` | `bg-indigo-50` → `--accent` | **4.6547** |
| `OccurrenceDetailsView:149` | `text-indigo-600` → `text-primary-text` | `<a>` rendering `Evidência #n` | `bg-indigo-50` → `--accent` | **4.6547** |
| `OccurrenceDetailsView:250` | `text-indigo-600` → `text-primary-text` | `<Link>` rendering `{t("infractions.promote.action")}` | modal panel → `--card` | **5.2096** |
| `OccurrenceDetailsView:260` | `text-indigo-600` → `text-primary-text` | `<Link>` rendering `{t("infractions.promote.linked")}` | `--card` | **5.2096** |

`FolderTreeSidebar:46` and `:187`'s two `dark:text-indigo-400` siblings are
deleted with them.

**Graphical — keeps `*-primary`, floor 3:1 (61 occurrences).** Twenty-two are
`text-`-prefixed brand classes on an element that paints no glyphs; thirty-nine
are non-`text-` utilities, which §1k makes graphical always.

The twenty-two `text-`-prefixed graphical sites, by surface:

| Surface | Sites | `--primary` on it |
| --- | --- | --- |
| `--card` (16) | `DocumentCenterPage:128` `<FolderPlus/>`; `DocumentGridTable:74` `<FileText/>`; `DocumentGridTable:133,154` `hover:text-indigo-600` on `<button>`s whose only child is `<Eye/>` / `<History/>`; `DocumentUploadModal:124` `<FileUp/>`; `FolderFormModal:106` `<FolderPlus/>`; `FolderFormModal:168` a raw `<input type="checkbox">` with no children; `FolderTreeSidebar:69` `<FolderOpen/>`, `:192` `<FolderIcon/>`, `:93,:107` `hover:text-indigo-600` on icon-only `<button>`s; `PDFViewerModal:36` `<FileText/>`; `NewOccurrenceModal:59` `<Plus/>`; `OccurrenceBookPage:63` `<Filter/>`; `OccurrenceTimelineLog:50` `<MessageSquare/>`, `:107` a raw checkbox | 3.4054 |
| `--accent` (2) | `DocumentCenterPage:100` `<FileText/>` in a `bg-indigo-50` tile; `OccurrenceBookPage:35` a `<div>` whose only child is `<BookOpen/>`, in a `bg-indigo-50` tile | **3.0427** |
| `--muted` (4) | `NewOccurrenceModal:136,154` raw checkboxes and `:140` `<Eye/>`, all inside `bg-gray-50` labels; `OccurrenceDetailsView:173` `<AlertCircle/>` inside the `bg-slate-50` management panel | **3.0427** |

The thirty-nine non-`text-` indigo utilities: `focus:ring-indigo-500` ×11 →
`focus:ring-ring`, `bg-indigo-600` ×8 → `bg-primary`, `bg-indigo-50` ×7 →
`bg-accent`, `hover:bg-indigo-700` ×7 → `hover:bg-primary/90`,
`hover:bg-indigo-50` ×2 and `hover:bg-indigo-100` ×1 → `hover:bg-accent`,
`border-indigo-200` ×2 → `border-border`, `focus:border-indigo-500` ×1 →
`focus:border-primary`. `11 + 8 + 7 + 7 + 3 + 2 + 1 = 39`, which with the
twenty-two `text-` graphical sites gives **61** graphical. With the twelve
`*-primary-text` sites that is **73** migrating indigo occurrences in all,
`dark:` siblings excluded.

## The context-dependent cases, settled at the real call sites

**The verification tests cannot detect a wrong choice in any of these.** They
are a **human review duty on this diff**.

**§1f case 1 — `bg-white` ×24 and `focus:bg-white` ×4 all take `bg-card`.**
Neither page root carries a background class at all (`DocumentCenterPage:94`
and `OccurrenceBookPage:31` are both bare `container mx-auto …`), so **no site
in these eleven files is a page shell** and none takes `bg-background`; none is
a floating layer with popover semantics, so none takes `bg-popover`. Eight of
the twenty-eight are **raw `<select>`/`<textarea>`/`<input>` fills**
(`DocumentUploadModal:150,241`, `FolderFormModal:143,184`,
`NewOccurrenceModal:78`, `OccurrenceDetailsView:185,202,221`), plus the four
`focus:bg-white` on `OccurrenceBookPage`'s raw input and three selects. They
take **`bg-card`**, following APRAS-80's already-accepted precedent, even
though `components/ui/`'s primitives use `bg-background`; the two are
byte-identical in `:root` and diverge only under a tenant theme. The divergence
is **recorded, not resolved** here.

**The one genuinely arguable site class: `bg-slate-950/70` ×3**
(`PDFViewerModal:26`, `DocumentUploadModal:115`, `FolderFormModal:97`), the
modal scrims. `GAP-OVERLAY` (§1h code 1) is defined for `bg-black` and
`bg-white` *only*, and `bg-slate-950` **has** a §1b row (`bg-foreground`,
ΔL 1.10, ΔE 4.69, `noted`), so the contract requires migration to
`bg-foreground/70`. The three `bg-black/40` scrims in `occurrence-management`
*are* code 1 and stay. That the same UI element resolves two different ways in
one PR is a consequence of the published codes, not a defect of this child;
naming it here is the alternative to silently inventing a ninth code. **The
inheritance it creates is stated rather than hidden:** `--foreground` inverts
in the `.dark` block, so whoever enables `.dark` inherits three scrims that
would paint near-white. `.dark` is never applied today, so nothing changes now.

**§1f case 2 — `bg-muted` versus `bg-accent`.** Seventeen resting fills take
`bg-muted`: the table heads and panels at `DocumentGridTable:56`,
`OccurrenceTable:74`, `OccurrenceDetailsView:96,131,171`,
`OccurrenceTimelineLog:58`; the chips at `DocumentGridTable:89`,
`FolderTreeSidebar:78`, `OccurrenceTable:93`; the PDF viewer stage at
`PDFViewerModal:74`; the filter fills at `OccurrenceBookPage:76,84,99,116`; the
checkbox cards at `NewOccurrenceModal:131,149`; and the cancel button's resting
fill at `NewOccurrenceModal:172`. Twelve interaction fills take `bg-accent`:
`DocumentUploadModal:134`, `FolderFormModal:116`, `PDFViewerModal:66`,
`FolderTreeSidebar:47,188`, `NewOccurrenceModal:64,131,149,172`,
`OccurrenceDetailsView:87`, plus `DocumentGridTable:70` and
`OccurrenceTable:88`'s row hovers as `hover:bg-accent/80`.

**§1f case 3 — emerald 500–700.** The band holds **6** occurrences here.
**One pair migrates** — `PDFViewerModal:58`'s `bg-emerald-600
hover:bg-emerald-700`, an interactive `<button>` fill — and **four stay**:
`DocumentGridTable:143`'s hover pair (set 7) and the three status glyphs of
sets 3, 4 and 6. This is the first child since the pilot to exercise the
*migrating* branch of case 3.

## Contrast, re-derived by importing `frontend/src/lib/contrast.ts`

Measured by importing `contrastRatio`, `parseOklch` and `hexToOklch` from
`frontend/src/lib/contrast.ts` — never reimplemented — with token values read
from `src/index.css` and palette values read from
`node_modules/tailwindcss/theme.css` (**Tailwind 4's OKLCH palette**, whose
lightness is written as a percentage and must be divided by 100 before
`parseOklch` sees it). The measurement reproduces APRAS-78's, APRAS-80's and
APRAS-88's published figures to the digit (`--primary-foreground` on
`--primary` 5.7588, `--muted-foreground` on `--muted` 4.6684, `--primary-text`
on `--card` 5.2096 and on `--accent` 4.6547, `--primary` on `--card` 3.4054),
which is the check that it is the same measurement.

| Pair | Background | Today | After |
| --- | --- | --- | --- |
| Headings `text-slate-900` / `text-gray-900` → `text-foreground` | `--card` | 17.8448 / 17.7467 | **19.8801** |
| Secondary text `text-slate-500` / `text-gray-500` → `text-muted-foreground` | `--card` | 4.7670 / 4.8357 | **5.2249** |
| `text-slate-600` / `text-gray-600` → `text-muted-foreground` | `--card` | 7.5635 / 7.5608 | **5.2249** |
| Table-head text `text-slate-500` on `bg-slate-50`, `text-gray-500` on `bg-gray-50` → on `bg-muted` | `--muted` | 4.5540 / 4.6325 | **4.6684** |
| Tag chip `text-slate-600` on `bg-slate-100` → on `bg-muted` | `--muted` | 6.8989 | **4.6684** |
| **`text-slate-400` ×11 / `text-gray-400` ×7 → `text-muted-foreground`** | `--card` | 2.6282 / 2.6023 | **5.2249** — repairs an AA failure at 18 sites |
| Primary buttons `text-white` on `bg-indigo-600` → `text-primary-foreground` on `bg-primary` | `--primary` | 6.4414 | **5.7588** |
| Download button `text-white` on `bg-emerald-600` → `text-primary-foreground` on `bg-primary` | `--primary` | 3.7194 | **5.7588** — repairs an AA failure at 1 site |
| **Selected tree row `text-indigo-700` → `text-primary-text`** ×2 | `--accent` | 7.2164 | **4.6547** |
| **Protocol / evidence chips `text-indigo-600` → `text-primary-text`** | `--accent` | 5.7621 | **4.6547** |
| **Links, protocol cell, "Criar" button `text-indigo-600` → `text-primary-text`** | `--card` | 6.4414 | **5.2096** |
| **Timeline transition `text-indigo-700` → `text-primary-text`** | `--muted` | 7.7283 | **4.6547** |
| Brand icons `text-indigo-600` / `text-indigo-500` → `text-primary` (graphical, floor 3) | `--card` | 6.4414 / 4.5587 | **3.4054** |
| Tile and inline glyphs → `text-primary` (graphical, floor 3) | `--accent` / `--muted` | 5.7621 / 6.1708 | **3.0427** |

**No full-opacity text pair this task produces falls below 4.5:1.** The tightest
are `--primary-text` on `--accent`/`--muted` at 4.6547 and `--muted-foreground`
on `--muted` at 4.6684.

### Kept pairs whose *surface* moves, measured so nobody attributes them later

A kept foreground can sit on a migrated background. Every such **text** pair
stays far above AA, so **this migration converts no passing text pair into a
failing one**: `text-gray-800` on `bg-gray-50` → on `--muted` 14.0676 →
**13.1205**; `text-gray-800` on `bg-gray-100` → `--muted` 13.3451 →
**13.1205**; `text-gray-700` on `bg-gray-50` → `--muted` 9.8728 → **9.2081**
and on `bg-gray-100` → `--muted` 9.3658 → **9.2081**;
`text-slate-700`, `text-slate-800`, `text-slate-300` and `text-gray-800` on
`bg-white` → `--card` are **unchanged to the digit** (10.3442, 14.6574, 1.4844,
14.6846), because `--card` is `oklch(1 0 0)` and `bg-white` is `#fff`.

**One kept pair does drop, and it is graphical.**
`NewOccurrenceModal:158`'s `text-gray-500` Lock glyph sits on a `bg-gray-50`
label that migrates to `--muted`: **4.6325 → 4.3206**. It is an icon, so the
applicable floor is 1.4.11's 3:1 and it still passes; but it crosses 4.5 and is
therefore named here rather than left for a reviewer to find. Its ternary
partner `text-emerald-600` moves 3.5631 → **3.3232** on the same surface, also
graphical, also still over 3. §1i forbids repairing either in place (the class
may be swapped, never added or removed), and the tree-wide repair is APRAS-90's.

### Declared sub-AA or unmeasurable, none of them introduced by this task

1. `--primary` on `--accent` / `--muted` is **3.0427** at six graphical sites
   (`DocumentCenterPage:100`, `OccurrenceBookPage:35`,
   `NewOccurrenceModal:136,140,154`, `OccurrenceDetailsView:173`). It clears
   1.4.11 by 0.043 and, for a pale tenant brand, does not clear it at all. §1k
   routes it there deliberately; this is APRAS-68 behaviour predating APRAS-77
   and this child must not be read as having introduced the number.
2. Unchanged pre-existing failures, all kept verbatim and all inside a status
   set: `text-gray-400` on `--card` **2.6023** (`OccurrenceTable:102`'s Lock
   glyph — the one `text-gray-400` in the pair that is *not* repaired, because
   set 3 keeps it), `text-emerald-600` on `--card` 3.7194 and on `bg-emerald-50`
   **3.5279**, `text-amber-700` on `bg-amber-50` 4.8611, `text-emerald-700` on
   `bg-emerald-50` 5.1582, `text-emerald-800` 7.2679 and `text-emerald-900`
   9.1968 on the same.
3. **No APRAS-90 site exists in these two directories.** APRAS-90 owns brand
   text carrying an opacity modifier over a brand tint; this child produces no
   `text-primary-text/N` and no `text-primary/N` anywhere. The five opacity
   modifiers it does carry over (`/70` ×3, `/80` ×2) and the eight it creates
   (`/90` ×8) are all border or background utilities.

### The consequence the table forces and §1i forbids repairing

Nine call sites lose an interaction distinction, because both members of a
`resting`/`hover` pair map to the same token:

- `text-slate-400 hover:text-slate-600` → `text-muted-foreground
  hover:text-muted-foreground` at `DocumentUploadModal:134`,
  `FolderFormModal:116`, `FolderTreeSidebar:60`, `PDFViewerModal:66`;
- `text-gray-400 hover:text-gray-600` → the same, at `NewOccurrenceModal:64`
  and `OccurrenceDetailsView:87`;
- `text-indigo-600 hover:text-indigo-700` → `text-primary-text
  hover:text-primary-text` at `FolderTreeSidebar:174`;
- `text-indigo-600 hover:text-indigo-800` and `bg-indigo-50
  hover:bg-indigo-100` → `text-primary-text hover:text-primary-text` and
  `bg-accent hover:bg-accent` at `OccurrenceTable:134`.

§1i forbids deleting the now-redundant class — that is a markup change, not a
colour change — so each substitution is made in place and the redundancy is
left. It is a published consequence of §1d's and §1e's rows, not a defect of
this child, and it is the natural companion follow-up to APRAS-90.

## The guard suite — what changes

Re-read against the file as it stands at `a8fc8ab`:

1. `MIGRATED_DIRECTORIES` gains **two** entries —
   `"src/features/document-management/components"` and
   `"src/features/occurrence-management/components"`. APRAS-78's comment says
   each sibling appends exactly one; this child's operator-given scope is two
   directories, so it appends two and says so in the comment.
2. `describe("MIGRATED_DIRECTORIES")`'s two tests each gain **two**
   assertions, in the shape already there
   (`…/document-management/components/DocumentGridTable.tsx` and
   `…/occurrence-management/components/OccurrenceTable.tsx` for the
   pinned-files test).
3. A new **appended, directory-scoped** `describe("APRAS-82's ledger
   arithmetic")`, in the shape APRAS-79, APRAS-80 and APRAS-81 established: the
   11 pinned files split 6 / 5 by directory, the 129 ledger rows, the 77
   exception pairs, the five gap-code counts, and the ten status sets still
   whole. **No child's existing block is edited**; APRAS-78's, APRAS-79's,
   APRAS-80's and APRAS-81's must still pass untouched.
4. **Performance.** Measured now at `a8fc8ab`: the suite runs **50 tests in
   941 ms**, `pinnedFiles()` returns **26** files
   (`src/components/ui` 9, `lot-management/components` 9,
   `visitor-management/components` 8), the exceptions file holds **254**
   entries (APRAS-78 22 + APRAS-79 148 + APRAS-80 84), and
   `it("fails when any single exception is removed")` alone takes **890 ms**,
   i.e. 254 × 26 = 6,604 scans at 0.1348 ms each. After APRAS-81 (200
   exceptions, 14 files) and this child (77 exceptions, 11 files) that test
   runs 531 × 51 = **27,081** scans, ≈**3.6 s**, well over the 2 s trigger
   APRAS-80 named. APRAS-81 is the child assigned the module-scope memo hoist;
   if it has landed, this child verifies the hoist still holds with the larger
   input and changes nothing, and if it has not, this child performs it —
   keyed on `file + "\0" + source`, a pure function of its arguments so the
   mutated-argument tests keep biting, with no assertion changed either way.
   The decidable requirement is that **every individual test in the file
   finishes under 2 s**.

## Files touched

- The six `frontend/src/features/document-management/components/*.tsx` and the
  five `frontend/src/features/occurrence-management/components/*.tsx`, per the
  `migrated / deleted / logged` table.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — the two directory
  entries, four assertions, the module-scope memo hoist if not already present,
  and the new scoped `describe`.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — **77** new
  entries, `src/`-relative, `task` `APRAS-82`.
- `docs/frontend/unmapped-colours.md` — **129** appended rows, one per kept
  occurrence, sorted by file then line, plus a closing `APRAS-82 total`
  paragraph in the shape APRAS-78/79/80/81 use. Nothing already in the file is
  rewritten.
- `frontend/src/features/__tests__/documentOccurrenceContrast.test.ts` — new.
- `frontend/src/components/__tests__/TenantBrandReach.test.tsx` — extended with
  one migrated component from each directory: `PDFViewerModal` and
  `OccurrenceTable`, both props-only so neither needs a query client, each
  asserted against the tenant token and never against a colour literal.

## Test criteria

1. `npx vitest run src/__tests__/themeTokenMigration.test.ts` green with both
   directories pinned: zero unexcused grammar matches across the 11 files, no
   stale exception, no unknown code, ledger parity in both directions, the
   preceding children's blocks untouched, and this block's 129.
2. The new contrast test asserts, by **importing** `contrastRatio`,
   `parseOklch` and `hexToOklch` from `src/lib/contrast.ts`, that every
   foreground/background pair this task changes either holds ≥
   `MINIMUM_CONTRAST_RATIO` or appears in an explicit in-file list of declared
   sub-AA / graphical pairs carrying its measured before/after ratio. Ratios to
   ±0.001 against the tables above, each against its declared background. Token
   values from `src/index.css`, palette values from
   `node_modules/tailwindcss/theme.css`; no colour literal hard-coded.
   Graphical pairs are asserted against the 3:1 floor, text pairs against 4.5.
3. The four existing suites under the two `__tests__/` directories — 28 tests —
   pass **unmodified**. None asserts on a class name, so none proves a colour.
4. `npx tsc -b` clean.
5. `npx vitest run --coverage` meets exactly **80 lines / 78 functions / 76
   branches / 80 statements**.
6. `npx eslint` diff-scoped. Re-measured now: the repository carries **375
   errors + 2 warnings across 64 files**, and **the 11 touched files carry 6
   errors + 1 warning across 3 files** (`DocumentCenterPage.tsx` 2 errors,
   `DocumentUploadModal.tsx` 2 errors + 1 warning, `FolderFormModal.tsx` 2
   errors; `occurrence-management` contributes zero).
7. `git diff --exit-code frontend/src/index.css` succeeds;
   `docs/frontend/theme-token-mapping.md` is byte-unchanged; no backend file,
   no Alembic revision, no route-registry entry in the diff; the `.dark` block
   stays unapplied.

## What this proves, and what it misses

**Proved.** Every substitution is a §1b–1e row, and `themeTokenCompile.test.ts`
already asserts each row's ΔL/ΔE from the compiled stylesheet to ±0.1. The
guard certifies nothing was dropped or silently substituted: each of the 447 is
either gone from the file or present in **both** the ledger and the exceptions
file. The contrast test certifies the pairs that change.

**Not proved, stated plainly.**

- No Playwright, no Storybook, no Chromatic, no Percy, and jsdom does not run
  the Tailwind pipeline: **no pixel and no computed-style proof**. Compiling
  Tailwind over a fixture proves the table is truthful and that no unlisted
  substitution slipped in; it does **not** prove the right row was chosen at
  the right call site.
- **The three §1f cases and every §1k verdict are invisible to every test
  here.** `bg-card` vs `bg-background`, and `bg-muted` vs `bg-accent`, are
  byte-identical in `:root`; `text-primary` vs `text-primary-text` on an icon
  is two legal classes. A **review duty on this diff**, and the three sites to
  start from are the `bg-slate-950/70` scrims, `DocumentGridTable:143` versus
  `PDFViewerModal:58`, and the two grays kept by sets 3 and 4.
- The rendering *does* move where the table says it moves: 18 `text-*-400`
  sites darken by ~17 L points, the indigo hue shift at 73 sites (plus 22
  deleted `dark:` indigo siblings), `text-*-600` lightening at 9 sites, the
  eight primary buttons going dark-on-emerald, the one emerald download button
  becoming brand, and the nine hover-distinction losses named above.
- The **78 deleted `dark:` siblings** change nothing today, because `.dark` is
  never applied. What changes is what the future dark-mode task inherits,
  alongside the 22 `dark:` classes kept — **all 100 of them live in
  `document-management`**, which is the only directory in this pair that has
  any — plus the three `bg-foreground/70` scrims named above.
- **The guard cannot enforce per-site completeness**, because the exceptions
  file carries no line number. `OccurrenceTable.tsx` is the worst case:
  `bg-gray-50`, `text-gray-700`, `text-gray-400`, `bg-gray-100` and
  `border-gray-200` are each migrated at one site and kept at another in that
  one file, and once excused an unmigrated occurrence anywhere in it passes.
  `NewOccurrenceModal.tsx` has the same shape for `text-gray-500`. The
  disposition table (240 / 78 / 129 with the per-file split), the ten-set
  inventory and the §1k site table are what a reviewer must check the diff
  against.

## Out of scope

Adding `--success` / `--warning` / `--info` tokens; migrating any `rose`,
`amber`, `blue`, `orange` or `sky` occurrence; APRAS-90's sub-AA repair tree;
deleting the now-redundant `hover:` classes; the 1.4.11 graphical floor for
pale tenant brands; enabling the `.dark` block; visual-regression
infrastructure; any other feature directory; and any amendment to APRAS-78's
mapping table, ledger rules or grammar.

## Expected Results

- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts` passes with `MIGRATED_DIRECTORIES` containing both `"src/features/document-management/components"` and `"src/features/occurrence-management/components"`, `pinnedFiles()` returning those directories' 6 and 5 source files respectively, and `violations(PINNED, EXCEPTIONS, LEDGER)` returning `[]`.
- [ ] Re-measuring the eleven files `frontend/src/features/{document-management,occurrence-management}/components/*.tsx` with the guard's §3b grammar accounts for all 447 baseline occurrences as 240 migrated + 78 deleted `dark:` siblings + 129 left and logged, with both halves closing independently (347 non-`dark:` = 240 + 107; 100 `dark:` = 78 + 22); after the change the eleven files together retain exactly 129 grammar matches and zero six-digit hex literals, `document-management` retaining 44 of them and `occurrence-management` 85.
- [ ] `docs/frontend/unmapped-colours.md` gains 129 rows whose `task` cell is `APRAS-82` — 69 `GAP-OUT-OF-BUDGET`, 30 `GAP-TINT`, 24 `GAP-NO-TOKEN`, 3 `GAP-OVERLAY`, 3 `GAP-BORDER-100`, and zero `GAP-SWATCH`, zero `GAP-NO-SURFACE`, zero `GAP-UNLISTED` — and `frontend/src/__tests__/themeTokenMigration.exceptions.json` gains exactly 77 entries whose `task` is `APRAS-82` (22 naming a `document-management` file, 55 an `occurrence-management` file), with the guard's ledger-parity check passing in both directions.
- [ ] Exactly twelve brand-text occurrences carry `text-primary-text` or `hover:text-primary-text`, at exactly these sites and no others: `FolderTreeSidebar.tsx` ×4 (the two selected tree rows, was `text-indigo-700`, and the "Criar" button's `text-indigo-600` plus its `hover:text-indigo-700`), `OccurrenceTable.tsx` ×3 (the protocol cell's `text-indigo-600`, and the details button's `text-indigo-600` plus its `hover:text-indigo-800`), `OccurrenceDetailsView.tsx` ×4 (the protocol chip, the evidence link, and the two `<Link>`s), `OccurrenceTimelineLog.tsx` ×1 (the status-transition line, was `text-indigo-700`); and no `-primary-text` appears on any non-`text-` utility anywhere in the diff.
- [ ] Twenty-two `text-`-prefixed brand occurrences carry `text-primary` or `hover:text-primary` because the element carrying them paints no glyphs — in `DocumentCenterPage.tsx` ×2, `DocumentGridTable.tsx` ×3, `DocumentUploadModal.tsx` ×1, `FolderFormModal.tsx` ×2, `FolderTreeSidebar.tsx` ×4, `PDFViewerModal.tsx` ×1, `NewOccurrenceModal.tsx` ×4, `OccurrenceBookPage.tsx` ×2, `OccurrenceTimelineLog.tsx` ×2, `OccurrenceDetailsView.tsx` ×1 — and no `indigo` class of any prefix remains anywhere in the eleven files **outside `OccurrenceTable.tsx`'s `getStatusBadgeClass`**, where exactly `bg-indigo-50`, `text-indigo-700` and `border-indigo-200` remain, on its `IN_PROGRESS` branch, kept whole by the status-set unit rule (the three indigo occurrences of the 76 that do not migrate; 73 do).
- [ ] `frontend/src/features/__tests__/documentOccurrenceContrast.test.ts` passes, importing `contrastRatio`, `parseOklch` and `hexToOklch` from `src/lib/contrast.ts` and reading every colour from `src/index.css` and `node_modules/tailwindcss/theme.css` with no hard-coded colour literal, asserting to ±0.001 that `--primary-text` on `--card` is 5.2096 and on `--accent` and `--muted` 4.6547, `--muted-foreground` on `--card` 5.2249 and on `--muted` 4.6684, `--foreground` on `--card` 19.8801, `--primary-foreground` on `--primary` 5.7588, and — against the 3:1 graphical floor — `--primary` on `--card` 3.4054 and on `--accent`/`--muted` 3.0427.
- [ ] The same test declares, in an explicit in-file list with before/after ratios, every pair this task leaves or puts below 4.5:1: the graphical `--primary` on `--accent`/`--muted` at 3.0427 (six sites), `NewOccurrenceModal.tsx:158`'s kept `text-gray-500` moving 4.6325 → 4.3206 and its kept `text-emerald-600` moving 3.5631 → 3.3232 as their `bg-gray-50` label becomes `bg-muted`, `OccurrenceTable.tsx:102`'s kept `text-gray-400` unchanged at 2.6023, and the kept emerald and amber status pairs `text-emerald-600` on `bg-emerald-50` 3.5279, `text-emerald-700` 5.1582, `text-emerald-800` 7.2679, `text-emerald-900` 9.1968 and `text-amber-700` on `bg-amber-50` 4.8611.
- [ ] The same test asserts that every kept **text** foreground sitting on a migrated background still clears 4.5:1: `text-gray-800` on `--muted` 13.1205 (from 14.0676 on `bg-gray-50` and 13.3451 on `bg-gray-100`), `text-gray-700` on `--muted` 9.2081 (from 9.8728 on `bg-gray-50` and 9.3658 on `bg-gray-100`), and `text-slate-700` 10.3442, `text-slate-800` 14.6574 and `text-gray-800` 14.6846 unchanged on `--card`.
- [ ] Grouping every grammar match in the eleven files by `(file, class-context span)` yields exactly **one** span holding both a migrated occurrence and a kept `GAP-TINT` occurrence — `DocumentGridTable.tsx:143`, where the migrating `text-slate-500` sits beside the kept `hover:text-emerald-600 hover:bg-emerald-50` pair and its two `dark:` siblings — and no other.
- [ ] All six branches of `OccurrenceTable.tsx`'s `getStatusBadgeClass` and all four of its `getPriorityBadgeClass` retain their original class strings verbatim, including the `bg-indigo-50 text-indigo-700 border-indigo-200` and `bg-emerald-50 text-emerald-700 border-emerald-200` branches, and each of their 26 classes has a ledger row; likewise `OccurrenceDetailsView.tsx:71,76`'s visibility badge ternary (6 classes), its `:160–165` resolution panel (5), `OccurrenceTimelineLog.tsx:67`'s internal-note badge (3), and `OccurrenceTable.tsx:100,102` and `NewOccurrenceModal.tsx:158`'s visibility glyph ternaries (2 each).
- [ ] `PDFViewerModal.tsx` contains no `emerald` class at all — its download button reads `bg-primary hover:bg-primary/90 text-primary-foreground` — while `DocumentGridTable.tsx:143` still reads `hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 dark:hover:text-emerald-400` unchanged, and `text-destructive` appears nowhere in the eleven files, because neither directory contains a single `red-*` class.
- [ ] Every opacity modifier present in the baseline is carried over unchanged on migrated classes: `bg-slate-950/70` → `bg-foreground/70` (×3, in `PDFViewerModal.tsx`, `DocumentUploadModal.tsx` and `FolderFormModal.tsx`), `hover:bg-slate-50/80` → `hover:bg-accent/80` (×1, `DocumentGridTable.tsx`), `hover:bg-gray-50/80` → `hover:bg-accent/80` (×1, `OccurrenceTable.tsx`), `hover:bg-indigo-700` → `hover:bg-primary/90` (×7) and `hover:bg-emerald-700` → `hover:bg-primary/90` (×1); the three `bg-black/40` scrims are unchanged and logged under `GAP-OVERLAY`; and the diff contains no `text-primary/N` and no `text-primary-text/N` anywhere.
- [ ] No `dark:` sibling of a migrated base survives in the six `document-management` files: zero `dark:bg-slate-900`, `dark:bg-slate-950`, `dark:bg-slate-800`, `dark:bg-slate-800/50`, `dark:bg-slate-800/40`, `dark:border-slate-800`, `dark:border-slate-700`, `dark:divide-slate-800`, `dark:text-white`, `dark:text-slate-400`, `dark:text-indigo-400`, `dark:bg-indigo-950/50`, `dark:bg-indigo-950/60`, `dark:hover:bg-slate-800`, `dark:hover:text-slate-200`, `dark:hover:bg-indigo-950/50` or `dark:hover:text-indigo-400` remains, and none appears in the ledger; exactly 22 `dark:` classes remain in those six files, all of them ledger-logged; the five `occurrence-management` files contain zero `dark:` occurrences before and after.
- [ ] `describe("the pilot's own ledger arithmetic")` and the equivalent blocks for APRAS-79, APRAS-80 and APRAS-81 still pass with their assertions unedited, and no APRAS-78, APRAS-79, APRAS-80 or APRAS-81 ledger row or exceptions entry is modified.
- [ ] `frontend/src/components/__tests__/TenantBrandReach.test.tsx` passes with two added cases that mount `PDFViewerModal` (with `isOpen` and a document) and `OccurrenceTable` (with one occurrence and `isLoading={false}`) under the mocked `useTenantProfile`, assert `getComputedStyle(document.documentElement).getPropertyValue("--primary")` equals the mocked theme's value, and and assert, **per component**, over the **whitespace-split class tokens** of the rendered markup (every `class` value split on `/\s+/`, so `bg-accent`, `hover:bg-accent` and `hover:bg-accent/80` are three distinct tokens and none matches another; no substring matching anywhere in this test), that the token set contains exactly what that component produces — `PDFViewerModal`: contains `bg-primary`, `hover:bg-primary/90`, `text-primary-foreground`, `text-primary`, `bg-card`, `bg-muted`, `bg-foreground/70` and `hover:bg-accent`, and contains neither the token `bg-accent` nor any `text-primary-text` token; `OccurrenceTable`: contains `text-primary-text`, `hover:text-primary-text`, `bg-accent`, `hover:bg-accent`, `hover:bg-accent/80`, `bg-card`, `bg-muted` and `border-border`, and contains none of the tokens `bg-primary`, `hover:bg-primary/90`, `text-primary-foreground` or `text-primary` — never a colour literal.
- [ ] `git diff --exit-code frontend/src/index.css` and `git diff --exit-code docs/frontend/theme-token-mapping.md` both succeed, and — after the developer has staged its own paths with `git add` — `git diff --name-only --cached` contains no backend file, no Alembic revision, no route-registry change, no file under `frontend/src/components/ui/`, `frontend/src/features/lot-management/`, `frontend/src/features/visitor-management/`, `frontend/src/features/project-management/` or `frontend/src/features/asset-management/`, and no path outside this set of seventeen: the eleven `.tsx` under the two component directories, `frontend/src/__tests__/themeTokenMigration.test.ts`, `frontend/src/__tests__/themeTokenMigration.exceptions.json`, `frontend/src/components/__tests__/TenantBrandReach.test.tsx`, `frontend/src/features/__tests__/documentOccurrenceContrast.test.ts`, `docs/frontend/unmapped-colours.md` and `docs/tasks/APRAS-82-spec.md`.
- [ ] `npx tsc -b` completes with no error.
- [ ] `npx vitest run --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint` over the eleven touched component files reports at most the 6 errors and 1 warning across 3 files present today (`DocumentCenterPage.tsx` 2 errors, `DocumentUploadModal.tsx` 2 errors + 1 warning, `FolderFormModal.tsx` 2 errors, and zero in all five `occurrence-management` files), and the repository total stays at 375 errors + 2 warnings across 64 files.
- [ ] The four existing suites in `frontend/src/features/document-management/__tests__/` and `frontend/src/features/occurrence-management/__tests__/` — 28 tests in total — pass without modification.
- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts --reporter=verbose` reports every individual test finishing under 2 s, including `it("fails when any single exception is removed")`, which at `a8fc8ab` measures 890 ms against 254 exceptions and 26 pinned files and runs against 77 more exceptions and 11 more pinned files after this task; the scan memo inside `violations()` is at module scope, keyed on the file path and its source text.
