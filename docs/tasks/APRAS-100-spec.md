# APRAS-100 — Turn the brand contrast failure into a warning instead of a hard block

## Scope

Today an **advanced** brand palette carrying a text/surface pair under 4.5:1 is
refused: `TenantService.validated_brand_theme` raises
`InsufficientContrastError`, `exception_handlers` answers **422** with a
`failures` list, and `TenantBrandColors.tsx` disables Save while its own
client-side reading finds a failing pair.

This task removes **only that verdict**. The measurement stays, byte for byte;
the refusal becomes a report. A low-contrast advanced palette is stored exactly
as submitted, and every failing pair travels back to the caller on the profile
body as `contrast_warnings`, so the screen — and any other client — can warn
without measuring anything itself.

In scope:

- the backend gate (service, exception, handler), the response schema, and the
  profile endpoint that fills the new field;
- the advanced brand form: Save stays enabled, the refusal panel becomes a
  warning panel, and the warning is announced to assistive technology;
- replacing the tests that pin the removed behaviour with tests that pin the
  new contract.

Explicitly **not** in scope:

- any change to how contrast is computed. `audit_contrast`, `contrast_ratio`,
  `MEASURED_PAIRS`, `build_theme`, `frontend/src/lib/contrast.ts` and
  `backend/tests/data/contrast_fixtures.json` keep their current behaviour and
  their current numbers;
- shape validation. A malformed palette is still 422;
- simple mode, which is never measured here and must not start being measured —
  the derivation owns both sides of every pair there (APRAS-68 D-A);
- the public route. `app/api/v1/endpoints/public_branding.py` must stay
  untouched: `backend/tests/test_public_branding.py` carries an AST guard that
  fails if that router ever calls `audit_contrast`, and `contrast_warnings` is
  not part of `PublicTenantBrandingRead`'s four-field security boundary;
- APRAS-88's rule that `--primary-text` is absent from `MEASURED_PAIRS`. The
  eight pairs are the eight pairs.

## The eight pairs, written down

Expected result 3 is checkable against this list. `MEASURED_PAIRS`
(`backend/app/core/branding.py`, mirrored in `frontend/src/lib/contrast.ts`),
in document order, as `(foreground, background)`:

1. `foreground/background`
2. `card-foreground/card`
3. `primary-foreground/primary`
4. `secondary-foreground/secondary`
5. `accent-foreground/accent`
6. `muted-foreground/muted`
7. `muted-foreground/background`
8. `muted-foreground/card`

`muted-foreground` appears three times on purpose. `border`, `input` and `ring`
are not measured. Both schemes (`light` and `dark`) are audited, so an advanced
palette yields up to sixteen readings.

## Approach

### Behaviour

**The API stops refusing, and starts reporting.**
`TenantService.validated_brand_theme` keeps normalising the shape and keeps
raising `InvalidBrandThemeError` (422); it no longer builds the theme to measure
it and no longer raises for contrast. `InsufficientContrastError` has no
remaining raiser and is removed, together with its entry in the handler's 422
tuple and the `content["failures"]` special case it was the only user of — a 422
body no longer carries `failures` at all.

**The warning rides the profile body, derived on read.** `_profile_of` in
`endpoints/tenant_profile.py` already derives `theme` on read; it now derives
`contrast_warnings` from that same theme and all four profile routes answer it,
which means the `PATCH` response that saved the palette is itself the response
that reports the warning. The value is `null` when the tenant has no
`brand_theme`, and an empty list when the stored mode is `simple` (never
measured) or when every pair clears 4.5:1. Each entry carries `pair`, `ratio`
rounded to 2dp, `minimum` (4.5) and `scheme` (`"light"` or `"dark"`) — the exact
entry shape the removed 422 used, so the screen's existing renderer needs no
new shape.

**The advanced form warns instead of blocking.** `blocked` loses its contrast
term and becomes malformed-hex only, so Save is enabled for a palette whose only
problem is contrast. The panel that was a refusal becomes a warning: warning
copy, a warning icon (`TriangleAlert` in place of `OctagonX`), the same per-pair list with the same
`pairFail` copy, and an amber surface (`--status-pending-bg` /
`--status-pending-fg`; the operator decided A, see §Decision). `failuresOf` and the `apiFailures` state it fed go away with
the 422 path, and so does `setApiFailures` in `edit` and in `save`.

**One list, one source, chosen by a stated rule.** The panel today renders
`[...apiFailures, ...clientFailures]` with the count as
`Math.max(clientFailures.length, apiFailures.length)`. That was sound only
because `apiFailures` was transient — set in `onError`, cleared on every edit.
`profile.contrast_warnings` is present on *every* read, so concatenation would
render each pair of a stored failing palette twice and leave `{{count}}` and the
worst ratio ambiguous. The rule, which replaces the concatenation:

- **draft clean** — no draft for this tenant (`draft === null ||
  draft.tenantId !== profile.id`, the same condition `current` already uses):
  the list is `profile.contrast_warnings ?? []`. The server measured what is
  stored, and that is what the fields show.
