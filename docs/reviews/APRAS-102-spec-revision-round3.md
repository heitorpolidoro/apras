# APRAS-102 — spec revision, round 3 (report)

Revised `docs/tasks/APRAS-102-spec.md`; touched `docs/tasks/APRAS-102-mock.html`
for one point. Nothing staged, nothing committed, no production code, no tests
run, no `npm install` / `uv sync`. Round-1 findings were not revisited per the
dispatch.

## Blocking finding — the clamp assertion

The reviewer is right and the reason is in the emitted strings, not in the
wording. I extracted `cylinderCard` from the mock and ran it at four inputs
(Node 24). Literal output:

| input | fill `d` | outline `d` |
| --- | --- | --- |
| `total = 0` | `M10 20.0 v120.0 a50 12 0 0 0 100 0 v-120.0` | `M10 20 v120 a50 12 0 0 0 100 0 v-120` |
| `executed > total` (100000/120000) | `M10 140.0 v0.0 a50 12 0 0 0 100 0 v-0.0` | same |
| baseline 480000/204000 | `M10 71.0 v69.0 a50 12 0 0 0 100 0 v-69.0` | same |
| 400000/174000 | `M10 72.2 v67.8 a50 12 0 0 0 100 0 v-67.8` | same |

`/-\d/` matches the outline in **every** case (`v-120`) and the fill in the
clamped case (`v-0.0`), so the old criterion was unsatisfiable by any correct
mirror of `_cylinder_svg @ 869`.

Replacement, now stated identically in §5 and in expected result 2: parse the
fill path's `d`, read `yStart` (move-to `y`) and `h` (first vertical operand =
fill height), with `top = 20`, `bottom = 140`.

- `executed > total` → `yStart === 140`, `h === 0`, surface ellipse `cy === 140`
- `total = 0` → `yStart === 20`, `h === 120`
- both → every **absolute coordinate** (`yStart`, ellipse `cy`) in `20..140`,
  inside the `0 0 120 165` viewBox. Relative operands are explicitly excluded,
  with the reason given, so the `/-\d/` idea cannot come back.

Discrimination check (the point of the standing observation): an unclamped
implementation computes `fy = 140 − 120·(−20)/100 = 164`, giving `yStart = 164`
and `h = −24`, so all three assertions fail. A clamped one passes all three at
all four inputs above. Numbers are parsed and compared numerically, so no
`toFixed` precision is imposed on the implementer. The literal strings checked
against are named in §5 itself.

## Seven small points

1. §5 rounding count: was "three of the six"; now "**five of the seven**", after
   adding the negative tie. Verified: `toFixed` differs from Python on `56.5`,
   `2.5`, `42.5`, `42.25`, `-20.5`; agrees on `57.5`, `2.675`.
2. §2 answer-A contradiction resolved in advance: a new paragraph pre-sanctions
   the in-tank number being the **unclamped** percentage (where `_cylinder_svg`
   prints clamped `{filled:.0f}%`), so answer A cannot contradict the
   "only one appearance divergence" rule. Under B the question does not arise.
3. Negative tie pinned: `(-20.5, 0) → "-20"` added to §5 and expected result 4
   (`format(-20.5,'.0f') == "-20"`, `(-20.5).toFixed(0) == "-21"` — both run).
4. `formatPercent` domain stated: `toFixed(20)` soundness argued from the ULP of
   `-100..100`, plus required explicit behaviour for `NaN`/`±Infinity` and a
   documented `decimals` range of `0..2`.
5. TZ restore required (`vi.stubEnv` or `afterAll`), with the TZ-sensitive
   suites named as the reason.
6. Gap positioning unit fixed: inline `style.left` / `style.width` as percent
   strings, with the baseline's `left:42%;width:22%` cited.
7. `utils/currency.ts` now given as the full path
   `frontend/src/features/project-management/utils/currency.ts`, naming the
   unrelated `purchase-management/utils/formatters.ts` as the ambiguity.

Also folded in (reviewer suggestion in the same list): a sentence in §3 stating
the ahead gap is *expected* to be faint (~1.3–1.4:1 over the track), so its
faintness is not read as a missing fill.

## Mock change

Only one, from the last suggestion: in option **A2** the "Saldo restante"
caption sat above empty space, making A look defective. Under `labelInside` the
caption now reads `Saldo restante (no tanque)` and the outside number is not
rendered; under B both caption and number are unchanged. The two options still
differ in exactly `labelInside`. Script syntax re-checked with `node --check`.

No other mock change — the geometry the blocking finding is about is correct as
drawn and stays as it is.
