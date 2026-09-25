# APRAS-84 — Migrate media, feedback, announcements and packages to semantic theme tokens

Child 7 of 8 of the APRAS-77 split, specified against the **amended** contract:
APRAS-78's three artefacts as extended by APRAS-79 / APRAS-80 and amended by
APRAS-88 at `c7c42fc`. Re-measured at **`2c58a76`**, the commit this task
branches from, after APRAS-90 (`a51b0f1`) and APRAS-75 (`2c58a76`) landed.

**This child carries one operator-authorised decision, expressed as two table
amendments, and nothing else.** Every call below is an *application* of a
published rule to a named call site, with a single exception the operator
decided personally: on the zoom slider the **track carries the tenant's brand
and the thumb carries the token the theme guarantees is legible on it**. That
decision retargets two cells — the one `bg-slate-300` row in §1b from
`bg-muted` to `bg-primary`, and `accent-indigo-600` out of §1e's shared
`*-primary` row into its own row targeting `accent-primary-foreground`. Both
are table amendments, not call-site judgements, and §7 below states exactly
what changes and why the table's own text leaves no other reading. Precedent:
APRAS-85 widening §3b and APRAS-81 extending §1f case 1, both authorised the
same way. No new gap code, no new token in `frontend/src/index.css`, no other
row touched.

Four directories, because the operator scoped this child that way. They share
one property that makes them a coherent unit and that no earlier child had:
**not one of the 351 occurrences carries a `dark:` variant**. §1g therefore
never fires — zero deletions, zero orphan siblings, zero `dark:` rows in the
ledger — and the whole of this child's risk sits in §1f, §1j and §1k. What the
four *do* exercise, which `purchase-management` did not, is the full white /
black surface spectrum: `bg-white` at four opacities, `bg-black` at four, and
the only `text-white` sites in the split that sit on a rowless surface.

## Scope

`frontend/src/features/media-management/components` (five files),
`frontend/src/features/feedback-management/components` (five),
`frontend/src/features/announcement-feed/components` (five) and
`frontend/src/features/package-management/components` (one) — **sixteen** files
— migrated from hard-coded Tailwind palette classes to the tokens the table
names, with every class left behind logged in the ledger and excepted in the
guard; then the four directory paths appended to `MIGRATED_DIRECTORIES`.