- **draft dirty** — the person has typed: the list is `clientFailures` and the
  server's field is ignored entirely. The server has not seen those colours.
- the two are never concatenated and never merged, so no reading is rendered
  twice, and the count and the worst ratio come from whichever single list is
  displayed.

Everything the section says about contrast — the panel's per-pair list, its
`{{count}}`, and the live paragraph's count and worst ratio — reads from that
one chosen list. There is no second computation and no mix: **the count and the
worst ratio in the announcement come from the same single list the panel
renders.**

`pairFail` names the pair but **not the scheme**, and that omission is
deliberate: the copy is inherited verbatim from the removed 422 renderer and the
wording is not being redesigned here. A palette failing the same pair in both
schemes therefore renders two identical lines — one per failing *reading*, which
is what "once" means in detailed criterion 7. Rendering the scheme is a copy change
and is out of scope.

The two lists are one type at the point of use. The renderer reads exactly
three fields — `pair`, `ratio`, `minimum` — and `BrandContrastFailure` (server,
four fields) is structurally assignable to `ContrastFailure` (client, those
three), so the chosen list is held in a single
`const shown: ContrastFailure[]` and needs **no cast and no type guard**.
`scheme` is carried by the server entries and simply not read, which is the
same thing §"`pairFail` names the pair but not the scheme" says about the copy.

The numbers agree across the switch by construction **for every scheme the
client measures**: `auditHexPalette` routes through `hexPaletteToScheme`, so
the client measures the same emitted 2dp `oklch()` strings the backend
measures, and a stored light pair reported at 3.93 still reads 3.93 on the
first keystroke that leaves it untouched. The qualifier is real and must not
be read away: `clientFailures` (`TenantBrandColors.tsx:762`) audits
`current.light` always but `current.dark` **only when `deriveDark` is false**,
while `profile.contrast_warnings` covers both server-derived schemes. For a
stored advanced theme with `deriveDark` true, the dark-scheme warnings
therefore *disappear* from the panel on the first keystroke rather than
agreeing at the same number. That is accepted here — the client cannot measure
a scheme it does not hold — and no test may assert the two lists are equal
across the clean→dirty switch; the tests assert each arm separately.

**The warning panel carries no live-region role.** The panel is `role="alert"`
today, which *is* an implicit `aria-live="assertive" aria-atomic="true"` region.
Keeping it would re-announce the whole per-pair list, assertively, on every
keystroke — exactly the harm the live paragraph below is designed to avoid, and
it would do so invisibly to every assertion in detailed criterion 9. The panel
must therefore carry **no** `role` and no `aria-live`; the paragraph is the only
live region in the section. It gains `data-testid="brand-contrast-warning"`
instead, because `TenantProfilePage.brand.test.tsx:301` locates the panel today
with `within(section).getByRole("alert")` and that locator has to move with it.
The paste dialog's own `role="alert"` problems panel (the `problemsTitle` block,
located that way at `:900`, `:918`, `:1067`, `:1081`) is a different element and
is not touched.

**The announcement is a named mechanism, not markup.** One paragraph,
**always mounted in advanced mode**, with a stable `id` (e.g.
`brand-contrast-live`), `role="status"`, `aria-live="polite"` and
`aria-atomic="true"`, carrying a single sentence and nothing else.

**That paragraph is `sr-only`** — the `className="sr-only"` the deleted
duplicate at `:1091` uses, a live region with no visual presence. This is
decided, not left open, and the rest of the design depends on it: the panel
already shows the count and every failing pair, and the emerald paragraph
already shows the all-pass sentence, so a *visible* live paragraph would put
the same sentence on screen twice in the all-pass state, one copy
`aria-hidden`. `sr-only` makes this task's visual change exactly one thing —
the warning panel's colour (amber, §Decision) — and makes
`aria-hidden="true"` on the emerald paragraph coherent: the sentence is seen
once and heard once, in different nodes. No test may assert the paragraph is
visible, and none may assert it is not in the accessibility tree; `sr-only`
is clipped, not hidden.

The `id` is
required anyway, because Save's `aria-describedby` points at it, so tests locate
this paragraph **by that `id`**, not by `getByRole("status")`: the `savedKey`
confirmation paragraph at `TenantBrandColors.tsx:990` already carries
`role="status"` in this same section, and although it only mounts after a
successful save, the `id` locator is unambiguous without depending on that.
Three cases, mutually exclusive, in this precedence:

1. **a malformed hex** — `clientFailures` is `[]` whenever `anyMalformed`,
   because the audit is skipped, so without this case the region would announce
   "every pair clears" while Save is disabled, and the Save button's
   `aria-describedby` would make that false sentence the *only* explanation an
   AT user gets for the disabled button. The sentence names the format fault
   and says saving is blocked (new key `warningAnnouncementMalformed`);
2. **failures** — the number of failing pairs **and the worst measured ratio**,
   e.g. "2 pares abaixo de 4,5:1 — o pior em 3,21:1" (`warningAnnouncement`,
   `{{count}}` and `{{worst}}`);
