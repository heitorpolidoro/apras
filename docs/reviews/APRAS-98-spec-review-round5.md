# APRAS-98 — spec review, round 5 (findings-only, final round before the cap)

Verdict: **APPROVED**. No blocking findings.

Reviewed: `docs/tasks/APRAS-98-spec.md`, `docs/tasks/APRAS-98-mock.html` at `2cb0d48`.
Mode: findings-only re-review of B11 and B12, plus the requested independent
sweep and a final whole-document pass. Nothing under `frontend/` was modified;
the verification script lives only in the session scratchpad.

## B11 — provenance half

The spec's "Where every ratio and hex in this section comes from" paragraph
(spec:150-165) does three things that the earlier drafts did not: it names the
exact entry points (`parseOklch`, `contrastRatio`, `oklchToHex`), it names the
*source of the inputs* (the literal `oklch()` strings in `src/index.css`), and
it states the failure mode concretely — both `--ring` values are out of gamut,
so the per-channel clip `contrast.ts` rule 2 forbids yields a different colour
and therefore different digits. It then anchors the figures to three
independent, already-committed artefacts. I checked all three citations:

- `docs/tasks/APRAS-87-spec.md:142` publishes `3.4054` for `--primary`
  (`oklch(0.62 0.15 160)`) on `--card`, and its line 23 publishes `#009f68`
  for the same colour. Both present, both matching.
