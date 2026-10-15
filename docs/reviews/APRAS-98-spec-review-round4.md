# APRAS-98 — spec review, round 4 (findings-only)

Spec: `/Users/heitor/workspace/apras/docs/tasks/APRAS-98-spec.md`
Mock: `/Users/heitor/workspace/apras/docs/tasks/APRAS-98-mock.html`
Tree: `master` @ `2cb0d48`. Nothing staged, nothing under `frontend/` modified,
no file in the repo written except this report.

VERDICT: NEEDS_REVISION

## Scope of this round

Round-3's single blocking finding B10, plus a consistency pass limited to what
the generator changed to fix it: § Test criteria's second 3b observable, expected
result 4, § 2's default and its rationale, the mock's new `.dark` section, the
new § Guard `M2` paragraph, and result 8's note.

---

## 1. B10 — the replacement second observable. RESOLVED, and it is sound.

This is the fifth attempt at this assertion, so I did not assess the argument —
I executed both implementations. React **19.2.6** and `react-dom` **19.2.6** are
what is installed (`frontend/node_modules/react/package.json`).

**The trace.** I built both hooks against the real `react-dom/client` out of
`frontend/node_modules`, in jsdom 29.1.1, with `React.act` and
`IS_REACT_ACT_ENVIRONMENT = true`, differing only in the keydown effect's deps
array; the effect body is `ObraPrintDialog.tsx:41-70` transcribed. The harness
focuses an opener outside the panel, mounts open, moves focus to the panel's
**second** control, installs counting wrappers on
`document.addEventListener` / `document.removeEventListener` that pass through to
the originals and tally only `type === "keydown"`, re-renders with a fresh
`onClose` arrow and no interaction, then reads the counters and
`document.activeElement`.

| deps | keydown adds | keydown removes | activeElement after re-render |
|---|---|---|---|
| `[open]` (Decision 3b) | **0** | **0** | the second control |
| `[open, onClose]` (rejected) | **1** | **1** | the **first** control |

Both halves of result 4 therefore discriminate, measured rather than argued:
(b) separates 0/0 from 1/1, and (a) separates "the second control" from "the
first control".

Each of the four questions put to me, answered:

- **Does React run cleanup-then-setup on a deps identity change for a passive
  `useEffect`, in this version?** Yes, and in the same commit's passive phase —
  the 1/1 row is that behaviour observed, not inferred. Order is
  `removeEventListener` then `addEventListener`, so the *deltas* are 1 and 1 and
  never cancel to 0.
- **Is "after mount" early enough to miss the initial `addEventListener` and
  late enough to catch the re-render's?** Yes, in both directions, and the table
  proves both. The `[open]` row reading 0 adds is the proof the mount's own
  `addEventListener` was missed; the `[open, onClose]` row reading 1 add is the
  proof the re-render's was caught. The mechanism: RTL 16.3.2 wraps **both**
  `render` and `rerender` in `act` (`pure.js:180-220`, `renderRoot` calls
  `actCompat` on every path including the `rerender` closure), so passive effects
  are flushed before each returns. The mount's listener is installed before the
  spies exist; the re-render's teardown/setup both happen inside `rerender`'s
  `act`, before the assertion.
- **Can anything else add or remove a `keydown` listener in that window?** No,
  checked individually rather than assumed:
  - `focusTrap.ts` registers nothing — `focusableWithin` and `cycleTabWithin` are
    pure, there is no `addEventListener` in the module.
  - `alert-modal.tsx`'s effect (`:57-65`) is the only other document keydown
    listener in the app, and it requires `AlertModal` to be rendered and `open`;
    a hook unit test renders neither.
  - user-event 14.6.1's `prepareDocument` attaches exactly two document
    listeners, `'focus'` and `'blur'`
    (`dist/cjs/document/prepareDocument.js:15,28`) — **no** `keydown`, and the
    `"keydown"` filter excludes them regardless. Its only other
    `addEventListener` anywhere in `dist/cjs` is `input.addEventListener('fileDialog', …)`
    in `utility/upload.js`.
  - `src/test/setup.ts` installs no listeners (jest-dom matchers, a
    `localStorage` stub, a `react-i18next` mock) and configures no
    `reactStrictMode`; `vitest.config.ts` sets none either. So the "not under
    `<StrictMode>`" condition is the default here, not something the test must
    fight.
  - jsdom adds no document keydown listener of its own; portals and `.focus()`
    add none. The counters confirm it: the `[open]` row is 0/0, which could not
    hold if any third party were registering keydown in that window.