3. **neither** — the existing `allPass` sentence.

Three consequences are the point of that design and must hold:

- the per-pair `<ul>` sits **outside** the live region, so re-rendering thirteen
  inputs on every keystroke does not re-announce thirteen list items;
- because the sentence carries the worst ratio, almost any edit that changes the
  readings changes the announced text, and an unchanged sentence is announced by
  no AT — which is the wanted behaviour on re-validation;
- because the paragraph is never unmounted, the transition **failing → passing**
  is announced too; an unmounted live region announces nothing.

The Save button gains `aria-describedby` pointing at that paragraph's `id`, so
someone who tabs to Save hears either why it is enabled-but-warned or why it is
disabled.

**The two existing all-pass nodes are reconciled, not left beside the new one.**
`allPass` is rendered twice today and the live paragraph's case 3 would make
three:

- the visible emerald paragraph at `:1036-1041` is gated on
  `clientFailures.length === 0 && apiFailures.length === 0`. `apiFailures`
  disappears, so that condition is **re-expressed against the single chosen
  list**: it renders when that list is empty. The paragraph stays visible, keeps
  its icon, and gains `aria-hidden="true"`, because the `sr-only` live paragraph
  is now the accessible carrier of that sentence and nothing should read it
  twice. The two nodes never collide on screen, the live one being `sr-only`.
- the `sr-only` copy at `:1091`, gated on `derivedFailures.length === 0`, is
  **deleted**. Its only job was announcing to assistive technology what the two
  `PairList`s show; the always-mounted live paragraph does that job now, and an
  invisible duplicate sitting next to a real live region is exactly the shape
  that makes announcements unpredictable. The `PairList`s themselves are
  untouched.

After this, `t("tenantProfile.brand.allPass")` appears **exactly twice** in
`TenantBrandColors.tsx`: the `aria-hidden` visible paragraph and the live
paragraph.

**The default palette now warns, and that is an improvement, not a question.**
`DEFAULT_PALETTE` (`TenantBrandColors.tsx:72-86`) through `build_theme` fails
three light pairs — `primary-foreground/primary` 4.26, `muted-foreground/muted`
4.11, `muted-foreground/background` 4.47 — so a tenant with no stored palette
who switches to advanced mode sees the warning panel and gets one polite
announcement. No operator decision is needed: today that same state disables Save
outright, so this task strictly improves it, and on a clean draft with no
`brand_theme` the chosen list is `profile.contrast_warnings ?? []`, i.e. empty —
the panel only appears once the mode switch has made the draft dirty. The
consequence for tests is concrete and is recorded in §Test criteria: the "every
pair clears" arm of the live-region test **cannot be reached from the default
palette** and must type the `READABLE` fixture, the way
`"keeps the save enabled for a palette every pair of which clears AA"` already
does.

**The paste review panel loses its refusal too.** The applied-palette review
(`TenantBrandColors.tsx:607-619`) has a refusal block of its own: `refusalTitle`
+ `refusalBody` + `paste.cannotSave` — "This palette cannot be saved while a
pair is below 4.5:1. Undo, fix the text and apply again…". That sentence becomes
false for exactly the reason `advancedNote` does, and leaving it would have the
dialog contradict the Save button two inches away. The block keeps its place and
its per-pair list and becomes a warning: `warningTitle`/`warningBody` (the same
renamed keys the section panel uses) plus a new `paste.saveableAnyway` replacing
`paste.cannotSave`, saying the palette can be saved as it is and that the pairs
below 4.5:1 are a warning. `paste.cannotSave` is deleted; it has no other
caller. `paste.appliedFail` keeps its wording — "No request was sent" stays
true, applying is still not saving.

**`refusalTitle`/`refusalBody` are renamed, not dropped silently.** Three
existing assertions are negative ones on `refusalTitle`
(`queryByText(...)).not.toBeInTheDocument()`): deleting the key would make `t()`
return the key string, which can never match, and all three would pass for the
wrong reason. Each is re-pointed at `warningTitle` in the same commit — see
§Test criteria, which names them.

**No third implementation.** The warning gets its ratios from
`profile.contrast_warnings` (server) or from `auditHexPalette` (the existing
`lib/contrast.ts`). No luminance weight, cube root or sRGB transfer may appear
in `TenantBrandColors.tsx` or anywhere else.

### Files touched

Backend:

- `backend/app/services/tenant_service.py` — `validated_brand_theme` drops the
  `build_theme`/`audit_contrast`/raise block and the now-unused import; its
  docstring loses the second refusal.
- `backend/app/core/exceptions.py` — remove `InsufficientContrastError`.
- `backend/app/core/exception_handlers.py` — remove its import, its entry in the
  422 tuple, and the `content["failures"]` branch.
