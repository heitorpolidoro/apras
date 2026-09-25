# Unmapped colours — the ledger

Every Tailwind palette class this repository keeps **on purpose**, one row per
occurrence.

A task that meets a colour with no row in
[`theme-token-mapping.md`](./theme-token-mapping.md) — or one whose row it is
forbidden to apply — **leaves the class exactly as it is** and appends a line
here. Opened by APRAS-78 (child 1 of the APRAS-77 split); APRAS-79 … APRAS-85
append to it and may not rewrite what is already in it.

## The rules this file exists to enforce

**No child of APRAS-77 may add a property to `frontend/src/index.css`.** A
one-off token per call site turns the token set into landfill, and
`build_theme` emits exactly 18 keys, so a property added here would be
unbranded forever. The answer to "there is no token for this colour" is a row
in this file, never a new token. (APRAS-88 added the eighteenth,
`--primary-text`, as the mapping table's own amendment — to the stylesheet and
to `build_theme` in one change, and never at a call site.)

**The status-colour ruling (operator, binding and permanent).** Success,
warning and info colours **stay hard-coded** and are **never** migrated,
because a status colour is *semantic, not brand*: green means success in every
condominium, and a condominium whose brand is red must not see "success"
rendered in red. The ruling is about **not migrating**; it does not fix the
label. Each such class is logged under whichever code §1h's precedence
assigns — `GAP-TINT` where the family has a token that is deliberately
withheld (`emerald`, `red`), `GAP-NO-TOKEN` where the family has no token at
all (`amber`, `blue`). Both codes forbid migration equally, so only the
recorded label differs; the `why` column still names the role.

Two consequences are recorded so they are not rediscovered as bugs:

1. Those surfaces **never respond to the tenant's brand**. That is the
   intended behaviour, not a reach failure of APRAS-68.
2. They are still hard-coded *light-scheme* colours, so **the task that
   eventually enables the `.dark` block inherits them** and must resolve them
   there.

