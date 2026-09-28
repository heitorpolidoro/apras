# APRAS-95 — Let an advanced brand palette be pasted as JSON or CSS instead of thirteen colour pickers

## Scope

Advanced mode of "Cores da marca" (`TenantBrandColors`) asks for thirteen colours
through thirteen `<input type="color">` fields. A palette that already exists as
text — a brand guide, a block of `index.css`, the JSON object the API stores —
can only be entered by opening thirteen native colour dialogs. This task adds a
**paste affordance** to advanced mode: one textarea that accepts either the JSON
object the API consumes or a block of `--key: #hex;` CSS declarations, validates
it in the browser, and writes it into the existing advanced-mode draft so the
thirteen fields, the live contrast panel and the Save button behave exactly as
if the values had been typed.

**Frontend only.** `backend/app/core/branding.py` is not touched:
`AUTHORED_KEYS` stays at thirteen, `normalize_brand_theme` keeps the same shape,
`MEASURED_PAIRS`, `audit_contrast` and the 422 body are unchanged, and the
`PATCH /api/v1/tenant-profile` request body is byte-for-byte the one the pickers
already send. Nothing in this task needs a backend change: the paste is a second
way to fill a draft that already has a validated shape and a client-side
measurement (`lib/contrast.ts`) mirroring the server's.

Out of scope: simple mode (two pickers, no paste — there is nothing to paste),
dark-mode authoring rules, copy-out/export (see **Out of Scope** below), and any
change to the server preview or to the emitted-variables panel.

## Approach

### 1. The parser — `frontend/src/lib/brandPalettePaste.ts` (new)

A pure module with no React and no i18n strings: text in, either a parsed result
or a list of problems out. Problems are returned as `{ key, params }` pairs (i18n
keys under `tenantProfile.brand.paste.*`) so every visible string stays in
`pt.json`/`en.json`, as the rest of the component does.

Result shape: `{ ok: true; light: BrandPalette; dark: BrandPalette | null | undefined }`
or `{ ok: false; problems: PasteProblem[] }`. `dark: undefined` means the pasted
text said nothing about the dark scheme; `null` means it said `"dark": null`.

**Form detection is automatic, with no radio button.** The trimmed text is handed
to `JSON.parse`; if that succeeds and yields an object, the text is JSON,
otherwise it is parsed as CSS. `:root { --background: #fff; }` is not valid JSON,
so the split is unambiguous.

**JSON grammar — what is accepted.**

| Input | Accepted |
|---|---|
| `{"mode":"advanced","light":{…13…},"dark":{…13…}}` | yes |
| `{"mode":"advanced","light":{…13…},"dark":null}` | yes — sets derive-dark on |
| `{"light":{…13…}}` (no `mode` wrapper) | yes |
| A bare palette object: the thirteen keys at the top level | yes — read as `light` |
| `"mode"` present with any value other than `"advanced"` | **no** — refused naming the mode, pointing at simple mode's two fields |
| Keys other than `mode`/`light`/`dark` at the top level of a wrapped object | **no** |
| Trailing commas, `//` or `/* */` comments, unquoted keys, single quotes | **no** — strict `JSON.parse`; the refusal quotes the parser's own position |
| Arbitrary whitespace and newlines, any key order, uppercase hex | yes |

**CSS grammar — what is accepted.** A block of declarations, one per line or
separated by `;`:

| Input | Accepted |
|---|---|
| `--background: #f7f1e5;` | yes |
| `background: #f7f1e5;` (leading `--` omitted) | yes — `--` is optional and stripped |
| A missing `;` on the last declaration | yes |
| Blank lines, arbitrary indentation and inner whitespace | yes |
| `/* … */` comments, including multi-line | yes — stripped before parsing (a chunk of `index.css` carries them) |
| One wrapping selector block, e.g. `:root { … }` or `.dark { … }` | yes — everything up to and including the first `{`, and a trailing `}`, are dropped; the selector itself is ignored |
| A second `{` or `}` after that strip (two blocks pasted at once) | **no** — refused, naming that only one block is read |
| `oklch(L C H)` values (what the "Variáveis CSS emitidas" panel shows) | **no** — refused with a message saying this field takes `#rrggbb`, because that panel is the most likely place text is copied from |
| Named colours (`white`), 3-digit hex, `rgb()` | **no** — refused naming the key and the value |