- `backend/app/schemas/tenant.py` — new `BrandContrastWarning` model (`pair`,
  `ratio`, `minimum`, `scheme`); `TenantProfileRead` gains
  `contrast_warnings: list[BrandContrastWarning] | None = None`.
  `PublicTenantBrandingRead` is not touched.
- `backend/app/api/v1/endpoints/tenant_profile.py` — `_profile_of` fills
  `contrast_warnings` from the derived theme for advanced mode.
- `backend/app/core/branding.py` — **comments and docstrings only**: the module
  header's "the advanced-mode refusal", `MEASURED_PAIRS`' "the 422 refusal
  contract" and the rule-1 note about "the 422" now describe the warning. No
  executable line changes.

Frontend:

- `frontend/src/api/tenantProfile.ts` — `TenantProfile` gains
  `contrast_warnings: BrandContrastFailure[] | null`. Declared **required**, so
  every typed `TenantProfile` literal in the repository must gain the field or
  `tsc -b` fails. Three test fixtures are literals of that type and must be
  updated in the same commit:
  `frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx:111`,
  `frontend/src/components/__tests__/TenantBrandTheme.test.tsx:71` and
  `frontend/src/components/__tests__/TenantBrandReach.test.tsx:100` (each a
  `const PROFILE: TenantProfile = {…}`; `contrast_warnings: null` is the right
  value for all three). `vitest run` does not typecheck, so a green `npm test`
  proves nothing here — `npm run build` is the check, and it is a CI gate
  (`.github/workflows/ci.yml:240`).
- `frontend/src/features/user-administration/components/TenantBrandColors.tsx` —
  `blocked`; the section warning panel (role dropped, `data-testid` added,
  `OctagonX` swapped for `TriangleAlert` in the `lucide-react` import, the
  single-source rule in place of the concatenation); the `sr-only` live-region
  paragraph with its three cases and its `id`; `aria-describedby` on Save; the visible
  all-pass paragraph (`:1036`) re-gated on the single list and made
  `aria-hidden`; the `sr-only` all-pass duplicate (`:1091`) deleted; the paste
  review block's refusal → warning; and the removal of `failuresOf`,
  `apiFailures` and both `setApiFailures` calls.
- `frontend/src/i18n/locales/en.json`, `.../pt.json` — `refusalTitle` and
  `refusalBody` **renamed** to `warningTitle`/`warningBody` (same `{{count}}`
  interpolation, wording no longer claiming a refusal); `paste.cannotSave`
  replaced by `paste.saveableAnyway`; new `warningAnnouncement` with `{{count}}`
  and `{{worst}}` and new `warningAnnouncementMalformed`; `advancedNote`
  reworded, since it currently promises "below 4.5:1 is refused and the API
  answers 422" and that sentence becomes false. Both locales keep identical key
  sets.
- `frontend/src/__tests__/themeTokenMigration.exceptions.json` — **must gain no
  entry**. The warning panel uses `bg-[var(--status-pending-bg)]` /
  `text-[var(--status-pending-fg)]`, the arbitrary-value form
  `components/ui/badge.tsx` and `LandingPage.tsx` already use, which the §3b
  grammar does not match. The file holds 882 entries overall; the six that name
  `TenantBrandColors.tsx` (`bg-amber-50`, `text-amber-900`, `bg-emerald-50`,
  `border-emerald-200`, `text-emerald-700`, `text-emerald-800`, all
  `task: APRAS-85`) stay exactly as they are — this task neither clears nor
  edits them, and the ~309 `amber`/`emerald` entries belonging to other files are
  none of its business.

Backend tests — **comments only**, no assertion may change:

- `backend/tests/test_branding.py:141` and `:937`, and the section header at
  `backend/tests/test_tenant_profile.py:473`, describe the 422 refusal contract
  in prose. Comment- and docstring-only edits there are **permitted and
  expected**, so the files do not keep describing a refusal that no longer
  exists. Any change to an `assert` in those files is out of scope and a sign the
  measurement moved.

### Test criteria

- `backend/tests/test_tenant_profile.py::test_advanced_palette_below_aa_is_refused_by_the_api`
  is **rewritten in place**, not deleted and not left passing elsewhere. Same
  palette (`_advanced_body(background="#2b2b2b", foreground="#4a4a4a")`), new
  name (e.g. `test_advanced_palette_below_aa_is_saved_and_warned`), asserting:
  status 200; the stored `brand_theme` holds the submitted hexes verbatim; the
  response's `contrast_warnings` names `foreground/background` with
  `ratio < 4.5`, `minimum == 4.5` and `scheme` in `{"light", "dark"}`; and a
  subsequent `GET` returns the same warnings. A reviewer must be able to see the
  old assertion's replacement in the diff of one function.