**The codes are a closed set of eight**, defined with their precedence in
[`theme-token-mapping.md` §1h](./theme-token-mapping.md#1h-gap-codes--the-closed-set).
Siblings may not add codes, add rows to the mapping table, or add tokens.

## The format

A single Markdown table, **append-only**, sorted by file then line, one row per
occurrence, with exactly these six columns:

- **task** — the Meridian id appending the row (`APRAS-78` … `APRAS-85`).
- **file** — repo-relative from the repository root.
- **line** — the line number at the time of writing. Drift is expected and is
  not an error; the guard does not check it.
- **class** — verbatim, variants and opacity included (`hover:bg-amber-600`,
  `bg-black/40`, `dark:text-slate-300`).
- **code** — one of the eight of §1h, verbatim.
- **why** — one sentence, at most 120 characters, naming the *role* the class
  plays, not restating the code.

Under a directory pinned in `frontend/src/__tests__/themeTokenMigration.test.ts`
every row here must also have an exact `(file, class, code)` entry in
`themeTokenMigration.exceptions.json`, and every such entry must have a row
here. The guard asserts both directions.

## The ledger

| task | file | line | class | code | why |
| --- | --- | --- | --- | --- | --- |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 28 | text-emerald-500 | GAP-TINT | success variant icon in the alert modal |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 29 | text-emerald-700 | GAP-TINT | success variant heading in the alert modal |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 30 | border-emerald-200 | GAP-TINT | success variant panel border in the alert modal |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 34 | text-amber-500 | GAP-NO-TOKEN | warning variant icon in the alert modal |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 35 | text-amber-700 | GAP-NO-TOKEN | warning variant heading in the alert modal |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 36 | border-amber-200 | GAP-NO-TOKEN | warning variant panel border in the alert modal |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 78 | bg-black/40 | GAP-OVERLAY | modal scrim behind the alert panel |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 122 | bg-amber-500 | GAP-NO-TOKEN | warning confirm button fill |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 122 | text-white | GAP-NO-SURFACE | label over the warning confirm button, whose amber fill carries no token |
| APRAS-78 | frontend/src/components/ui/alert-modal.tsx | 122 | hover:bg-amber-600 | GAP-NO-TOKEN | warning confirm button hover fill |
| APRAS-78 | frontend/src/components/ui/alert.tsx | 12 | border-emerald-500/50 | GAP-TINT | success alert border |
| APRAS-78 | frontend/src/components/ui/alert.tsx | 12 | text-emerald-700 | GAP-TINT | success alert text |
| APRAS-78 | frontend/src/components/ui/alert.tsx | 12 | bg-emerald-50 | GAP-TINT | success alert tint |
| APRAS-78 | frontend/src/components/ui/alert.tsx | 13 | border-amber-500/50 | GAP-NO-TOKEN | warning alert border |
| APRAS-78 | frontend/src/components/ui/alert.tsx | 13 | text-amber-700 | GAP-NO-TOKEN | warning alert text |
| APRAS-78 | frontend/src/components/ui/alert.tsx | 13 | bg-amber-50 | GAP-NO-TOKEN | warning alert tint |
| APRAS-78 | frontend/src/components/ui/badge.tsx | 32 | bg-emerald-100 | GAP-TINT | active-user badge tint |
| APRAS-78 | frontend/src/components/ui/badge.tsx | 32 | text-emerald-800 | GAP-TINT | active-user badge text, which holds 6.7502:1 on that tint today |
| APRAS-78 | frontend/src/components/ui/badge.tsx | 33 | bg-red-100 | GAP-TINT | inactive-user badge tint |
| APRAS-78 | frontend/src/components/ui/badge.tsx | 33 | text-red-800 | GAP-TINT | inactive-user badge text |
| APRAS-78 | frontend/src/components/ui/badge.tsx | 35 | bg-red-100 | GAP-TINT | destructive badge tint |
| APRAS-78 | frontend/src/components/ui/badge.tsx | 35 | text-red-800 | GAP-TINT | destructive badge text |
| APRAS-78 | frontend/src/components/ui/badge.tsx | 36 | bg-amber-100 | GAP-NO-TOKEN | warning badge tint |
| APRAS-78 | frontend/src/components/ui/badge.tsx | 36 | text-amber-800 | GAP-NO-TOKEN | warning badge text |

**APRAS-78 total — 24 occurrences:** 12 `GAP-TINT`, 10 `GAP-NO-TOKEN`,
1 `GAP-NO-SURFACE`, 1 `GAP-OVERLAY`. With the 7 occurrences the pilot
migrated, that accounts for all 31 palette occurrences in
`frontend/src/components/ui/`.

## APRAS-79 — `src/features/lot-management/components`

The nine files of the lot-management feature, child 2 of 8 of the APRAS-77
split. Nothing above this heading is rewritten.

| task | file | line | class | code | why |
| --- | --- | --- | --- | --- | --- |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 57 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 67 | bg-red-50 | GAP-TINT | error alert tint triple; the surface cannot move, so the text stays too. 4.4506:1 fails AA today, pre-existing |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 67 | text-red-600 | GAP-TINT | error alert tint triple; the surface cannot move, so the text stays too. 4.4506:1 fails AA today, pre-existing |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 67 | dark:bg-red-950/50 | GAP-TINT | error alert tint triple; the surface cannot move, so the text stays too. 4.4506:1 fails AA today, pre-existing |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 67 | dark:text-red-400 | GAP-TINT | error alert tint triple; the surface cannot move, so the text stays too. 4.4506:1 fails AA today, pre-existing |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 85 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 85 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 93 | divide-slate-100 | GAP-BORDER-100 | hairline divider between user rows; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 93 | dark:divide-slate-800 | GAP-BORDER-100 | hairline divider between user rows; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 98 | bg-emerald-50 | GAP-TINT | selected user row fill; emerald at scale 50 is resolved as a tint by scale alone |
| APRAS-79 | frontend/src/features/lot-management/components/LinkUserAccountModal.tsx | 98 | dark:bg-emerald-950/40 | GAP-TINT | selected user row fill; emerald at scale 50 is resolved as a tint by scale alone |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 57 | bg-purple-50 | GAP-SWATCH | Proprietario category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 57 | text-purple-700 | GAP-SWATCH | Proprietario category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 57 | ring-purple-600/20 | GAP-SWATCH | Proprietario category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 57 | dark:bg-purple-900/30 | GAP-SWATCH | Proprietario category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 57 | dark:text-purple-300 | GAP-SWATCH | Proprietario category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 63 | bg-blue-50 | GAP-SWATCH | Inquilino category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 63 | text-blue-700 | GAP-SWATCH | Inquilino category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 63 | ring-blue-700/10 | GAP-SWATCH | Inquilino category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 63 | dark:bg-blue-900/30 | GAP-SWATCH | Inquilino category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 63 | dark:text-blue-300 | GAP-SWATCH | Inquilino category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 69 | bg-emerald-50 | GAP-SWATCH | Responsavel financeiro category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 69 | text-emerald-700 | GAP-SWATCH | Responsavel financeiro category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 69 | ring-emerald-600/20 | GAP-SWATCH | Responsavel financeiro category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 69 | dark:bg-emerald-900/30 | GAP-SWATCH | Responsavel financeiro category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 69 | dark:text-emerald-300 | GAP-SWATCH | Responsavel financeiro category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 75 | bg-slate-50 | GAP-SWATCH | Outro (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 75 | text-slate-600 | GAP-SWATCH | Outro (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 75 | ring-slate-500/10 | GAP-SWATCH | Outro (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 75 | dark:bg-slate-800 | GAP-SWATCH | Outro (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 75 | dark:text-slate-400 | GAP-SWATCH | Outro (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 99 | border-slate-100 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 99 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 114 | bg-blue-100 | GAP-NO-TOKEN | VACANT status badge; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 114 | text-blue-800 | GAP-NO-TOKEN | VACANT status badge; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 114 | dark:bg-blue-900/40 | GAP-NO-TOKEN | VACANT status badge; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 114 | dark:text-blue-300 | GAP-NO-TOKEN | VACANT status badge; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 116 | bg-emerald-100 | GAP-TINT | OCCUPIED status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 116 | text-emerald-800 | GAP-TINT | OCCUPIED status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 116 | dark:bg-emerald-900/40 | GAP-TINT | OCCUPIED status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 116 | dark:text-emerald-300 | GAP-TINT | OCCUPIED status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 117 | bg-amber-100 | GAP-NO-TOKEN | UNDER_CONSTRUCTION status badge; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 117 | text-amber-800 | GAP-NO-TOKEN | UNDER_CONSTRUCTION status badge; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 117 | dark:bg-amber-900/40 | GAP-NO-TOKEN | UNDER_CONSTRUCTION status badge; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 117 | dark:text-amber-300 | GAP-NO-TOKEN | UNDER_CONSTRUCTION status badge; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 166 | hover:text-slate-700 | GAP-OUT-OF-BUDGET | inactive tab label on hover; every candidate for neutral body text exceeds the budget |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 166 | dark:hover:text-slate-300 | GAP-OUT-OF-BUDGET | inactive tab label on hover; every candidate for neutral body text exceeds the budget |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 177 | hover:text-slate-700 | GAP-OUT-OF-BUDGET | inactive tab label on hover; every candidate for neutral body text exceeds the budget |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 177 | dark:hover:text-slate-300 | GAP-OUT-OF-BUDGET | inactive tab label on hover; every candidate for neutral body text exceeds the budget |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 225 | bg-slate-100 | GAP-SWATCH | linked-user avatar circle fill, a data-encoding colour code 2 names by name |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 225 | text-slate-600 | GAP-SWATCH | linked-user avatar circle fill, a data-encoding colour code 2 names by name |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 225 | dark:bg-slate-800 | GAP-SWATCH | linked-user avatar circle fill, a data-encoding colour code 2 names by name |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 225 | dark:text-slate-300 | GAP-SWATCH | linked-user avatar circle fill, a data-encoding colour code 2 names by name |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 234 | bg-amber-100 | GAP-NO-TOKEN | primary-link tag; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 234 | text-amber-800 | GAP-NO-TOKEN | primary-link tag; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 234 | dark:bg-amber-900/50 | GAP-NO-TOKEN | primary-link tag; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 234 | dark:text-amber-300 | GAP-NO-TOKEN | primary-link tag; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 276 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 277 | border-red-200 | GAP-TINT | confirm dialog border; the heading beside it was judged free-standing and measured 4.8073:1, not a triple |
| APRAS-79 | frontend/src/features/lot-management/components/LotDetailsView.tsx | 277 | dark:border-red-900/50 | GAP-TINT | confirm dialog border; the heading beside it was judged free-standing and measured 4.8073:1, not a triple |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 94 | bg-black/50 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 96 | border-slate-100 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 96 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 112 | bg-red-50 | GAP-TINT | error alert tint triple holding 5.9842:1; migrating the text alone gives 4.4006:1 and fails AA |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 112 | text-red-700 | GAP-TINT | error alert tint triple holding 5.9842:1; migrating the text alone gives 4.4006:1 and fails AA |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 112 | dark:bg-red-900/30 | GAP-TINT | error alert tint triple holding 5.9842:1; migrating the text alone gives 4.4006:1 and fails AA |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 112 | dark:text-red-400 | GAP-TINT | error alert tint triple holding 5.9842:1; migrating the text alone gives 4.4006:1 and fails AA |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 119 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 119 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 130 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 130 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 143 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 143 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 155 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 155 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 165 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 165 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 177 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 177 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 191 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 191 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 197 | focus:border-blue-500 | GAP-NO-TOKEN | focus border; blue has no token at any scale and the operator note keeps focus rings blue |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 208 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 208 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 215 | focus:border-blue-500 | GAP-NO-TOKEN | focus border; blue has no token at any scale and the operator note keeps focus rings blue |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 220 | border-slate-100 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/LotFormModal.tsx | 220 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 33 | bg-blue-100 | GAP-NO-TOKEN | VACANT status badge; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 33 | text-blue-800 | GAP-NO-TOKEN | VACANT status badge; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 33 | dark:bg-blue-900/40 | GAP-NO-TOKEN | VACANT status badge; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 33 | dark:text-blue-300 | GAP-NO-TOKEN | VACANT status badge; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 39 | bg-emerald-100 | GAP-TINT | OCCUPIED status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 39 | text-emerald-800 | GAP-TINT | OCCUPIED status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 39 | dark:bg-emerald-900/40 | GAP-TINT | OCCUPIED status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 39 | dark:text-emerald-300 | GAP-TINT | OCCUPIED status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 45 | bg-amber-100 | GAP-NO-TOKEN | UNDER_CONSTRUCTION status badge; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 45 | text-amber-800 | GAP-NO-TOKEN | UNDER_CONSTRUCTION status badge; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 45 | dark:bg-amber-900/40 | GAP-NO-TOKEN | UNDER_CONSTRUCTION status badge; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 45 | dark:text-amber-300 | GAP-NO-TOKEN | UNDER_CONSTRUCTION status badge; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 143 | text-blue-600 | GAP-NO-TOKEN | primary lot marker icon; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 143 | dark:text-blue-400 | GAP-NO-TOKEN | primary lot marker icon; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 152 | text-amber-600 | GAP-NO-TOKEN | unlink warning icon; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotTable.tsx | 152 | dark:text-amber-400 | GAP-NO-TOKEN | unlink warning icon; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/LotsPage.tsx | 161 | focus:border-blue-500 | GAP-NO-TOKEN | focus border; blue has no token at any scale and the operator note keeps focus rings blue |
| APRAS-79 | frontend/src/features/lot-management/components/LotsPage.tsx | 174 | focus:border-blue-500 | GAP-NO-TOKEN | focus border; blue has no token at any scale and the operator note keeps focus rings blue |
| APRAS-79 | frontend/src/features/lot-management/components/LotsPage.tsx | 236 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-79 | frontend/src/features/lot-management/components/LotsPage.tsx | 237 | border-red-200 | GAP-TINT | confirm dialog border; the heading beside it was judged free-standing and measured 4.8073:1, not a triple |
| APRAS-79 | frontend/src/features/lot-management/components/LotsPage.tsx | 237 | dark:border-red-900/50 | GAP-TINT | confirm dialog border; the heading beside it was judged free-standing and measured 4.8073:1, not a triple |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 92 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 99 | bg-red-50 | GAP-TINT | error alert tint triple; the surface cannot move, so the text stays too. 4.4506:1 fails AA today, pre-existing |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 99 | text-red-600 | GAP-TINT | error alert tint triple; the surface cannot move, so the text stays too. 4.4506:1 fails AA today, pre-existing |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 99 | dark:bg-red-950/50 | GAP-TINT | error alert tint triple; the surface cannot move, so the text stays too. 4.4506:1 fails AA today, pre-existing |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 99 | dark:text-red-400 | GAP-TINT | error alert tint triple; the surface cannot move, so the text stays too. 4.4506:1 fails AA today, pre-existing |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 106 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 106 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 121 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 121 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 134 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 134 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 149 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 149 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 160 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 160 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 180 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 180 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 192 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 192 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 206 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentFormModal.tsx | 206 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 30 | bg-purple-50 | GAP-SWATCH | Proprietario relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 30 | text-purple-700 | GAP-SWATCH | Proprietario relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 30 | ring-purple-700/10 | GAP-SWATCH | Proprietario relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 30 | dark:bg-purple-900/30 | GAP-SWATCH | Proprietario relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 30 | dark:text-purple-300 | GAP-SWATCH | Proprietario relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 36 | bg-pink-50 | GAP-SWATCH | Conjuge relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 36 | text-pink-700 | GAP-SWATCH | Conjuge relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 36 | ring-pink-700/10 | GAP-SWATCH | Conjuge relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 36 | dark:bg-pink-900/30 | GAP-SWATCH | Conjuge relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 36 | dark:text-pink-300 | GAP-SWATCH | Conjuge relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 42 | bg-blue-50 | GAP-SWATCH | Inquilino relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 42 | text-blue-700 | GAP-SWATCH | Inquilino relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 42 | ring-blue-700/10 | GAP-SWATCH | Inquilino relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 42 | dark:bg-blue-900/30 | GAP-SWATCH | Inquilino relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 42 | dark:text-blue-300 | GAP-SWATCH | Inquilino relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 48 | bg-emerald-50 | GAP-SWATCH | Filho relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 48 | text-emerald-700 | GAP-SWATCH | Filho relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 48 | ring-emerald-600/20 | GAP-SWATCH | Filho relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 48 | dark:bg-emerald-900/30 | GAP-SWATCH | Filho relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 48 | dark:text-emerald-300 | GAP-SWATCH | Filho relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 54 | bg-amber-50 | GAP-SWATCH | Dependente relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 54 | text-amber-700 | GAP-SWATCH | Dependente relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 54 | ring-amber-600/20 | GAP-SWATCH | Dependente relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 54 | dark:bg-amber-900/30 | GAP-SWATCH | Dependente relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 54 | dark:text-amber-300 | GAP-SWATCH | Dependente relationship category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 60 | bg-slate-50 | GAP-SWATCH | Outro relationship (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 60 | text-slate-600 | GAP-SWATCH | Outro relationship (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 60 | ring-slate-500/10 | GAP-SWATCH | Outro relationship (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 60 | dark:bg-slate-800 | GAP-SWATCH | Outro relationship (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 60 | dark:text-slate-400 | GAP-SWATCH | Outro relationship (default branch) category badge swatch: one hue per enum value, must not follow the tenant brand |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 107 | bg-emerald-100 | GAP-SWATCH | resident avatar circle fill, a data-encoding colour code 2 names by name |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 107 | text-emerald-800 | GAP-SWATCH | resident avatar circle fill, a data-encoding colour code 2 names by name |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 107 | dark:bg-emerald-900/40 | GAP-SWATCH | resident avatar circle fill, a data-encoding colour code 2 names by name |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 107 | dark:text-emerald-300 | GAP-SWATCH | resident avatar circle fill, a data-encoding colour code 2 names by name |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 125 | text-emerald-700 | GAP-TINT | linked-user chip; a status tint whose surface, border and text migrate as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 125 | dark:text-emerald-400 | GAP-TINT | linked-user chip; a status tint whose surface, border and text migrate as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 125 | bg-emerald-50 | GAP-TINT | linked-user chip; a status tint whose surface, border and text migrate as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 125 | dark:bg-emerald-950/40 | GAP-TINT | linked-user chip; a status tint whose surface, border and text migrate as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 125 | border-emerald-200 | GAP-TINT | linked-user chip; a status tint whose surface, border and text migrate as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 125 | dark:border-emerald-800/50 | GAP-TINT | linked-user chip; a status tint whose surface, border and text migrate as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 154 | bg-emerald-100 | GAP-TINT | is_active status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 154 | text-emerald-800 | GAP-TINT | is_active status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 154 | dark:bg-emerald-900/40 | GAP-TINT | is_active status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 154 | dark:text-emerald-300 | GAP-TINT | is_active status badge; success tint, a token that exists and is deliberately withheld |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 155 | bg-slate-100 | GAP-TINT | inactive status badge; the neutral member of the is_active status pair, which migrates as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 155 | text-slate-600 | GAP-TINT | inactive status badge; the neutral member of the is_active status pair, which migrates as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 155 | dark:bg-slate-800 | GAP-TINT | inactive status badge; the neutral member of the is_active status pair, which migrates as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 155 | dark:text-slate-400 | GAP-TINT | inactive status badge; the neutral member of the is_active status pair, which migrates as a unit or not at all |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 181 | text-amber-600 | GAP-NO-TOKEN | unlink warning icon; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentTable.tsx | 181 | dark:text-amber-400 | GAP-NO-TOKEN | unlink warning icon; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentsTab.tsx | 175 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentsTab.tsx | 176 | border-red-200 | GAP-TINT | confirm dialog border; the heading beside it was judged free-standing and measured 4.8073:1, not a triple |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentsTab.tsx | 176 | dark:border-red-900/50 | GAP-TINT | confirm dialog border; the heading beside it was judged free-standing and measured 4.8073:1, not a triple |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentsTab.tsx | 197 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentsTab.tsx | 198 | border-amber-200 | GAP-NO-TOKEN | unlink warning dialog border; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentsTab.tsx | 198 | dark:border-amber-900/50 | GAP-NO-TOKEN | unlink warning dialog border; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentsTab.tsx | 199 | text-amber-600 | GAP-NO-TOKEN | unlink warning icon; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/ResidentsTab.tsx | 199 | dark:text-amber-400 | GAP-NO-TOKEN | unlink warning icon; amber has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 73 | bg-black/50 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 75 | border-slate-100 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 75 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 91 | bg-red-50 | GAP-TINT | error alert tint triple holding 5.9842:1; migrating the text alone gives 4.4006:1 and fails AA |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 91 | text-red-700 | GAP-TINT | error alert tint triple holding 5.9842:1; migrating the text alone gives 4.4006:1 and fails AA |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 91 | dark:bg-red-900/30 | GAP-TINT | error alert tint triple holding 5.9842:1; migrating the text alone gives 4.4006:1 and fails AA |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 91 | dark:text-red-400 | GAP-TINT | error alert tint triple holding 5.9842:1; migrating the text alone gives 4.4006:1 and fails AA |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 97 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 97 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 107 | focus:border-blue-500 | GAP-NO-TOKEN | focus border; blue has no token at any scale and the operator note keeps focus rings blue |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 120 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 120 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 126 | focus:border-blue-500 | GAP-NO-TOKEN | focus border; blue has no token at any scale and the operator note keeps focus rings blue |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 149 | text-blue-600 | GAP-NO-TOKEN | primary checkbox accent and focus ring; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 149 | focus:ring-blue-500 | GAP-NO-TOKEN | primary checkbox accent and focus ring; blue has no token at any scale |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 149 | dark:bg-slate-800 | GAP-OUT-OF-BUDGET | orphan dark checkbox fill with no light base; every surface candidate exceeds the budget |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 153 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 153 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 161 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 161 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 171 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 171 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 182 | border-slate-100 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-79 | frontend/src/features/lot-management/components/UserLotAssignmentModal.tsx | 182 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |

**APRAS-79 total — 211 occurrences:** 58 `GAP-SWATCH`, 49
`GAP-OUT-OF-BUDGET`, 46 `GAP-TINT`, 38 `GAP-NO-TOKEN`, 12 `GAP-BORDER-100`,
8 `GAP-OVERLAY`.
With the 166 occurrences migrated to a token and the 143 `dark:` siblings
deleted alongside them (§1g), that accounts for all 520 palette occurrences in
`frontend/src/features/lot-management/components/`. The 211 occupy
**148** distinct `(file, class)` pairs, which is the number of entries
appended to `themeTokenMigration.exceptions.json`; eleven pairs play two
roles in one file and carry the code §1h's precedence puts first.

| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 56 | border-white | GAP-NO-SURFACE | ring around the timeline dot, over a kept palette fill that carries no token |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 56 | bg-slate-100 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 56 | dark:border-slate-900 | GAP-NO-SURFACE | ring around the timeline dot, over a kept palette fill that carries no token |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 58 | bg-emerald-100 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 58 | text-emerald-600 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 58 | dark:bg-emerald-950 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 58 | dark:text-emerald-400 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 59 | bg-slate-100 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 59 | text-slate-500 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 59 | dark:bg-slate-800 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 59 | dark:text-slate-400 | GAP-TINT | timeline status dot; the success and neutral state tints are semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 78 | bg-emerald-50 | GAP-TINT | on-site status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 78 | text-emerald-700 | GAP-TINT | on-site status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 78 | dark:bg-emerald-950/50 | GAP-TINT | on-site status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 78 | dark:text-emerald-400 | GAP-TINT | on-site status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 82 | bg-slate-100 | GAP-TINT | left-site status badge tint, the same ternary as the on-site branch; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 82 | text-slate-600 | GAP-TINT | left-site status badge tint, the same ternary as the on-site branch; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 82 | dark:bg-slate-800 | GAP-TINT | left-site status badge tint, the same ternary as the on-site branch; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 82 | dark:text-slate-400 | GAP-TINT | left-site status badge tint, the same ternary as the on-site branch; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 98 | bg-amber-600 | GAP-NO-TOKEN | check-out button fill; amber has no token at any scale |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 98 | text-white | GAP-NO-SURFACE | check-out button label over bg-amber-600, a palette colour with no row |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 98 | hover:bg-amber-700 | GAP-NO-TOKEN | check-out button fill; amber has no token at any scale |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 106 | border-slate-100 | GAP-BORDER-100 | hairline divider inside a card; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 106 | dark:border-slate-800/80 | GAP-BORDER-100 | hairline divider inside a card; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 108 | text-slate-700 | GAP-OUT-OF-BUDGET | inline time label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 108 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | inline time label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 115 | text-slate-700 | GAP-OUT-OF-BUDGET | inline time label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AccessLogTimeline.tsx | 115 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | inline time label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 113 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 115 | border-slate-100 | GAP-BORDER-100 | hairline divider under the modal header; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 115 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider under the modal header; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 131 | border-red-200 | GAP-TINT | error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 131 | bg-red-50 | GAP-TINT | error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 131 | text-red-700 | GAP-TINT | error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 131 | dark:border-red-900/50 | GAP-TINT | error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 131 | dark:bg-red-950/50 | GAP-TINT | error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 131 | dark:text-red-400 | GAP-TINT | error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 140 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 140 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 208 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 208 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 218 | text-slate-700 | GAP-OUT-OF-BUDGET | unselected option label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 218 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | unselected option label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 229 | text-slate-700 | GAP-OUT-OF-BUDGET | unselected option label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 229 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | unselected option label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 239 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 239 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 265 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 265 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 298 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 298 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 309 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 309 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 323 | text-slate-700 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 323 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form field label; every candidate for neutral body text exceeds the budget (published 17.93) |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 334 | border-slate-100 | GAP-BORDER-100 | hairline divider above the modal footer; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx | 334 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider above the modal footer; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationQrModal.tsx | 57 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationQrModal.tsx | 59 | border-slate-100 | GAP-BORDER-100 | hairline divider under the modal header; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/AuthorizationQrModal.tsx | 59 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider under the modal header; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 159 | border-red-200 | GAP-TINT | scan error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 159 | bg-red-50 | GAP-TINT | scan error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 159 | text-red-700 | GAP-TINT | scan error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 159 | dark:border-red-900/50 | GAP-TINT | scan error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 159 | dark:bg-red-950/50 | GAP-TINT | scan error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 159 | dark:text-red-400 | GAP-TINT | scan error alert tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 206 | divide-slate-100 | GAP-BORDER-100 | hairline row divider in the search result list; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 206 | dark:divide-slate-800/80 | GAP-BORDER-100 | hairline row divider in the search result list; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 318 | border-slate-100 | GAP-BORDER-100 | hairline divider between package rows; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx | 318 | dark:border-slate-800/80 | GAP-BORDER-100 | hairline divider between package rows; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 47 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 49 | border-slate-100 | GAP-BORDER-100 | hairline divider under the modal header; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 49 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider under the modal header; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 65 | bg-emerald-50 | GAP-TINT | valid access banner tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 65 | text-emerald-800 | GAP-TINT | valid access banner tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 65 | dark:bg-emerald-950/50 | GAP-TINT | valid access banner tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 65 | dark:text-emerald-300 | GAP-TINT | valid access banner tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 66 | bg-red-50 | GAP-TINT | invalid access banner tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 66 | text-red-800 | GAP-TINT | invalid access banner tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 66 | dark:bg-red-950/50 | GAP-TINT | invalid access banner tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 66 | dark:text-red-300 | GAP-TINT | invalid access banner tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 70 | text-emerald-600 | GAP-TINT | valid access banner icon, the same variant as the banner; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 70 | dark:text-emerald-400 | GAP-TINT | valid access banner icon, the same variant as the banner; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 72 | text-red-600 | GAP-TINT | invalid access banner icon, the same variant as the banner; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 72 | dark:text-red-400 | GAP-TINT | invalid access banner icon, the same variant as the banner; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 80 | bg-red-50 | GAP-TINT | check-in error box tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 80 | text-red-700 | GAP-TINT | check-in error box tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 80 | dark:bg-red-950/50 | GAP-TINT | check-in error box tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/GatekeeperEntryModal.tsx | 80 | dark:text-red-400 | GAP-TINT | check-in error box tint; the surface has no row, so the text cannot migrate alone without failing AA |
| APRAS-80 | frontend/src/features/visitor-management/components/QrScannerModal.tsx | 57 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-80 | frontend/src/features/visitor-management/components/QrScannerModal.tsx | 59 | border-slate-100 | GAP-BORDER-100 | hairline divider under the modal header; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/QrScannerModal.tsx | 59 | dark:border-slate-800 | GAP-BORDER-100 | hairline divider under the modal header; applying border would make it read as a border |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorAuthPage.tsx | 143 | bg-black/40 | GAP-OVERLAY | modal scrim; no overlay token exists |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorAuthPage.tsx | 144 | border-red-200 | GAP-TINT | revoke dialog border; the red border has no row while the panel surface takes its own row |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorAuthPage.tsx | 144 | dark:border-red-900/50 | GAP-TINT | revoke dialog border; the red border has no row while the panel surface takes its own row |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 26 | bg-emerald-50 | GAP-TINT | active status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 26 | text-emerald-700 | GAP-TINT | active status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 26 | dark:bg-emerald-950/50 | GAP-TINT | active status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 26 | dark:text-emerald-400 | GAP-TINT | active status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 33 | bg-amber-50 | GAP-NO-TOKEN | expired status badge tint; amber has no token at any scale |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 33 | text-amber-700 | GAP-NO-TOKEN | expired status badge tint; amber has no token at any scale |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 33 | dark:bg-amber-950/50 | GAP-NO-TOKEN | expired status badge tint; amber has no token at any scale |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 33 | dark:text-amber-400 | GAP-NO-TOKEN | expired status badge tint; amber has no token at any scale |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 40 | bg-red-50 | GAP-TINT | revoked status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 40 | text-red-700 | GAP-TINT | revoked status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 40 | dark:bg-red-950/50 | GAP-TINT | revoked status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 40 | dark:text-red-400 | GAP-TINT | revoked status badge tint; semantic status colour, never brand |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 119 | text-red-600 | GAP-TINT | revoke control tint; the border and hover fill have no row, so the text cannot migrate alone |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 119 | border-red-200 | GAP-TINT | revoke control tint; the border and hover fill have no row, so the text cannot migrate alone |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 119 | hover:bg-red-50 | GAP-TINT | revoke control tint; the border and hover fill have no row, so the text cannot migrate alone |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 119 | dark:text-red-400 | GAP-TINT | revoke control tint; the border and hover fill have no row, so the text cannot migrate alone |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 119 | dark:border-red-900/50 | GAP-TINT | revoke control tint; the border and hover fill have no row, so the text cannot migrate alone |
| APRAS-80 | frontend/src/features/visitor-management/components/VisitorTable.tsx | 119 | dark:hover:bg-red-950/50 | GAP-TINT | revoke control tint; the border and hover fill have no row, so the text cannot migrate alone |

**APRAS-80 total — 113 occurrences:** 61 `GAP-TINT`, 22
`GAP-OUT-OF-BUDGET`, 16 `GAP-BORDER-100`, 6 `GAP-NO-TOKEN`, 5 `GAP-OVERLAY`,
3 `GAP-NO-SURFACE`.
With the 193 occurrences migrated to a token and the 158 `dark:` siblings
deleted alongside them (§1g), that accounts for all 464 palette occurrences in
`frontend/src/features/visitor-management/components/`. The two halves close
independently: 254 non-`dark:` = 193 + 61, and 210 `dark:` = 158 + 52. The 113
occupy **84** distinct `(file, class)` pairs, which is the number of entries
appended to `themeTokenMigration.exceptions.json`.

## APRAS-82 — `document-management` and `occurrence-management`

Child 5 of 8. Two directories, because the operator scoped this child that
way: `frontend/src/features/document-management/components` (six files) and
`frontend/src/features/occurrence-management/components` (five files).

| task | file | line | class | code | why |
| --- | --- | --- | --- | --- | --- |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 38 | text-slate-300 | GAP-OUT-OF-BUDGET | empty-state icon tint; slate-300 is outside the neutral band the mapping table budgets |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 38 | dark:text-slate-600 | GAP-OUT-OF-BUDGET | empty-state icon tint; slate-300 is outside the neutral band the mapping table budgets |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 39 | text-slate-800 | GAP-OUT-OF-BUDGET | empty-state heading; slate-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 39 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | empty-state heading; slate-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 66 | text-slate-700 | GAP-OUT-OF-BUDGET | table body text; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 66 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | table body text; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 143 | hover:text-emerald-600 | GAP-TINT | download control tint; the hover fill has no row, so the pair cannot migrate alone |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 143 | hover:bg-emerald-50 | GAP-TINT | download control tint; the hover fill has no row, so the pair cannot migrate alone |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 143 | dark:hover:bg-emerald-950/50 | GAP-TINT | download control tint; the hover fill has no row, so the pair cannot migrate alone |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 143 | dark:hover:text-emerald-400 | GAP-TINT | download control tint; the hover fill has no row, so the pair cannot migrate alone |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 166 | hover:text-rose-600 | GAP-NO-TOKEN | delete control tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 166 | hover:bg-rose-50 | GAP-NO-TOKEN | delete control tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 166 | dark:hover:bg-rose-950/50 | GAP-NO-TOKEN | delete control tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/document-management/components/DocumentGridTable.tsx | 166 | dark:hover:text-rose-400 | GAP-NO-TOKEN | delete control tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 143 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 143 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 165 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 165 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 178 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 178 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 192 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 192 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 205 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 205 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 222 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 222 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 234 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/DocumentUploadModal.tsx | 234 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 124 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 124 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 137 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 137 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 155 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 155 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 162 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 162 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 177 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderFormModal.tsx | 177 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderTreeSidebar.tsx | 47 | text-slate-700 | GAP-OUT-OF-BUDGET | tree row resting text; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderTreeSidebar.tsx | 47 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | tree row resting text; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderTreeSidebar.tsx | 121 | hover:text-rose-600 | GAP-NO-TOKEN | delete control tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/document-management/components/FolderTreeSidebar.tsx | 121 | dark:hover:text-rose-400 | GAP-NO-TOKEN | delete control tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/document-management/components/FolderTreeSidebar.tsx | 188 | text-slate-700 | GAP-OUT-OF-BUDGET | tree row resting text; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/document-management/components/FolderTreeSidebar.tsx | 188 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | tree row resting text; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 55 | bg-black/40 | GAP-OVERLAY | modal scrim over the page; black is an overlay, not a surface, and has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 72 | text-gray-700 | GAP-OUT-OF-BUDGET | form label weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 78 | text-gray-800 | GAP-OUT-OF-BUDGET | form control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 90 | text-gray-700 | GAP-OUT-OF-BUDGET | form label weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 99 | text-gray-800 | GAP-OUT-OF-BUDGET | form control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 104 | text-gray-700 | GAP-OUT-OF-BUDGET | form label weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 113 | text-gray-800 | GAP-OUT-OF-BUDGET | form control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 118 | text-gray-700 | GAP-OUT-OF-BUDGET | form label weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 126 | text-gray-800 | GAP-OUT-OF-BUDGET | form control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 139 | text-gray-800 | GAP-OUT-OF-BUDGET | form control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 157 | text-gray-800 | GAP-OUT-OF-BUDGET | form control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 158 | text-emerald-600 | GAP-TINT | visibility glyph pair; a non-interactive status glyph and its neutral ternary partner stay together |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 158 | text-gray-500 | GAP-TINT | visibility glyph pair; a non-interactive status glyph and its neutral ternary partner stay together |
| APRAS-82 | frontend/src/features/occurrence-management/components/NewOccurrenceModal.tsx | 172 | text-gray-700 | GAP-OUT-OF-BUDGET | form label weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceBookPage.tsx | 62 | text-gray-700 | GAP-OUT-OF-BUDGET | filter bar heading; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceBookPage.tsx | 76 | text-gray-800 | GAP-OUT-OF-BUDGET | filter control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceBookPage.tsx | 84 | text-gray-800 | GAP-OUT-OF-BUDGET | filter control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceBookPage.tsx | 99 | text-gray-800 | GAP-OUT-OF-BUDGET | filter control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceBookPage.tsx | 116 | text-gray-800 | GAP-OUT-OF-BUDGET | filter control text; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 39 | bg-black/40 | GAP-OVERLAY | modal scrim over the page; black is an overlay, not a surface, and has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 61 | bg-black/40 | GAP-OVERLAY | modal scrim over the page; black is an overlay, not a surface, and has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 71 | text-emerald-700 | GAP-TINT | public visibility badge tint; a status colour, never brand, and its surface has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 71 | bg-emerald-50 | GAP-TINT | public visibility badge tint; a status colour, never brand, and its surface has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 71 | border-emerald-200 | GAP-TINT | public visibility badge tint; a status colour, never brand, and its surface has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 76 | text-gray-600 | GAP-TINT | private visibility badge tint; the ternary partner of a status badge stays with it |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 76 | bg-gray-100 | GAP-TINT | private visibility badge tint; the ternary partner of a status badge stays with it |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 76 | border-gray-200 | GAP-TINT | private visibility badge tint; the ternary partner of a status badge stays with it |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 101 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 111 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 119 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 128 | text-gray-700 | GAP-OUT-OF-BUDGET | section heading weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 131 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 139 | text-gray-700 | GAP-OUT-OF-BUDGET | section heading weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 160 | bg-emerald-50 | GAP-TINT | resolution panel tint; a status colour whose surface has no row, so the set stays whole |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 160 | border-emerald-200 | GAP-TINT | resolution panel tint; a status colour whose surface has no row, so the set stays whole |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 161 | text-emerald-900 | GAP-TINT | resolution panel tint; a status colour whose surface has no row, so the set stays whole |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 162 | text-emerald-600 | GAP-TINT | resolution panel tint; a status colour whose surface has no row, so the set stays whole |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 165 | text-emerald-800 | GAP-TINT | resolution panel tint; a status colour whose surface has no row, so the set stays whole |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 172 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 179 | text-gray-700 | GAP-OUT-OF-BUDGET | form label weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 185 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 196 | text-gray-700 | GAP-OUT-OF-BUDGET | form label weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 202 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 213 | text-gray-700 | GAP-OUT-OF-BUDGET | form label weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceDetailsView.tsx | 221 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 22 | bg-amber-50 | GAP-NO-TOKEN | open status badge tint; amber has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 22 | text-amber-700 | GAP-NO-TOKEN | open status badge tint; amber has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 22 | border-amber-200 | GAP-NO-TOKEN | open status badge tint; amber has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 24 | bg-blue-50 | GAP-NO-TOKEN | under-review status badge tint; blue has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 24 | text-blue-700 | GAP-NO-TOKEN | under-review status badge tint; blue has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 24 | border-blue-200 | GAP-NO-TOKEN | under-review status badge tint; blue has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 26 | bg-indigo-50 | GAP-TINT | in-progress status badge tint; a status colour, never brand, and the set migrates as a unit or not at all |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 26 | text-indigo-700 | GAP-TINT | in-progress status badge tint; a status colour, never brand, and the set migrates as a unit or not at all |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 26 | border-indigo-200 | GAP-TINT | in-progress status badge tint; a status colour, never brand, and the set migrates as a unit or not at all |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 28 | bg-emerald-50 | GAP-TINT | resolved status badge tint; a status colour, never brand, and its surface has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 28 | text-emerald-700 | GAP-TINT | resolved status badge tint; a status colour, never brand, and its surface has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 28 | border-emerald-200 | GAP-TINT | resolved status badge tint; a status colour, never brand, and its surface has no row |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 30 | bg-rose-50 | GAP-NO-TOKEN | rejected status badge tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 30 | text-rose-700 | GAP-NO-TOKEN | rejected status badge tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 30 | border-rose-200 | GAP-NO-TOKEN | rejected status badge tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 32 | bg-gray-50 | GAP-TINT | default status badge tint; the neutral branch stays with the five coloured branches of its set |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 32 | text-gray-700 | GAP-TINT | default status badge tint; the neutral branch stays with the five coloured branches of its set |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 32 | border-gray-200 | GAP-TINT | default status badge tint; the neutral branch stays with the five coloured branches of its set |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 39 | bg-rose-100 | GAP-NO-TOKEN | urgent priority badge tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 39 | text-rose-800 | GAP-NO-TOKEN | urgent priority badge tint; rose has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 41 | bg-orange-100 | GAP-NO-TOKEN | high priority badge tint; orange has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 41 | text-orange-800 | GAP-NO-TOKEN | high priority badge tint; orange has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 43 | bg-sky-100 | GAP-NO-TOKEN | medium priority badge tint; sky has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 43 | text-sky-800 | GAP-NO-TOKEN | medium priority badge tint; sky has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 45 | bg-gray-100 | GAP-TINT | low priority badge tint; the neutral branch stays with the three coloured branches of its set |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 45 | text-gray-700 | GAP-TINT | low priority badge tint; the neutral branch stays with the three coloured branches of its set |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 86 | divide-gray-100 | GAP-BORDER-100 | hairline row divider; the 100 step is below the weight the border token carries |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 93 | text-gray-800 | GAP-OUT-OF-BUDGET | category chip label; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 100 | text-emerald-600 | GAP-TINT | visibility glyph pair; a non-interactive status glyph and its neutral ternary partner stay together |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 102 | text-gray-400 | GAP-TINT | visibility glyph pair; a non-interactive status glyph and its neutral ternary partner stay together |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTable.tsx | 125 | text-gray-700 | GAP-OUT-OF-BUDGET | reporter cell weight; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 57 | ring-gray-100 | GAP-BORDER-100 | timeline dot halo; the 100 step is below the weight the border token carries |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 58 | border-gray-100 | GAP-BORDER-100 | timeline card hairline; the 100 step is below the weight the border token carries |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 67 | text-amber-700 | GAP-NO-TOKEN | internal-note badge tint; amber has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 67 | bg-amber-50 | GAP-NO-TOKEN | internal-note badge tint; amber has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 67 | border-amber-200 | GAP-NO-TOKEN | internal-note badge tint; amber has no token at any scale |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 80 | text-gray-700 | GAP-OUT-OF-BUDGET | timeline note body; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 87 | text-gray-800 | GAP-OUT-OF-BUDGET | note form heading; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 102 | text-gray-700 | GAP-OUT-OF-BUDGET | internal-only checkbox label; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-82 | frontend/src/features/occurrence-management/components/OccurrenceTimelineLog.tsx | 117 | text-gray-700 | GAP-OUT-OF-BUDGET | status select text; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |

**APRAS-82 total — 129 occurrences:** 69 `GAP-OUT-OF-BUDGET`, 30 `GAP-TINT`,
24 `GAP-NO-TOKEN`, 3 `GAP-OVERLAY`, 3 `GAP-BORDER-100`. No `GAP-SWATCH`, no
`GAP-NO-SURFACE`, no `GAP-UNLISTED`.
With the 240 occurrences migrated to a token and the 78 `dark:` siblings
deleted alongside them (§1g), that accounts for all 447 palette occurrences in
the two directories. The two halves close independently: 347 non-`dark:` =
240 + 107, and 100 `dark:` = 78 + 22. Per directory, 44 of the 129 stay in
`document-management` and 85 in `occurrence-management`. The 129 occupy **77**
distinct `(file, class)` pairs — 22 in `document-management`, 55 in
`occurrence-management` — which is the number of entries appended to
`themeTokenMigration.exceptions.json`.

## APRAS-81 — `project-management` and `asset-management`

Child 4 of 8. Two directories, because the operator scoped this child that
way: `frontend/src/features/project-management/components` (eight files) and
`frontend/src/features/asset-management/components` (six files).

| task | file | line | class | code | why |
| --- | --- | --- | --- | --- | --- |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 132 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 152 | bg-red-50 | GAP-TINT | submit error alert; a status colour is semantic, not brand, and the alert migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 152 | text-red-700 | GAP-TINT | submit error alert; a status colour is semantic, not brand, and the alert migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 152 | border-red-200 | GAP-TINT | submit error alert; a status colour is semantic, not brand, and the alert migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 159 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 170 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 175 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 186 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 197 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 208 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 212 | border-gray-100 | GAP-BORDER-100 | checkbox row hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 223 | text-blue-600 | GAP-NO-TOKEN | native checkbox tint; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 223 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 227 | text-gray-800 | GAP-OUT-OF-BUDGET | consumable checkbox label; gray-800 has no row; the table budgets 900 and 500/600 |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 237 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 247 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 252 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 265 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 270 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 281 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 292 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 304 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 309 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 332 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 337 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 350 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 356 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 369 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 375 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 395 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 400 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 410 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 427 | bg-blue-600 | GAP-NO-TOKEN | submit button fill; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 427 | hover:bg-blue-700 | GAP-NO-TOKEN | submit button hover fill; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetFormModal.tsx | 427 | text-white | GAP-NO-SURFACE | submit button label over a blue fill; that background carries no token, so no foreground token names it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 27 | bg-emerald-100 | GAP-TINT | ENTRADA movement badge; a status colour is semantic, not brand, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 27 | text-emerald-800 | GAP-TINT | ENTRADA movement badge; a status colour is semantic, not brand, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 28 | text-emerald-600 | GAP-TINT | ENTRADA movement badge; a status colour is semantic, not brand, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 34 | bg-blue-100 | GAP-NO-TOKEN | SAIDA movement badge; blue has no token at any scale, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 34 | text-blue-800 | GAP-NO-TOKEN | SAIDA movement badge; blue has no token at any scale, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 35 | text-blue-600 | GAP-NO-TOKEN | SAIDA movement badge; blue has no token at any scale, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 41 | bg-amber-100 | GAP-NO-TOKEN | AJUSTE movement badge; amber has no token at any scale, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 41 | text-amber-800 | GAP-NO-TOKEN | AJUSTE movement badge; amber has no token at any scale, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 42 | text-amber-600 | GAP-NO-TOKEN | AJUSTE movement badge; amber has no token at any scale, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 48 | bg-red-100 | GAP-TINT | BAIXA movement badge; a status colour is semantic, not brand, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 48 | text-red-800 | GAP-TINT | BAIXA movement badge; a status colour is semantic, not brand, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 49 | text-red-600 | GAP-TINT | BAIXA movement badge; a status colour is semantic, not brand, and the badge migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 59 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 103 | text-gray-700 | GAP-OUT-OF-BUDGET | movement delta and author; gray-700 has no row; the table budgets 900 and 500/600 |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 115 | text-gray-800 | GAP-OUT-OF-BUDGET | movement reason body; gray-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetMovementHistoryModal.tsx | 122 | text-gray-700 | GAP-OUT-OF-BUDGET | movement delta and author; gray-700 has no row; the table budgets 900 and 500/600 |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 37 | bg-blue-50 | GAP-NO-TOKEN | fixed-assets tile glyph surface; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 37 | text-blue-600 | GAP-NO-TOKEN | fixed-assets tile glyph; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 61 | border-amber-300 | GAP-NO-TOKEN | low-stock alert tile; amber has no token at any scale, and the alert's classes migrate as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 61 | bg-amber-50/20 | GAP-NO-TOKEN | low-stock alert tile; amber has no token at any scale, and the alert's classes migrate as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 66 | text-amber-700 | GAP-NO-TOKEN | low-stock alert tile; amber has no token at any scale, and the alert's classes migrate as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 69 | text-amber-900 | GAP-NO-TOKEN | low-stock alert tile; amber has no token at any scale, and the alert's classes migrate as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 73 | bg-amber-100 | GAP-NO-TOKEN | low-stock alert tile; amber has no token at any scale, and the alert's classes migrate as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 73 | text-amber-600 | GAP-NO-TOKEN | low-stock alert tile; amber has no token at any scale, and the alert's classes migrate as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 84 | text-emerald-700 | GAP-TINT | patrimonial value figure; a status colour is semantic, not brand, so it stays hard-coded |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 88 | bg-emerald-50 | GAP-TINT | patrimonial value tile glyph surface; a status colour never follows the brand |
| APRAS-81 | frontend/src/features/asset-management/components/AssetSummaryCards.tsx | 88 | text-emerald-600 | GAP-TINT | patrimonial value tile glyph; a status colour never follows the brand |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 32 | bg-emerald-100 | GAP-TINT | NOVO condition badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 32 | text-emerald-800 | GAP-TINT | NOVO condition badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 32 | border-emerald-200 | GAP-TINT | NOVO condition badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 34 | bg-blue-100 | GAP-NO-TOKEN | BOM condition badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 34 | text-blue-800 | GAP-NO-TOKEN | BOM condition badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 34 | border-blue-200 | GAP-NO-TOKEN | BOM condition badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 36 | bg-amber-100 | GAP-NO-TOKEN | REGULAR condition badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 36 | text-amber-800 | GAP-NO-TOKEN | REGULAR condition badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 36 | border-amber-200 | GAP-NO-TOKEN | REGULAR condition badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 39 | bg-orange-100 | GAP-NO-TOKEN | RUIM/DANIFICADO condition badge; orange has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 39 | text-orange-800 | GAP-NO-TOKEN | RUIM/DANIFICADO condition badge; orange has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 39 | border-orange-200 | GAP-NO-TOKEN | RUIM/DANIFICADO condition badge; orange has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 41 | bg-red-100 | GAP-TINT | BAIXADO condition badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 41 | text-red-800 | GAP-TINT | BAIXADO condition badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 41 | border-red-200 | GAP-TINT | BAIXADO condition badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 43 | bg-gray-100 | GAP-TINT | default condition badge; the neutral branch stays with the rest of the condition scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 43 | text-gray-800 | GAP-TINT | default condition badge; the neutral branch stays with the rest of the condition scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 43 | border-gray-200 | GAP-TINT | default condition badge; the neutral branch stays with the rest of the condition scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 50 | bg-cyan-50 | GAP-SWATCH | ELETRONICOS category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 50 | text-cyan-700 | GAP-SWATCH | ELETRONICOS category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 50 | border-cyan-200 | GAP-SWATCH | ELETRONICOS category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 52 | bg-amber-50 | GAP-SWATCH | FERRAMENTAS category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 52 | text-amber-700 | GAP-SWATCH | FERRAMENTAS category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 52 | border-amber-200 | GAP-SWATCH | FERRAMENTAS category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 54 | bg-purple-50 | GAP-SWATCH | MOBILIARIO category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 54 | text-purple-700 | GAP-SWATCH | MOBILIARIO category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 54 | border-purple-200 | GAP-SWATCH | MOBILIARIO category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 56 | bg-red-50 | GAP-SWATCH | SEGURANCA category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 56 | text-red-700 | GAP-SWATCH | SEGURANCA category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 56 | border-red-200 | GAP-SWATCH | SEGURANCA category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 58 | bg-teal-50 | GAP-SWATCH | LIMPEZA category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 58 | text-teal-700 | GAP-SWATCH | LIMPEZA category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 58 | border-teal-200 | GAP-SWATCH | LIMPEZA category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 60 | bg-indigo-50 | GAP-SWATCH | MANUTENCAO category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 60 | text-indigo-700 | GAP-SWATCH | MANUTENCAO category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 60 | border-indigo-200 | GAP-SWATCH | MANUTENCAO category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 62 | bg-gray-50 | GAP-SWATCH | default category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 62 | text-gray-700 | GAP-SWATCH | default category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 62 | border-gray-200 | GAP-SWATCH | default category swatch; a category scale must not follow the brand or it loses hues to it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 86 | text-gray-700 | GAP-OUT-OF-BUDGET | table head label; gray-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 136 | text-gray-800 | GAP-OUT-OF-BUDGET | asset location cell; gray-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 162 | bg-amber-100 | GAP-NO-TOKEN | low-stock badge tint; amber has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 162 | text-amber-800 | GAP-NO-TOKEN | low-stock badge label; amber has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 164 | text-amber-600 | GAP-NO-TOKEN | low-stock warning glyph; amber has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 182 | hover:text-blue-600 | GAP-NO-TOKEN | record-movement hover tint; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetTable.tsx | 202 | hover:text-amber-600 | GAP-NO-TOKEN | edit-asset hover tint; amber has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 149 | bg-blue-50 | GAP-NO-TOKEN | page-header tile surface; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 149 | text-blue-600 | GAP-NO-TOKEN | page-header tile glyph; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 168 | bg-blue-600 | GAP-NO-TOKEN | new-asset button fill; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 168 | hover:bg-blue-700 | GAP-NO-TOKEN | new-asset button hover fill; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 168 | text-white | GAP-NO-SURFACE | new-asset button label over a blue fill; that background carries no token, so no foreground token names it |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 191 | bg-blue-50 | GAP-NO-TOKEN | active tab; blue has no token at any scale, and the tab's active pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 191 | text-blue-700 | GAP-NO-TOKEN | active tab; blue has no token at any scale, and the tab's active pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 203 | bg-blue-50 | GAP-NO-TOKEN | active tab; blue has no token at any scale, and the tab's active pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 203 | text-blue-700 | GAP-NO-TOKEN | active tab; blue has no token at any scale, and the tab's active pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 215 | bg-blue-50 | GAP-NO-TOKEN | active tab; blue has no token at any scale, and the tab's active pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 215 | text-blue-700 | GAP-NO-TOKEN | active tab; blue has no token at any scale, and the tab's active pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 227 | bg-amber-50 | GAP-NO-TOKEN | low-stock tab and counter; amber has no token at any scale, and the pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 227 | text-amber-700 | GAP-NO-TOKEN | low-stock tab and counter; amber has no token at any scale, and the pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 231 | text-amber-500 | GAP-NO-TOKEN | low-stock tab and counter; amber has no token at any scale, and the pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 234 | bg-amber-200 | GAP-NO-TOKEN | low-stock tab and counter; amber has no token at any scale, and the pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 234 | text-amber-900 | GAP-NO-TOKEN | low-stock tab and counter; amber has no token at any scale, and the pair migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 253 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 261 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 278 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/AssetsInventoryPage.tsx | 330 | bg-black/50 | GAP-OVERLAY | delete-confirmation scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 87 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 113 | bg-red-50 | GAP-TINT | submit error alert; a status colour is semantic, not brand, and the alert migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 113 | text-red-700 | GAP-TINT | submit error alert; a status colour is semantic, not brand, and the alert migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 113 | border-red-200 | GAP-TINT | submit error alert; a status colour is semantic, not brand, and the alert migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 119 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 125 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 136 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 147 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 152 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 160 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 165 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 177 | focus:ring-blue-500 | GAP-NO-TOKEN | focus ring; blue has no token at any scale, and the focus-ring sweep is a task of its own |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 193 | bg-blue-600 | GAP-NO-TOKEN | submit button fill; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 193 | hover:bg-blue-700 | GAP-NO-TOKEN | submit button hover fill; blue has no token at any scale |
| APRAS-81 | frontend/src/features/asset-management/components/StockMovementModal.tsx | 193 | text-white | GAP-NO-SURFACE | submit button label over a blue fill; that background carries no token, so no foreground token names it |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 23 | bg-emerald-500 | GAP-TINT | budget progress fill; a status colour never follows the brand, and the set migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 25 | bg-red-500 | GAP-TINT | budget progress fill; a status colour never follows the brand, and the set migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 27 | bg-amber-500 | GAP-NO-TOKEN | over-budget warning fill; amber has no token at any scale |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 34 | text-emerald-600 | GAP-TINT | budget status glyph and figure; a status colour is semantic, not brand, so it stays hard-coded |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 34 | dark:text-emerald-400 | GAP-TINT | dark sibling of the kept budget status glyph; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 46 | text-emerald-600 | GAP-TINT | budget status glyph and figure; a status colour is semantic, not brand, so it stays hard-coded |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 63 | border-slate-100 | GAP-BORDER-100 | metric panel hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 63 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept metric panel hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 67 | text-slate-800 | GAP-OUT-OF-BUDGET | metric figure; slate-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 67 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of the kept metric figure; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 72 | border-slate-100 | GAP-BORDER-100 | metric panel hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 72 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept metric panel hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 79 | text-red-600 | GAP-TINT | over-budget figure; a status colour is semantic, not brand, so it stays hard-coded |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 79 | dark:text-red-400 | GAP-TINT | dark sibling of the kept over-budget figure; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 80 | text-slate-800 | GAP-OUT-OF-BUDGET | metric figure; slate-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 80 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of the kept metric figure; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 87 | border-slate-100 | GAP-BORDER-100 | metric panel hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 87 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept metric panel hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 94 | text-red-600 | GAP-TINT | over-budget figure; a status colour is semantic, not brand, so it stays hard-coded |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 94 | dark:text-red-400 | GAP-TINT | dark sibling of the kept over-budget figure; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 95 | text-emerald-600 | GAP-TINT | budget status glyph and figure; a status colour is semantic, not brand, so it stays hard-coded |
| APRAS-81 | frontend/src/features/project-management/components/BudgetVsActualProgressBar.tsx | 95 | dark:text-emerald-400 | GAP-TINT | dark sibling of the kept budget status glyph; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 271 | border-emerald-200 | GAP-TINT | report-success alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 271 | bg-emerald-50 | GAP-TINT | report-success alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 271 | text-emerald-800 | GAP-TINT | report-success alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 271 | dark:border-emerald-900 | GAP-TINT | report-success alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 271 | dark:bg-emerald-950 | GAP-TINT | report-success alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 271 | dark:text-emerald-200 | GAP-TINT | report-success alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 272 | border-red-200 | GAP-TINT | report-error alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 272 | bg-red-50 | GAP-TINT | report-error alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 272 | text-red-800 | GAP-TINT | report-error alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 272 | dark:border-red-900 | GAP-TINT | report-error alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 272 | dark:bg-red-950 | GAP-TINT | report-error alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 272 | dark:text-red-200 | GAP-TINT | report-error alert; a status colour is semantic, not brand, and the alert's classes migrate as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 317 | text-red-600 | GAP-TINT | delete-project control; the destructive tint set has no row for its surface and migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 317 | border-red-200 | GAP-TINT | delete-project control; the destructive tint set has no row for its surface and migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 317 | hover:bg-red-50 | GAP-TINT | delete-project control; the destructive tint set has no row for its surface and migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 317 | dark:hover:bg-red-950 | GAP-TINT | delete-project control; the destructive tint set has no row for its surface and migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 345 | text-slate-700 | GAP-OUT-OF-BUDGET | description body and filter-chip label; slate-700 has no row; the table budgets 900 and 500/600 |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 345 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | dark sibling of the kept body and chip label; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 427 | text-slate-700 | GAP-OUT-OF-BUDGET | description body and filter-chip label; slate-700 has no row; the table budgets 900 and 500/600 |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 427 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | dark sibling of the kept body and chip label; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 442 | text-slate-300 | GAP-OUT-OF-BUDGET | empty-state glyph tint; slate-300 is outside the neutral band the mapping table budgets |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 442 | dark:text-slate-600 | GAP-OUT-OF-BUDGET | dark sibling of the kept empty-state glyph; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 443 | text-slate-800 | GAP-OUT-OF-BUDGET | empty-state heading; slate-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/ConstructionTrackerPage.tsx | 443 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of the kept empty-state heading; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneFormModal.tsx | 73 | border-slate-100 | GAP-BORDER-100 | modal header and footer hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneFormModal.tsx | 73 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept modal hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneFormModal.tsx | 182 | border-slate-100 | GAP-BORDER-100 | modal header and footer hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneFormModal.tsx | 182 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept modal hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneFormModal.tsx | 209 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 28 | bg-emerald-100 | GAP-TINT | milestone DONE column badge; a status colour is semantic, not brand, and the triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 28 | text-emerald-800 | GAP-TINT | milestone DONE column badge; a status colour is semantic, not brand, and the triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 28 | dark:bg-emerald-950 | GAP-TINT | milestone DONE column badge; a status colour is semantic, not brand, and the triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 28 | dark:text-emerald-300 | GAP-TINT | milestone DONE column badge; a status colour is semantic, not brand, and the triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 28 | border-emerald-200 | GAP-TINT | milestone DONE column badge; a status colour is semantic, not brand, and the triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 28 | dark:border-emerald-800 | GAP-TINT | milestone DONE column badge; a status colour is semantic, not brand, and the triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 35 | bg-blue-100 | GAP-NO-TOKEN | milestone IN_PROGRESS column badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 35 | text-blue-800 | GAP-NO-TOKEN | milestone IN_PROGRESS column badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 35 | dark:bg-blue-950 | GAP-NO-TOKEN | milestone IN_PROGRESS column badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 35 | dark:text-blue-300 | GAP-NO-TOKEN | milestone IN_PROGRESS column badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 35 | border-blue-200 | GAP-NO-TOKEN | milestone IN_PROGRESS column badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 35 | dark:border-blue-800 | GAP-NO-TOKEN | milestone IN_PROGRESS column badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 42 | bg-slate-100 | GAP-TINT | milestone NEXT_STEPS column badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 42 | text-slate-800 | GAP-TINT | milestone NEXT_STEPS column badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 42 | dark:bg-slate-800 | GAP-TINT | milestone NEXT_STEPS column badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 42 | dark:text-slate-300 | GAP-TINT | milestone NEXT_STEPS column badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 42 | border-slate-200 | GAP-TINT | milestone NEXT_STEPS column badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 42 | dark:border-slate-700 | GAP-TINT | milestone NEXT_STEPS column badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 91 | text-slate-700 | GAP-OUT-OF-BUDGET | column label and milestone date; slate-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 91 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of the kept column label; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 151 | border-slate-100 | GAP-BORDER-100 | milestone card footer hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 151 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept footer hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 155 | text-slate-700 | GAP-OUT-OF-BUDGET | column label and milestone date; slate-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 155 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | dark sibling of the kept milestone date; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 163 | text-slate-700 | GAP-OUT-OF-BUDGET | column label and milestone date; slate-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/MilestoneTimeline.tsx | 163 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | dark sibling of the kept milestone date; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectFormModal.tsx | 99 | border-slate-100 | GAP-BORDER-100 | modal header and footer hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/ProjectFormModal.tsx | 99 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept modal hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectFormModal.tsx | 303 | border-slate-100 | GAP-BORDER-100 | modal header and footer hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/ProjectFormModal.tsx | 303 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept modal hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectFormModal.tsx | 332 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 23 | bg-slate-100 | GAP-TINT | PLANNED status badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 23 | text-slate-800 | GAP-TINT | PLANNED status badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 23 | dark:bg-slate-800 | GAP-TINT | PLANNED status badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 23 | dark:text-slate-300 | GAP-TINT | PLANNED status badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 23 | border-slate-200 | GAP-TINT | PLANNED status badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 23 | dark:border-slate-700 | GAP-TINT | PLANNED status badge; the badge triple migrates as a unit or not at all |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 28 | bg-blue-100 | GAP-NO-TOKEN | IN_PROGRESS status badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 28 | text-blue-800 | GAP-NO-TOKEN | IN_PROGRESS status badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 28 | dark:bg-blue-950 | GAP-NO-TOKEN | IN_PROGRESS status badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 28 | dark:text-blue-300 | GAP-NO-TOKEN | IN_PROGRESS status badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 28 | border-blue-200 | GAP-NO-TOKEN | IN_PROGRESS status badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 28 | dark:border-blue-800 | GAP-NO-TOKEN | IN_PROGRESS status badge; blue has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 33 | bg-amber-100 | GAP-NO-TOKEN | PAUSED status badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 33 | text-amber-800 | GAP-NO-TOKEN | PAUSED status badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 33 | dark:bg-amber-950 | GAP-NO-TOKEN | PAUSED status badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 33 | dark:text-amber-300 | GAP-NO-TOKEN | PAUSED status badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 33 | border-amber-200 | GAP-NO-TOKEN | PAUSED status badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 33 | dark:border-amber-800 | GAP-NO-TOKEN | PAUSED status badge; amber has no token at any scale, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 38 | bg-emerald-100 | GAP-TINT | COMPLETED status badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 38 | text-emerald-800 | GAP-TINT | COMPLETED status badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 38 | dark:bg-emerald-950 | GAP-TINT | COMPLETED status badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 38 | dark:text-emerald-300 | GAP-TINT | COMPLETED status badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 38 | border-emerald-200 | GAP-TINT | COMPLETED status badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 38 | dark:border-emerald-800 | GAP-TINT | COMPLETED status badge; a status colour is semantic, not brand, and the triple migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 89 | bg-black/50 | GAP-OVERLAY | cover-photo control scrim; a scrim is an opacity over the photo behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 94 | text-white | GAP-NO-SURFACE | icon over the cover-photo scrim; the background carries no token, so no foreground token names it |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 103 | text-white | GAP-NO-SURFACE | icon over the cover-photo scrim; the background carries no token, so no foreground token names it |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 103 | hover:text-red-400 | GAP-OUT-OF-BUDGET | delete icon over the cover photo; the red-400 row moves the hue by more than the table budgets |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 124 | text-slate-800 | GAP-OUT-OF-BUDGET | card detail figure; slate-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 124 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of the kept card detail figure; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 139 | border-slate-100 | GAP-BORDER-100 | card body divider; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 139 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept card body divider; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 146 | text-slate-800 | GAP-OUT-OF-BUDGET | card detail figure; slate-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 146 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of the kept card detail figure; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 164 | text-slate-800 | GAP-OUT-OF-BUDGET | card detail figure; slate-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 164 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of the kept card detail figure; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 172 | bg-red-500 | GAP-TINT | budget-bar fill over budget; a status colour never follows the brand, and the ternary migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectSummaryCard.tsx | 173 | bg-emerald-500 | GAP-TINT | budget-bar fill within budget; a status colour never follows the brand, and the ternary migrates as a unit |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateFeed.tsx | 51 | text-slate-700 | GAP-OUT-OF-BUDGET | update body text; slate-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateFeed.tsx | 51 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | dark sibling of the kept update body text; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateFeed.tsx | 100 | text-slate-700 | GAP-OUT-OF-BUDGET | update body text; slate-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateFeed.tsx | 100 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | dark sibling of the kept update body text; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateFeed.tsx | 129 | bg-black/80 | GAP-OVERLAY | photo lightbox scrim; a scrim is an opacity over what is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateFeed.tsx | 133 | bg-black/60 | GAP-OVERLAY | lightbox close-button scrim; a scrim is an opacity over what is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateFeed.tsx | 133 | hover:bg-black | GAP-OVERLAY | lightbox close-button hover scrim; it stays with the resting scrim it darkens |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateFeed.tsx | 133 | text-white | GAP-NO-SURFACE | lightbox close icon over the scrim; the background carries no token, so no foreground token names it |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateModal.tsx | 59 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateModal.tsx | 61 | border-slate-100 | GAP-BORDER-100 | modal header and footer hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateModal.tsx | 61 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept modal hairline; it stays with its base |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateModal.tsx | 144 | border-slate-100 | GAP-BORDER-100 | modal header and footer hairline; the 100 step is below the weight the border token carries |
| APRAS-81 | frontend/src/features/project-management/components/ProjectUpdateModal.tsx | 144 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept modal hairline; it stays with its base |

**APRAS-81 total — 276 occurrences:** 87 `GAP-NO-TOKEN`, 77 `GAP-TINT`,
51 `GAP-OUT-OF-BUDGET`, 23 `GAP-BORDER-100`, 21 `GAP-SWATCH`,
11 `GAP-OVERLAY` and 6 `GAP-NO-SURFACE`. No `GAP-UNLISTED`.
With the 228 occurrences migrated to a token and the 83 `dark:` siblings
deleted alongside them (§1g), that accounts for all 587 palette occurrences in
the two directories. The two halves close independently: 447 non-`dark:` =
228 + 219, and 140 `dark:` = 83 + 57. Per directory, 133 of the 276 stay in
`project-management` and 143 in `asset-management`. The 276 occupy **200**
distinct `(file, class)` pairs — 101 in `project-management`, 99 in
`asset-management` — which is the number of entries appended to
`themeTokenMigration.exceptions.json`.

## APRAS-83 — `finance`, `purchase-management` and `access-control`

Child 6 of 8. Three directories, because the operator scoped this child that
way: `frontend/src/features/finance/components` (ten files),
`frontend/src/features/purchase-management/components` (six) and
`frontend/src/features/access-control/components` (six).

| task | file | line | class | code | why |
| --- | --- | --- | --- | --- | --- |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 22 | dark:divide-slate-800/80 | GAP-BORDER-100 | dark sibling of the kept row divider; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 22 | divide-slate-100 | GAP-BORDER-100 | row divider at the 100 step, below the weight the border token carries; migrating it would thicken it |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 27 | text-emerald-500 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 29 | text-red-500 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 47 | bg-emerald-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 47 | dark:bg-emerald-950/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 47 | dark:text-emerald-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 47 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 48 | bg-red-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 48 | dark:bg-red-950/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 48 | dark:text-red-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/AccessEventFeed.tsx | 48 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 18 | bg-emerald-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 18 | dark:bg-emerald-950/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 18 | dark:text-emerald-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 18 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 22 | bg-slate-100 | GAP-TINT | kept because its ternary partner is a status colour; a set migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 22 | dark:bg-slate-800 | GAP-TINT | kept because its ternary partner is a status colour; a set migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 22 | dark:text-slate-400 | GAP-TINT | kept because its ternary partner is a status colour; a set migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 22 | text-slate-600 | GAP-TINT | kept because its ternary partner is a status colour; a set migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 26 | bg-amber-100 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 26 | dark:bg-amber-950/50 | GAP-NO-TOKEN | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 26 | dark:text-amber-400 | GAP-NO-TOKEN | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 26 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 68 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 68 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 76 | dark:divide-slate-800/80 | GAP-BORDER-100 | dark sibling of the kept row divider; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/DeviceTable.tsx | 76 | divide-slate-100 | GAP-BORDER-100 | row divider at the 100 step, below the weight the border token carries; migrating it would thicken it |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 8 | bg-emerald-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 8 | dark:bg-emerald-950/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 8 | dark:text-emerald-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 8 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 9 | bg-amber-100 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 9 | dark:bg-amber-950/50 | GAP-NO-TOKEN | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 9 | dark:text-amber-400 | GAP-NO-TOKEN | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 9 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 10 | bg-red-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 10 | dark:bg-red-950/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 10 | dark:text-red-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 10 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 58 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 58 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 58 | dark:bg-red-950/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 58 | dark:border-red-900/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 58 | dark:text-red-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 58 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 64 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/access-control/components/FacialTemplateSyncPanel.tsx | 64 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 48 | bg-black/40 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 51 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 51 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 68 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 68 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 68 | dark:bg-red-950/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 68 | dark:border-red-900/50 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 68 | dark:text-red-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 68 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 75 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | dark sibling of kept body text; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 75 | text-slate-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 86 | dark:text-slate-300 | GAP-OUT-OF-BUDGET | dark sibling of kept body text; it stays with its base |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 86 | text-slate-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 97 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/access-control/components/RegisterDeviceModal.tsx | 97 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/BudgetLineFormModal.tsx | 53 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/BudgetLineFormModal.tsx | 53 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/BudgetLineFormModal.tsx | 138 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/BudgetLineFormModal.tsx | 138 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/BudgetLineFormModal.tsx | 166 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/finance/components/BudgetVsActualTable.tsx | 73 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/BudgetVsActualTable.tsx | 73 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/BudgetVsActualTable.tsx | 85 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of kept body text; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/BudgetVsActualTable.tsx | 85 | text-slate-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/finance/components/BudgetVsActualTable.tsx | 99 | text-emerald-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/BudgetVsActualTable.tsx | 99 | text-red-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 40 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 40 | dark:bg-emerald-950 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 41 | dark:text-emerald-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 41 | text-emerald-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 47 | dark:text-emerald-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 47 | text-emerald-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 54 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 54 | dark:bg-red-950 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 55 | dark:text-red-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 55 | text-red-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 61 | dark:text-red-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CashBalanceCard.tsx | 61 | text-red-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/CategoryFormModal.tsx | 43 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/CategoryFormModal.tsx | 43 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CategoryFormModal.tsx | 84 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/CategoryFormModal.tsx | 84 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CategoryFormModal.tsx | 110 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/finance/components/CategoryTransactionDrilldown.tsx | 59 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/CategoryTransactionDrilldown.tsx | 59 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CategoryTransactionDrilldown.tsx | 79 | dark:text-slate-700 | GAP-OUT-OF-BUDGET | dark sibling of kept body text; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/CategoryTransactionDrilldown.tsx | 79 | text-slate-300 | GAP-OUT-OF-BUDGET | empty-state glyph; no row at the 300 step, and repairing its contrast in place is APRAS-90's work |
| APRAS-83 | frontend/src/features/finance/components/StatementChart.tsx | 53 | bg-emerald-500 | GAP-SWATCH | credit bar of the statement chart; a chart series encodes its own meaning and must not follow the brand |
| APRAS-83 | frontend/src/features/finance/components/StatementChart.tsx | 59 | bg-red-500 | GAP-SWATCH | debit bar of the statement chart; a chart series encodes its own meaning and must not follow the brand |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 36 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 36 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 38 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of kept body text; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 38 | text-slate-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 41 | dark:text-emerald-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 41 | text-emerald-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 44 | dark:text-red-400 | GAP-TINT | dark sibling of the kept status colour; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 44 | text-red-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 47 | dark:text-slate-200 | GAP-OUT-OF-BUDGET | dark sibling of kept body text; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/StatementTable.tsx | 47 | text-slate-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/finance/components/TransactionFormModal.tsx | 67 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/TransactionFormModal.tsx | 67 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/TransactionFormModal.tsx | 193 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/finance/components/TransactionFormModal.tsx | 193 | dark:border-slate-800 | GAP-BORDER-100 | dark sibling of the kept hairline; it stays with its base |
| APRAS-83 | frontend/src/features/finance/components/TransactionFormModal.tsx | 220 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 81 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 126 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 129 | text-gray-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 136 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 136 | border-amber-200 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 137 | text-amber-800 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 140 | text-amber-900 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 148 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 151 | text-gray-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 237 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 237 | border-emerald-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 239 | text-emerald-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 240 | text-emerald-900 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 248 | text-emerald-900 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 251 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 261 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 274 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestDetailModal.tsx | 282 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 165 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 184 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 184 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 184 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 192 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 210 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 229 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 281 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 281 | border-amber-200 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 281 | text-amber-800 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx | 302 | text-gray-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestsPage.tsx | 294 | text-amber-600 | GAP-NO-TOKEN | amber has no row at any scale; adding a warning token is out of this child's scope |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestsPage.tsx | 331 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/purchase-management/components/PurchaseRequestsPage.tsx | 364 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 198 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale; adding a warning token is out of this child's scope |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 231 | text-sky-700 | GAP-NO-TOKEN | informational note; no sky token exists at any scale, and adding one is out of this child's scope |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 337 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 337 | text-gray-900 | GAP-TINT | kept because its ternary partner is a status colour; a set migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 386 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 386 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 386 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 406 | bg-emerald-50/60 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 430 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 447 | bg-emerald-50/40 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 458 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 466 | bg-emerald-50/40 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 486 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 494 | bg-emerald-50/40 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 527 | bg-emerald-50/40 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 527 | border-emerald-300 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 528 | border-gray-200 | GAP-TINT | kept because its ternary partner is a status colour; a set migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 562 | text-gray-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 578 | text-gray-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx | 586 | text-gray-800 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 265 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 280 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 280 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 280 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 288 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 306 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 350 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 396 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 498 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 512 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/QuoteFormModal.tsx | 553 | text-amber-600 | GAP-NO-TOKEN | amber has no row at any scale; adding a warning token is out of this child's scope |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 75 | bg-black/50 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 88 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 88 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 88 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 113 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 113 | border-amber-200 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 116 | text-amber-600 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 117 | text-amber-900 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 140 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 140 | border-amber-200 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 143 | text-amber-600 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 144 | text-amber-900 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 159 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 173 | text-gray-700 | GAP-OUT-OF-BUDGET | body text one step off the foreground token; the move is outside the budget the table publishes |
| APRAS-83 | frontend/src/features/purchase-management/components/SelectQuoteModal.tsx | 188 | text-amber-600 | GAP-NO-TOKEN | amber has no row at any scale; adding a warning token is out of this child's scope |

**APRAS-83 total — 190 occurrences:** 83 `GAP-TINT`, 33 `GAP-OUT-OF-BUDGET`,
33 `GAP-BORDER-100`, 29 `GAP-NO-TOKEN`, 10 `GAP-OVERLAY` and 2 `GAP-SWATCH` —
the first child to use the swatch code, at the two bars of the statement
chart. No `GAP-NO-SURFACE` and no `GAP-UNLISTED`.
With the 233 occurrences migrated to a token and the 111 `dark:` siblings
deleted alongside them (§1g), that accounts for all 534 palette occurrences in
the three directories. The two halves close independently: 372 non-`dark:` =
233 + 139, and 162 `dark:` = 111 + 51. Per directory, 49 of the 190 stay in
`finance`, 78 in `purchase-management` and 63 in `access-control`. The 190
occupy **145** distinct `(file, class)` pairs — 37 in `finance`, 52 in
`purchase-management` and 56 in `access-control` — which is the number of
entries appended to `themeTokenMigration.exceptions.json`.
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementCard.tsx | 53 | text-emerald-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementCard.tsx | 81 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementFormModal.tsx | 64 | bg-black/40 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementFormModal.tsx | 83 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementFormModal.tsx | 92 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementFormModal.tsx | 97 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementFormModal.tsx | 106 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementFormModal.tsx | 111 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/announcement-feed/components/AnnouncementFormModal.tsx | 127 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/announcement-feed/components/CommentThread.tsx | 42 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-84 | frontend/src/features/announcement-feed/components/CommentThread.tsx | 52 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/announcement-feed/components/CommentThread.tsx | 84 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/announcement-feed/components/MediaCarousel.tsx | 42 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/announcement-feed/components/MediaCarousel.tsx | 56 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/announcement-feed/components/MediaCarousel.tsx | 64 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackChannelPage.tsx | 50 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackChannelPage.tsx | 58 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackChannelPage.tsx | 70 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 27 | bg-black/40 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 45 | bg-black/40 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 49 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 66 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 69 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 75 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 75 | border-emerald-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 76 | text-emerald-900 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 77 | text-emerald-600 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 80 | text-emerald-800 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 88 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackDetailsView.tsx | 97 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 38 | divide-gray-100 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 51 | bg-rose-500 | GAP-NO-TOKEN | rose has no row at any scale; the unread badge's fill and its label migrate as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 51 | text-white | GAP-NO-SURFACE | unread badge label over bg-rose-500, a palette fill with no row, so no foreground token names it |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 57 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 60 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 66 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 66 | border-emerald-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 66 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 67 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 67 | border-amber-200 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackHistoryList.tsx | 67 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 15 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 15 | border-amber-200 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 15 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 17 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 17 | border-emerald-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 17 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 19 | bg-gray-50 | GAP-TINT | the default branch of a status map whose other branches are tints; the set migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 19 | border-gray-200 | GAP-TINT | the default branch of a status map whose other branches are tints; the set migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 19 | text-gray-700 | GAP-TINT | the default branch of a status map whose other branches are tints; the set migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 62 | divide-gray-100 | GAP-BORDER-100 | hairline divider inside a panel; applying border would make it read as a border |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 66 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/FeedbackInboxTable.tsx | 82 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/feedback-management/components/NewFeedbackForm.tsx | 38 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/feedback-management/components/NewFeedbackForm.tsx | 44 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/NewFeedbackForm.tsx | 54 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/feedback-management/components/NewFeedbackForm.tsx | 66 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/feedback-management/components/NewFeedbackForm.tsx | 78 | text-gray-800 | GAP-OUT-OF-BUDGET | panel body weight; gray-800 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/AvatarCropEditor.tsx | 63 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/AvatarCropEditor.tsx | 89 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/AvatarCropEditor.tsx | 99 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/AvatarWithFallback.tsx | 36 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/AvatarWithFallback.tsx | 48 | bg-amber-500/90 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/AvatarWithFallback.tsx | 48 | text-white | GAP-NO-SURFACE | badge label over bg-amber-500/90, a palette fill with no row, so no foreground token names it |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 38 | text-slate-800 | GAP-OUT-OF-BUDGET | panel heading weight; slate-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 44 | bg-amber-100 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 44 | text-amber-800 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 53 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 53 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 53 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 69 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 84 | bg-black/20 | GAP-OVERLAY | thumbnail hover scrim; a scrim is an opacity over the photo behind it, not a surface with a token |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 84 | text-white | GAP-NO-SURFACE | hint over the bg-black/20 thumbnail scrim; that background carries no token, so no foreground token names it |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 91 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 95 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 101 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 106 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 106 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 106 | hover:bg-red-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 106 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 126 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 128 | text-slate-800 | GAP-OUT-OF-BUDGET | panel heading weight; slate-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 142 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/PhotoApprovalQueuePage.tsx | 162 | bg-black/80 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 76 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 78 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 79 | text-slate-800 | GAP-OUT-OF-BUDGET | panel heading weight; slate-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 87 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 87 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 87 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 116 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 138 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 150 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-84 | frontend/src/features/media-management/components/PhotoUploadModal.tsx | 154 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 101 | bg-black/60 | GAP-OVERLAY | modal scrim; a scrim is an opacity over whatever is behind it, not a surface with a token |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 103 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 104 | text-slate-800 | GAP-OUT-OF-BUDGET | panel heading weight; slate-800 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 118 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 118 | border-red-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 118 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 126 | border-slate-800 | GAP-OUT-OF-BUDGET | the tree's only border-slate-800; the 800 step has no border row and is nowhere near the border token |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 140 | border-slate-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 147 | text-slate-700 | GAP-OUT-OF-BUDGET | form label weight; slate-700 has no row; the table budgets 900 for headings and 500/600 for secondary text |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 157 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 157 | border-amber-300 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 157 | hover:bg-amber-100 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/media-management/components/WebcamCaptureDialog.tsx | 157 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-84 | frontend/src/features/package-management/components/PackageStatusPage.tsx | 61 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-84 | frontend/src/features/package-management/components/PackageStatusPage.tsx | 73 | text-gray-700 | GAP-OUT-OF-BUDGET | form field label; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |

**APRAS-84 total — 109 occurrences:** 47 `GAP-OUT-OF-BUDGET`, 28 `GAP-TINT`,
14 `GAP-NO-TOKEN`, 9 `GAP-BORDER-100`, 8 `GAP-OVERLAY` and 3 `GAP-NO-SURFACE`
— the first child to use the no-surface code outside the pilot, at the three
`text-white` sites whose palette backgrounds carry no row. No `GAP-SWATCH` and
no `GAP-UNLISTED`.
With the 242 occurrences migrated to a token, that accounts for all 351
palette occurrences in the four directories. **Not one carries a `dark:`
variant**, so §1g never fires here: no sibling is deleted and no `dark:` row
appears above. Per directory, 49 of the 109 stay in `media-management`, 43 in
`feedback-management`, 15 in `announcement-feed` and 2 in
`package-management`; `AnnouncementFeedPage.tsx` is the one file that migrates
completely and has no row. The 109 occupy **80** distinct `(file, class)`
pairs — 36 in `media-management`, 33 in `feedback-management`, 9 in
`announcement-feed` and 2 in `package-management` — which is the number of
entries appended to `themeTokenMigration.exceptions.json`. One class is logged
twice in one file under two codes: `FeedbackInboxTable.tsx`'s `text-gray-700`
is a kept tint inside status set 1 at line 19 and out of budget as a table
cell at line 82. The exceptions file is keyed `(file, class)` and carries one
code, so that pair takes `GAP-TINT`, the earlier of the two in §1h's
precedence order.

| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 33 | dark:text-blue-400 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 33 | text-blue-500 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 34 | bg-blue-500/10 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 40 | dark:text-emerald-400 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 40 | text-emerald-500 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 41 | bg-emerald-500/10 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 47 | dark:text-amber-400 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 47 | text-amber-500 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 48 | bg-amber-500/10 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 54 | dark:text-indigo-400 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 54 | text-indigo-500 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 55 | bg-indigo-500/10 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 61 | dark:text-purple-400 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 61 | text-purple-500 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 62 | bg-purple-500/10 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 68 | dark:text-orange-400 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 68 | text-orange-500 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 69 | bg-orange-500/10 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 75 | dark:text-green-400 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 75 | text-green-500 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 76 | bg-green-500/10 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 82 | dark:text-rose-400 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 82 | text-rose-500 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 83 | bg-rose-500/10 | GAP-SWATCH | module identity colour; a data swatch must not follow the tenant brand, or two modules collapse into one colour |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 116 | bg-amber-500/10 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 116 | border-amber-500/20 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 116 | dark:text-amber-400 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/dashboard/components/GeneralDashboardPage.tsx | 116 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/AttachmentUploader.tsx | 181 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/AttachmentUploader.tsx | 181 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/CycleCloseModal.tsx | 52 | bg-black/40 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/infraction-management/components/CycleCloseModal.tsx | 104 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/CycleCloseModal.tsx | 104 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/InfractionDetailsView.tsx | 61 | text-gray-700 | GAP-OUT-OF-BUDGET | body text at the 700 step; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-85 | frontend/src/features/infraction-management/components/InfractionStageTimeline.tsx | 31 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-85 | frontend/src/features/infraction-management/components/InfractionStageTimeline.tsx | 49 | text-gray-700 | GAP-OUT-OF-BUDGET | body text at the 700 step; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-85 | frontend/src/features/infraction-management/components/InfractionStageTimeline.tsx | 57 | bg-amber-100 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/InfractionStageTimeline.tsx | 57 | text-amber-800 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/InfractionStageTimeline.tsx | 99 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/infraction-management/components/NewInfractionModal.tsx | 166 | bg-black/40 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/infraction-management/components/NewInfractionModal.tsx | 260 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/infraction-management/components/NewInfractionModal.tsx | 336 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/NewInfractionModal.tsx | 336 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/components/NextStepPanel.tsx | 62 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionRulesPage.tsx | 225 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionRulesPage.tsx | 238 | text-gray-700 | GAP-OUT-OF-BUDGET | body text at the 700 step; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionRulesPage.tsx | 276 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionsPage.tsx | 262 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionsPage.tsx | 269 | text-gray-700 | GAP-OUT-OF-BUDGET | body text at the 700 step; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionsPage.tsx | 337 | border-gray-100 | GAP-BORDER-100 | hairline at the 100 step, below the weight the border token carries; migrating it would thicken the rule |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionsPage.tsx | 346 | text-gray-700 | GAP-OUT-OF-BUDGET | body text at the 700 step; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionsPage.tsx | 355 | bg-red-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/pages/InfractionsPage.tsx | 355 | text-red-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/pages/MyInfractionsPage.tsx | 57 | text-gray-700 | GAP-OUT-OF-BUDGET | body text at the 700 step; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-85 | frontend/src/features/infraction-management/pages/MyInfractionsPage.tsx | 63 | text-gray-700 | GAP-OUT-OF-BUDGET | body text at the 700 step; gray-700 has no row; the table budgets 900 for headings and 500/600 for body |
| APRAS-85 | frontend/src/features/infraction-management/pages/MyInfractionsPage.tsx | 67 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/infraction-management/pages/MyInfractionsPage.tsx | 67 | text-amber-800 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/space-reservation-management/components/ReservableSpacesPage.tsx | 243 | text-amber-600 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/space-reservation-management/components/SpaceBookingPage.tsx | 16 | bg-emerald-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/space-reservation-management/components/SpaceBookingPage.tsx | 16 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/space-reservation-management/components/SpaceBookingPage.tsx | 18 | bg-amber-100 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/space-reservation-management/components/SpaceBookingPage.tsx | 18 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/space-reservation-management/components/SpaceBookingPage.tsx | 22 | bg-slate-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/space-reservation-management/components/SpaceBookingPage.tsx | 22 | text-slate-500 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/space-reservation-management/components/SpaceBookingPage.tsx | 24 | bg-slate-100 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/space-reservation-management/components/SpaceBookingPage.tsx | 24 | text-slate-500 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/AuditTimeline.tsx | 111 | text-emerald-600 | GAP-TINT | a status colour is semantic, not brand; emerald at this step has no row and must not follow the brand |
| APRAS-85 | frontend/src/features/task-management/components/DueDateBadge.tsx | 18 | dark:text-amber-400 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/DueDateBadge.tsx | 18 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/DueDateBadge.tsx | 19 | dark:text-amber-400 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/DueDateBadge.tsx | 19 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/HighlightedText.tsx | 62 | bg-yellow-200 | GAP-NO-TOKEN | yellow has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/task-management/components/HighlightedText.tsx | 62 | dark:bg-yellow-500/40 | GAP-NO-TOKEN | yellow has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 75 | bg-slate-50/50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 75 | dark:bg-slate-900/20 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 76 | border-t-slate-400 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 81 | bg-blue-50/50 | GAP-NO-TOKEN | blue has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 81 | dark:bg-blue-900/20 | GAP-NO-TOKEN | blue has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 82 | border-t-blue-400 | GAP-NO-TOKEN | blue has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 87 | bg-amber-50/50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 87 | dark:bg-amber-900/20 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 88 | border-t-amber-500 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 93 | bg-green-50/50 | GAP-NO-TOKEN | green has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 93 | dark:bg-green-900/20 | GAP-NO-TOKEN | green has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 94 | border-t-green-400 | GAP-NO-TOKEN | green has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 99 | bg-red-50/50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 99 | dark:bg-red-900/20 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskBoard.tsx | 100 | border-t-red-400 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskDashboard.tsx | 307 | dark:hover:bg-white/10 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/task-management/components/TaskDashboard.tsx | 307 | hover:bg-black/10 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/task-management/components/TaskDashboard.tsx | 342 | bg-black/50 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 146 | bg-amber-100 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 146 | dark:bg-amber-500/20 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 146 | dark:text-amber-300 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 146 | text-amber-800 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 166 | bg-sky-100 | GAP-NO-TOKEN | sky has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 166 | dark:bg-sky-500/20 | GAP-NO-TOKEN | sky has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 166 | dark:text-sky-300 | GAP-NO-TOKEN | sky has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 166 | text-sky-800 | GAP-NO-TOKEN | sky has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 216 | dark:hover:bg-white/10 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/task-management/components/TaskFilterBar.tsx | 216 | hover:bg-black/10 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/user-administration/components/InviteAdministratorDialog.tsx | 99 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/components/InviteAdministratorDialog.tsx | 99 | border-emerald-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/components/InviteAdministratorDialog.tsx | 101 | text-emerald-900 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/components/InviteAdministratorDialog.tsx | 104 | text-emerald-900 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/components/Navbar.tsx | 153 | dark:text-amber-400 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/Navbar.tsx | 153 | text-amber-600 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/SimulationBanner.tsx | 32 | bg-amber-400 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/SimulationBanner.tsx | 32 | text-amber-950 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/SimulationBanner.tsx | 46 | bg-amber-400/40 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/SimulationBanner.tsx | 46 | border-amber-950/30 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/SimulationBanner.tsx | 46 | hover:bg-amber-400/70 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/TenantBrandColors.tsx | 469 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/TenantBrandColors.tsx | 469 | text-amber-900 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/TenantBrandColors.tsx | 552 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand; emerald at this step has no row and must not follow the brand |
| APRAS-85 | frontend/src/features/user-administration/components/TenantBrandColors.tsx | 599 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/components/TenantBrandColors.tsx | 599 | border-emerald-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/components/TenantBrandColors.tsx | 599 | text-emerald-800 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/components/TenantInvitationsPanel.tsx | 24 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/TenantInvitationsPanel.tsx | 24 | text-amber-700 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/components/TenantInvitationsPanel.tsx | 26 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand; emerald at this step has no row and must not follow the brand |
| APRAS-85 | frontend/src/features/user-administration/components/TenantInvitationsPanel.tsx | 26 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand; emerald at this step has no row and must not follow the brand |
| APRAS-85 | frontend/src/features/user-administration/pages/AdminUserDashboard.tsx | 292 | bg-black/50 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/user-administration/pages/ContactInfoDashboard.tsx | 175 | bg-black/50 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantProfilePage.tsx | 225 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand; emerald at this step has no row and must not follow the brand |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantProfilePage.tsx | 225 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand; emerald at this step has no row and must not follow the brand |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantProfilePage.tsx | 364 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantProfilePage.tsx | 364 | border-amber-200 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantProfilePage.tsx | 364 | text-amber-900 | GAP-NO-TOKEN | amber has no row at any scale, and the status set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantProfilePage.tsx | 397 | bg-amber-50 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantProfilePage.tsx | 397 | text-amber-800 | GAP-NO-TOKEN | amber has no row at any scale; a warning or highlight token is out of scope for this task |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantProfilePage.tsx | 417 | bg-black/40 | GAP-OVERLAY | scrim or hover veil; an opacity over whatever is behind it, not a surface with a token of its own |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 53 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand; emerald at this step has no row and must not follow the brand |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 53 | text-emerald-700 | GAP-TINT | a status colour is semantic, not brand; emerald at this step has no row and must not follow the brand |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 257 | bg-emerald-50 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 257 | border-emerald-200 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 258 | text-emerald-900 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 261 | text-emerald-900 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 263 | text-emerald-800 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 272 | border-emerald-300 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 272 | text-emerald-800 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 278 | text-emerald-800 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 283 | text-emerald-800 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 299 | border-emerald-300 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |
| APRAS-85 | frontend/src/features/user-administration/pages/TenantsAdminPage.tsx | 299 | text-emerald-800 | GAP-TINT | a status colour is semantic, not brand, and the set it belongs to migrates as a unit or not at all |

**APRAS-85 total — 145 occurrences:** 53 `GAP-NO-TOKEN`, 46 `GAP-TINT`, 24
`GAP-SWATCH`, 10 `GAP-OVERLAY`, 7 `GAP-OUT-OF-BUDGET` and 5 `GAP-BORDER-100`.
No `GAP-NO-SURFACE` and no `GAP-UNLISTED`: both `text-white` occurrences sat on
a migrating `bg-emerald-700`, so the no-surface code never fires.
With the 167 occurrences migrated to a token and **no** `dark:` sibling deleted
— every one of the 24 `dark:` classes here pairs with a base this child keeps,
so §1g's first half never fires — that accounts for all 312 palette
occurrences in the six directories. The two halves close independently: 288
non-`dark:` = 167 + 121, and 24 `dark:` = 0 + 24. Per directory, 29 of the 145
stay in `infraction-management`, 44 in `user-administration`, 35 in
`task-management`, 28 in `dashboard`, 9 in `space-reservation-management` and 0
in `assembly-voting`, which migrates completely. The 145 occupy **126**
distinct `(file, class)` pairs — 25 in `infraction-management`, 35 in
`user-administration`, 33 in `task-management`, 26 in `dashboard`, 7 in
`space-reservation-management` and 0 in `assembly-voting` — which is the number
of entries appended to `themeTokenMigration.exceptions.json`. Two classes are
logged twice in one file under two codes: `GeneralDashboardPage.tsx`'s
`bg-amber-500/10` and `dark:text-amber-400` are module swatches in the colour
map and warning tints in the preview badge at line 116. The exceptions file is
keyed `(file, class)` and carries one code, so both pairs take `GAP-SWATCH`,
the earlier of the two in §1h's precedence order.
Five of the 145 are occurrences no earlier child could see: the
`border-t-{slate,blue,amber,green,red}-*` header stripes of `TaskBoard.tsx`'s
column map, which job (c)'s widening of §3b's `prefix` production brought
inside the grammar. They are kept verbatim — a status set migrates as a unit or
not at all — and ledgered here for the first time.