- **Is 0/0 versus 1/1 unreachable from the other side?** Yes. Under `[open]` the
  keydown effect's only dep is unchanged, so React does not re-run it; the
  ref-sync effect does re-run (its dep `onClose` changed) but touches no
  listener. Under `[open, onClose]` the deps did change, and the effect body
  removes exactly one keydown listener and adds exactly one. There is no third
  outcome available to either implementation short of a remount, which nothing
  here triggers.

Two implementation preconditions the spec already states and which the trace
depends on, worth keeping intact: the ref must be synced in its **own**
`useEffect` with `[onClose]` (a bare render-time assignment would also pass (b),
but it is forbidden by § Decision 3b) and the listener counting must filter on
`"keydown"`, since the ref-sync effect runs on exactly the re-render under test.

One non-blocking mechanical note: `renderHook`'s `TestComponent` returns `null`
(`pure.js`), so neither 3b test can use bare `renderHook` — both need a test
component that renders the panel. (a) already implies this; it is not a defect,
only a thing the implementer discovers.

## 2. The removed observable is recorded where QA sees it. CONFIRMED.

Expected result 4 ends: "Two phrasings may be asserted as extra cases but do
**not** count towards this result, because they pass under `[open, onClose]`
too: 'a later Escape invokes the new callback', and 'the re-render does not
re-capture the opener' (the alternative's cleanup restores focus to the opener
before its setup re-reads `document.activeElement`, so it re-captures the same
node)." Both demotions are inside the result, with the reason, so QA reading
only the results cannot credit either. § Test criteria carries the same
demotion in prose plus the removal note. This is the right shape.

## 3. Test (a) is unchanged. CONFIRMED.

Result 4(a) and § Test criteria's ordered recipe (mount open with ≥2 focusable
controls; move focus to a control that is **not** `focusableWithin(panel)[0]`;
assert that node by identity *first*; re-render with a new `onClose`; assert the
same node) are word-for-word the version approved in round 3 (round-3 report
§ 2, "Test (a) now discriminates — this is a real fix"). No drift.

## 4. § Guard's `M2` paragraph. CONFIRMED, and true.

The spec (§ The guard test) says `M2` "deliberately does not match
`focusTrap.ts:39` itself", because the argument is an identifier so the argument
text contains no `tabindex`; that the positive control exercises `M1` only; and
that "`M2` is unproven over the real tree … a forbid-only matcher whose regex has
never fired against a real file". All three are stated, and all three are true.
Executed over the live tree:

- 268 `.ts`/`.tsx` files under `frontend/src` excluding `__tests__/` — well past
  the `>20` the positive control asserts.
- `M1` (`/\bFOCUSABLE_SELECTOR\b/`) matches **exactly one** file,
  `src/features/project-management/lib/focusTrap.ts` (which becomes
  `src/lib/focusTrap.ts`).
- `M2` (`/querySelectorAll\s*(<[^>]*>)?\s*\([^)]*tabindex/i`) matches **zero**
  files — including with `__tests__/` back in the sweep. Note why it is silent on
  line 39 even on a whole-file scan: the `tabindex` text lives at lines 34-35, in
  the constant's definition, i.e. *before* the `querySelectorAll`, and the call's
  own parentheses close immediately after `FOCUSABLE_SELECTOR`, so `[^)]*` cannot
  reach any `tabindex`.
- `skipcq: JS-R1005` occurs in exactly one file, the same one.

## 5. Mock § 3 (dark) and the one-letter answer. Sound.

The dark section is framed "Not a separate question — the answer to § 2 applies
to both themes", only **A** and **B** carry letter badges, and the third panel
carries a `✕` badge, the heading "What `button.tsx` writes today" and the caption
"Not shipped by this spec; shown for contrast." It **clarifies**: it is the only
place the reader can see what the spec's `ring-offset-card` improvement is an
improvement *over*, and it cannot be mistaken for a third option. § 2's panels
are now badged "alternative" (A) and "spec default" (B), which makes the moved
default visible on the screen rather than only in the prose. The question stays
answerable with one letter.