CSS never carries a mode wrapper, so a CSS paste always fills **`light`** and
says nothing about dark (`dark: undefined`).

**Per-palette key and value rules, identical in both forms.** Exactly the
thirteen `BRAND_AUTHORED_KEYS`, no more and no fewer; each value must satisfy
`isValidHexColor` (`#rrggbb`, either case). Values are carried through **as
typed** — not lowercased — because the pickers do the same and the server is the
single normalisation point.

**Partial pastes are refused, and the thirteen must all be present.** The reasons
are worth recording: `_normalized_palette` requires `set(palette) == set(AUTHORED_KEYS)`
exactly, so a merged half-palette cannot be the thing the contract describes;
six of the eight `MEASURED_PAIRS` read two different keys, so a palette half
pasted and half left over from the previous condominium produces a contrast
verdict nobody authored; and a single colour is what the thirteen pickers are
already for. A missing key is refused with the missing keys named; an unknown key
is refused with that key named (never silently dropped — the server refuses it
too, and the two judgements must agree).

### 2. Where it lives in the UI — a header button opening a dialog

**Operator decision (2026-09-27): option B.** The paste field is reached from a
button in the section header and opens in a **dialog over the fields**. The
alternative considered and not chosen was option A, a collapsed block in place
above the thirteen fields.

* **The button.** In the `Cores da marca` header row (the same flex row that
  carries the title and the simple/advanced toggle), rendered **only in advanced
  mode**: `data-testid="brand-paste-open"`, label "Colar paleta", a
  `ClipboardPaste` icon, `aria-haspopup="dialog"`. Simple mode renders no button
  — there is nothing to paste into two pickers.
* **The dialog.** Mirrors the dialog this very page already hand-rolls for the
  slug change (`TenantProfilePage.tsx`, the `confirming` branch):
  `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing at its own
  `<h2>`, over `fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4`,
  panel `rounded-xl bg-card p-6 shadow-xl`, and it is mounted only while open.
  That shape, not `components/ui/alert-modal.tsx` — `AlertModal` takes a
  `message` and a single confirm button and cannot host a form — and not a new
  primitive or a new dependency. `data-testid="brand-paste-dialog"`.
* **Contents, input state.** The `<h2>` title, a one-line hint naming both
  accepted forms, a `<textarea data-brand-paste>`, and a footer with "Aplicar"
  and "Cancelar".

Because the dialog covers the thirteen fields while it is open, the operator
cannot watch them fill in behind it. Everything the operator has to judge —
what was applied, and any refusal — therefore happens **inside the dialog**
(§3), not behind it.

### 3. Applying: what the dialog shows, and where refusals render

"Aplicar" runs the parser on the textarea's text. Two outcomes, and the dialog
**never closes by itself** in either.

**Grammar refusal — the apply does not happen.** Nothing is written to the
draft, the thirteen fields keep their current values, and the dialog stays open
in its input state with the pasted text **kept verbatim** in the textarea (not
cleared, not reformatted). Every problem is listed in a `role="alert"` region
directly under the textarea, each naming the specific fault: malformed text with
the parser's own position, the missing keys, the unknown key, the key whose value
is not `#rrggbb`. Re-pressing "Aplicar" after an edit replaces the list.

**Apply succeeds — the dialog switches to a result state instead of closing.**
The parsed `light` replaces the draft's light palette through the existing
`edit(...)` path; an authored `dark` palette also replaces the dark draft and
clears the derive-dark checkbox; an explicit `"dark": null` sets it; an absent
`dark` leaves both exactly as they were. The dialog then shows, in place of its
input footer:

1. a confirmation line naming the count applied (thirteen, or twenty-six with a
   dark palette);
2. **the applied values, key by key:** thirteen rows of `key`, previous value,
   applied value, each with a swatch, rows whose value changed marked as changed;
3. **the draft preview** — the same `Preview` card described in §4, rendering the
   palette just applied (and a second card for an authored dark palette);