- `backend/tests/test_branding.py:370` uses `#009f68`. Present.
- `#009f68` appears in 8 files under `docs/tasks/` (the spec claims "six sibling
  mocks" plus APRAS-87 — consistent).

The mock carries the same method note in its own `<style>` comment, including the
per-channel-clip warning, so a future author editing the mock alone also meets
it. That is the part that matters: the recurrence happened in the *mock's* hex
comments as much as in the spec prose.

Judgement: the provenance half is closed **for this task**. The paragraph is
more than an exhortation — it is a reproducible recipe plus three cross-checks a
reader can run without re-deriving anything. What prose cannot do is stop the
next *new* mock from repeating the method error, and that is not a hole in
APRAS-98's deliverable: a mechanical criterion here would have to be a test that
parses hex comments out of `docs/tasks/*-mock.html` and re-derives them through
`contrast.ts`, which is a separate guard task of the
`themeContrast.test.ts` / `brandTextOpacity.test.ts` family and plainly outside
a dialog-focus task. Recorded as a suggestion, not a finding.

## B11 — the figures not in last round's list (checked, not trusted)

I copied `frontend/src/lib/contrast.ts` to the scratchpad and ran every token
the mock declares through `oklchToHex`/`isInGamut`/`contrastRatio` with
Node 24's native type stripping. Every mock hex comment is correct:

| token | value | hex | gamut |
| --- | --- | --- | --- |
| light `--background` | `oklch(0.99 0 0)` | `#fcfcfc` | in |
| light `--foreground` | `oklch(0.14 0.01 160)` | `#060a08` | in |
| light `--card` | `oklch(1 0 0)` | `#ffffff` | in |
| light `--muted-foreground` | `oklch(0.53 0.02 160)` | `#627068` | in |
| light `--input` | `oklch(0.92 0.01 160)` | `#dfe7e2` | in |
| light `--destructive` | `oklch(0.58 0.24 27)` | `#e60018` | **out** |
| light `--ring`/`--primary` | `oklch(0.62 0.15 160)` | `#009f68` | **out** |
| dark `--card` | `oklch(0.16 0.01 160)` | `#0a0f0c` | in |
| dark `--destructive` | `oklch(0.55 0.22 25)` | `#d40924` | in |
| dark `--ring`/`--primary` | `oklch(0.65 0.15 160)` | `#00aa6f` | **out** |

Ratios: light ring/card `3.4054`, light ring/destructive `1.4117`, dark
ring/card `6.4180`, dark ring/destructive `1.8021`. The mock's rounded forms
(3.41, 1.41, 6.42, 1.80) are the correct roundings. The generator's note that
the dark ring is out of gamut while its published hex happens to equal the
gamut-mapped value is confirmed (`#00aa6f`). The generator's sweep was accurate;
no eleventh-hour defect survives in the hex comments.

I also verified the mock's token block is a faithful selective copy: all 12
light and all 12 dark declarations are byte-identical to `src/index.css`
(`:root` 32-66, `.dark` 90-115, both line ranges as cited), and no stale value
(`3.3564`, `1.4252`, `6.4408`, `1.8085`, `00a166`, `e60016`) occurs in either
file.

## B12 — the §1 caption

Resolved. The "After" caption now reads: drawn in the **option A** form (ring
flush), A is the *alternative*, the spec's default is **B**, see § 2. The panel
renders `.ring-a`, so words and picture agree, and §2's "spec default" badge on
B is consistent with it. An operator reading §1 first is told the default before
being shown the picture and is pointed at the section that asks the question, so
the misleading reading B12 named is gone. One residual cosmetic mismatch — the
panel labelled "After" shows the form the spec is *not* defaulting to — is a
suggestion below, not a finding: the caption pre-empts it in the same breath.

## Whole-document pass

Every line-number and factual claim I could cheaply check holds at `2cb0d48`:

- `TenantProfilePage.tsx`: dialog 418-468; scrim at 419; panel div at 425 with
  exactly the quoted `className`; Cancel `<button>` at 447 / `className` 450;
  confirm at 454 / `className` 457; early return at 107; `submit` at 157 with
  `setConfirming(false)` then `update.mutate`; Save disabled at 394-396 via
  `update.isPending`; no `focus-visible:` class on either dialog button today.
- `ObraPrintDialog.tsx`: effect 41-70 with deps `[open, onClose]`, the
  `return undefined` comment citing JS-0045, opener capture 51-54, restore in
  cleanup at 68, `../lib/focusTrap` import at line 6, docstring 19-25 claiming
  the behaviour as the component's own.
- `focusTrap.ts`: `FOCUSABLE_SELECTOR`, `focusableWithin`, `cycleTabWithin`
  exported; `querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)` at line 39, so
  `M2` is indeed silent there as the spec insists; the single
  `// skipcq: JS-R1005` at line 52 and nowhere else under `src`; the test names
  `FOCUSABLE_SELECTOR` at its lines 17 and 76 and imports `../lib/focusTrap`.
- `alert-modal.tsx`: Escape effect at 57-65, not exported; the three-class ring
  at line 115.
- `button.tsx:7` and `GeneralDashboardPage.tsx:162` both carry a bare
  `focus-visible:ring-offset-2` with no offset colour; `ring-offset-color","#fff"`
  is literally present in the installed `tailwindcss@4.2.4`
  (`dist/lib.js`), so the white-seam argument for `ring-offset-card` is sound.
- `focus-visible:ring-2 focus-visible:ring-ring` occurs in 9 files — the spec's
  "nine places" — including `PublicObrasReportPage.tsx:102`.
- `contrast.ts:59` is the comment excluding `ring` from the measured pairs, as
  cited; `ring` is absent from `MEASURED_PAIRS`.
- `brandTextOpacity.test.ts:92-111` is the `__tests__`-excluding tree walk the
  guard is modelled on; `themeTokenMigration.exceptions.json` is a JSON array of
  objects with `file`/`task` keys, so the proposed
  `{file, matcher, reason, task}` shape is a real sibling pattern.
- `vitest.config.ts` thresholds are 80/78/76/80, matching result 10; coverage
  `include: ["src/**/*"]`, so the move is measured as before.
- `AGENTS.md:422-423` is the `lib/ — Generic utility functions` entry the move
  relies on.

The result list is 10, in English, each mechanically checkable by someone
holding only the list: every focus claim names a node by identity, the guard
result enumerates its four assertions and the exact regex, the class result
enumerates the exact class list, and result 10 names commands with thresholds
and the "no worse than measured baseline" lint form. Result 4's two observables
are both stated in a form that fails against the rejected `[open, onClose]`
implementation, and the two non-discriminating phrasings are explicitly excluded
from counting. Result 8's A/B disjunction is the one conditional, and it carries
its own instruction to collapse to a single unconditional class list once the
operator answers — the same shape earlier rounds accepted.

Nothing blocking. The spec is clean.

## Suggestions (non-blocking)

1. The durable fix for the B11 class of defect is not prose in one spec. Either
   add a short rule to `AGENTS.md` ("any contrast ratio or hex published in a
   spec, mock or token comment is produced by importing
   `frontend/src/lib/contrast.ts`; a per-channel clip is forbidden") or file a
   guard task that re-derives hex comments in `docs/tasks/*-mock.html` through
   `contrast.ts`, in the family of `themeContrast.test.ts`. Out of scope for
   APRAS-98.
2. Mock §1: once the operator answers, re-draw the "After" panel in the chosen
   form (`.ring-b` if B stands) so the picture labelled "After" is the thing
   that ships. Harmless today because the caption says which form it is.
3. Mock §1 caption could name the two forms the way the operator sees them
   ("ring touching the button" / "ring with a thin gap") rather than only
   "option A"/"option B", matching §2's plain-language framing.