- A new backend test pins the known pair of detailed criterion 4 against
  `audit_contrast`, using this palette (verified against the current
  implementation while writing this spec):

  | key | value | | key | value |
  |---|---|---|---|---|
  | `background` | `#fbfdfc` | | `accent` | `#eaf5ef` |
  | `foreground` | `#141a17` | | `accent-foreground` | `#1d2a23` |
  | `card` | `#ffffff` | | `muted` | `#e4e8e7` |
  | `card-foreground` | `#141a17` | | `muted-foreground` | `#6f746e` |
  | `primary` | `#0b6b47` | | `border` | `#dfe8e3` |
  | `primary-foreground` | `#fafafa` | | | |
  | `secondary` | `#eaf5ef` | | | |
  | `secondary-foreground` | `#1d2a23` | | | |

  With `dark: null`, `audit_contrast(build_theme(...)["light"])` is exactly
  `[ContrastFailure("muted-foreground/muted", 3.93, 4.5)]` and the dark scheme
  is clean. The number is 3.93 because `audit_contrast` reads the **emitted**
  2dp `oklch()` strings; the raw hex-to-hex reading of the same two colours is
  3.86, and a test that measures the hexes directly and expects 3.93 is wrong.
- The existing `test_a_malformed_brand_theme_is_422_and_stores_nothing` and
  `test_a_twelve_key_palette_and_an_unknown_key_are_both_422` keep passing
  unmodified — they are the evidence for detailed criterion 5.
- `test_branding.py`'s existing `audit_contrast` assertions (the 9×9×2 sweep,
  the `_BAD_PALETTE` case, the fixture cross-check) keep passing **unmodified**.
  Any edit to them is a sign the measurement moved.
- `frontend/.../TenantProfilePage.brand.test.tsx`, six named changes — two tests
  rewritten in place, one test replaced, three assertions re-pointed:
  - `"disables the save and names the failing pair while a pair is below 4.5:1"`
    is **rewritten in place** into one asserting the save is **enabled** for the
    same two hexes (`background: #121212`, `foreground: #1a1a1a`) while the
    warning panel still names `foreground/background` with its ratio. Its
    `within(section).getByRole("alert")` locator (`:301`) becomes
    `getByTestId("brand-contrast-warning")`, and the rewritten test also asserts
    that node has **no** `role` and no `aria-live` attribute — the panel losing
    its implicit assertive live region is the whole mechanism of expected
    result 5, and nothing else would catch its return.

    This rewritten test is also the **only positive anchor on the renamed
    keys**, and must carry one. The three assertions re-pointed at
    `warningTitle` below are all negatives, so without an anchor a typo between
    the key the component passes to `t()` and the key the locales define would
    make `t()` return the dotted path in both places, leave every query
    unmatchable, and pass all three for the wrong reason — the previous round's
    finding, one step removed. The repository has no "every `t()` key resolves"
    guard (`src/i18n/__tests__/parity.test.ts` checks en/pt parity, empty values
    and retired keys only, none of which catches a key missing from both locales).

    The anchor has to be written against two facts about this file, and the
    obvious spelling of it is red:

    - **the count is not 1.** Those two hexes are typed over `DEFAULT_PALETTE`,
      and `auditHexPalette` on the result returns **four** failures, not the
      typed one alone: `foreground/background` 1.09,
      `primary-foreground/primary` 4.26, `muted-foreground/muted` 4.11 and
      `muted-foreground/background` 4.08 (the three §"The default palette now
      warns" names, plus the typed pair; `deriveDark` is on, so only the light
      scheme is audited). A hardcoded `{ count: 1 }` cannot match a panel
      rendering "4".
    - **the file's `t()` helper takes no options.** `t` at
      `TenantProfilePage.brand.test.tsx:42` is
      `(key: string): string` — a plain path walk into `pt.json`. It returns the
      raw template, `{{count}}` and all, and passing a second argument is a
      `tsc` error, not an interpolation.

    So the anchor is written as: locate the panel by its `data-testid`; assert
    `within(panel).getByText(t("tenantProfile.brand.warningTitle"))` (that key
    has no interpolation, so it matches directly); then take the count from the
    panel itself — `within(panel).getAllByRole("listitem").length`, one `<li>`
    per rendered reading — and assert the panel's text contains
    `t("tenantProfile.brand.warningBody").replace("{{count}}", String(count))`.
    Assert first that the template does contain `"{{count}}"`, so a key that
    resolves to nothing fails on a readable assertion rather than on a
    `TypeError`. The count is never written down in the test, so the assertion
    holds at four and would hold at one; what it pins is that both renamed keys
    resolve and that the panel's `{{count}}` equals the number of lines it
    renders — which is also the single-source rule in miniature. Neither
    assertion may be dropped: `warningTitle` alone was the previous round's
    finding.
  - `"renders the API's 422 failures even though the client check passed"` is
    replaced by one pinning the clean-draft arm of the single-source rule, and
    its fixture has to be built so that only the server's list can produce the
    assertion:
    - the served profile's `brand_theme.mode` is **`"advanced"`** — otherwise
      the advanced panel is not on screen at all, and by this spec's own rule
      `contrast_warnings` would be `[]` anyway;
    - its stored `light` palette is the `READABLE` fixture (`:54`), every
      measured pair of which clears AA, so the client's own reading of the
      prefilled draft is **empty**;
    - its `contrast_warnings` carries one entry the client would never
      produce: `{ pair: "muted-foreground/card", ratio: 3.91, minimum: 4.5,
      scheme: "light" }`;
    - the draft is left **clean** — the test types nothing and switches no
      mode.

    It then asserts the panel is on screen, names `muted-foreground/card` with
    `3.91`, holds **exactly one** `<li>`, and that the `allPass` sentence is
    absent from the chosen-list paragraph. The fixture is the whole point:
    `current = draftFor(profile)` prefills from the stored palette and
    `clientFailures` is gated on `current.mode`, not on the draft, so a stored
    *failing* palette would make both lists non-empty and the test would pass
    whichever list won. A pair and ratio the client cannot produce, next to an
    empty client reading, is the only shape that proves the server's field was
    chosen.
  - `"applies a palette whose contrast fails, names both pairs and disables the
    save"` (`:855`) is **rewritten in place**, renamed to end "…and keeps the
    save enabled". Same pasted palette; the two pair sentences stay; both
    `expect(await saveButton()).toBeDisabled()` become `toBeEnabled()`; and
    `getByText(t("tenantProfile.brand.paste.cannotSave"))` becomes
    `getByText(t("tenantProfile.brand.paste.saveableAnyway"))`. Left as it is,
    this test fails the moment `blocked` loses its contrast term, so expected
    result 8 is unreachable without it.
  - the three negative assertions on the renamed key are re-pointed at
    `t("tenantProfile.brand.warningTitle")`, one per test:
    `"falls back to the generic failure list when the save fails with a 500"`
    (`:641`), `"ignores a 422 whose body carries no failures list"` (`:666`,
    which otherwise "stays" unmodified), and `"applies the thirteen values and
    stays open, showing them and the eight pairs"` (`:840`). A reviewer must see
    three one-line changes; a `refusalTitle` left anywhere in this file after
    the rename is an assertion that can no longer fail.