4. **the eight measured pairs** with their ratios. Reuse `lib/contrast.ts` and
   invent no ratio arithmetic — but **`readingsOf` cannot be handed a hex
   palette**. It calls `parseOklch` on each side and `continue`s when either
   returns `null`, so a draft of thirteen `#rrggbb` values yields an **empty
   list, silently** — a blank pair table, not an error. And `auditHexPalette`
   returns only the failures, never the five that pass. So the draft readings
   need the hex→`oklch()` conversion `auditHexPalette` already performs
   internally, lifted into something both can call — export a
   `readingsOfHexPalette`, or convert the draft once and pass the result to the
   existing `readingsOf`. Whichever is chosen, the dialog must show all eight
   pairs, the passing ones included, because the margin is the point;
5. a footer with "Desfazer" and "Fechar".

The dialog does not close immediately on success **because landing thirteen
values silently is the failure mode this task exists to avoid**: the whole
reason the operator wants a paste field is to change thirteen colours at once,
and a dialog that closes on success leaves them looking at thirteen changed
fields with no statement of what changed or whether it is legible. The result
state is that statement, and it is where requirement "preview before commit" is
satisfied now that the fields are covered.

**Contrast failures are not a refusal to apply — they block Save.** The paste
*is* applied; the client then measures. When any of the eight pairs is under
4,5:1 the result state carries, under the pair list, the section's existing
refusal wording (`refusalTitle`, `refusalBody`, `pairFail`) and a line saying
the palette cannot be saved until the pair is fixed. The operator may "Desfazer",
edit the text and re-apply, or "Fechar" and fix the offending field by hand.
Behind the dialog the section's own refusal panel is lit and Save is disabled by
the existing `blocked` — again with no new code path, because the applied values
land in the same draft the pickers write to.

**The failing pair reaches the operator before the request — this is the point
of the task.** Pasting the worked palette below with `muted-foreground` at
`#6f746e` must, on "Aplicar" and with **no request sent**, show inside the
dialog `muted-foreground/muted — 3,93:1, abaixo do mínimo de 4,5:1` and
`muted-foreground/background — 4,30:1, …`, and leave Save disabled. Those
figures were reproduced through `build_theme` → `audit_contrast` (`#6f746e`:
3.9300 on `muted`, 4.3005 on `background`, 4.8313 on `card`); `#5d625c` is the
first tone of the same family that clears every pair (5.0717 / 5.5499 / 6.2348),
and `audit_contrast` came back empty for it in both schemes.

**Dismissal semantics.**

| Gesture | Text only typed / refused | After a successful apply |
|---|---|---|
| "Cancelar" (input state) / "Fechar" (result state) | closes; the typed text is discarded; the draft is untouched | closes; the applied values **stay** in the draft |
| Escape | same as Cancelar | same as Fechar |
| Backdrop click | same as Cancelar | same as Fechar |

Closing is therefore **never an undo**. The one undo is the "Desfazer" button in
the result state: the dialog holds a snapshot of the pre-apply draft palette (and
the derive-dark flag) for as long as it stays open, and "Desfazer" writes that
snapshot back through `edit(...)` and returns to the input state with the pasted
text still in the textarea. The snapshot is dropped when the dialog closes, and
there is no undo after that — the section has never had one, and nothing has been
committed either: Save is still a separate, still-required press, the thirteen
fields remain editable by hand, and the draft preview (§4) is what shows the
operator what is pending. The button in the result state is labelled "Fechar",
not "Cancelar", so it cannot be read as an undo. Reopening the dialog always
starts with an empty textarea.

**Focus and keyboard.** The hand-rolled shape above provides the structure
(`role`, `aria-modal`, `aria-labelledby` on the title) but no behaviour, so this
task adds, scoped to this dialog: initial focus on the textarea when it opens;
Escape closing it, through a `keydown` effect mirroring the one in
`components/ui/alert-modal.tsx`; Tab and Shift+Tab cycling only among the panel's
own focusable elements; and focus returning to the `brand-paste-open` button when
it closes.

### 4. The draft preview

