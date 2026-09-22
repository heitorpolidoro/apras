# APRAS-76 — Fix the default theme's muted text contrast, which is below WCAG AA

## Scope

Repair every text/background pair declared in `frontend/src/index.css` that
measures below the WCAG 2.1 AA minimum of **4.5:1** for normal text, in the
light (`:root`) block and the `.dark` block, and pin the whole set with a test
that derives the pairs from the file itself.

The full sweep found **two** failing pairs, both in the light block. The one on
the board is real and confirmed; the second was found by this sweep and is
worse:

| block | pair | measured today | after |
|---|---|---|---|
| light | `--muted-foreground` on `--muted` | **4.2913** | **4.6684** |
| light | `--primary-foreground` on `--primary` | **3.2169** | **5.7548** |

Everything else passes: the 17 other light pairs (worst `--destructive-foreground`
on `--destructive`, 4.5425) and all 19 dark pairs (worst `--muted-foreground`
on `--muted`, 5.3726).

**Not in scope**: any component markup, any Tailwind class, any backend file,
`app/core/branding.py` and APRAS-68's white-label derivation. See *Out of Scope*
for the two accessibility findings deliberately left for another task.

## Approach

### Behavior

**1. Two token values change in `frontend/src/index.css`, in `:root` only.**

- `--muted-foreground: oklch(0.55 0.02 160)` → `oklch(0.53 0.02 160)`.
  Measured after the fix: **4.6684** on `--muted`, **5.0771** on `--background`,
  **5.2249** on `--card` (`--secondary` and `--accent` are byte-identical to
  `--muted`, so they are covered by the same number). `0.54` is **not**
  sufficient — it measures **4.4754** on `--muted` — so the emitted value must
  be `0.53`. This is the same landing value APRAS-68's repair loop reaches for
  hue 160, which is what makes a branded and an unbranded tenant agree.
- `--primary-foreground: oklch(0.98 0 0)` → `oklch(0.15 0.02 160)`.
  Near-white on the emerald `--primary` is **3.2169**; the dark candidate is
  **5.7548**. `--primary` itself does **not** move: `oklch(0.15 0.02 H)` is
  exactly the foreground APRAS-68's "better of `oklch(0.98 0 0)` and
  `oklch(0.15 0.02 H)`" rule picks for this hue, so a tenant that brands with
  the shipped emerald gets the same rendering as an unbranded one. The rejected
  alternative — darkening `--primary` to `oklch(0.52 0.15 160)` and keeping
  white text (4.9178) — was rejected precisely because it would *create* the
  branded/unbranded divergence this task exists to remove, and it changes the
  product's brand colour. `text-primary-foreground` appears in the codebase
  only ever together with a full-opacity `bg-primary`, so nothing else is
  affected; on the `hover:bg-primary/90` state the surface gets lighter, which
  moves a dark foreground further from the threshold rather than nearer.
- `.dark` is **not edited**: every dark pair already passes, including
  `--primary-foreground` `oklch(0.1 0.02 160)` on `--primary` at 6.7821. A
  passing pair is left alone.
- Each changed line carries a short CSS comment naming the constraint and the
  test that enforces it, so the next palette edit is warned in place.

**2. One new test enumerates the pairs from `index.css` itself.**

It reads the file with `node:fs`, parses `--name: oklch(L C H)` declarations out
of the `:root` and `.dark` blocks, and builds the dark scheme as
`{...root, ...dark}` — the cascade, so the status/priority tokens declared only
in `:root` are measured in both schemes. Pairs are then **derived by naming
convention**, never listed:

- `--foreground` ↔ `--background`; every other `--X-foreground` ↔ `--X`;
- every `--Y-fg` ↔ `--Y-bg` (the nine status/priority badge pairs);
- plus `--muted-foreground` against `--background` and `--card`, the two
  surfaces muted text is actually rendered on.

A token ending in `-foreground` or `-fg` whose partner is absent **fails the
test** naming the token, so a token added later cannot dodge enumeration; the
test also asserts both blocks were found and that at least 19 pairs were derived
per scheme, so a parser that silently matches nothing fails loudly.

**3. The measurement, stated because two of its steps each cost APRAS-68 a
review round.** The test owns its own ≈40-line implementation — deliberately
**not** importing any production module, so it is an independent oracle of the
file it guards (APRAS-68 separately creates `frontend/src/lib/contrast.ts`;
neither task depends on the other, and whichever lands second may unify them
later).

1. OKLCH → OKLab → **linear** sRGB (Ottosson matrices).
2. Relative luminance `0.2126R + 0.7152G + 0.0722B` is computed **directly on
   those linear channels**. Applying the sRGB→linear transfer a second time is
   the trap: it *inflates* light-on-light ratios (the broken pair reads 10.9585
   instead of 4.2913) and would make every illegible palette pass.