- A frontend test asserts the live region, locating the paragraph **by its
  `id`** (not `getByRole("status")`, since `:990` also uses that role in this
  section) and checking that node carries `role="status"`, `aria-live="polite"`,
  `aria-atomic="true"` and the `sr-only` class. No assertion in this test may be
  `toBeVisible()`: the paragraph is `sr-only` by design, and jsdom's
  visibility check treats a clipped node as visible anyway, so such an assertion
  would pin nothing and mislead the next reader. It exists in advanced mode while a pair fails, once
  every pair clears, **and** while a hex is malformed; its text differs across
  all three; the failing-pair `<ul>` is **not** a descendant of it; and the Save
  button's `aria-describedby` resolves to that `id`. The malformed case
  additionally asserts the sentence names the format fault while Save is
  disabled — not the all-pass sentence. The **all-pass arm must type the
  `READABLE` fixture** (`:54`, as
  `"keeps the save enabled for a palette every pair of which clears AA"` already
  does at `:311`): it is unreachable from `DEFAULT_PALETTE`, which fails three
  light pairs.
- A frontend test asserts the all-pass reconciliation: with the `READABLE`
  palette typed, `t("tenantProfile.brand.allPass")` is carried by **exactly two**
  nodes in the section — the `sr-only` live paragraph, and a visible paragraph
  with `aria-hidden="true"` — and the former `sr-only` duplicate at `:1091` is
  gone. The count must be taken with
  `within(section).getAllByText(t("tenantProfile.brand.allPass"))`, which does
  not filter `aria-hidden` nodes. A role- or accessible-name-based query hides
  the `aria-hidden` paragraph, collapses the count to one, and would make the
  result unassertable; so would `toBeVisible()` on the live paragraph, which is
  `sr-only`. One of the two nodes is then identified by its `id` (the live one)
  and the other asserted to carry `aria-hidden="true"`.
- Detailed criterion 13 gets a mechanical guard — one new node-environment test
  (the `// @vitest-environment node` + `node:fs` pattern
  `themeTokenMigration.test.ts` already uses) that walks `frontend/src` and
  `backend/app`, **skipping test files** (`**/__tests__/**`, `*.test.ts`,
  `*.test.tsx`, `test_*.py`), and asserts the set of remaining files containing
  the WCAG weight literal `0.2126` is **exactly**
  `{frontend/src/lib/contrast.ts, backend/app/core/branding.py}`. The exclusion
  is load-bearing, not tidiness: `frontend/src/__tests__/themeContrast.test.ts:62`
  holds `const RED_WEIGHT = 0.2126;` and lives under `frontend/src`, so a guard
  without it fails on master.
- `cd backend && uv run pytest` green; `cd frontend && npm test` green; and
  `cd frontend && npm run build` (`tsc -b && vite build`) green — the CI gate at
  `.github/workflows/ci.yml:240`, and the only check that catches the three
  `TenantProfile` fixtures listed in §Files touched, since `vitest run` does not
  typecheck.
- `cd frontend && npm run lint` **no worse than base**: the repository carries
  ~375 pre-existing errors across 64 files, so the criterion is a comparison
  against `master`, never "zero".