The existing `Preview` pair renders `profile.theme` — the server's answer — and
must keep doing so. A pasted palette has never been to the server, so advanced
mode additionally renders a **draft preview** in the section: one `Preview` card
for the authored light palette, and a second for the authored dark palette when
one is authored, labelled as the unsaved draft. The dialog's result state renders
the same component with the same props, which is why the operator sees the same
thing inside the dialog and, after closing it, in the section. It renders the
authored hexes verbatim and **derives nothing** — in advanced mode
`_advanced_scheme` emits the thirteen literally (2dp plus the gamut snap), so
painting the typed hex is showing what was authored, not a port of the
derivation, and the rule in this file's header comment (D-D: the client measures,
never derives) is untouched. Simple mode gets no draft preview and no paste
button.

### 5. Round-trip identity

`bodyFor(draft)` is not changed, and apply only writes `light`, `dark` and
`deriveDark` on the draft. A palette entered through the pickers and the same
palette pasted therefore produce an identical `PATCH` body, and the stored JSON
`normalize_brand_theme` returns is byte-identical.

### Files touched

* `frontend/src/lib/brandPalettePaste.ts` — new; the two grammars, the thirteen-key
  rule, the problem list.
* `frontend/src/lib/__tests__/brandPalettePaste.test.ts` — new; grammar table above,
  case by case.
* `frontend/src/features/user-administration/components/TenantBrandColors.tsx` —
  the advanced-mode header button, the paste dialog (input state, result state,
  problem region, snapshot/undo, focus and Escape handling), and the draft
  preview; no change to `bodyFor`, `draftFor` or the save/reset paths.
* `frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx` —
  open/close and dismissal cases, paste-accepted result state, paste-refused-for-contrast,
  paste-refused-for-grammar, undo, and round-trip identity.
* `frontend/src/i18n/locales/pt.json`, `frontend/src/i18n/locales/en.json` — the
  `tenantProfile.brand.paste.*` strings, in both locales (UI copy in Portuguese
  matches the rest of the section).
* `docs/tasks/APRAS-95-mock.html` — the visual reference (dialog input, accepted
  and refused states).

### Test criteria

Unit (`brandPalettePaste.test.ts`): each accepted and each refused row of the two
grammar tables; the worked palette in all four accepted JSON shapes yields the
same thirteen values; a CSS block copied with `:root { }`, comments and mixed
indentation yields the same thirteen; an `oklch()` value, a 3-digit hex, a
missing key and an unknown key each yield a problem naming the offending thing.

Component (`TenantProfilePage.brand.test.tsx`): the header button appears in
advanced mode only and opens a dialog with `aria-modal="true"`; pasting the
worked palette and pressing "Aplicar" leaves the dialog open showing the count,
the thirteen applied values and eight passing pairs, and after "Fechar" the
thirteen fields hold the pasted values and Save is enabled; pasting the `#6f746e`
variant shows both failing pairs with 3,93 and 4,30 inside the still-open dialog
and disables Save with no request sent; a malformed paste leaves the fields
untouched, keeps the pasted text in the textarea and lists the problem inside
the dialog; "Desfazer" restores the values the fields held before "Aplicar";
Escape and a backdrop click close the dialog and keep an applied palette;
pasting then saving sends exactly the body that typing the same thirteen sends.

## Expected Results

- [ ] In advanced mode of "Cores da marca" the section header carries a "Colar
      paleta" button; pressing it opens a dialog (`role="dialog"`,
      `aria-modal="true"`, labelled by its own title) containing a textarea,
      "Aplicar" and "Cancelar", over the thirteen colour fields. In simple mode
      the button is absent, and with the dialog closed the thirteen pickers are
      the only way to enter colours.
- [ ] Pasting `{"mode": "advanced", "light": {"background": "#f7f1e5", "foreground": "#1d2925", "card": "#ffffff", "card-foreground": "#1d2925", "primary": "#174b40", "primary-foreground": "#f7f1e5", "secondary": "#eee6d7", "secondary-foreground": "#082f2a", "accent": "#ead6a4", "accent-foreground": "#082f2a", "muted": "#eee6d7", "muted-foreground": "#5d625c", "border": "#ddd1b6"}}`
      into that textarea and pressing "Aplicar" does not close the dialog: the
      dialog states that thirteen values were applied, lists the thirteen keys
      with their previous and applied values, previews the applied palette, and
      shows the eight measured pairs all passing. Closing the dialog leaves those
      thirteen values in the thirteen fields with the save button enabled.