3. Gamut mapping, at the emitted 2 dp precision: the values **parsed out of
   `index.css`** are rounded to 2 decimal places — a no-op in practice, since
   every authored value in the file is already at or below 2 dp, so it only
   guards a future 3 dp edit — and chroma is then reduced on the 0.01 grid at
   constant `L`/`H` until all three linear channels are within `[0, 1]`
   (tolerance 1e-4), which is what CSS Color 4 §13 requires a browser to do.
   This is not academic here: `--primary` `oklch(0.62 0.15 160)` is **out of
   gamut** and is painted as `oklch(0.62 0.14 160)` = `#019f68`; measuring the
   unmapped value measures a colour no browser shows.
   **The rounding and the grid belong to this step only — the raw OKLCH →
   linear sRGB converter of step 1 must round nothing and must map no gamut**,
   so that the oracle can call it on arbitrary-precision input: rounding
   `oklch(0.628 0.2577 29.23)` to 2 dp yields linear
   `(1.0149, -0.0017, -0.0009)`, which misses the ±1e-3 pin below by an order
   of magnitude and is itself out of gamut. If that pin fails, the matrices or
   the transfer are wrong; the tolerance is not to be loosened.
4. WCAG 2.1 ratio `(Lhi + 0.05) / (Llo + 0.05)`, minimum **4.5**, with the
   failure message naming scheme, both tokens and the ratio at 4 dp.

### Files touched

- `frontend/src/index.css` — two `:root` values (`--muted-foreground`,
  `--primary-foreground`) plus their explanatory comments. Nothing else.
- `frontend/src/__tests__/themeContrast.test.ts` — new; parser, measurement
  oracle, pair derivation, the AA assertion and the oracle pins below.

### Test criteria

- Every derived pair in both schemes measures ≥ 4.5; the suite fails naming the
  pair otherwise. Verified by temporarily restoring `oklch(0.55 0.02 160)` and
  seeing the run go red on `muted-foreground/muted`.
- Oracle pins, in their own `describe`, so a broken measurement cannot quietly
  certify a broken palette:
  - `ratio(oklch(0 0 0), oklch(1 0 0))` is exactly **21** (±1e-9);
  - `oklch(0.628 0.2577 29.23)`, passed **unrounded and unmapped** to the
    step-1 converter, gives linear ≈ `(1, 0, 0)` (±1e-3) — pins the matrices
    and the absence of a second transfer;
  - `oklch(0.62 0.15 160)` is reported out of gamut and snaps to chroma
    **0.14**, while an in-gamut colour is returned unchanged;
  - the historical value **4.2913** (±1e-3) for `oklch(0.55 0.02 160)` on
    `oklch(0.96 0.01 160)` and **4.6684** (±1e-3) for the shipped `0.53`.
- `npx vitest run` green; `npm run lint` and `npm run build` clean; the frontend
  coverage thresholds are untouched (the new file is a test and is excluded from
  coverage).
- `git diff --stat` lists exactly the two files above.

![Mockup](APRAS-76-mock.html)

## Expected Results

- [ ] Every text/background pair derived from `frontend/src/index.css` measures
      ≥ 4.5:1 in both the light and the dark scheme, on the emitted 2dp value
      after CSS Color 4 §13 chroma-reduction gamut mapping.
- [ ] `--muted-foreground` on `--muted` in `:root` measures ≥ 4.5:1 (4.6684 at
      `oklch(0.53 0.02 160)`, against 4.2913 today).
- [ ] `--primary-foreground` on `--primary` in `:root` measures ≥ 4.5:1 (5.7548
      at `oklch(0.15 0.02 160)`, against 3.2169 today), with `--primary` itself
      unchanged.
- [ ] `frontend/src/__tests__/themeContrast.test.ts` derives its pairs by
      parsing `index.css`, fails on any `-foreground`/`-fg` token whose partner
      is missing, and turns red when `--muted-foreground` is reverted to
      `oklch(0.55 0.02 160)`.
- [ ] The measurement is pinned by oracle cases: black-on-white is exactly 21,
      `oklch(0.628 0.2577 29.23)` passed unrounded and ungamut-mapped to the
      OKLCH→linear-sRGB converter gives linear `(1, 0, 0)` within ±1e-3, and
      `oklch(0.62 0.15 160)` snaps to chroma 0.14.
- [ ] `git diff --name-only` lists exactly `frontend/src/index.css` and
      `frontend/src/__tests__/themeContrast.test.ts`; no component, no
      Tailwind class and no backend file changes.
- [ ] `npx vitest run`, `npm run lint` and `npm run build` are all green in
      `frontend/`.

## Out of Scope

- **`text-primary` as body text on a surface** — `--primary` on `--background`
  measures **3.3114** and on `--card` **3.4078**, and the class is used ~48
  times. Every available repair either changes the brand colour or adds a
  second "accessible primary" token and edits those call sites, which the "no
  component markup changes" boundary of this task forbids. Measured and named
  here so it is not rediscovered; it needs its own task, and it is a property
  APRAS-68's derivation shares for a branded tenant.
- **Non-text contrast (3:1)** — `--border`, `--input`, `--ring` and icon-only
  surfaces are not measured, matching APRAS-68's boundary.
- **Alpha composites** — `bg-primary/10`, `bg-primary/90` and friends are
  blends computed at paint time, not declared pairs; the test measures declared
  tokens only.
- **`app/core/branding.py` and APRAS-68** — no backend file is touched and no
  dependency is declared in either direction.
