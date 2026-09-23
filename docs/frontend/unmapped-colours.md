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