- [ ] Pasting the same object with `"muted-foreground": "#6f746e"` and pressing
      "Aplicar" sends no HTTP request and leaves the dialog open, and inside the
      dialog names both failing pairs with their ratios — `muted-foreground/muted`
      at 3,93 and `muted-foreground/background` at 4,30, against the 4,5 minimum —
      and says the palette cannot be saved. The save button is disabled both while
      the dialog is open and after it is closed, and the thirteen fields hold the
      pasted values afterwards, `muted-foreground: #6f746e` included — a contrast
      failure is not a refusal to apply, so an implementation that declined to
      apply would leave the previous palette standing, and that palette passes.
- [ ] A refused paste (a missing key, an unknown key, a value that is not a
      six-digit hex such as `oklch(0.55 0.01 140)` or `#fff`, or unparseable text)
      leaves the dialog open, keeps the pasted text unchanged in the textarea,
      lists one problem per fault naming the offending key or value inside the
      dialog, and leaves all thirteen colour fields with the values they had
      before "Aplicar".
- [ ] A CSS block of thirteen `--key: #hex;` declarations is accepted, including
      when wrapped in `:root { … }`, when it carries `/* … */` comments, and when
      the leading `--` is omitted; the fields end up with the same thirteen values
      the equivalent JSON produces.
- [ ] A partial paste is never merged onto the current fields: fewer than thirteen
      keys is always a refusal.
- [ ] After a successful "Aplicar", pressing "Desfazer" in the dialog puts the
      thirteen fields back to the values they held before "Aplicar". Closing the
      dialog with "Fechar", Escape or a click on the backdrop keeps the applied
      values instead, and offers no undo afterwards; doing the same before any
      successful "Aplicar" discards the typed text and changes no field.
- [ ] Opening the dialog moves focus into the textarea, Tab and Shift+Tab stay
      inside the dialog, Escape closes it, and closing it returns focus to the
      "Colar paleta" button. Reopening the dialog shows an empty textarea.
- [ ] Saving a palette that was pasted produces the same `PATCH /api/v1/tenant-profile`
      body as saving the same palette entered through the thirteen fields, and the
      stored `brand_theme` JSON is identical.
- [ ] Advanced mode shows a preview of the pasted palette before it is saved, both
      inside the dialog after "Aplicar" and in the section after the dialog closes,
      and that preview is distinct from the preview of the palette the server last
      returned.
- [ ] `backend/app/core/branding.py` is unchanged: `AUTHORED_KEYS` still holds
      thirteen keys, `MEASURED_PAIRS` still eight pairs, and the whole existing
      backend and frontend test suites pass.
- [ ] `docs/tasks/APRAS-95-mock.html` opens standalone and shows the header button,
      the dialog's input state, its accepted result state, and its refused states —
      the grammar refusal and the `#6f746e` contrast refusal with its measured 3,93
      on `muted` and 4,30 on `background`.

**Duplicate keys resolve last-wins, in both grammars.** A CSS block declaring
`--background` twice, or JSON with a repeated key, is accepted and the final
occurrence stands — `JSON.parse` already behaves that way and the CSS reader
matches it rather than contradicting the language it imitates. It is not an
error, because a palette assembled by hand from two sources is exactly how a
duplicate arises and the operator's intent is unambiguous.

The slug dialog this one mirrors has no Escape handler and no focus trap;
**APRAS-98** tracks fixing that. This task adds both to its own dialog and
changes `TenantProfilePage.tsx` not at all.

## Out of Scope

* **Copy-out / export.** Recommended as a follow-up task, not built here: the
  operator asked to paste in, and a copy-out of the *authored* thirteen hexes is
  a separate affordance with its own placement question (the existing "Variáveis
  CSS emitidas" panel already copies out the emitted `oklch()` values, which is
  not the same text). Adding it now would double the surface of a task whose
  point is the inbound direction.
* Any backend change, including a lenient JSON mode or a CSS-accepting endpoint.
* Simple mode, dark-mode derivation rules, and the server preview.
* A section-level undo history, or persisting the pasted text across dialog
  openings.