The `.dark` token values are per-token exact. All twelve declarations the mock
carries — `--background`, `--foreground`, `--card`, `--muted`,
`--muted-foreground`, `--input`, `--border`, `--destructive`,
`--destructive-foreground`, `--primary`, `--primary-foreground`, `--ring` —
match `src/index.css:90-115` character for character. The block is a *subset*
(it omits `--card-foreground`, `--popover`, `--popover-foreground`,
`--primary-text`, `--secondary`, `--secondary-foreground`, `--accent`,
`--accent-foreground` and the `--primary-text` comment), which the word
"VERBATIM" oversells; see Suggestions. No value is wrong.

The **figures** printed beside those tokens are a different matter — finding B11.

## 6. Result 8's conditional. Sufficient, with a caveat.

Both branches of the disjunction are exact, complete class lists, so QA holding
only the results can decide pass/fail against the diff: the two buttons carry one
of the two named lists. It is weaker than an unconditional criterion but it is
not unverifiable, and the note telling the recorder to collapse it lives *inside*
the result where QA sees it. Not a blocking finding. The residual risk is only
that an unanswered § 2 lets a sloppier choice pass — bounded, because both
branches are compliant and B is the default.

---

## 7. B11 — the contrast figures are derived by the clip the repo forbids.

Round 3 verified the light figures and recorded the method: "oklch → linear sRGB
→ WCAG relative luminance". That is a **naive per-channel clip**, and it is
precisely the defect `src/lib/contrast.ts`'s own rule 2 exists to prevent:

> 2. **Out-of-gamut colours are chroma-reduced, never clipped.** CSS Color 4 §13
>    requires a browser to gamut-map an out-of-range `oklch()` by reducing chroma
>    at constant lightness and hue. A naive per-channel clip is a *different
>    colour*.

Both `--ring` values are **out of gamut** (`isInGamut(oklch(0.62 0.15 160))` =
false; same at `0.65`), as is the light `--destructive`, so the distinction bites
on every figure in this spec.