Not covered: `media-management/hooks/`, `feedback-management/hooks/`,
`announcement-feed/hooks/`, `package-management/hooks/` or any `__tests__/`
(none of the four hook files — `useMediaAssets.ts`, `useFeedback.ts`,
`useAnnouncements.ts`, `usePackages.ts` — contains a palette class, verified,
and the guard's non-recursive directory walk does not reach them), any other
feature directory, `index.css`, the backend, the `.dark` block, and any
amendment to the mapping table, the ledger's rules or the guard's grammar.

**Mockup: `docs/tasks/APRAS-84-mock.html`.** Most of this child is a token
substitution whose pairs are byte-identical in `:root` or already tabulated.
The slider track is not: a grey bar becoming the condominium's brand colour is
something a resident sees, so the mock reproduces `AvatarCropEditor`'s panel at
true size under four candidate treatments and six themes — the product default,
whose `--primary` and `--muted` are written by hand in
`frontend/src/index.css`, plus the five tenant brands `build_theme` derives —
with every ratio measured through `frontend/src/lib/contrast.ts`. The other visible
changes are enumerated under *What this proves, and what it misses*.

## The re-measurement

Measured now, at `2c58a76`, over the sixteen non-test `.tsx` files with the §3b
grammar exactly as the guard builds it (scale alternatives longest-first, both
word boundaries, opacity suffix). **Nothing here is carried over from a
sibling.**

| Figure | Value |
| --- | --- |
| Palette occurrences | **351** — the task's reported figure reproduces exactly |
| Files | **16**, not the reported 17. The fourth directory, `package-management`, holds **one** component, not two; its second non-test file is `hooks/usePackages.ts`, which the walk does not reach and which carries zero palette classes. The occurrence count is unaffected. |
| Distinct classes | **81** |
| Six-digit hex literals anywhere in the 16 files | **0** |
| `dark:`-prefixed | **0** — all 351 are non-`dark:` |
| `media-management/components` | 5 files, **140** occurrences |
| `feedback-management/components` | 5 files, **113** |
| `announcement-feed/components` | 5 files, **74** |
| `package-management/components` | 1 file, **24** |
| Per file | PhotoApprovalQueuePage 46, PhotoUploadModal 40, WebcamCaptureDialog 30, FeedbackInboxTable 30, FeedbackDetailsView 27, PackageStatusPage 24, AnnouncementFormModal 23, FeedbackHistoryList 21, AvatarCropEditor 19, NewFeedbackForm 18, FeedbackChannelPage 17, AnnouncementCard 13, AnnouncementFeedPage 13, MediaCarousel 13, CommentThread 12, AvatarWithFallback 5 |

**The `dark:` rule is not exercised by this child at all.** §1g's two halves
both have zero instances here. An implementer who finds one has mis-measured.

## The disposition of all 351

| Disposition | n |
| --- | --- |
| Light class migrated to a token | **242** |
| `dark:` sibling of a migrated class, deleted (§1g) | **0** |
| Left untouched and logged | **109** |
| **Total** | **351** |

Per file, as `migrated / logged`:

| File | m / l |
| --- | --- |
| `AvatarCropEditor.tsx` | 16 / 3 |
| `AvatarWithFallback.tsx` | 2 / 3 |
| `PhotoApprovalQueuePage.tsx` | 26 / 20 |
| `PhotoUploadModal.tsx` | 30 / 10 |
| `WebcamCaptureDialog.tsx` | 17 / 13 |
| `FeedbackChannelPage.tsx` | 14 / 3 |
| `FeedbackDetailsView.tsx` | 15 / 12 |
| `FeedbackHistoryList.tsx` | 10 / 11 |
| `FeedbackInboxTable.tsx` | 18 / 12 |
| `NewFeedbackForm.tsx` | 13 / 5 |
| `AnnouncementCard.tsx` | 11 / 2 |
| `AnnouncementFeedPage.tsx` | 13 / 0 |
| `AnnouncementFormModal.tsx` | 16 / 7 |
| `CommentThread.tsx` | 9 / 3 |
| `MediaCarousel.tsx` | 10 / 3 |
| `PackageStatusPage.tsx` | 22 / 2 |

Per directory: `media-management` 91 / 49 = 140; `feedback-management`
70 / 43 = 113; `announcement-feed` 59 / 15 = 74; `package-management`
22 / 2 = 24. `AnnouncementFeedPage.tsx` is the one file that migrates
completely, with no ledger row.

The 109 occupy **80** distinct `(file, class)` pairs — 36 in
`media-management`, 33 in `feedback-management`, 9 in `announcement-feed`, 2 in
`package-management` — which is the number of exceptions entries this task
appends.

## The gap codes, each counted from its own membership

| Code | Occ. | Derivation, enumerated |
| --- | --- | --- |
| `GAP-OUT-OF-BUDGET` | **47** | `text-gray-800` 17 (all), `text-gray-700` 13 (of 14; the fourteenth is in status set 1 and is coded `GAP-TINT` by precedence), `text-slate-700` 12 (all), `text-slate-800` 4 (all), `border-slate-800` 1 (all — `WebcamCaptureDialog:126`, the tree's only occurrence of that class). `17 + 13 + 12 + 4 + 1 = 47` |
| `GAP-TINT` | **28** | `bg-red-50` 4, `text-red-700` 4, `border-red-200` 4, `hover:bg-red-100` 1, `bg-emerald-50` 3, `border-emerald-200` 3, `text-emerald-700` 2, `text-emerald-600` 2, `text-emerald-800` 1, `text-emerald-900` 1, plus the neutral branch of status set 1 — `bg-gray-50` 1, `text-gray-700` 1, `border-gray-200` 1. `13 + 12 + 3 = 28` |
| `GAP-NO-TOKEN` | **14** | every `amber` occurrence in the four directories, 13: `text-amber-700` 3, `bg-amber-50` 3, `border-amber-200` 2, and one each of `border-amber-300`, `hover:bg-amber-100`, `bg-amber-100`, `text-amber-800`, `bg-amber-500/90`. Plus `bg-rose-500` 1. `13 + 1 = 14` |
| `GAP-BORDER-100` | **9** | `border-slate-100` 5, `divide-gray-100` 2, `border-gray-100` 2. All occurrences of all three |
| `GAP-OVERLAY` | **8** | `bg-black/60` 3 (`PhotoApprovalQueuePage:126`, `PhotoUploadModal:76`, `WebcamCaptureDialog:101`), `bg-black/40` 3 (`FeedbackDetailsView:27`, `:45`, `AnnouncementFormModal:64`), `bg-black/80` 1 (`PhotoApprovalQueuePage:162`), `bg-black/20` 1 (`PhotoApprovalQueuePage:84`, the hover scrim over a thumbnail) |
| `GAP-NO-SURFACE` | **3** | `text-white` on `bg-amber-500/90` (`AvatarWithFallback:48`), on `bg-rose-500` (`FeedbackHistoryList:51`) and on `bg-black/20` (`PhotoApprovalQueuePage:84`) — three palette backgrounds with no row, which is §1h code 5 verbatim |

`47 + 28 + 14 + 9 + 8 + 3 = 109`. **Zero `GAP-SWATCH`, zero `GAP-UNLISTED`,
and zero `dark:` rows.** This is the **first child to use `GAP-NO-SURFACE`
outside the pilot**, and it uses it three times.

## Every status set in these directories

The triple rule is binding tree-wide: a status variant's class set migrates as
a **unit or not at all**, every member must have a row in §1b–1e, and the
resulting pair must hold ≥ 4.5:1. **A ternary's or a lookup map's branches are
one set.** There are **twelve** sets here, holding **44** of the 109 kept
occurrences.

| # | Set | Members | n | Code |
| --- | --- | --- | --- | --- |
| 1 | `FeedbackInboxTable:15,17,19` `getStatusBadgeClass`, 3 branches | amber 3, emerald 3, gray 3 (`bg-gray-50`, `text-gray-700`, `border-gray-200`) | 9 | NO-TOKEN 3 / TINT 6 |
| 2 | `FeedbackHistoryList:66,67` ANSWERED/PENDING ternary | emerald 3 \| amber 3 | 6 | TINT 3 / NO-TOKEN 3 |
| 3 | `FeedbackDetailsView:75,76,77,80` board-response panel | `bg-emerald-50`, `border-emerald-200`, `text-emerald-900`, `text-emerald-600`, `text-emerald-800` | 5 | TINT |
| 4 | `PhotoApprovalQueuePage:106` reject button | `text-red-700`, `bg-red-50`, `hover:bg-red-100`, `border-red-200` | 4 | TINT |
| 5 | `WebcamCaptureDialog:157` "Tirar Outra" button | `text-amber-700`, `bg-amber-50`, `border-amber-300`, `hover:bg-amber-100` | 4 | NO-TOKEN |
| 6 | `PhotoApprovalQueuePage:53` error alert | `bg-red-50`, `text-red-700`, `border-red-200` | 3 | TINT |
| 7 | `PhotoUploadModal:87` error alert | same three | 3 | TINT |
| 8 | `WebcamCaptureDialog:118` camera-error alert | same three | 3 | TINT |
| 9 | `PhotoApprovalQueuePage:44` pending count chip | `bg-amber-100`, `text-amber-800` | 2 | NO-TOKEN |
| 10 | `AvatarWithFallback:48` "Em Aprovação" badge | `bg-amber-500/90`, `text-white` | 2 | NO-TOKEN 1 / NO-SURFACE 1 |
| 11 | `FeedbackHistoryList:51` unread badge | `bg-rose-500`, `text-white` | 2 | NO-TOKEN 1 / NO-SURFACE 1 |
| 12 | `AnnouncementCard:53` read-receipt glyph | `text-emerald-600` | 1 | TINT |

`9+6+5+4+4+3+3+3+2+2+2+1 = 44`, of which **28** are `GAP-TINT` (matching that
code's total exactly, so every `GAP-TINT` occurrence in this child belongs to a
set), **14** `GAP-NO-TOKEN` (likewise its whole total) and **2** of the three
`GAP-NO-SURFACE`. The remaining 65 kept occurrences are the 47
`GAP-OUT-OF-BUDGET`, the 9 `GAP-BORDER-100`, the 8 `GAP-OVERLAY` and the one
free-standing `GAP-NO-SURFACE` (`PhotoApprovalQueuePage:84`). `44 + 65 = 109`.

**The rowless member of each.** Sets 1, 2, 5, 9, 10 and 11 are blocked by a
family with no token — `amber` in five of them, `rose` in the sixth. Sets 4, 6,
7 and 8 are red tint triples, which §1j makes `GAP-TINT` by name. Set 3 is
blocked by `bg-emerald-50` and `text-emerald-900`, neither of which has a §1b
row for its role. Set 12 is the operator's status ruling applied through §1f
case 3: a non-interactive status glyph.

**Four consequences worth stating once.**

1. **Set 1's neutral branch is kept because its ternary partner is a status
   colour.** `bg-gray-50`, `text-gray-700` and `border-gray-200` at
   `FeedbackInboxTable:19` are the `default` branch of a three-way status map;
   two of the three have rows and would migrate anywhere else in the same file.
   This is APRAS-82 set 3 / APRAS-83 set 3's precedent applied once, and it is
   why the ledger carries a `bg-gray-50` and a `border-gray-200` entry for
   `FeedbackInboxTable.tsx` in which those same classes also migrate. It is
   named as a **review duty**, not hidden in a count. By §1h precedence all
   three take `GAP-TINT`, including `text-gray-700`, which would otherwise be
   `GAP-OUT-OF-BUDGET`.
2. **Set 4 is a destructive *control* that nonetheless stays.** The reject
   button at `PhotoApprovalQueuePage:106` is exactly the "free-standing
   destructive control" §1j sends to `text-destructive` — except that it is not
   free-standing: its `text-red-700` shares a class string with `bg-red-50` and
   `hover:bg-red-100`, neither of which has a row, so the unit rule freezes the
   whole set. Meanwhile the *other* destructive control in the same file,
   `PhotoApprovalQueuePage:150`'s `text-white bg-red-600 hover:bg-red-700`
   confirm button, is a solid fill with every member rowed and **does** migrate.
   A reviewer should check precisely these two against each other.
3. **Red splits three ways, all under published rules.** Thirteen of the
   eighteen red occurrences stay (sets 4, 6, 7, 8); five migrate — the solid
   destructive button at `:150` (3), `MediaCarousel:41`'s `text-red-600`
   `<FileText/>` PDF glyph, and the two `hover:text-red-600` delete-icon
   buttons at `AnnouncementCard:72` and `CommentThread:62`. `MediaCarousel:41`
   is the one arguable member: it is decoration denoting a file type rather
   than an error, but §1j's list of free-standing cases names "an icon"
   explicitly, and `--destructive` is never branded, so the move is ΔE 0.60 and
   semantically inert. **Named as a review site.**
4. **Emerald splits four to twelve.** Two interactive fills migrate —
   `PhotoApprovalQueuePage:114`'s "Aprovar" button and `PackageStatusPage:93`'s
   `<Button>` — carrying their `hover:bg-emerald-700` with them, 4 occurrences
   in all. The other twelve are status tints or glyphs (sets 2, 3, 12) and
   stay.

**The proof there is no thirteenth set.** A split span is a class-context span
— as `classContexts()` in the guard computes it, not a line — holding both a
migrated occurrence and a kept `GAP-TINT` occurrence. Run mechanically over all
351 occurrences grouped by `(file, span)`, that check returns **zero** spans.
This is the first child with none; `QuoteComparisonTable`-shaped mixed spans do
not occur here. The implementer must re-run the check and get zero. (Spans that
mix a migrated occurrence with a kept occurrence under any *other* code are
expected and are not counted; `FeedbackDetailsView:49`'s category chip, where
`bg-gray-100` and `border-gray-200` migrate beside a kept
`GAP-OUT-OF-BUDGET` `text-gray-800`, is the commonest shape.)

## Behaviour — the substitutions

Every substitution is a table row applied verbatim.

- **White surfaces ×41 → the `card` family** — §1f case 1, settled below.
  `bg-white` ×34 → `bg-card`, `focus:bg-white` ×2 → `focus:bg-card`,
  `bg-white/80` ×2 → `bg-card/80`, `hover:bg-white` ×2 → `hover:bg-card`,
  `bg-white/70` ×1 → `bg-card/70`. **Zero take `bg-background`, zero take
  `bg-popover`.**
- `text-white` ×13 of 16 → **`text-primary-foreground`** ×12 and
  **`text-destructive-foreground`** ×1 (`PhotoApprovalQueuePage:150`). The
  other three are `GAP-NO-SURFACE`.
- `border-gray-200` ×14 (of 15) + `border-slate-200` ×7 → `border-border` (21).
- `border-slate-300` ×10 + `border-gray-300` ×1 → `border-input` (11).
- `text-gray-900` ×12 → `text-foreground`. There is **no** `text-slate-900` in
  these directories.
- To `text-muted-foreground` ×40: `text-gray-500` 17, `text-gray-400` 8,
  `text-slate-500` 6, `text-slate-400` 4, `text-slate-600` 3, `text-gray-600`
  2. Plus `hover:text-slate-600` ×2 and `hover:text-gray-600` ×2 →
  `hover:text-muted-foreground` (4).
- Resting neutral fills ×24 → `bg-muted`: `bg-slate-50` 9, `bg-gray-50` 7 (of
  8), `bg-gray-100` 6, and one each of `bg-slate-100` and `bg-slate-200` —
  §1f case 2, settled below.
- **`bg-slate-300` ×1 → `bg-primary`** — `AvatarCropEditor:81`'s zoom-slider
  track, the tree's only occurrence of that class, under the amendment §7
  states. It is *not* §1f case 2: case 2's candidate set is `muted` / `accent`
  and its scope is the 50/100/200 scales.
- Neutral interaction fills ×15 → `hover:bg-accent`: `hover:bg-slate-100` 6,
  `hover:bg-gray-100` 6, and one each of `hover:bg-slate-50`, `hover:bg-gray-50`
  and `hover:bg-gray-200`. Plus `hover:bg-gray-50/80` ×2 →
  **`hover:bg-accent/80`**, the opacity carried verbatim.
- `bg-slate-900` ×2 → `bg-foreground` (`AvatarCropEditor:65`'s crop stage,
  `WebcamCaptureDialog:126`'s video stage).
- **Indigo ×47, split by §1k** — see the next section: 4 → `*-primary-text`,
  43 → `primary` / `accent` / `ring` / `border`. Of the 43: `bg-indigo-600` 11
  → `bg-primary`, `hover:bg-indigo-700` 10 → `hover:bg-primary/90`,
  `focus:ring-indigo-500` 5 → `focus:ring-ring`, `bg-indigo-50` 4 →
  `bg-accent`, `hover:bg-indigo-100` 1 → `hover:bg-accent`, `border-indigo-400`
  1 and `border-indigo-500` 1 → `border-primary`, **`accent-indigo-600` 1 →
  `accent-primary-foreground`** (the zoom-slider thumb, under the second half
  of §7's amendment — *not* `accent-primary`, which is what §1e's unamended
  row would give), and the 9 graphical `text-`-prefixed sites → `text-primary`
  / `hover:text-primary`.
- Emerald ×4: `bg-emerald-600` ×2 → `bg-primary` and `hover:bg-emerald-700` ×2
  → `hover:bg-primary/90` — §1f case 3's interactive branch.
- Red ×5: `bg-red-600` → `bg-destructive`, `hover:bg-red-700` →
  `hover:bg-destructive`, `text-red-600` → `text-destructive`,
  `hover:text-red-600` ×2 → `hover:text-destructive`.

`41 + 13 + 21 + 11 + 12 + 44 + 24 + 1 + 17 + 2 + 47 + 4 + 5 = 242`, reading the
bullets in order, with **one** occurrence attributed in two places and counted
once: `hover:bg-indigo-100` appears in the indigo bullet's 47 and is *excluded*
from the neutral-interaction bullet's 15, which is why that bullet reads 15 and
not 16 while `hover:bg-accent` is produced 16 times in total.

**Opacity modifiers are carried over verbatim**, never dropped and never
rounded to a different `N`: `bg-white/80` → `bg-card/80`, `bg-white/70` →
`bg-card/70`, `hover:bg-gray-50/80` → `hover:bg-accent/80`, and
`hover:bg-indigo-700` / `hover:bg-emerald-700` → `hover:bg-primary/90`, per
§1i's named target. §1i measures such a target against the base token with the
alpha declared **unmeasured**. **No `text-primary/N` and no
`text-primary-text/N` is produced anywhere**, so this child creates no APRAS-90
site.

No `dark:` sibling is deleted, because there is none.

## §1k applied — which brand classes are characters

§1k asks one question per call site, from the JSX, with no measurement: *does
this element paint glyphs of text?* Traced at every site, not assumed.

**Characters — take `*-primary-text`, floor 4.5:1 (4 occurrences, 2 call
sites).**

| Site | Classes → targets | Why it is text | Surface | After |
| --- | --- | --- | --- | --- |
| `PhotoUploadModal:106` | `text-indigo-600` → `text-primary-text`, `hover:text-indigo-800` → `hover:text-primary-text` | a `<button>` whose only child is the string "Ajustar Recorte" | `bg-white` → `--card` | **5.2096** |
| `FeedbackInboxTable:91` | the same two | a `<button>` rendering `<Eye/>` **and** the label "Ver Detalhes" from one `currentColor` — §1k's "mixed element wins for text" | `bg-indigo-50` → `--accent` | **4.6547** |

**Graphical — keeps `*-primary`, floor 3:1 (9 `text-`-prefixed + 34 non-`text-`
indigo + 4 emerald).** The nine `text-`-prefixed graphical sites, by surface:

| Surface | Sites | `--primary` on it |
| --- | --- | --- |
| `--card` (3) | `FeedbackChannelPage:51` `<Filter/>`, `AnnouncementFormModal:68` `<Plus/>` (both self-closing icons inside a heading, §1k's named 53-site shape), `FeedbackHistoryList:72` `<Eye/>` (`text-indigo-500`) | 3.4054 |
| `--accent` (3) | `FeedbackChannelPage:31`, `AnnouncementFeedPage:36` and `PackageStatusPage:27` — three `<div className="p-3 bg-indigo-50 text-indigo-600">` tiles whose only child is an icon | **3.0427** |
| `--muted` / `--accent` (3) | `AnnouncementFormModal:112` `<Paperclip/>` inside a `bg-gray-50` label; `NewFeedbackForm:75` `<input type="checkbox" className="rounded text-indigo-600">`, an input element that paints no glyphs; `AnnouncementCard:64`'s `hover:text-indigo-600` on a `<button>` whose only child is `<Pencil/>`, hovering to `bg-accent` | **3.0427** |

The 34 non-`text-` indigo utilities are graphical always, by §1k's third
clause: the 11 + 10 primary fills, the 5 focus rings, the 5 accent tints, the 2
brand borders and `accent-indigo-600`. §1k's verdict on `accent-indigo-600` is
unchanged by §7 — an `<input type="range">` paints no glyphs, so the thumb is
graphical and its floor is 3:1. What §7 changes is *which* token a graphical
brand site may take there, and `accent-*` still never takes `*-primary-text`.
The four emerald occurrences are all
`bg-`/`hover:bg-` and likewise graphical. `4 + 9 + 34 = 47` indigo occurrences
in all.

**The zoom-slider track is graphical too, by the same third clause**: it is a
`bg-` utility on an `<input type="range">`, which paints no glyphs. Its floor
is 3:1, not 4.5:1, which is what makes 3.0427 a pass rather than a failure.
§1k's verdict is unaffected by §7's amendment: §1k picks *which* brand token a
site takes once it is going to a brand token, and neither `bg-*` nor `accent-*`
ever takes `*-primary-text`.

## The context-dependent cases, settled at the real call sites

**The verification tests cannot detect a wrong choice in any of these.** They
are a **human review duty on this diff**.

**§1f case 1 — all 41 white surfaces take the `card` family.** No white fill in
these sixteen files is a page shell: the four page roots
(`FeedbackChannelPage:29`, `AnnouncementFeedPage:33`, `PackageStatusPage:25`,
`PhotoApprovalQueuePage:35`) are bare `container`/`p-6` wrappers carrying no
background class at all, so the page surface is `App.tsx:112`'s `min-h-screen
bg-background` and nothing here competes with it. None of the 41 is a floating
layer with popover semantics, so none takes `bg-popover`.

**Five** of the 41 are **raw `<select>`/`<input>`/`<textarea>` fills** —
`FeedbackChannelPage:58` and `:70` (`focus:bg-white` on two selects),
`NewFeedbackForm:44` (a select), `FeedbackDetailsView:97` (a textarea) and
`PackageStatusPage:87` (a text input). They take the **`card`** family,
following APRAS-80's already-accepted precedent, even though `components/ui/`'s
primitives use `bg-background`; the two are byte-identical in `:root` and
diverge only under a tenant theme. The divergence is **recorded, not resolved**
here.

**The two `focus:bg-white` selects are the one genuinely new shape.** Their
resting fill is `bg-gray-50`, which §1f case 2 sends to `bg-muted`, and their
*focus* fill is white. Case 2's "interaction fills take `accent`" is scoped by
its own text to neutral fills at 50/100/200; `bg-white` is case 1, whose
candidate set is `card` / `background` / `popover` and does not contain
`accent`. So the pair migrates to `bg-muted focus:bg-card`, not to
`bg-muted focus:bg-accent`. **Named here so a reviewer decides it deliberately
rather than discovering it.**

**The three floating white surfaces in `MediaCarousel`.** `:54` and `:62` are
nav buttons reading `bg-white/80 hover:bg-white`, and `:71` is the inactive
carousel dot reading `bg-white/70`. None is a scrim or a backdrop — they are
controls and an indicator painted *on top of* media — so §1h code 1
`GAP-OVERLAY`, which is defined for `bg-black`/`bg-white` "used as a scrim or
backdrop", does not reach them and the §1b row governs. The eight `bg-black/N`
in this child *are* code 1 and stay. That `bg-white/80` migrates while
`bg-black/20` does not is a consequence of the published code's own wording,
not a defect of this child.

**§1f case 2 — `bg-muted` versus `bg-accent`.** 24 resting fills take
`bg-muted` and 15 interaction fills take `hover:bg-accent`, enumerated in the
substitutions above. The 25th resting fill, `bg-slate-300`, is outside case 2's
scale range and takes `bg-primary` under §7's amendment. Separately, the five brand tints (`bg-indigo-50` ×4,
`hover:bg-indigo-100` ×1) take `accent` under §1e's own row, not under case 2.

**`AnnouncementFormModal:127`'s cancel button** is the one site where a button's
**resting** fill is a neutral 100: `text-gray-700 bg-gray-100
hover:bg-gray-200`. Case 2 keys on *when the fill appears*, not on whether the
element is a control, so the resting half takes `bg-muted` and the hover half
`hover:bg-accent`. The two are byte-identical in `:root`. **A review duty.**

**`PackageStatusPage:93` is the only site in this child that renders a
`components/ui` primitive.** Its `<Button>` carries no `variant`, so it already
emits `buttonVariants`' `default` — `bg-primary text-primary-foreground
hover:bg-primary/90` — while its own `className` overrides that with
`bg-emerald-600 hover:bg-emerald-700 text-white`. After migration the override
becomes the same three tokens the variant already supplies, and `cn`'s
`twMerge` collapses each duplicate to one. §1i forbids *deleting* the now
redundant override — that is a markup change — so it stays. The rendered result
is unchanged either way; this is the same published-consequence shape as the
redundant `hover:` classes below.

## Contrast, re-derived by importing `frontend/src/lib/contrast.ts`

Measured by importing `contrastRatio` and `parseOklch` from
`frontend/src/lib/contrast.ts` — never reimplemented — with token values read
from `src/index.css` and palette values read from
`node_modules/tailwindcss/theme.css` (**Tailwind 4's OKLCH palette**, whose
lightness is written as a percentage and must be divided by 100 before
`parseOklch` sees it). The measurement reproduces APRAS-78's, APRAS-80's,
APRAS-83's and APRAS-88's published figures to the digit (`--primary-text` on
`--card` 5.2096 and on `--accent` 4.6547, `--muted-foreground` on `--card`
5.2249 and on `--muted` 4.6684, `--primary-foreground` on `--primary` 5.7588,
`--primary` on `--card` 3.4054, on `--background` 3.3091, on `--accent`
3.0427), which is the check that it is the same measurement.

| Pair | Background | Today | After |
| --- | --- | --- | --- |
| Headings `text-gray-900` → `text-foreground` | `--card` | 17.7467 | **19.8801** |
| Secondary text `text-gray-500` / `text-slate-500` → `text-muted-foreground` | `--card` | 4.8357 / 4.7670 | **5.2249** |
| `text-gray-600` / `text-slate-600` → `text-muted-foreground` | `--card` | 7.5608 / 7.5635 | **5.2249** |
| Table-head text `text-gray-500` on `bg-gray-50` → on `bg-muted` | `--muted` | 4.6325 | **4.6684** |
| **`text-gray-400` ×8 / `text-slate-400` ×4 → `text-muted-foreground`** | `--card` | 2.6023 / 2.6282 | **5.2249** — repairs an AA failure at 12 sites |
| Primary button `text-white` on `bg-indigo-600` → `text-primary-foreground` on `bg-primary` | `--primary` | 6.4414 | **5.7588** |
| **Approve buttons `text-white` on `bg-emerald-600` → `text-primary-foreground` on `bg-primary`** | `--primary` | 3.7194 | **5.7588** — repairs an AA failure at 2 sites |
| Confirm-reject button `text-white` on `bg-red-600` → `text-destructive-foreground` on `bg-destructive` | `--destructive` | 4.8619 | **4.5381** |
| **Crop-adjust link `text-indigo-600` → `text-primary-text`** | `--card` | 6.4414 | **5.2096** |
| **"Ver Detalhes" control `text-indigo-600` → `text-primary-text`** | `--accent` | 5.7621 | **4.6547** |
| Brand icons `text-indigo-600` / `text-indigo-500` → `text-primary` (graphical, floor 3) | `--card` | 6.4414 / 4.5587 | **3.4054** |
| Tile and inline brand glyphs → `text-primary` (graphical) | `--accent` / `--muted` | 5.7621 | **3.0427** |
| **Zoom-slider track `bg-slate-300` → `bg-primary`** (graphical) | `bg-slate-50` → `--muted` | 1.4181 | **3.0427** — repairs a 1.4.11 failure, by 0.0427 |
| **Zoom-slider thumb `accent-indigo-600` → `accent-primary-foreground`, measured against its own track** (graphical) | `bg-slate-300` → `--primary` | 4.3394 | **5.7588** — improves, and is guaranteed in both palette modes (§7) |
| Zoom-slider thumb against the **panel** either side of the 4 px track | `bg-slate-50` → `--muted` | 6.1536 | **17.5222** in the default theme; see §7 for the three brands where it is ≈1.06 |
| PDF glyph `text-red-600` → `text-destructive` (graphical) | `--card` | 4.8619 | **4.8073** |
| Delete-control glyphs `hover:text-red-600` → `hover:text-destructive` (graphical) ×2 | `--card` / `--muted` | 4.8619 | **4.8073** / **4.2953** |

**No full-opacity text pair this task produces falls below 4.5:1.** The
tightest is `--destructive-foreground` on `--destructive` at **4.5381**, then
`--primary-text` on `--accent` at 4.6547 and `--muted-foreground` on `--muted`
at 4.6684.

### Kept pairs whose *surface* moves, measured so nobody attributes them later

A kept foreground can sit on a migrated background. Every such **text** pair
stays far above AA, so **this migration converts no passing text pair into a
failing one**:

| Kept foreground | from | to | |
| --- | --- | --- | --- |
| `text-gray-800` | `bg-gray-50` 14.0676 / `bg-gray-100` 13.3451 / `bg-slate-50` 14.0283 | `--muted` | **13.1205** |
| `text-gray-700` | `bg-gray-100` 9.3658 (`PackageStatusPage:73`) | `--muted` | **9.2081** |
| `text-slate-700` | `bg-slate-200` 8.3972 (`AvatarWithFallback:36`) | `--muted` | **9.2424** (improves) |
| `text-gray-800`, `text-gray-700`, `text-slate-700`, `text-slate-800` | `bg-white` | `--card` | **unchanged to the digit**: 14.6846, 10.3058, 10.3442, 14.6574 |

`--card` is `oklch(1 0 0)` and `bg-white` is `#fff`, which is why the last row
does not move at all.

### Declared sub-AA, unmeasurable or worsened — and which are this task's

1. `--primary` on `--accent` / `--muted` is **3.0427** at six graphical sites
   and on `--card` **3.4054** at three more. Those clear 1.4.11 by 0.043 and
   0.405 and, for a pale tenant brand, do not clear it at all. §1k routes them
   there deliberately; this is APRAS-68 behaviour predating APRAS-77 and this
   child must not be read as having introduced the numbers.
2. `--destructive` on `--muted` is **4.2953** at `CommentThread:62`'s
   `<Trash2/>` hover glyph. Graphical, above 3. APRAS-88 §7 already records
   this pair as a named follow-up.
3. **The zoom slider repairs a 1.4.11 failure and creates none.** The track
   goes 1.4181 → **3.0427**, clearing the graphical floor for the first time;
   the thumb, which `accent-color` paints, goes 4.3394 → **5.7588** against
   that track. The earlier draft of this spec left the thumb on
   `accent-primary` under §1e's unamended row, which put it at **1.0000** on
   its own track; the operator rejected that and chose the swap §7 states. Both
   halves are graphical, so 3:1 is the floor in both, and both now clear it.
   The residual risk is the track's per-tenant one, at item 4 — not the thumb,
   whose pair is inside `MEASURED_PAIRS` and is held above 4.5:1 in both
   palette modes, by the two distinct mechanisms item 4 and §7 name.
4. **`--primary` is re-derived per tenant, so 3.0427 is not a guarantee.**
   3.0427 is the *default* theme's figure — `--primary` on `--muted` exactly as
   `frontend/src/index.css` writes them at lines 39 and 55, the shipped theme
   and not a `build_theme` output — and clears 3:1 by 0.0427. Measured through
   `build_theme` for five condominium brands a síndico could type, the track
   reads **3.3246** (`#059669`), **4.2451** (`#dc2626`), **4.5361**
   (`#2563eb`) and **4.9895** (`#7c3aed`) — four of the five pass, and a dark
   brand passes comfortably. The fifth, a **pale** brand, does not: `#facc15`
   yields
   **1.3661**, which is *worse than the 1.4181 the track has today*. The
   consequence is stated rather than guarded: no test in this repository can
   enumerate the brands tenants will type, `--border`, `--input` and `--ring`
   are outside `MEASURED_PAIRS` by APRAS-68's own decision, and adding a
   graphical floor to `build_theme`'s refusal contract would start rejecting
   palettes that are stored and working today. The pale-brand case is recorded
   in the new contrast test as a named, expected failure with its measured
   figure, and the tree-wide 1.4.11 repair stays APRAS-90's. The **thumb**
   carries no equivalent risk, for two different reasons in the two palette
   modes. `("primary-foreground", "primary")` is `MEASURED_PAIRS[2]`, so an
   **advanced** palette whose thumb would read below 4.5:1 on its own track is
   refused with 422 by `TenantService.validated_brand_theme`
   (`backend/app/services/tenant_service.py:646–657`), the only non-test caller
   of `audit_contrast`; `build_theme` itself never raises. A **simple** palette
   is never measured — that same function returns before building anything
   whose mode is not `ADVANCED_MODE` — because it cannot fail: both sides of
   this pair are emitted by `derive_brand_surface`, whose `_pick_foreground` +
   `_repair_surface` walk moves the surface in 0.01 lightness steps until the
   pair clears 4.5:1, and that loop's convergence over every emittable brand is
   swept by `test_the_brand_surface_lattice_never_fails_and_never_leaves_the_gamut`
   in `backend/tests/test_branding.py` (§7 states what the loop's `_MAX_STEPS`
   bound would do if it were ever reached: return the failing colour silently,
   with no 422). Either way the thumb is the one part of this control the
   platform holds above AA, which is precisely why §7 moves the colour-carrying
   role onto it.
5. `AvatarWithFallback:36`'s avatar fallback fill gets worse and stays:
   `bg-slate-200` on `bg-white` **1.2319** → `--muted` on `--card` **1.1192**,
   failing the 3:1 graphical floor before this task as well as after. Its only
   §1b row is `bg-muted`, §1i permits swapping a class but never adding or
   removing one, and no operator decision names it, so it is migrated and
   logged. APRAS-90 owns the repair.
6. **Ruled not a `GAP-SWATCH`, deliberately.** `AvatarWithFallback:36` is an
   *avatar fill*, which §1h code 2 names by example — but code 2's head clause
   is "a data-encoding colour", and this fill is one constant neutral for every
   user, encoding nothing. It therefore migrates. The example covers
   per-identity generated avatar colours, of which this tree has none. **Named
   as a review site**, because it is the one place a reviewer could reasonably
   read the code the other way; if the operator prefers the literal reading,
   the change is three ledger rows and three exceptions and nothing else.
7. `MediaCarousel:71`'s active dot moves from `bg-indigo-600` to `bg-primary`.
   Against the carousel's own `bg-gray-100` → `--muted` container it goes
   5.8539 → **3.0427**; when media is present the dot sits over the image and
   the pair is **unmeasurable**, as it is today. Graphical either way.
8. Unchanged pre-existing failures, all kept verbatim inside a status set:
   `text-emerald-600` on `bg-emerald-50` **3.5279** (`FeedbackDetailsView:77`)
   and on `--card` **3.7194** (`AnnouncementCard:53`); `text-white` on
   `bg-rose-500` **3.7327** and on `bg-amber-500` **2.1452** — two *text* pairs
   that fail AA today, are `GAP-NO-SURFACE` / `GAP-NO-TOKEN`, and are left
   exactly as they are. Kept status pairs that pass: `text-red-700` on
   `bg-red-50` 5.9842 and on `bg-red-100` 5.3552, `text-amber-700` on
   `bg-amber-50` 4.8611, `text-amber-800` on `bg-amber-100` 6.4027,
   `text-emerald-700` on `bg-emerald-50` 5.1582, `text-emerald-800` 7.2679,
   `text-emerald-900` 9.1968, `text-gray-700` on `bg-gray-50` 9.8728.
9. **No APRAS-90 site exists in these four directories.** APRAS-90 owns brand
   text carrying an opacity modifier over a brand tint; this child produces no
   `text-primary-text/N` and no `text-primary/N` anywhere. Every opacity
   modifier it carries or creates is a background utility.

### The consequence the table forces and §1i forbids repairing

Four call sites lose an interaction distinction, because both members of a
`resting`/`hover` pair map to the same token: `text-slate-400
hover:text-slate-600` → `text-muted-foreground hover:text-muted-foreground` at
`PhotoUploadModal:80` and `WebcamCaptureDialog:110`, and `text-gray-400
hover:text-gray-600` likewise at `FeedbackDetailsView:58` and
`AnnouncementFormModal:75`. A fifth is new in shape: `PhotoApprovalQueuePage:150`'s
`bg-red-600 hover:bg-red-700` → `bg-destructive hover:bg-destructive`, because
§1e gives `bg-red-700` the plain `*-destructive` row with no `/90` target — the
`/90` targets §1i names are `primary` only.

§1i forbids deleting the now-redundant class — that is a markup change, not a
colour change — so each substitution is made in place and the redundancy is
left. It is a published consequence of §1d's and §1e's rows, not a defect of
this child, and it is the natural companion follow-up to APRAS-90.

## The guard suite — what changes

Re-read against the file as it stands at `2c58a76`, where
`MIGRATED_DIRECTORIES` holds three entries and `pinnedFiles()` returns 26 files
(9 + 9 + 8):

1. `MIGRATED_DIRECTORIES` gains **four** entries —
   `"src/features/media-management/components"`,
   `"src/features/feedback-management/components"`,
   `"src/features/announcement-feed/components"` and
   `"src/features/package-management/components"`. APRAS-78's comment says each
   sibling appends exactly one; this child's operator-given scope is four
   directories, so it appends four and says so in the comment.
2. `describe("MIGRATED_DIRECTORIES")`'s two tests each gain **four**
   assertions, in the shape already there
   (`…/media-management/components/PhotoApprovalQueuePage.tsx`,
   `…/feedback-management/components/FeedbackInboxTable.tsx`,
   `…/announcement-feed/components/MediaCarousel.tsx` and
   `…/package-management/components/PackageStatusPage.tsx` for the pinned-files
   test).
3. A new **appended, directory-scoped** `describe("APRAS-84's ledger
   arithmetic")`, in the shape APRAS-79 and APRAS-80 established: the 16 pinned
   files split 5 / 5 / 5 / 1 by directory, the 109 ledger rows, the 80
   exception pairs, the six gap-code counts, zero `dark:` rows, the twelve
   status sets still whole, and the zero split spans. **No child's existing
   block is edited**; APRAS-78's, APRAS-79's, APRAS-80's and — if they have
   landed first — APRAS-81's, APRAS-82's and APRAS-83's must still pass
   untouched.
4. `frontend/src/__tests__/themeTokenCompile.test.ts`'s `ROWS` has **two**
   entries **retargeted in place**, in the shape APRAS-88 used when it
   retargeted the nine `text-*` brand rows: `{ source: "bg-slate-300", target:
   "bg-primary", dL: 24.9, dE: 29.21 }` and — the entry the previous draft
   missed, at `themeTokenCompile.test.ts:134` — `{ source:
   "accent-indigo-600", target: "accent-primary-foreground", dL: 36.1, dE:
   45.18 }`. Appending rows instead would leave the stale `bg-slate-300 →
   bg-muted` and `accent-indigo-600 → accent-primary` rows passing (neither
   `--muted` nor `--primary` moves) and green a suite over a table
   contradicting itself. No other row is touched, and the file's tolerance
   stays ±0.1 — the ΔE figures are 29.209 and 45.179 measured, so both sit
   well inside it.
5. **Performance.** Measured now at `2c58a76`: the suite runs **50 tests in
   1.19 s**, `pinnedFiles()` returns **26** files, the exceptions file holds
   **254** entries (APRAS-78 22 + APRAS-79 148 + APRAS-80 84), and
   `it("fails when any single exception is removed")` alone takes **866 ms**,
   i.e. 254 × 26 = 6,604 scans at 0.1311 ms each. After this child (80 more
   exceptions, 16 more files) that test runs 334 × 42 = **14,028** scans,
   ≈**1.84 s** — inside the 2 s trigger APRAS-80 named, but only just, and far
   outside it if APRAS-81, APRAS-82 or APRAS-83 have landed first. The memo
   inside `violations()` is a **function-local** `Map` today
   (`themeTokenMigration.test.ts:329`), so it is rebuilt on each of the
   hundreds of mutated-argument calls. APRAS-81 is the child assigned the
   module-scope hoist; if it has landed, this child verifies the hoist still
   holds with the larger input and changes nothing, and if it has not, this
   child performs it — keyed on `file + "\0" + source`, a pure function of its
   arguments so the mutated-argument tests keep biting, with no assertion
   changed either way. The decidable requirement is that **every individual
   test in the file finishes under 2 s**.

## Files touched

- The five `frontend/src/features/media-management/components/*.tsx`, the five
  `frontend/src/features/feedback-management/components/*.tsx`, the five
  `frontend/src/features/announcement-feed/components/*.tsx` and
  `frontend/src/features/package-management/components/PackageStatusPage.tsx`,
  per the `migrated / logged` table.
- `frontend/src/__tests__/themeTokenMigration.test.ts` — the four directory
  entries, eight assertions, the module-scope memo hoist if not already
  present, and the new scoped `describe`.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — **80** new
  entries, `src/`-relative, `task` `APRAS-84`.
- `docs/frontend/unmapped-colours.md` — **109** appended rows, one per kept
  occurrence, sorted by file then line, plus a closing `APRAS-84 total`
  paragraph in the shape APRAS-78/79/80 use. Nothing already in the file is
  rewritten.
- `docs/frontend/theme-token-mapping.md` — **the amendments §7 states, and
  nothing else**: §1a's named-move list gains a fifth entry **and** its first
  entry names a third indigo target, §1b's `bg-slate-300` row retargets to
  `bg-primary` with the recomputed ΔL 24.90 / ΔE 29.21 and budget class
  `moves (named)`, §1e's `bg-indigo-600 / border-indigo-600 /
  accent-indigo-600` row drops `accent-indigo-600` from its class cell and a
  new single-class `accent-indigo-600` row is inserted immediately beneath it
  reading target `accent-primary-foreground`, L `51.10 → 15.00`, ΔL `36.10`,
  ΔE `45.18`, budget `moves (named)`, and §1j's appendix row renames its
  verdict cell from `§1b bg-slate-300 → bg-muted` to `§1b bg-slate-300 →
  bg-primary`. The appendix's totals — 152 classes, 2,369 occurrences, no
  residue — are unchanged, because the row's membership and count are
  unchanged. The appendix needs **no** amendment for `accent-indigo-600`: its
  verdict cell for that class reads `§1e indigo → primary / ring`, a
  section-level pointer that APRAS-88 already left unamended when it retargeted
  `text-indigo-*` to `text-primary-text`, so the cell is by published precedent
  a pointer to §1e rather than a per-class target, and §1e is where the new row
  lives. `accent-indigo-600` stays in that row's class list at count 1, so the
  appendix's totals are untouched twice over.
- `frontend/src/__tests__/themeTokenCompile.test.ts` — **two** `ROWS` entries,
  each retargeted in place.
- `frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts`
  — new.
- `frontend/src/components/__tests__/TenantBrandReach.test.tsx` — extended with
  one migrated component from each directory plus the slider itself:
  `AvatarWithFallback`, `FeedbackInboxTable`, `MediaCarousel` and
  `AvatarCropEditor` (all four props-only) and `PackageStatusPage` (its two
  data hooks mocked with `vi.mock`), each asserted against the tenant token and
  never against a colour literal. `AvatarCropEditor`'s asserted token set is
  where the thumb's class is pinned, and it reads **`accent-primary-foreground`**
  — the previous draft of this spec pinned `accent-primary` there and was
  wrong.

## Test criteria

1. `npx vitest run src/__tests__/themeTokenMigration.test.ts` green with all
   four directories pinned: zero unexcused grammar matches across the 16 files,
   no stale exception, no unknown code, ledger parity in both directions, the
   preceding children's blocks untouched, and this block's 109.
2. The new contrast test asserts, by **importing** `contrastRatio` and
   `parseOklch` from `src/lib/contrast.ts`, that every foreground/background
   pair this task changes either holds ≥ `MINIMUM_CONTRAST_RATIO` or appears in
   an explicit in-file list of declared sub-AA / graphical pairs carrying its
   measured before/after ratio. Ratios to ±0.001 against the tables above, each
   against its declared background. Token values from `src/index.css`, palette
   values from `node_modules/tailwindcss/theme.css`; no colour literal
   hard-coded. Graphical pairs are asserted against the 3:1 floor, text pairs
   against 4.5.
3. The five existing suites under the four `__tests__/` directories — 44 tests
   — pass **unmodified**. None asserts on a class name, so none proves a colour.
4. `npx tsc -b` clean.
5. `npx vitest run --coverage` meets exactly **80 lines / 78 functions / 76
   branches / 80 statements**.
6. `npx eslint` diff-scoped. Re-measured now: the repository carries **375
   errors + 2 warnings across 64 files**, and **the 16 touched files carry 3
   errors and 1 warning across 2 files** (`PhotoUploadModal.tsx` 1 error;
   `WebcamCaptureDialog.tsx` 2 errors and 1 warning; `feedback-management`,
   `announcement-feed` and `package-management` contribute zero).
7. `git diff --exit-code frontend/src/index.css` succeeds;
   `docs/frontend/theme-token-mapping.md`'s diff is confined to §1a's named-move
   list, §1b's `bg-slate-300` row, §1e's `accent-indigo-600` split and §1j's
   appendix verdict cell for the `bg-slate-300` row, with §1c, §1d, §1f, §1g,
   §1h, §1i, §1k, §2, §3 and §4 byte-unchanged;
   no backend file, no Alembic revision, no route-registry entry in the diff;
   the `.dark` block stays unapplied.
8. `npx vitest run src/__tests__/themeTokenCompile.test.ts` green with both
   retargeted rows.

## What this proves, and what it misses

**Proved.** Every substitution is a §1b–1e row, and `themeTokenCompile.test.ts`
already asserts each row's ΔL/ΔE from the compiled stylesheet to ±0.1. The
guard certifies nothing was dropped or silently substituted: each of the 351 is
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
  is two legal classes. A **review duty on this diff**, and the six sites to
  start from are the two `focus:bg-white` selects, `MediaCarousel`'s three
  floating white surfaces, `AnnouncementFormModal:127`'s resting button fill,
  `MediaCarousel:41`'s red PDF glyph, `AvatarWithFallback:36`'s avatar fill,
  and `PhotoApprovalQueuePage:106` versus `:150`.
- The rendering *does* move where the table says it moves: 12 `text-*-400`
  sites darken by ~17 L points, the indigo hue shift at 47 sites, `text-*-600`
  lightening at 5 sites, the three primary fills going dark-on-emerald, two
  brand controls becoming `--primary-text`, the five red sites moving to
  `--destructive`, **the zoom-slider track turning from grey to the
  condominium's brand colour while its thumb stops being brand-coloured and
  becomes the theme's `--primary-foreground`**, and the five interaction
  distinctions lost. The slider is the one change in this child that a resident
  will notice as a change of *design* rather than of shade; it is mocked rather
  than described.
- **This child changes nothing about dark mode**, because it contains no
  `dark:` class at all. It neither deletes nor inherits one.
- **The guard cannot enforce per-site completeness**, because the exceptions
  file carries no line number. `FeedbackInboxTable.tsx` is the worst case:
  `bg-gray-50`, `text-gray-700` and `border-gray-200` are each migrated at one
  site and kept at another in that one file, and once excused an unmigrated
  occurrence anywhere in it passes. The disposition table (242 / 109 with the
  per-file split), the twelve-set inventory and the §1k site table are what a
  reviewer must check the diff against.

## Out of scope

Adding `--success` / `--warning` / `--info` tokens; migrating any `amber` or
`rose` occurrence; APRAS-90's sub-AA repair tree; deleting the now-redundant
`hover:` classes or `PackageStatusPage:93`'s redundant `<Button>` override;
repairing the avatar fill's pre-existing 1.4.11 failure; changing the slider's
geometry, its `h-1` height or the browser's native thumb shape — only the two
colour tokens move; adding a graphical floor to `build_theme`'s refusal
contract so that a pale tenant brand cannot drive the track below 3:1;
enabling the `.dark` block;
visual-regression infrastructure; any other feature directory; and any
amendment to APRAS-78's mapping table, ledger rules or grammar **other than
the retargeted `bg-slate-300` row and the split-out `accent-indigo-600` row §7
names**.

## §7 — The amendment: the track carries the brand, the thumb carries its foreground

### The operator's decision, in one sentence

`AvatarCropEditor.tsx:81`'s zoom slider swaps which of its two parts carries
the tenant's colour. Today the **thumb** is brand-coloured (`accent-indigo-600`)
and the **track** is a fixed grey (`bg-slate-300`). Afterwards the **track** is
brand-coloured (`bg-primary`) and the **thumb** is the token the theme declares
legible against the brand (`accent-primary-foreground`). The control keeps
following the condominium's brand — which was the operator's original intent —
and, unlike the earlier draft of this spec, both halves clear WCAG 1.4.11.

### Why the earlier draft was rejected, and what was measured

The earlier draft sent the track to `bg-primary` and left the thumb on
`accent-primary` under §1e's unamended row, which put the thumb on a track of
exactly its own colour. It offered the operator a second option —
`bg-muted-foreground` track, brand thumb — which had never been checked against
the thumb and fails too. Every candidate, re-measured here by importing
`contrastRatio` and `parseOklch` from `frontend/src/lib/contrast.ts`, panel =
`bg-muted`, both floors 3:1:

| Track | Thumb | track × panel | thumb × track | |
| --- | --- | --- | --- | --- |
| `bg-primary` | `accent-primary` | 3.0427 ✓ | **1.0000 ✗** | the rejected draft |
| `bg-muted-foreground` | `accent-primary` | 4.6684 ✓ | **1.5343 ✗** | the rejected option B |
| `bg-border` | `accent-primary` | 1.1278 ✗ | 2.6978 ✗ | |
| **`bg-primary`** | **`accent-primary-foreground`** | **3.0427 ✓** | **5.7588 ✓** | **chosen** |
| `bg-foreground` | `accent-primary` | 17.7626 ✓ | 5.8378 ✓ | rejected: track stops following the brand |
| `bg-secondary-foreground` | `accent-primary` | 16.0931 ✓ | 5.2891 ✓ | rejected: same reason |

**The geometry, stated so nobody re-litigates it.** The brand thumb sits at
lightness 0.62 — a mid tone. For a track to contrast with a mid-tone thumb the
track must be markedly lighter or markedly darker; lighter vanishes into the
light panel, so the only ways out are a dark track (rows 5 and 6, which stop
the control following the brand) or a swap of the colour-carrying roles (row
4). The operator chose the swap.

### It is two amendments, not a call-site judgement. Stated plainly.

**Half one — the track.** `bg-slate-300` has exactly **one** published row in
§1b, whose target cell reads `bg-muted` with no `§1f` marker beside it — unlike
the 50/100/200 rows, every one of which reads `bg-muted / §1f case 2`. §1f case
2's own text scopes itself to "neutral fills at 50/100/200" and offers the
candidate set `muted` / `accent`; `primary` is not in it, and 300 is not in its
range. There is therefore **no reading of the table under which a call site may
send `bg-slate-300` to `bg-primary`**. Sending it there amends the table.

**Half two — the thumb, and it needs its own amendment.** Asked explicitly and
answered explicitly: **§1e's existing row does not permit it.**
`accent-indigo-600` shares a row with `bg-indigo-600` and `border-indigo-600`,
and that row's single target cell reads `*-primary` — which for this class
expands to `accent-primary` and to nothing else. `accent-primary-foreground` is
a different token; no §1k clause reaches it either, because §1k chooses between
`*-primary` and `*-primary-text` and `accent-*` never takes the latter. So the
thumb move is an amendment in its own right, and is written as one.

**The exact cells, and nothing more.**

1. **§1a, entry 1** — the indigo family's entry, which "since APRAS-88 names
   **two** targets", is edited to name **three**: `*-primary` for graphical
   objects, `*-primary-text` for characters (§1k), and
   **`accent-primary-foreground` for the one `accent-` utility in the tree**,
   at ΔE 45.18. The list's *length* does not change here; the naming does. It
   has to be named because ΔE 45.18 is over 12, which §1a's own budget rule
   makes `moves`, and a `moves` row the operator decision does not name is a
   `GAP`.
2. **§1a, the list** — goes from four entries to five, gaining
   **`bg-slate-300` → `bg-primary`** at ΔE 29.21, for the same budget reason.
3. **§1b** — the `bg-slate-300` row's target becomes `bg-primary` and its
   published figures become **L 86.90 → 62.00, ΔL 24.90, ΔE 29.21, budget
   `moves (named)`**, recomputed with the document's own arithmetic (OKLab
   distance, L in 0–100, chroma ×100), which reproduces the row's existing 9.43
   for `bg-muted` to the digit and is therefore the same arithmetic.
4. **§1e** — the row `bg-indigo-600 / border-indigo-600 / accent-indigo-600 |
   *-primary | 51.10 → 62.00 | 10.90 | 37.24 | moves (named)` loses
   `accent-indigo-600` from its class cell, its four numeric cells unchanged,
   and a new single-class row is inserted immediately beneath it:
   **`accent-indigo-600` | `accent-primary-foreground` | 51.10 → 15.00 | 36.10
   | 45.18 | moves (named)**. Measured, not asserted: indigo-600 is
   `oklch(51.1% 0.262 276.966)` and `--primary-foreground` is
   `oklch(0.15 0.02 160)`, giving ΔL 36.10 and ΔE 45.179.
5. **§1j's appendix** — the verdict cell of the row `§1b bg-slate-300 →
   bg-muted` is renamed to `§1b bg-slate-300 → bg-primary`. Its membership
   (`bg-slate-300` 1) and its occurrence count (1) do not move, so the
   appendix's published totals — **152 classes, 2,369 occurrences, no
   residue** — are untouched. The appendix needs **no** change for
   `accent-indigo-600`: that class sits in the row whose verdict cell reads
   `§1e indigo → primary / ring`, which APRAS-88 already left unamended when it
   retargeted `text-indigo-*` to `text-primary-text`, so by published precedent
   that cell is a pointer to §1e rather than a per-class target — and §1e is
   where the new row lives. Class count, occurrence count and totals all stay.

Nothing else in the document changes. In particular §1c, §1d, §1f, §1h's eight
gap codes, §1i's single `/90` alpha, §1k and §3b's grammar are byte-unchanged.

### `accent-primary-foreground` is a real utility, verified by compiling it

Not assumed. Compiled through Tailwind 4's own `compile()` over
`frontend/src/index.css`, exactly as `themeTokenCompile.test.ts` does it, the
two utilities emit:

```
.accent-primary            { accent-color: var(--color-primary); }
.accent-primary-foreground { accent-color: var(--color-primary-foreground); }
```

and `index.css`'s `@theme` block declares `--color-primary-foreground:
var(--primary-foreground)`, so the thumb resolves to the same token
`buttonVariants`' `default` uses for text on a brand fill. The change is a
**token substitution** in §1i's sense — one class swapped for one class in the
same `className` string, none added and none removed — so §1i is satisfied.
`frontend/src` contains exactly one `accent-indigo-600` (this call site) and
one `accent-primary` (`RoleMultiSelect.tsx:102`, authored directly, in a
directory this task does not touch and which `MIGRATED_DIRECTORIES` does not
pin); the amendment retargets the *migration* of `accent-indigo-600` and does
not forbid `accent-primary` being written anywhere, so no sibling is disturbed.

### Why no sibling is disturbed by the track half either

`bg-slate-300` occurs **once** in `frontend/src` (`AvatarCropEditor.tsx:81`;
the only other hit in the tree is the row inside `themeTokenCompile.test.ts`
itself), and that one occurrence is inside this child's own scope. Verified per
directory, not assumed: APRAS-81's, APRAS-82's, APRAS-83's and APRAS-85's specs
contain no `bg-slate-300` at all, no published migrated-to-`bg-muted` count in
any of them includes it, and this child's own 242 / 109 disposition is
unchanged — both occurrences still migrate, only to different tokens.
`AvatarCropEditor.tsx` stays at **16 / 3**. APRAS-85 mentions
`accent-indigo-600` only as a §3b *grammar* fixture, matching the **source**
class, which this amendment does not touch.

### The contrast story, honestly: both halves improve

| Pair | Today | After (default theme) |
| --- | --- | --- |
| track × panel (`bg-slate-300` on `bg-slate-50` → `bg-primary` on `bg-muted`) | 1.4181 ✗ | **3.0427 ✓** |
| thumb × track (`accent-indigo-600` on `bg-slate-300` → `accent-primary-foreground` on `bg-primary`) | 4.3394 ✓ | **5.7588 ✓** |

Both figures were re-derived for this revision by importing `contrast.ts`, not
carried over.

**The thumb half is guaranteed — by two different mechanisms, one per palette
mode, and the distinction matters because only one of them is a 422.**
`("primary-foreground", "primary")` is `MEASURED_PAIRS[2]` in both
`frontend/src/lib/contrast.ts` and `backend/app/core/branding.py`, and
`MINIMUM_CONTRAST_RATIO` is 4.5. What that buys differs by mode:

* **Advanced mode — refused with 422.** `build_theme` itself never raises. The
  one non-test caller of `audit_contrast` is
  `TenantService.validated_brand_theme`
  (`backend/app/services/tenant_service.py:646–657`), which builds the theme,
  audits every scheme against `MEASURED_PAIRS` and raises
  `InsufficientContrastError` — a 422 listing each failing pair with its
  measured ratio — if any pair reads under 4.5:1. A tenant who authors all
  thirteen tokens by hand therefore cannot store a thumb that is illegible on
  its own track.
* **Simple mode — never measured, because the derivation owns both sides.**
  `validated_brand_theme` returns at line 647–648, before anything is built,
  for every palette whose mode is not `ADVANCED_MODE`; no request-time
  measurement happens at all. It is not needed: in simple mode both halves of
  this pair come out of one function, `derive_brand_surface`
  (`backend/app/core/branding.py`), which snaps the tenant's clamped brand with
  `snap_to_gamut`, chooses the foreground with `_pick_foreground` (the better
  of near-white `oklch(0.98 0 0)` and a near-black at the brand's own hue) and
  then moves the **surface** away from that foreground with `_repair_surface`,
  in `_STEP` = 0.01 lightness increments, until
  `contrast_ratio(surface, text) >= MINIMUM_CONTRAST_RATIO`. The pair the
  slider depends on is the loop's own exit condition, so a simple-mode palette
  cannot emit a failing thumb.

**What happens if the repair hits its bound.** `_repair_surface` is bounded at
`_MAX_STEPS` = 100 iterations and has **no failure path**: unlike
`_walk_to_legible_text`, which returns `None` when a walk runs out of grid, it
simply returns the last colour it produced, still failing, without raising and
without any 422 — and in simple mode nothing downstream measures it. The bound
is unreachable in practice, because 100 steps of 0.01 crosses the whole
lightness range, and that is asserted rather than assumed:
`test_the_brand_surface_lattice_never_fails_and_never_leaves_the_gamut` in
`backend/tests/test_branding.py` sweeps every `(lightness, chroma, hue)` triple
`_clamp_input` can produce — L 0.20–0.92 by 0.01, C 0.00–0.22 by 0.01, H every
5°, light and dark — and asserts 0 failures, 0 out-of-gamut emissions and a
worst case at or above 4.5. Any change to `_STEP`, `_MAX_STEPS` or the
near-white/near-black constants that broke the thumb would break that sweep
first.

Between the two mechanisms, no palette that can reach the database — authored
or derived — carries a thumb below 4.5:1 on its own track, which is more than
the 3:1 graphical floor this control needs. No other placement of the brand on
this control has that property.

### The accepted, named risk: the track moves with the tenant brand

**3.0427 clears 3:1 by 0.0427, and `--primary` is re-derived per tenant.**
Measured through `build_theme` — the repository's only theme derivation — and
then through `contrast.ts`:

| Theme | track × panel | | thumb × track | |
| --- | --- | --- | --- | --- |
| product default — `--primary` `oklch(0.62 0.15 160)` on `--muted` `oklch(0.96 0.01 160)`, both read from `src/index.css` (lines 39, 55) | **3.0427** | ✓ by 0.0427 | 5.7588 | ✓ |
| `#059669` (a síndico types the green) | 3.3246 | ✓ | 5.2705 | ✓ |
| `#dc2626` | 4.2451 | ✓ | 4.5159 | ✓ |
| `#2563eb` | 4.5361 | ✓ | 4.8098 | ✓ |
| `#7c3aed` | 4.9895 | ✓ | 5.3007 | ✓ |
| `#facc15` (pale yellow) | **1.3661** | ✗ — **worse than the 1.4181 it has today** | 12.8247 | ✓ |

**The first row is the shipped theme, not a sixth tenant brand.** Only the five
rows beneath it are `build_theme` output; the default row's two values are the
tokens `src/index.css` declares, which is why the contrast test reads them from
that file rather than quoting them as data.

**A pale-branded condominium ships an invisible track.** That is stated here
rather than guarded, because nothing in this repository can guard it:
`--border`, `--input` and `--ring` are outside `MEASURED_PAIRS` by APRAS-68's
explicit decision, `build_theme`'s 422 contract measures eight *text* pairs and
adding a ninth graphical one would begin refusing palettes that are stored and
working today, and no test can enumerate the brands tenants will type. **The
operator has accepted this knowingly.** What this child does instead is
**record** the figures: the new contrast test carries the table above's five
`build_theme` rows as data and reads the default row's two values from
`src/index.css` like every other token it measures, asserts each cell to
±0.001, and marks the pale-yellow track as an expected,
**named** failure. The tree-wide 1.4.11 repair remains APRAS-90's.

### One secondary observation, recorded and not acted on

A browser paints the native range thumb taller than the 4 px track, so a sliver
of thumb overhangs onto the panel. Measured thumb × **panel**: 17.5222 in the
default theme, 17.5221 for `#059669`, 17.5198 for `#facc15` — and **1.0638**,
**1.0603** and **1.0624** for `#dc2626`, `#2563eb` and `#7c3aed`, whose
`--primary-foreground` `build_theme` derives as the near-white
`oklch(0.98 0.00 0.00)`. For those three brands the overhanging sliver blends
into the panel and the thumb reads as the shape the track cuts around it, which
is still 4.5:1-separated from the track it sits on. It is recorded as a named
observation rather than repaired: repairing it would mean adding a ring or a
border class, which §1i forbids (a class added, not swapped), and it is
strictly better than what the rejected draft would have shipped.

### This is a visual change, not an equivalence

Filed plainly, because the rest of this child is not: every other substitution
here is either byte-identical in `:root` or a shade move inside a published
budget. This one turns a neutral grey bar into the condominium's brand colour
and simultaneously stops the draggable dot being brand-coloured. A resident of
a red-branded condominium will see a red bar with a near-white dot where there
was a grey bar with an indigo dot. That is the operator's decision and the spec
implements it; it is recorded as a **design change** so that no reviewer reads
it as a token substitution, and so that the mock — not the diff — is what the
decision was made from.

### Open questions

**None.** The zoom-slider question this spec previously asked was decided by
the operator in favour of the combination above, and
`docs/tasks/APRAS-84-mock.html` now renders that combination as the decided
state with the rejected candidates kept beside it for provenance.


## Expected Results

- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts` passes with `MIGRATED_DIRECTORIES` containing all four of `"src/features/media-management/components"`, `"src/features/feedback-management/components"`, `"src/features/announcement-feed/components"` and `"src/features/package-management/components"`, `pinnedFiles()` returning those directories' 5, 5, 5 and 1 source files respectively, and `violations(PINNED, EXCEPTIONS, LEDGER)` returning `[]`.
- [ ] Re-measuring the sixteen files `frontend/src/features/{media-management,feedback-management,announcement-feed,package-management}/components/*.tsx` with the guard's §3b grammar accounts for all 351 baseline occurrences as 242 migrated + 109 left and logged, with zero `dark:`-prefixed occurrences before and after and zero `dark:` classes deleted; after the change the sixteen files together retain exactly 109 grammar matches and zero six-digit hex literals, `media-management` retaining 49, `feedback-management` 43, `announcement-feed` 15 and `package-management` 2, and `AnnouncementFeedPage.tsx` retaining none. The 351 baseline is read from the state immediately before this task's own commits, those commits being identified with `git log --grep '(APRAS-84)' --format=%H` — the `<type>(APRAS-84): …` scope convention this repository commits under — and the baseline being `<oldest such commit>^`, inspected with `git show <that>:<path>`. No assertion names a literal commit hash, and none requires a branch point, a remote or a report.
- [ ] `AvatarCropEditor.tsx` migrates 16 of its 19 occurrences and keeps 3, and its **one** `bg-slate-300` — the zoom-slider track at the `<input type="range">`, the only occurrence of that class anywhere under `frontend/src` outside `frontend/src/__tests__/themeTokenCompile.test.ts` — becomes **`bg-primary`**, not `bg-muted`, and its **one** `accent-indigo-600` — the zoom-slider thumb on that same `<input type="range">`, the only occurrence of that class anywhere under `frontend/src` — becomes **`accent-primary-foreground`**, not `accent-primary`. After the change, splitting that `<input>`'s `className` on `/\s+/` yields a token list that contains `bg-primary` and `accent-primary-foreground` and contains none of the tokens `bg-muted`, `bg-slate-300`, `accent-indigo-600` or `accent-primary` (whitespace-split token equality, so `accent-primary` does not match `accent-primary-foreground`); the panel element that encloses it carries `bg-muted`; `grep -R "bg-slate-300" frontend/src` returns exactly one line, inside `frontend/src/__tests__/themeTokenCompile.test.ts`; and `grep -R "accent-indigo" frontend/src` returns exactly one line, in that same file. The `<input>` gains no class and loses no class: its token count is the same before and after, each of the two changes being one token swapped for one token. The three kept occurrences are three `text-slate-700`, each logged `GAP-OUT-OF-BUDGET`.
- [ ] `docs/frontend/theme-token-mapping.md` is amended in exactly five places and nowhere else: (a) §1a's named-move list grows from four entries to five, the fifth being `bg-slate-300` → `bg-primary`; (b) §1a's first entry, the indigo family, now names three targets rather than two — `*-primary` for graphical objects, `*-primary-text` for characters, and `accent-primary-foreground` for `accent-indigo-600`; (c) §1b's single `bg-slate-300` row now reads target `bg-primary`, L `86.90 → 62.00`, ΔL `24.90`, ΔE `29.21`, budget `moves (named)`; (d) §1e's row whose class cell read `bg-indigo-600` / `border-indigo-600` / `accent-indigo-600` now lists only `bg-indigo-600` and `border-indigo-600`, its target `*-primary` and its four numeric cells `51.10 → 62.00`, `10.90`, `37.24`, `moves (named)` all unchanged, and a new single-class row appears immediately beneath it reading `accent-indigo-600` | `accent-primary-foreground` | `51.10 → 15.00` | `36.10` | `45.18` | `moves (named)`; and (e) §1j's appendix row whose verdict cell read `§1b bg-slate-300 → bg-muted` now reads `§1b bg-slate-300 → bg-primary`, with that row's class list (`bg-slate-300` 1) and occurrence count (1) unchanged. The appendix's published totals are still `152` classes and `2,369` occurrences with no residue, and the appendix row that lists `accent-indigo-600` 1 among fourteen indigo classes totalling 167 occurrences is byte-unchanged, its verdict cell still reading `§1e indigo → primary / ring`. `git diff docs/frontend/theme-token-mapping.md` shows no changed line in §1c, §1d, §1f, §1g, §1h, §1i, §1k, §2, §3 or §4, adds and removes no gap code (the set stays at eight), adds no token to `frontend/src/index.css`, and adds exactly one row anywhere in the document, namely §1e's new `accent-indigo-600` row.
- [ ] `npx vitest run src/__tests__/themeTokenCompile.test.ts` passes with its `ROWS` array holding exactly one `bg-slate-300` entry and exactly one `accent-indigo-600` entry, each retargeted **in place**: `{ source: "bg-slate-300", target: "bg-primary", dL: 24.9, dE: 29.21 }` and `{ source: "accent-indigo-600", target: "accent-primary-foreground", dL: 36.1, dE: 45.18 }`. No `bg-slate-300` → `bg-muted` entry and no `accent-indigo-600` → `accent-primary` entry remains anywhere in the file, `ROWS` has the same number of elements before and after, the `TOLERANCE` constant is still `0.1`, and no other entry in `ROWS` is added, removed or edited. The suite compiles `accent-primary-foreground` through Tailwind and resolves it to `--primary-foreground`, so a target name that does not exist as a utility fails here rather than silently painting nothing.
- [ ] `docs/frontend/unmapped-colours.md` gains 109 rows whose `task` cell is `APRAS-84` — 47 `GAP-OUT-OF-BUDGET`, 28 `GAP-TINT`, 14 `GAP-NO-TOKEN`, 9 `GAP-BORDER-100`, 8 `GAP-OVERLAY`, 3 `GAP-NO-SURFACE`, and zero `GAP-SWATCH`, zero `GAP-UNLISTED` — and `frontend/src/__tests__/themeTokenMigration.exceptions.json` gains exactly 80 entries whose `task` is `APRAS-84` (36 naming a `media-management` file, 33 a `feedback-management` file, 9 an `announcement-feed` file, 2 a `package-management` file), with the guard's ledger-parity check passing in both directions. No `bg-slate-300` row and no `bg-slate-300` exception is created, because that occurrence migrates.
- [ ] Exactly four brand-text occurrences carry a `-primary-text` token, at exactly two call sites and no others: `PhotoUploadModal.tsx`'s "Ajustar Recorte" button, whose `text-indigo-600 hover:text-indigo-800` becomes `text-primary-text hover:text-primary-text`, and `FeedbackInboxTable.tsx`'s "Ver Detalhes" button, whose `text-indigo-600 hover:text-indigo-800` becomes the same pair; no `-primary-text` appears on any `bg-`, `border-`, `ring-`, `divide-`, `outline-`, `fill-`, `stroke-` or `accent-` utility anywhere in the diff.
- [ ] Nine `text-`-prefixed brand occurrences become `text-primary` or `hover:text-primary` because the element carrying them paints no glyphs — `FeedbackChannelPage.tsx` ×2, `AnnouncementFeedPage.tsx` ×1, `AnnouncementFormModal.tsx` ×2, `PackageStatusPage.tsx` ×1, `NewFeedbackForm.tsx` ×1 (a `<input type="checkbox">`), `FeedbackHistoryList.tsx` ×1 (the only `text-indigo-500`) and `AnnouncementCard.tsx` ×1 (a `hover:` variant) — and no `indigo` class of any prefix, with or without a `hover:`, `focus:` or `accent-` variant, remains anywhere in the sixteen files.
- [ ] `bg-primary` is produced at exactly 14 occurrences across the sixteen files — 11 from `bg-indigo-600`, 2 from `bg-emerald-600` and 1 from `AvatarCropEditor.tsx`'s `bg-slate-300` — and `bg-muted` at exactly 24: `bg-slate-50` ×9, `bg-gray-50` ×7, `bg-gray-100` ×6, `bg-slate-100` ×1 and `bg-slate-200` ×1, with no `bg-slate-300` among them.
- [ ] `frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts` passes, importing `contrastRatio` and `parseOklch` from `src/lib/contrast.ts` and reading every **token** value it uses from `src/index.css` and every **Tailwind palette** value it uses from `node_modules/tailwindcss/theme.css` rather than hand-writing them: no value of any `--token` and no value of any Tailwind palette class appears in this file as a literal. The **one** permitted exception, and the only colour literals the file may contain, are the backend-emitted strings the slider's per-theme results below mandate, capped by provenance and brand set rather than by a count: for each of the five named tenant brands `#059669`, `#dc2626`, `#2563eb`, `#7c3aed` and `#facc15`, the `oklch()` strings `build_theme` emits for that brand as its `--primary`, its `--primary-foreground` and its `--muted` — the three tokens the track, thumb and thumb-against-panel pairs are measured from — together with those same five `#RRGGBB` strings, which name the brands. Those are `build_theme`'s **output quoted as test data** and appear in neither of the two source files the rule above makes it read. The **product default is not among them**: it is not a tenant brand and not a `build_theme` output but the shipped theme, so its `--primary`, `--primary-foreground` and `--muted` are read from `src/index.css` exactly like every other token this file measures, and no literal for it appears anywhere. A grep for colour literals in this file therefore returns nothing outside that set: every match is either one of those five `#RRGGBB` strings or an `oklch()` string `build_theme` emits as the `--primary`, `--primary-foreground` or `--muted` of one of those five brands. **No number of literals is asserted, and none should be**: the same `oklch()` string can be emitted for more than one brand — `oklch(0.98 0.00 0.00)` is the `--primary-foreground` of three of the five — so the set is decided by provenance, brand and token role, never by counting. The test asserts to ±0.001 that `--primary-text` on `--card` is 5.2096 and on `--accent` 4.6547, `--muted-foreground` on `--card` 5.2249 and on `--muted` 4.6684, `--foreground` on `--card` 19.8801, `--primary-foreground` on `--primary` 5.7588, `--destructive-foreground` on `--destructive` 4.5381, `--destructive` on `--card` 4.8073, and — against the 3:1 graphical floor — `--primary` on `--card` 3.4054 and on `--accent`/`--muted` 3.0427.
- [ ] The same test asserts the zoom slider's two graphical pairs by name and to ±0.001, both against the 3:1 graphical floor: the **track**, `bg-slate-300` on `bg-slate-50` measuring 1.4181 and failing the floor before this task, becomes `--primary` on `--muted` measuring **3.0427** and **passing** it; and the **thumb**, `accent-indigo-600` on `bg-slate-300` measuring 4.3394 before, becomes `--primary-foreground` on `--primary` measuring **5.7588** and passing. Neither appears in the test's list of declared sub-floor pairs, because this task's slider introduces no sub-floor pair in the default theme. The test additionally asserts, from `MEASURED_PAIRS` and `MINIMUM_CONTRAST_RATIO` imported from `src/lib/contrast.ts` rather than from a literal, that the tuple `["primary-foreground", "primary"]` is a member of `MEASURED_PAIRS` and that `MINIMUM_CONTRAST_RATIO` is 4.5 — the two facts behind the thumb pair being platform-guaranteed rather than a measurement that happens to pass, a guarantee delivered by a different mechanism in each palette mode and stated as such in the test's own comment: for an **advanced** palette by the 422 `TenantService.validated_brand_theme` raises (`backend/app/services/tenant_service.py:646–657`, the only non-test caller of `audit_contrast`; `build_theme` itself never raises), and for a **simple** palette, which that function returns from before measuring anything, by `derive_brand_surface`'s `_pick_foreground` + `_repair_surface` derivation, which owns both sides of the pair and walks the surface until it clears 4.5:1.
- [ ] The same test carries a named table of **six themes — the product default plus five tenant brands**. The five tenant brands, `#059669`, `#dc2626`, `#2563eb`, `#7c3aed` and `#facc15`, carry the `oklch()` strings `backend/app/core/branding.py`'s `build_theme` emits for each — quoted verbatim as data, never re-derived in TypeScript, and being the one colour-literal exception result 9 permits, since they are backend output rather than a token or palette value the file could have read from `src/index.css` or `node_modules/tailwindcss/theme.css`. The **product-default row carries no colour literal at all**: it is the shipped theme, so its `--primary`, `--primary-foreground` and `--muted` are read from `src/index.css` like every other token the file reads, which is what result 9's grep requires of it. The test asserts, to ±0.001, each theme's **track** (`--primary` on that theme's `--muted`) and each theme's **thumb** (`--primary-foreground` on that theme's `--primary`). Track: the product default 3.0427, `#059669` 3.3246, `#dc2626` 4.2451, `#2563eb` 4.5361, `#7c3aed` 4.9895 — all five recorded as clearing 3:1 — and `#facc15` **1.3661**, recorded as an **expected, named failure** which the test's own message states is worse than the track's present 1.4181 and is an accepted risk the operator took knowingly. Thumb: 5.7588, 5.2705, 4.5159, 4.8098, 5.3007 and 12.8247, all six asserted to clear 4.5 and therefore the 3:1 floor. The test states in the same place that no guard exists for the track and that `--border`, `--input` and `--ring` remain outside `MEASURED_PAIRS`, while the thumb pair is inside it.
- [ ] The same test declares, in an explicit in-file list with before/after ratios, every other pair this task leaves or puts below 4.5:1: the graphical `--primary` at 3.0427 on `--accent`/`--muted` (6 sites) and 3.4054 on `--card` (3 sites); `--destructive` on `--muted` 4.2953 at `CommentThread.tsx`'s delete glyph; `AvatarWithFallback.tsx`'s avatar fill going 1.2319 → 1.1192, recorded as failing the 3:1 floor **before** this task as well as after; the zoom-slider **thumb measured against the panel** rather than against its track, which the native range widget overhangs by a few pixels above and below the 4 px bar — `--primary-foreground` on `--muted` reading 17.5222 in the default theme, 17.5221 for `#059669` and 17.5198 for `#facc15`, but **1.0638** for `#dc2626`, **1.0603** for `#2563eb` and **1.0624** for `#7c3aed`, whose `--primary-foreground` `build_theme` derives as `oklch(0.98 0.00 0.00)`, each recorded as a named observation and not repaired, since repairing it would add a class and §1i permits only swapping one; and the kept status pairs `text-emerald-600` on `bg-emerald-50` 3.5279 and on white 3.7194, `text-white` on `bg-rose-500` 3.7327 and on `bg-amber-500` 2.1452.
- [ ] The same test asserts that every kept **text** foreground sitting on a migrated background still clears 4.5:1: `text-gray-800` on `--muted` 13.1205 (from 14.0676 on `bg-gray-50`, 13.3451 on `bg-gray-100` and 14.0283 on `bg-slate-50`), `text-gray-700` on `--muted` 9.2081 (from 9.3658 on `bg-gray-100`), `text-slate-700` on `--muted` 9.2424 (from 8.3972 on `bg-slate-200`), and `text-gray-800` 14.6846, `text-gray-700` 10.3058, `text-slate-700` 10.3442 and `text-slate-800` 14.6574 unchanged on `--card`.
- [ ] Grouping every grammar match in the sixteen files by `(file, class-context span)` — using the guard's own exported `classContexts()`, not by line — yields **zero** spans holding both a migrated occurrence and a kept `GAP-TINT` occurrence.
- [ ] All twelve status sets retain their original class strings verbatim: the three branches of `FeedbackInboxTable.tsx`'s `getStatusBadgeClass` (9 classes, including its neutral `default` branch `bg-gray-50 text-gray-700 border-gray-200`), `FeedbackHistoryList.tsx`'s ANSWERED/PENDING ternary (6), `FeedbackDetailsView.tsx`'s board-response panel (5), `PhotoApprovalQueuePage.tsx`'s reject button (4) and error alert (3) and pending-count chip (2), `WebcamCaptureDialog.tsx`'s "Tirar Outra" button (4) and camera-error alert (3), `PhotoUploadModal.tsx`'s error alert (3), `AvatarWithFallback.tsx`'s "Em Aprovação" badge (2), `FeedbackHistoryList.tsx`'s unread badge (2) and `AnnouncementCard.tsx`'s read-receipt glyph (1) — 44 classes in all, each with a ledger row.
- [ ] Exactly four `emerald` occurrences migrate — `PhotoApprovalQueuePage.tsx`'s "Aprovar" button and `PackageStatusPage.tsx`'s `<Button>`, each reading `bg-primary hover:bg-primary/90 text-primary-foreground` afterwards — while the other twelve `emerald` occurrences in the sixteen files are unchanged; and exactly five `red` occurrences migrate — `PhotoApprovalQueuePage.tsx`'s confirm-reject button reading `bg-destructive hover:bg-destructive text-destructive-foreground`, `MediaCarousel.tsx`'s `<FileText/>` reading `text-destructive`, and the `hover:text-red-600` of `AnnouncementCard.tsx` and `CommentThread.tsx` reading `hover:text-destructive` — while the other thirteen `red` occurrences, all inside status sets 4, 6, 7 and 8, are unchanged.
- [ ] Every opacity modifier present in the baseline is carried over unchanged on migrated classes: `bg-white/80` → `bg-card/80` (×2, `MediaCarousel.tsx`), `bg-white/70` → `bg-card/70` (×1, `MediaCarousel.tsx`), `hover:bg-gray-50/80` → `hover:bg-accent/80` (×2, `FeedbackHistoryList.tsx` and `FeedbackInboxTable.tsx`), `hover:bg-indigo-700` → `hover:bg-primary/90` (×10) and `hover:bg-emerald-700` → `hover:bg-primary/90` (×2); the eight `bg-black/20`, `bg-black/40`, `bg-black/60` and `bg-black/80` scrims are unchanged and logged under `GAP-OVERLAY`; `bg-amber-500/90` is unchanged and logged under `GAP-NO-TOKEN`; and the diff contains no `text-primary/N` and no `text-primary-text/N` anywhere, so `frontend/src/__tests__/brandTextOpacity.test.ts` passes unmodified.
- [ ] `text-white` survives at exactly three sites in the sixteen files, all logged under `GAP-NO-SURFACE` — `AvatarWithFallback.tsx` on `bg-amber-500/90`, `FeedbackHistoryList.tsx` on `bg-rose-500`, and `PhotoApprovalQueuePage.tsx` on the `bg-black/20` thumbnail scrim — and appears nowhere else; the other thirteen baseline `text-white` occurrences are `text-primary-foreground` ×12 and `text-destructive-foreground` ×1.
- [ ] `describe("the pilot's own ledger arithmetic")` and the equivalent blocks for every sibling already present in the file still pass with their assertions unedited, and no ledger row or exceptions entry belonging to another task is modified.
- [ ] `frontend/src/components/__tests__/TenantBrandReach.test.tsx` passes with five added cases that mount `AvatarWithFallback` (with `status="PENDING_APPROVAL"` and no `photoUrl`, so the badge renders), `FeedbackInboxTable` (with `isLoading={false}` and one item whose `status` is `"PENDING"`), `MediaCarousel` (with two media items of which the first is **not** `"IMAGE"`, so the PDF link, both nav buttons and both dots render), `PackageStatusPage` (with `useMyPackages` and `useMarkPackagePickedUp` replaced by `vi.mock`, returning one lot holding one package whose status is `AWAITING_PICKUP`) and `AvatarCropEditor` (with `imageSrc`, `onCropComplete` and `onCancel` stubs — it takes props only and needs no mock) under the mocked `useTenantProfile`, assert `getComputedStyle(document.documentElement).getPropertyValue("--primary")` equals the mocked theme's value, and assert, **per component**, over the **whitespace-split class tokens of the FULL rendered markup** — every `class` value in the mounted output split on `/\s+/`, explicitly **including the tokens contributed by any `components/ui/` primitive the component renders**, not only the tokens written in the component's own source — that the token set is exactly as follows. Splitting is strict, so `bg-card`, `bg-card/80` and `hover:bg-card` are three distinct tokens and none matches another; no substring matching anywhere in this test. `AvatarWithFallback`, `FeedbackInboxTable`, `MediaCarousel` and `AvatarCropEditor` render **no** `components/ui/` primitive, so each of those four sets is entirely its own. `AvatarWithFallback`: contains `bg-muted`, `border-input`, `text-slate-700`, `bg-amber-500/90` and `text-white`, and contains none of the tokens `bg-card`, `bg-primary`, `text-primary`, `text-primary-text`, `text-primary-foreground`, `text-muted-foreground`, `text-foreground`, `bg-accent` or `text-destructive`. `FeedbackInboxTable`: contains `bg-card`, `border-border`, `bg-muted`, `text-muted-foreground`, `text-foreground`, `text-primary-text`, `hover:text-primary-text`, `bg-accent`, `hover:bg-accent` and `hover:bg-accent/80`, and contains none of the tokens `text-primary`, `bg-primary`, `text-primary-foreground`, `text-destructive`, `border-input` or `bg-background`. `MediaCarousel`: contains `bg-muted`, `bg-card`, `bg-card/80`, `bg-card/70`, `hover:bg-card`, `hover:bg-accent`, `text-destructive` and `bg-primary`, and contains none of the tokens `text-primary`, `text-primary-text`, `text-primary-foreground`, `border-border`, `bg-accent`, `text-muted-foreground` or `text-foreground`. `AvatarCropEditor`: contains `bg-muted`, `border-border`, `text-slate-700`, `bg-foreground`, `border-primary`, `text-muted-foreground`, **`bg-primary`**, **`accent-primary-foreground`**, `bg-card`, `border-input`, `hover:bg-accent`, `text-primary-foreground` and `hover:bg-primary/90`, and contains none of the tokens **`accent-primary`**, `accent-indigo-600`, `text-primary`, `text-primary-text`, `text-destructive`, `bg-accent`, `bg-background`, `text-foreground` or `bg-slate-300` — `accent-primary` being excluded by whitespace-split token equality, which does not treat it as matching `accent-primary-foreground`; and the single element carrying `bg-primary` and `accent-primary-foreground` is the same one, the `<input type="range">`. `PackageStatusPage` renders `ui/button` at the **`default`** variant — the `<Button>` carries no `variant` prop, so `buttonVariants` contributes `bg-primary`, `text-primary-foreground` and `hover:bg-primary/90`, which `twMerge` collapses against the component's own identical override — so its set contains `bg-card`, `border-border`, `bg-accent`, `bg-muted`, `border-input`, `text-primary`, `text-foreground`, `text-muted-foreground`, `text-gray-700`, and `bg-primary`, `text-primary-foreground` and `hover:bg-primary/90` **counting the button's contribution**, and contains none of the tokens `text-primary-text`, `text-destructive`, `bg-background` or `hover:bg-accent`. Never a colour literal is asserted anywhere in the test.
- [ ] `git diff --exit-code frontend/src/index.css` succeeds, and — after the developer has staged its own paths with `git add` — `git diff --name-only --cached` contains no backend file, no Alembic revision, no route-registry change, no file under `frontend/src/components/ui/`, `frontend/src/features/public-site/`, `frontend/src/features/lot-management/`, `frontend/src/features/visitor-management/`, `frontend/src/features/document-management/`, `frontend/src/features/occurrence-management/`, `frontend/src/features/finance/`, `frontend/src/features/purchase-management/` or `frontend/src/features/access-control/`, and no path outside this set of twenty-six: the sixteen `.tsx` under the four component directories, `frontend/src/__tests__/themeTokenMigration.test.ts`, `frontend/src/__tests__/themeTokenMigration.exceptions.json`, `frontend/src/__tests__/brandTextRole.test.ts`, `frontend/src/__tests__/themeTokenCompile.test.ts`, `frontend/src/components/__tests__/TenantBrandReach.test.tsx`, `frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts`, `docs/frontend/unmapped-colours.md`, `docs/frontend/theme-token-mapping.md`, `docs/tasks/APRAS-84-spec.md` and `docs/tasks/APRAS-84-mock.html`. `frontend/src/__tests__/brandTextRole.test.ts` is APRAS-87's graphical-site guard (landed at `0815915`, after this spec was written): it reconciles a live scan of bare `text-primary` against a declared set of graphical sites, per file and in both directions, so a migration that moves an icon onto `text-primary` must append its declaration there or the guard fails. Any change to it must be a pure append inside `GRAPHICAL_PRIMARY_SITES` — no existing declaration removed or weakened, and no change to that file's surfaces, ratios or imports. If this task's migration adds no bare `text-primary`, the file is absent from the staged set instead.
- [ ] `npx tsc -b` completes with no error.
- [ ] `npx vitest run --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint` over the sixteen touched component files reports at most the 3 errors and 1 warning across 2 files present today (`PhotoUploadModal.tsx` 1 error, `WebcamCaptureDialog.tsx` 2 errors and 1 warning, and zero in all five `feedback-management`, all five `announcement-feed` and the one `package-management` file), and the repository-wide error and warning totals are no higher after the change than they were immediately before this task's own commits, that state being identified as `<oldest commit matching git log --grep '(APRAS-84)'>^` and never as a literal commit hash.
- [ ] The five existing suites in `frontend/src/features/media-management/__tests__/`, `frontend/src/features/feedback-management/__tests__/`, `frontend/src/features/announcement-feed/__tests__/` and `frontend/src/features/package-management/__tests__/` — 44 tests in total — pass without modification.
- [ ] `npx vitest run src/__tests__/themeTokenMigration.test.ts --reporter=verbose` reports every individual test finishing under 2 s, including `it("fails when any single exception is removed")`; the scan memo inside `violations()` is at module scope, keyed on the file path and its source text, and every mutated-argument test still fails when its mutation is applied.
