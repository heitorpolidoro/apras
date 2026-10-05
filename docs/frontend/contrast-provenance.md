# Colour provenance

Where a colour figure in this repository is allowed to come from, and what the
figures currently are.

This page exists because of a specific failure, not as a style preference.
Across five review rounds of APRAS-98, three agents in a row converted an
`oklch()` value to a hex by clipping each sRGB channel into `[0, 1]`, each
reported the result as independently re-derived, and a reviewer blessed it. The
correct values were already published elsewhere in the tree at the time. Three
passes reproducing the same wrong method is not three checks: **independence of
agent is not independence of method.**

## The convention

> `frontend/src/lib/contrast.ts` is the only permitted source of a colour
> figure in this repository. A document that quotes a hex or a ratio records
> **how** it was derived — the function called and the input given — so a
> reader can tell a measurement from a recollection. A figure with no recorded
> provenance is a recollection and may not be relied on. A per-channel sRGB
> clip is not an approximation of the gamut map; it is a different colour.

CSS Color 4 §13 requires a browser to bring an out-of-range `oklch()` into sRGB
by reducing chroma at constant lightness and hue, not by clipping channels.
`contrast.ts` does that — `gamutMap` bisects chroma and clips only once the
remaining OKLab error is under the just-noticeable difference — and
`backend/app/core/branding.py` does the same thing in Python, pinned against
`backend/tests/data/contrast_fixtures.json`. A clip reaches a different colour,
and in a contrast ratio it moves the second decimal, where no reader can see
it.

### How to quote a figure this module does not produce

One sentence, and it is the whole rule: **to quote a figure `contrast.ts` does
not produce, write it with `≠`, or suppress the claim with an anchored
`<!-- contrast-guard: ignore — reason -->` line (which also means editing the
exact list in `frontend/src/__tests__/docsColourProvenance.test.ts`), and never
place either marker alone on a line when you are documenting the marker rather
than using it.** The guard's connector set is equality-only, so `≠` is both true
prose and mechanically inert; and both markers are detected on the raw line, so
an occurrence with prose beside it — like the one in the previous clause — is
documentation and is ignored.

The ratio marker's template, documented here the same way, is
`<!-- ratio: oklch(L C H) on oklch(L C H) = N.NNNN -->`: one HTML comment alone
on its line, both operands literal so no token resolution is needed, and the
figure at exactly four decimal places. `frontend/src/__tests__/docsColourProvenance.test.ts`
re-derives every anchored occurrence with `contrastRatio` and compares
`derived.toFixed(4)` for string equality. A marker whose operands do not parse
fails the suite naming its file and line; it is never skipped.

**Ratios written in prose are not guarded.** A ratio appears as `3.4054`, as
`3.41:1`, as `≥ 4.5:1`, as a bare table cell and as a bold figure mid-sentence,
with its two operands named by token, by hex, by `oklch()` string or by role, in
either order and often in another clause. Locating those mechanically needs a
token-resolution engine for both blocks of `index.css`, which is a separate
deliverable. Until it exists, only the marked ratios below are checked and the
convention above covers the rest.

## The three published hexes

Each is written as a connector claim so the guard re-derives it from the
`oklch()` beside it:

- light `--primary` and light `--ring`, `oklch(0.62 0.15 160)` → `#009f68`
- light `--destructive`, `oklch(0.58 0.24 27)` → `#e60018`
- dark `--primary`, `--primary-text` and `--ring`, `oklch(0.65 0.15 160)` → `#00aa6f`

The clip method reaches `oklch(0.62 0.15 160)` ≠ `#00a166` and
`oklch(0.58 0.24 27)` ≠ `#e60016`. Those two are the values that were published
by mistake, and they are written here with `≠` on purpose.

### Agreement is not evidence of method

Dark `--ring` is the trap. `oklch(0.65 0.15 160)` paints `#00aa6f` under the
gamut map **and** under the clip: the two methods coincide there. One figure in
APRAS-98's mock was therefore right by accident while every figure around it was
wrong, and a reader who spot-checked that one would have concluded the method
was sound. **A hex that agrees tells you nothing about how it was obtained** —
only the recorded derivation does.

## The four marked ratios

Measured with `contrastRatio` on the values `frontend/src/index.css` declares.
Each marker below is re-derived by the guard on every run.

Light `--ring` on `--card`:

<!-- ratio: oklch(0.62 0.15 160) on oklch(1 0 0) = 3.4054 -->

Light `--ring` on `--destructive`:

