# APRAS-90 — Clear the brand-text-at-opacity site on the gatehouse counter

Follow-up to APRAS-80, which landed at `a8fc8ab`. §1i of the theme-token
migration contract forbids a migration child from adding or removing a class,
so APRAS-80 carried the `/80` over and declared the sub-AA composite instead of
repairing it. This task performs the repair. §1i binds the APRAS-77 children
only; it does not bind this task.

## Scope

**One deliverable: brand text rendered at a fractional opacity over a brand
tint clears WCAG 2.1 AA (4.5:1) tree-wide, and a test keeps it that way as the
remaining migration children land.**

### What the sweep found at HEAD

Swept over `frontend/src`, `.ts`/`.tsx`, excluding `__tests__/` directories and
`*.test.ts(x)`, for `text-primary-text/<n>`, `text-primary/<n>` and any
surviving `text-indigo-<scale>/<n>`. **Exactly one site exists**, and it is the
known one:

`frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx:150`
— the gatehouse's active-visitor counter label, `text-xs font-semibold
text-primary-text/80`. DOM ancestry traced from the JSX, not assumed: `:150` →
its unfilled `<div>` wrapper at `:146` → the counter card at `:144`, which
carries `bg-accent border border-border`. The surface is `--accent`. At
`text-xs` (12px, semibold) the element is **normal** text, so its floor is
4.5:1 — not the 3:1 large-text allowance the sibling number at `:147`
(`text-2xl font-black`) would enjoy.

There is **no** `text-primary/<n>` anywhere (so APRAS-79's pre-amendment
lot-management migration left no site of this shape), and **no** surviving
`text-indigo-<scale>/<n>` outside test prose.

### Measured at HEAD, by importing `frontend/src/lib/contrast.ts`

Never reimplemented; values read out of `src/index.css`'s `:root`, never
`.dark`, never a literal. Compositing is APRAS-80's model — `oklchToHex` →
8-bit sRGB channel mix → `hexToOklch`.

| Pair | Hex | Ratio on `--accent` | Verdict |
| --- | --- | --- | --- |
| `--primary-text` at `/80` over `--accent` (HEAD, the label) | `#429471` | **3.2883** | fails AA |
| `--foreground` on `--accent` (**the label, after this task**) | `#060a08` | **17.7626** | passes AA |
| `--primary-text` solid on `--accent` (the counter **number**, unchanged) | `#177c52` | **4.6547** | passes AA |
| `--muted-foreground` on `--accent` (offered, not chosen) | — | 4.6684 | passes AA |
| (pre-APRAS-80, for the record) `indigo-600/80` over `indigo-50` | — | 4.0551 | already failed |

`--accent` is `#ecf4ef`. The failure is pre-existing; this task clears it
rather than repairing a regression.

### The operator's decision (answered; no longer open)

The first draft of this spec asked whether the label should stay branded at
4.6547 — 0.15 above the floor, on a token `build_theme` re-derives per tenant
with no cushion — or become `text-foreground`. **The operator answered
`text-foreground · 17.7626`.** So:

- the counter **label** (`:150`) becomes `text-foreground`;
- the counter **number** (`:147`) stays `text-primary-text`, exactly as the
  question framed the option — the counter stays visibly branded.

This is a legitimate §1k choice, not an exception: the label is a caption
rather than brand text, and §1k admits a neutral foreground token there. The
consequence is that this task's product edit is **not** the deletion of a
`/80` modifier as originally briefed — it is a class substitution on the same
line. Every result below is written to that shape.

### Residual, declared not hidden

4.6547 remains the tightest full-opacity brand-text pair in the tree, but
after this task it is no longer this label's number. It survives at
`GatekeeperDashboard:147` (the counter number, `text-2xl font-black` — large
text, whose §1k floor is 3:1, so it holds 1.65 of headroom there) and at
`AuthorizationFormModal:217,228` (normal text, where the 0.15 margin is real).
`--primary-text` is re-derived per tenant by `build_theme` with no cushion, so
a tenant brand can land that pair at exactly 4.50. That is APRAS-88's property
and is out of scope here; it is written down so a later reader does not
attribute it to this task.

### Interaction with the unlanded siblings — why this task is ordering-independent