I ported `contrast.ts`'s `gamutMap` + `relativeLuminance` and **validated the
port against the repository's own cross-language contract**,
`backend/tests/data/contrast_fixtures.json` — all 8 cases within the file's
`tolerance` of 0.01, including the two out-of-gamut cases the file's own comment
says exist to fail a clipping port ("a port that clips per channel where the
browser reduces chroma gets 4.52 where this file says 3.74"). Then:

| pair | spec / mock claim | naive clip | **gamut-mapped (correct)** |
|---|---|---|---|
| light `--ring` on `--card` | 3.3564 / "3.36:1" | 3.3564 | **3.4054** |
| light `--ring` on `--destructive` | 1.4252 / "1.43:1" | 1.4252 | **1.4117** |
| dark `--ring` on `--card` | 6.4408 / "6.44:1" | 6.4408 | **6.4180** |
| dark `--ring` on `--destructive` | 1.8085 / "1.81:1" | 1.8085 | **1.8021** |
| light `--ring` → hex | `#00a166` | `#00a166` | **`#009f68`** |
| light `--destructive` → hex | `#e60016` | `#e60016` | **`#e60018`** |

All four claimed figures reproduce the clip column exactly, to four decimals.
That is not coincidence — it identifies the method, and it means the generator's
"independent re-derivation" reproduced the same wrong method rather than
confirming the numbers.

Two independent corroborations that the right-hand column is the repository's
own answer:

- **`docs/tasks/APRAS-87-spec.md:23`**, under the heading "Re-derived at HEAD, by
  importing `frontend/src/lib/contrast.ts` and never reimplementing it", records
  the identical colour pair: "`--primary` `oklch(0.62 0.15 160)` → **`#009f68`**
  … on `--card`: **3.4054**". APRAS-98 says `#00a166` and 3.3564 for the same two
  colours. Two specs in `docs/tasks/` now disagree about one number.
- **`#009f68`** is the hex the whole repository uses for this colour:
  `backend/tests/test_branding.py:370,372,481,483` and the mocks of APRAS-82,
  -84, -87, -88 and -90. `#00a166` appears nowhere except APRAS-98's spec and
  mock.

**Why this blocks, and what it does *not* block.** No decision changes: 3.4054
still clears the 3:1 floor (with slightly more margin than claimed), 1.4117 is
still a vanishing edge, and § 2's default-B rationale stands untouched. The mock
also *paints* correctly, because browsers gamut-map the real `oklch()` strings it
declares. What is wrong is the **stated evidence**: a spec that publishes
contrast numbers for a compliance claim ("just over the 3:1 WCAG 1.4.11 floor"),
by the one method this repository has a cross-language fixture file to forbid,
and prints a hex that contradicts a backend test fixture and five sibling
documents, is wrong in the part the operator and every later reader will quote.
The fix is textual and mechanical: five numbers, two hexes, in the spec
(§ Decision 4, lines 146-147 and 158-161) and the mock (header swatch, § 2 prose,
§ 3 prose and the § 3 panel headings). Re-derive by importing
`src/lib/contrast.ts` as APRAS-87 did, not by hand.

## 8. B12 — the mock's § 1 "After" caption still names A as the spec's pick.

§ 1's After panel reads: "`focus-visible:outline-none focus-visible:ring-2
focus-visible:ring-ring` — shown here in **the spec's current pick, option A of
section 2**." The default moved to B this round, and § 2 now says "The spec now
picks **B**" with B badged "spec default". The operator meets the stale sentence
first and the correct one second, on the one screen whose purpose is a one-letter
answer. Introduced by this round's fix, and a one-sentence repair: either relabel
it as "option A, the alternative — see § 2" or render the After panel with
`.ring-b`.

---

## Blocking Findings

- **B11 — every contrast figure in the spec and the mock is computed by the
  per-channel clip that `src/lib/contrast.ts` rule 2 and
  `backend/tests/data/contrast_fixtures.json` exist to forbid, and the light
  `--ring` hex contradicts the rest of the repository.** Both `--ring` values are
  out of gamut, so the clip is a different colour. Gamut-mapped, by a port
  validated against all 8 fixture cases including the two anti-clipping ones:
  light ring on card is **3.4054** not 3.3564; light ring on destructive
  **1.4117** not 1.4252; dark ring on card **6.4180** not 6.4408; dark ring on
  destructive **1.8021** not 1.8085; the light ring is **`#009f68`** not
  `#00a166`, and the light destructive **`#e60018`** not `#e60016`.
  `docs/tasks/APRAS-87-spec.md:23` already publishes `#009f68` and `3.4054` for
  the identical pair, derived by importing `contrast.ts`, and `#009f68` is the
  value in `backend/tests/test_branding.py:370` and in four sibling mocks — so
  APRAS-98 currently contradicts a sibling spec and a backend fixture. No
  decision in § 2 changes (3.4054 still clears 3:1; 1.4117 is still a vanishing
  edge), so do not re-litigate the default — correct the five figures and the two
  hexes in § Decision 4 (lines 146-147, 158-161) and in the mock (header swatch,
  § 2 prose, § 3 prose, § 3 panel headings), re-derived by importing
  `src/lib/contrast.ts` rather than by hand.

- **B12 — the mock's § 1 "After" caption still calls option A "the spec's current
  pick", which § 2 now contradicts.** The default moved to B this round; § 2 says
  "The spec now picks B" and badges B "spec default", while § 1 tells the operator
  A is the current pick, on the same page as the one-letter question. Relabel it
  as the alternative with a pointer to § 2, or render the After panel with
  `.ring-b`.

## Suggestions

- The mock's two "copied VERBATIM from `src/index.css` (lines 32-66 / 90-115)"
  comments describe a *selective* copy: `.dark` carries 12 of the block's 21
  declarations (`--card-foreground`, `--popover`, `--popover-foreground`,
  `--primary-text`, `--secondary`, `--secondary-foreground`, `--accent`,
  `--accent-foreground` are absent), and `:root` likewise. Every value present is
  exact, so nothing is wrong — but "the tokens this mock uses, copied verbatim
  from …" would stop a future reader believing the block is complete and
  reasoning about a token that is not there.
- § Test criteria's 3b tests cannot use bare `renderHook`: RTL's
  `TestComponent` renders `null`, so there is no panel. Both need a small test
  component that renders the panel and calls the hook. Worth one clause, since
  (a)'s premise is "at least two focusable controls in the panel".
- `src/test/setup.ts` and `vitest.config.ts` set no `reactStrictMode` and
  register no document listeners, so "must not wrap the hook in `<StrictMode>`"
  is the default rather than something to arrange. Saying so would keep an
  implementer from adding a defensive opt-out.
- Result 8's disjunction is mechanically checkable (two exact class lists), so it
  is not a gate failure — but collapsing it the moment § 2 is answered remains
  the right move, and the note inside the result is the right place for the
  instruction.
