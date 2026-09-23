# Unmapped colours — the ledger

Every Tailwind palette class this repository keeps **on purpose**, one row per
occurrence.

A task that meets a colour with no row in
[`theme-token-mapping.md`](./theme-token-mapping.md) — or one whose row it is
forbidden to apply — **leaves the class exactly as it is** and appends a line
here. Opened by APRAS-78 (child 1 of the APRAS-77 split); APRAS-79 … APRAS-85
append to it and may not rewrite what is already in it.

## The rules this file exists to enforce

**No task may add a property to `frontend/src/index.css`.** A one-off token
per call site turns the token set into landfill, and `build_theme` emits
exactly 17 keys, so a property added here would be unbranded forever. The
answer to "there is no token for this colour" is a row in this file, never a
new token.

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