Read at HEAD: `docs/tasks/APRAS-81-spec.md` (§ "no `text-primary-text/N` and no
`text-primary/N` anywhere", expected result on opacity carry-over),
`-82-` (same, plus "No `text-primary/N` and no `text-primary-text/N` is
produced anywhere"), `-83-`, `-84-` and `-85-` (all four state the identical
sentence, and each names the opacity modifiers it does carry over — all of them
`bg-*`, `border-*`, `divide-*` or `hover:bg-*`, never a `text-` brand class).
**None of APRAS-81…85 can create a site of this shape**, and each carries an
expected result that already forbids it.

`docs/tasks/APRAS-87-spec.md` converts 29 **bare** `text-primary` occurrences
to `text-primary-text`. Its match rule is `text-primary` not followed by
`[\w-]`, which *would* also match `text-primary/<n>` — but there is no
`text-primary/<n>` in the tree at HEAD, so APRAS-87 converts no opacity-bearing
class and creates no site of this shape either. Its effect on this task's sweep
is therefore **nil**. It does, however, rewrite
`GatekeeperDashboard.tsx:145` — the `<Users/>` glyph named in Out of scope
below — from `text-primary` to `text-primary-text`. That is APRAS-87's change,
not this task's, and it is why every statement this spec makes about that glyph
is written as an invariant over *this task's* diff (the glyph's class token is
whatever the tree holds when APRAS-90 starts, and APRAS-90 does not touch it)
rather than as a fixed tree state.

Consequently **no sibling must land before this task**, and this spec publishes
**no tree-wide count that a sibling landing first could falsify**. The
ordering-independent form is a test that re-runs the sweep against the tree as
it stands (Approach, item 4), not a frozen list.

### Out of scope

- Any change to `frontend/src/index.css` — not one property, not one value.
- Any palette class (`text-indigo-*`, `text-emerald-*`, `slate-*`, …) and any
  directory not yet migrated; APRAS-81…85 own those.
- Any **graphical** utility. §1k gives icons, borders, rings and every
  non-`text-` utility the 3:1 floor on `*-primary`; this task touches none of
  them. In particular `GatekeeperDashboard.tsx:145`'s `<Users/>` glyph
  (`text-primary` on `bg-accent`, 3.0427 at HEAD; `text-primary-text` once
  APRAS-87 lands) is left exactly as this task finds it, whichever of the two
  tokens it carries.
- Any neutral-token opacity (`text-muted-foreground/80`, `/50`, `/70`,
  `text-foreground/80`). They are not brand text on a brand tint and are not
  this task's subject.