<!-- ratio: oklch(0.62 0.15 160) on oklch(0.58 0.24 27) = 1.4117 -->

Dark `--ring` on `--card`:

<!-- ratio: oklch(0.65 0.15 160) on oklch(0.16 0.01 160) = 6.4180 -->

Dark `--ring` on `--destructive`:

<!-- ratio: oklch(0.65 0.15 160) on oklch(0.55 0.22 25) = 1.8021 -->

For the same four pairs the clip method reports 3.3564, 1.4252, 6.4408 and
1.8085. Those four figures are wrong; they are quoted outside any marker so
this page does not fail on them, and they are listed because each differs from
the correct value only in the second decimal.

## The out-of-gamut inventory

These are the only tokens where a clip and a gamut map can differ at all: the
`oklch()` declarations in `frontend/src/index.css` for which `isInGamut` is
false, each painted with `oklchToHex`. **This table is the authoritative copy.**
`frontend/src/__tests__/docsColourProvenance.test.ts` parses it out of this file
and asserts set equality against `index.css`, so a token added, moved out of
gamut or repainted turns CI red until this table is updated here. The test holds
no copy of these rows.

| block | token | oklch | hex |
|---|---|---|---|
| `:root` | `--primary` | `oklch(0.62 0.15 160)` | `#009f68` |
| `:root` | `--destructive` | `oklch(0.58 0.24 27)` | `#e60018` |
| `:root` | `--ring` | `oklch(0.62 0.15 160)` | `#009f68` |
| `:root` | `--status-pending-bg` | `oklch(0.96 0.05 85)` | `#fff0d1` |
| `:root` | `--status-pending-fg` | `oklch(0.5 0.12 85)` | `#7e5d00` |
| `:root` | `--status-in-progress-bg` | `oklch(0.93 0.06 240)` | `#ceedff` |
| `:root` | `--status-in-progress-fg` | `oklch(0.4 0.15 240)` | `#004d7d` |
| `:root` | `--status-blocked-bg` | `oklch(0.95 0.08 70)` | `#ffebd2` |
| `:root` | `--status-blocked-fg` | `oklch(0.5 0.15 70)` | `#8b5600` |
| `:root` | `--status-completed-bg` | `oklch(0.94 0.1 160)` | `#b3ffd6` |
| `:root` | `--status-completed-fg` | `oklch(0.4 0.15 160)` | `#005931` |
| `:root` | `--status-canceled-bg` | `oklch(0.95 0.04 20)` | `#ffe7e6` |
| `:root` | `--priority-medium-fg` | `oklch(0.38 0.1 210)` | `#004d58` |
| `:root` | `--priority-high-bg` | `oklch(0.95 0.08 70)` | `#ffebd2` |
| `:root` | `--priority-high-fg` | `oklch(0.5 0.15 70)` | `#8b5600` |
| `:root` | `--priority-urgent-bg` | `oklch(0.94 0.1 25)` | `#ffdfda` |
| `.dark` | `--primary` | `oklch(0.65 0.15 160)` | `#00aa6f` |
| `.dark` | `--primary-text` | `oklch(0.65 0.15 160)` | `#00aa6f` |
| `.dark` | `--ring` | `oklch(0.65 0.15 160)` | `#00aa6f` |

Nineteen rows: sixteen in `:root` and three in `.dark`.

### The missing `--status-canceled-fg` is not a miscount

The table has five `--status-*-bg` rows but only **four** `--status-*-fg` rows,
and that asymmetry is real. `--status-canceled-fg: oklch(0.5 0.15 20)` is **in**
gamut, while the structurally identical `--status-blocked-fg:
oklch(0.5 0.15 70)` is **out**. At lightness 0.5 and chroma 0.15, hue 20 sits
inside sRGB while hues 70, 160 and 240 do not — the hue alone flips it. Adding a
`--status-canceled-fg` row here to "restore the symmetry" breaks the set
equality against `index.css` and fails the suite, which is the intended
outcome.

## The one named exception

`frontend/src/__tests__/themeContrast.test.ts` is a deliberate second oracle for
the stylesheet (APRAS-76). It does not import `contrast.ts`, because an
independent implementation is what makes its green run evidence, and it reduces
chroma on a 0.01 grid rather than by bisection. It therefore reports
`oklch(0.62 0.15 160)` ≠ `#019f68`, and 3.4078 where `contrast.ts` derives
3.4054 — a grid artefact, not a clip.

That file is **not** a source for a published figure. If a figure here ever
disagrees with it, `contrast.ts` wins and the difference belongs in this
section.