### Detailed criteria (demoted from Expected Results)

The Expected Results below are the outcome-level contract. Every requirement
that used to be spelled out as a result is kept here intact, as test-recipe
detail; none was dropped.

- [ ] `PATCH /api/v1/tenant-profile` with an advanced palette whose measured
      contrast falls below 4.5:1 answers **200**, and the stored `brand_theme`
      holds the submitted colours verbatim.
- [ ] That response, and a later `GET`, carry `contrast_warnings`: one entry per
      measured pair below 4.5:1, each naming `pair`, `ratio` at 2dp, `minimum`
      (4.5) and `scheme`. The field is `null` with no `brand_theme` and `[]` in
      simple mode or when every pair clears.
- [ ] `InsufficientContrastError` no longer exists, and no 422 body carries a
      `failures` key.
- [ ] `audit_contrast` still measures the same eight pairs in the same order;
      `test_branding.py`'s existing `audit_contrast` assertions pass unmodified;
      and a new test pins the palette tabulated in the spec to exactly
      `[ContrastFailure("muted-foreground/muted", 3.93, 4.5)]` in the light
      scheme, with the dark scheme clean.
- [ ] A malformed palette — missing key, extra key, or a value that is not
      `#rrggbb` — is still **422** and stores nothing; the two existing
      malformed-palette tests pass unmodified.
- [ ] In advanced mode the Save button is enabled when the only problem is
      contrast, and still disabled when any typed hex is malformed.
- [ ] The advanced form shows one line per failing reading — each `(pair,
      scheme)` exactly once, with its ratio at 2dp — from a single source chosen
      by a stated rule: `profile.contrast_warnings` while the draft is clean,
      `clientFailures` from `auditHexPalette` once the draft is dirty, never both
      concatenated. The chosen list is one `ContrastFailure[]` and the renderer
      reads only `pair`, `ratio` and `minimum`, with no cast. The panel's
      `{{count}}` and the announcement's count and worst ratio come from that
      same single list. `pairFail` does not name the
      scheme (deliberate, inherited from the removed 422 renderer), so the same
      pair failing in both schemes renders two identical lines. A test covers
      each arm, and one asserts a stored failing palette renders each reading
      exactly once. The clean-draft test serves an **advanced** profile whose
      stored palette is the all-clearing `READABLE` fixture — so the client's own
      reading is empty — and whose `contrast_warnings` names
      `muted-foreground/card` at 3.91, a reading the client cannot produce, and
      asserts the panel holds exactly that one line.
- [ ] The warning panel carries warning copy and a `TriangleAlert` icon in place
      of `OctagonX` — both unconditional — and is
      styled on `--status-pending-bg`/`--status-pending-fg` (the operator's decision A; no
      `--destructive` classes remain on it) with **no new entry added to
      `themeTokenMigration.exceptions.json`**, and carries **no `role` and no
      `aria-live`** — it is reachable by
      `data-testid="brand-contrast-warning"`, and a test asserts the absence of
      both attributes.
- [ ] A single `sr-only` paragraph with a stable `id`, `role="status"`,
      `aria-live="polite"` and `aria-atomic="true"` is mounted in advanced mode in
      all three states. Its sentence carries the failing-pair count and the worst
      ratio when pairs fail; names the format fault when any typed hex is
      malformed — never the all-pass sentence while Save is disabled; and is the
      all-pass sentence otherwise. The per-pair list is not inside it, and the
      Save button's `aria-describedby` resolves to that `id`. One frontend test
      asserts all three states (reaching the all-pass state by typing the
      `READABLE` fixture, unreachable from the default palette), the
      non-containment and the `aria-describedby`, locating the paragraph by `id`.
- [ ] `allPass` is carried by exactly two nodes in the advanced section, counted
      with `getAllByText` (which does not filter `aria-hidden`): the `sr-only`
      live paragraph, and the visible paragraph (re-gated on the single chosen list,
      `apiFailures` gone) now marked `aria-hidden="true"`. The `sr-only`
      duplicate at `TenantBrandColors.tsx:1091` no longer exists. A test asserts
      the count of two and the `aria-hidden`.
- [ ] No copy promises a refusal any more: `advancedNote`,
      `warningTitle`/`warningBody` (renamed from `refusalTitle`/`refusalBody`)
      and `paste.saveableAnyway` (replacing `paste.cannotSave`) all describe a
      warning, in both `en.json` and `pt.json`, with identical key sets. No
      `refusalTitle`, `refusalBody` or `paste.cannotSave` reference survives
      anywhere under `frontend/src`.