- Amending `docs/frontend/theme-token-mapping.md` (§1i's unmeasured-alpha rule
  stands as written and is APRAS-78's property) or
  `docs/frontend/unmapped-colours.md`. `text-primary-text/80` is a **token**
  class, so the migration grammar never matched it: it has no ledger row and no
  entry in `themeTokenMigration.exceptions.json`, and neither file changes.
- Any backend file, Alembic revision or route-registry change.
- Raising `MIGRATED_DIRECTORIES`.

## Approach

**Behaviour.** The gatehouse counter label paints `--foreground` on
`--accent`, at 17.7626:1, while the counter number stays branded on
`--primary-text`. No brand-text-at-opacity site exists anywhere in the tree,
and none may be introduced without a declared, measured justification.

**Files touched.**

1. `frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx`
   — line 150 (the counter **label**): the class token `text-primary-text/80`
   becomes `text-foreground`. This is the whole product change: one class token
   substituted on one line, no element altered, and line 147 (the counter
   **number**, `text-primary-text`) untouched.
2. `frontend/src/lib/contrast.ts` — export the compositing helper
   (`compositeOver(foreground, background, alpha)`), moved **verbatim** from
   `visitorManagementContrast.test.ts`'s local `composite`, so the model APRAS-80
   established lives in exactly one place. No existing export changes; no
   arithmetic is reimplemented.
3. `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts`
   — delete the local `composite` and import `compositeOver`; move the
   `GatekeeperDashboard:150 counter label` entry out of `DECLARED_SUB_AA` (now
   three entries, all untouched-by-APRAS-80 palette pairs) and into `CLEARED`
   as `text-primary-text/80 -> text-foreground on bg-accent`, before 3.2883,
   after 17.7626, floor `MINIMUM_CONTRAST_RATIO`; adjust the two cases that
   hard-code `DECLARED_SUB_AA`'s length and its first, composited member.
4. `frontend/src/__tests__/brandTextOpacity.test.ts` — **new**, the
   ordering-independent guard. Node environment. It walks `frontend/src` for
   `.ts`/`.tsx` excluding `__tests__/` and `*.test.ts(x)`, matches
   `(?<![\w-])text-(?:primary-text|primary)/(\d{1,3})(?![\w-])` and
   `(?<![\w-])text-indigo-(?:50|[1-9]00|950)/(\d{1,3})(?![\w-])`, and asserts
   the match set equals a declared constant `PASSING_BRAND_TEXT_OPACITY`, an
   array **empty at this commit**. A site may only be added to that array
   together with its surface and its measured composite, and a second case
   asserts every entry's ratio is ≥ `MINIMUM_CONTRAST_RATIO` — which is how the
   contract's "leave opacity alone where the composite still clears the floor"
   survives without a silent exemption. Two further cases pin the numbers, both
   via `contrastRatio`/`parseOklch`/`compositeOver` over values read from
   `src/index.css`'s `:root` (never `.dark`, never a colour literal): the
   deleted composite (`--primary-text` at alpha 0.8 over `--accent`) measured
   3.2883 and was below the floor, and the replacement (`--foreground` on
   `--accent`) measures 17.7626 and is at or above it. Positive/negative control
   cases pin the grammar: it matches `text-primary-text/80` and
   `text-indigo-600/80`; it does not match `text-primary-text`,
   `text-primary-foreground`, `text-primary`, `bg-primary/10` or
   `text-muted-foreground/80`.
5. `frontend/src/__tests__/themeTokenMigration.test.ts` — remove the now-dead
   `"text-primary-text/80"` entry from the `MIGRATED_TARGETS` array in the
   status-set case. It is redundant even today (`"text-primary-text"` precedes
   it in the alternation and its `(?![\w-])` lookahead already admits a
   following `/`), so removing it changes no verdict; the file is otherwise
   untouched and the guard still passes.

**Test criteria.** `npx tsc -b` clean from `frontend/`;
`npx vitest run --coverage` green at 80 lines / 78 functions / 76 branches / 80
statements; `npx eslint .` with no new finding against the baseline of 375
errors + 2 warnings across 64 files, the five touched files contributing at
most the 2 errors present today (`GatekeeperDashboard.tsx`
`react-hooks/set-state-in-effect` at :52 and :60, which this task neither
causes nor may fix);
`src/__tests__/themeContrast.test.ts`,
`src/__tests__/themeTokenCompile.test.ts` and the visitor-management contrast
module all pass; no file under `backend/`, no Alembic revision, no route-registry
change.

## Expected Results

- [ ] In `frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx`, splitting every `className` string literal on `/\s+/` into class tokens (no substring matching anywhere in this result): the token `text-primary-text/80` does not appear anywhere in the file; inside the element whose token set contains `bg-accent`, the descendant whose token set contains `text-2xl` and `font-black` (the counter number) carries the token `text-primary-text`, and the descendant whose token set contains `text-xs` and `font-semibold` (the counter label) carries the token `text-foreground` and does not carry `text-primary-text`.
- [ ] The APRAS-90 commit's own diff for `frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx` — `git show --format= -- <that path>` on the commit, or `git diff <commit>^ <commit> -- <that path>` — contains exactly one removed line and one added line, and the removed line becomes the added line by replacing the single substring `text-primary-text/80` with `text-foreground` and changing nothing else on that line. (The repository configures no Prettier, so this line cannot be reflowed; it is 74 columns before the edit and 69 after.) No other line of that file appears in that diff.
- [ ] Over every `.ts`/`.tsx` file under `frontend/src/`, excluding `__tests__/` directories and `*.test.ts`/`*.test.tsx` files, matched by whitespace-split class token and not by substring, no token matches `text-primary-text/<digits>`, `text-primary/<digits>` or `text-indigo-<scale>/<digits>`. There is no permitted exception at this commit: the sweep's allow-list constant is empty.
- [ ] `frontend/src/lib/contrast.ts` exports a compositing helper taking a foreground `Oklch`, a background `Oklch` and an alpha, implemented as `oklchToHex` on both sides, an 8-bit per-channel mix, and `hexToOklch` back — the model APRAS-80 established — and `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts` imports it and declares no local compositing function of its own. Every other export of `contrast.ts` is unchanged.
- [ ] A new test file `frontend/src/__tests__/brandTextOpacity.test.ts` exists and passes. It re-runs the sweep above against the tree as it stands at run time — it reads no frozen list of files or sites — so a later commit that introduces a brand-text opacity class fails it.
- [ ] That test asserts, using `contrastRatio` and `parseOklch` imported from `frontend/src/lib/contrast.ts` over token values read out of `frontend/src/index.css`'s `:root` block and never out of `.dark`, and with no colour literal on either side: the deleted pair — `--primary-text` composited at alpha 0.8 over `--accent`, measured against `--accent` — is 3.2883 to ±0.001 and is strictly below 4.5; and the pair that replaces it on the counter label — solid `--foreground` on `--accent` — is 17.7626 to ±0.001 and is greater than or equal to 4.5.
- [ ] That test contains grammar control cases asserting the sweep pattern matches the strings `text-primary-text/80` and `text-indigo-600/80`, and does not match `text-primary-text`, `text-primary-foreground`, `text-primary`, `text-foreground`, `bg-primary/10` or `text-muted-foreground/80`.
- [ ] In `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts`, the `GatekeeperDashboard:150` counter-label pair is no longer an entry of `DECLARED_SUB_AA`, which now holds exactly three entries — the `AccessLogTimeline` `:59`, `:58` and `:98` pairs — and every one of those three still carries `published` equal to `publishedBefore`. The counter label instead appears in `CLEARED` with a `move` string naming `text-primary-text/80 -> text-foreground on bg-accent`, `publishedBefore` 3.2883, `publishedAfter` 17.7626 and floor `MINIMUM_CONTRAST_RATIO`. The separate pre-existing `CLEARED` entry named `GatekeeperDashboard:147 active-visitor counter` — the counter **number** — is unchanged and still carries `publishedAfter` 4.6547. The whole module passes.
- [ ] `frontend/src/__tests__/themeTokenMigration.test.ts` no longer lists the string `"text-primary-text/80"` anywhere, still lists `"text-foreground"` in the same `MIGRATED_TARGETS` array, and the file passes unchanged in every other respect.
- [ ] `frontend/src/index.css` is byte-identical to its state before the task, `docs/frontend/theme-token-mapping.md` and `docs/frontend/unmapped-colours.md` are byte-identical, and `frontend/src/__tests__/themeTokenMigration.exceptions.json` is byte-identical — both the class removed and the class added are token classes, so neither has a ledger row or an exception entry.
- [ ] No graphical utility changes. Measured as an invariant over this task's own commit diff, not over a fixed tree state: the line carrying `GatekeeperDashboard.tsx`'s `<Users/>` glyph does not appear in the APRAS-90 commit's diff at all, so whichever brand token that glyph holds when APRAS-90 starts — `text-primary` at HEAD, `text-primary-text` if APRAS-87 has landed first — it holds unchanged afterwards. In the same commit diff, no `border-*`, `ring-*`, `divide-*` or `bg-*` class token is added or removed in that file.
- [ ] `npx tsc -b` from `frontend/` exits 0, and `npx vitest run --coverage` passes with thresholds unchanged at 80 lines / 78 functions / 76 branches / 80 statements.
- [ ] `npx eslint .` from `frontend/` reports no new error or warning against the baseline of 375 errors + 2 warnings across 64 files, and the five files this task touches contribute at most the 2 errors present today — both `react-hooks/set-state-in-effect` in `GatekeeperDashboard.tsx`, at lines 52 and 60 — which this task neither causes nor fixes.
- [ ] No file under `backend/` is modified, no Alembic revision is added, and the route registry is unchanged.

## Mockup

`docs/tasks/APRAS-90-mock.html` **is** provided, and the reason is narrow. The
change is a one-token substitution, so there is no new layout, state or
interaction to review — but the question the operator had to answer was *how
does each candidate label colour read on a gatehouse tablet in daylight*, and
that is a question about the rendered pixels. The mock renders the counter card
at the exact measured hexes (`#429471` before, `#060a08` for the chosen
`text-foreground`, `#177c52` and `#627068` for the two rejected options, all on
`#ecf4ef`), labels each with its measured ratio, and carries a brightness
slider that simulates a washed-out daylight screen. It now records the
operator's decision rather than presenting it as open; the rejected options stay
on the page for context, marked as such.

## Operator decision (closed)

**Asked:** the repaired pair landed at 4.6547, 0.15 above the floor, on a token
a tenant brand can push to exactly 4.50 — make the caption `text-foreground`
instead of keeping it branded?

**Answered by the operator:** *"gostei da opção: text-foreground · 17.7626"*.
Folded into this spec: the label takes `text-foreground`, the number stays
`text-primary-text`. No open question remains on this task.