- [ ] Three tests are **rewritten in place** on the same inputs — the backend
      `test_advanced_palette_below_aa_is_refused_by_the_api`, the frontend
      `"disables the save and names the failing pair while a pair is below
      4.5:1"`, and the frontend `"applies a palette whose contrast fails, names
      both pairs and disables the save"` (both of its `toBeDisabled()` become
      `toBeEnabled()` and `paste.cannotSave` becomes `paste.saveableAnyway`) —
      and exactly one test is **replaced**, `"renders the API's 422 failures even
      though the client check passed"`, whose subject no longer exists, by the
      clean-draft arm of the single-source rule. Separately, the three
      `queryByText(refusalTitle)).not.toBeInTheDocument()` assertions in
      `"falls back to the generic failure list when the save fails with a 500"`
      (`:641`), `"ignores a 422 whose body carries no failures list"` (`:666`) and
      `"applies the thirteen values and stays open, showing them and the eight
      pairs"` (`:840`) are each re-pointed at `warningTitle`. Because those three
      are negatives, the rewritten `"…while a pair is below 4.5:1"` test carries
      the **positive anchor**: inside the warning panel it asserts
      `warningTitle` is rendered, and that the panel's text contains
      `warningBody` with `{{count}}` substituted by the number of `<li>` lines
      the panel itself renders — the count is not hardcoded, because those two
      hexes over `DEFAULT_PALETTE` fail **four** light pairs, and the file's
      local `t()` helper takes no interpolation options. So a key that resolves
      in neither locale, or a typo between component and locales, or a
      `{{count}}` disagreeing with the rendered lines, fails an assertion
      instead of making four tests pass vacuously. No assertion of
      the removed 422 survives on another path.
- [ ] A node-environment guard test asserts that, **excluding test files**
      (`**/__tests__/**`, `*.test.ts`, `*.test.tsx`, `test_*.py`), the files
      under `frontend/src` and `backend/app` containing the literal `0.2126` are
      exactly `frontend/src/lib/contrast.ts` and `backend/app/core/branding.py`.
      `frontend/src/__tests__/themeContrast.test.ts` holds that literal and is
      excluded by the rule, not by a special case.
- [ ] `app/api/v1/endpoints/public_branding.py` is unchanged and
      `test_public_branding.py`'s AST guard still passes.
- [ ] `uv run pytest`, `npm test` and `npm run build` (`tsc -b && vite build`)
      all green — the build including the three `TenantProfile` fixtures updated
      for the required `contrast_warnings` field; `npm run lint` no worse than
      `master`.

## Decision

The operator answered **A** (2026-10-12): the warning panel is amber, styled on
`--status-pending-bg`/`--status-pending-fg`, the tint the product's "pendente"
badges use. Red (`--destructive`) is not kept. The warning copy, the
`TriangleAlert` icon and the dropped `role="alert"` are unconditional, as the detailed criteria above state. The side-by-side mock is
[`docs/tasks/APRAS-100-mock.html`](APRAS-100-mock.html); option A there is the
chosen rendering.

## Expected Results

- [ ] `PATCH /api/v1/tenant-profile` with an advanced palette below 4.5:1 answers **200** and stores the submitted colours verbatim; a malformed palette is still **422** and stores nothing.
- [ ] The PATCH response and a later `GET` carry `contrast_warnings`: one entry per failing measured pair (`pair`, `ratio`, `minimum`, `scheme`), `null` with no `brand_theme`, `[]` when nothing fails.
- [ ] `InsufficientContrastError` and the 422 `failures` body no longer exist, while `audit_contrast` still measures the same eight pairs in the same order.
- [ ] In advanced mode the Save button is enabled when the only problem is contrast, and disabled when a typed hex is malformed.
- [ ] The advanced form lists each failing reading exactly once from a single source, in an amber warning panel with warning copy and a `TriangleAlert` icon, without `role` or `aria-live`.
- [ ] One `sr-only` live-region paragraph announces the failing count and worst ratio, the format fault, or the all-pass sentence, and the Save button's `aria-describedby` points at it.
- [ ] No copy promises a refusal any more: `en.json` and `pt.json` carry identical warning-worded keys and no `refusalTitle`, `refusalBody` or `paste.cannotSave` survives.
- [ ] `uv run pytest`, `npm test` and `npm run build` are green, `npm run lint` is no worse than `master`, and `public_branding.py` is unchanged.

## Out of Scope

- Changing any contrast number, pair list, or the gamut-mapping rules.
- Measuring simple mode, or adding `--primary-text`'s pairs to
  `MEASURED_PAIRS` (APRAS-88 forbids it).
- Surfacing warnings on the public `/c/<slug>` branding route.
- Clearing any of the six `TenantBrandColors.tsx` palette-class exceptions
  `themeTokenMigration.exceptions.json` already holds (all `task: APRAS-85`), or
  any of the other 876 entries.
- Adding the scheme to the `pairFail` line, or any other rewording of the
  per-pair copy inherited from the 422 renderer.
- Changing any `assert` in `backend/tests/test_branding.py` or in the
  `test_tenant_profile.py` sections this task does not rewrite; only their
  comments and docstrings may be corrected.
- Any treatment of the fact that `DEFAULT_PALETTE` fails three light pairs: it
  warns instead of blocking, which is the point of the task, and the palette
  itself is not being changed here.
