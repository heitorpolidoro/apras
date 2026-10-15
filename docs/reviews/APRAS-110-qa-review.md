# APRAS-110 — QA verification

**Task**: Show the acting condominium's logo in the header
**Verified against**: the 20 expected results only
**Worktree**: `/Users/heitor/workspace/apras/.claude/worktrees/agent-a51db4f2b8aa8ad65`
**Base**: `ea37e9a`, nine staged paths, nothing unstaged, nothing committed
**Date**: 2026-10-05

VERDICT: APPROVED

## Toolchain actually used

- `vitest` 5.0.3, run from the worktree's own `frontend/`.
- **eslint 10.11.0** (`npx eslint --version` → `v10.11.0`), i.e. the version `package-lock.json` pins, run from the worktree's own install. The stale 9.39.4 in the main checkout was not used and none of the figures below come from it.
- `npm run build` → vite 8.3.1, `tsc` included.

## Expected Results Checked

- [x] **R1** — `TenantHeaderLogo.tsx` exists at `frontend/src/features/user-administration/components/TenantHeaderLogo.tsx`; `Navbar.tsx` imports it and renders `<TenantHeaderLogo />` inside the `<header>`'s left group. `grep -c "size-3.5" frontend/src/features/user-administration/components/Navbar.tsx` **printed `0`** (exit status 1, as the result anticipates — the printed number is what I judged). The `size-3.5` dot now lives only in `TenantHeaderLogo.tsx`'s fallback branch.
- [x] **R2** — asserted by *"renders the acting condominium's logo from the public logo route"*. The fixture's `logo_url` is deliberately the storage path `/static/uploads/vila-nova.png`, so the `src` assertion cannot pass by echoing it; `src` is exactly `tenantLogoUrl("vila-nova")` and `alt` exactly `Residencial Vila Nova`. Passes.
- [x] **R3** — asserted by *"names the link after the condominium and keeps one link in the banner"*: `getByRole("link", { name: "Residencial Vila Nova" })` resolves, `href="/"`, and `within(getByRole("banner")).getAllByRole("link")` has length 1 (plus an identity check that it is the same node). The query is banner-scoped, as required. Passes.
- [x] **R4** — asserted by *"shows the fallback and keeps the appName name when no logo is configured"*: banner-scoped `queryByRole("img")` is `null`, `getByTestId("tenant-header-fallback")` resolves, and the banner-scoped `getByRole("link", { name: "APRAS" })` resolves and is the same node as the fallback. Navbar's existing case **"exposes exactly one link in the banner, the appName logo pointing at /"** is present at `Navbar.test.tsx:1022` and passes unmodified — the staged diff to that file is a 27-line addition only (the `useTenantProfile` mock), with no case body touched.
- [x] **R5** — asserted by *"shows the fallback with no spinner and no skeleton while the profile is pending"*: no banner `img`, fallback present, `queryByRole("status")` and `queryByRole("progressbar")` both `null`. Passes.
- [x] **R6** — asserted by *"shows the fallback when the profile read failed"*. Passes.
- [x] **R7** — asserted by *"suppresses the image and shows the fallback once the bytes fail"*. Passes.
- [x] **R8** — asserted by the single case *"recovers by itself once, 60 s after the failure, and then stops"*, under `vi.useFakeTimers()`, with no re-render and no prop change: (a) +59 000 ms keeps `img` `null`; (b) a further +2 000 ms brings the image back with `src` exactly `tenantLogoUrl("vila-nova")` and no fallback; (c) a second `fireEvent.error` plus +120 000 ms leaves the image gone and the fallback present. All three advances are wrapped in `act`. Passes. See the mutations below for the two broken-retry probes and for the `act` claim.
- [x] **R9** — asserted by *"replaces the element on a slug change…"*: `second !== first`, `src` exactly `tenantLogoUrl("parque-azul")`, and `fireEvent.error(first)` on the detached node leaves the live image in place with no fallback. Passes; the mutation below shows the case is load-bearing.
- [x] **R10** — `classTokens(banner img).sort()` equals exactly `["h-7","max-w-32","object-contain","w-auto"]`, asserted in both schemes. The source `className` is literally `"h-7 w-auto max-w-32 object-contain"`: no `dark:` token, no `invert`, no `filter`, and none of the card's tokens.
- [x] **R11** — asserted by *"wraps the image in a card whose only paint token is dark:-gated, in both schemes"*: one case, rendered twice (plain, then inside `<div className="dark">` as an **ancestor**), each time checking that `getByTestId("tenant-header-logo-plate")` resolves, that `banner img.parentElement === plate`, and that `classTokens(plate).sort()` equals exactly `["dark:bg-foreground","inline-flex","items-center","px-1","rounded-md"]`, plus a direct equality of the two arrays. Implementation: a wrapper `<span className="inline-flex items-center px-1 rounded-md dark:bg-foreground">` around the `<img>`. All four wrong implementations were built and each failed — see below.
- [x] **R12** — four absence assertions exist (`logo_url: null`, pending, error, and the latched state), the latched one repeated inside a `.dark` ancestor. The plate is part of the state-1 return only, so it cannot exist in the fallback branch. Proven load-bearing: wrapping the plate around the fallback mark fails **all four**.
- [x] **R13** — three cases. Logo branch: the wrapping link's tokens are `flex items-center hover:opacity-80 transition-opacity`, no `md:hidden`. `logo_url: null`: the fallback carries `md:hidden`. After `fireEvent.error`: the fallback does **not** carry it (`logoUrl === null && "md:hidden"` is the only gate). Passes.
- [x] **R14** — `npx vitest run src/features/user-administration/__tests__/TenantHeaderLogo.test.tsx` → **1 file passed, 18 tests passed**, with at least one case per state (state 1: four; states 2/3/4: three; state 5 latch: three; card: five; `md:hidden`: three).
- [x] **R15** — the four Navbar files: **4 passed, 45 tests passed**. Case counts per file against `git show ea37e9a:` are identical (34 / 5 / 4 / 2 = 45); a grep for `.skip`, `.only`, `.todo`, `xit(`, `xdescribe(` across all five test files matched nothing.
- [x] **R16** — full `npx vitest run` in `frontend/`: **198 files passed, 2594 tests passed**, no failing file at all, so none newly failing. `npm run build` (vite + `tsc`) exited **0**.
- [x] **R17** — `npx eslint . -f json` with eslint **10.11.0** over the worktree: **370 errors, 2 warnings, 372 problems, 66 files**, exactly the stated lockfile-pinned baseline for `ea37e9a` — no increase. Per-file: `TenantHeaderLogo.tsx`, `TenantHeaderLogo.test.tsx`, `Navbar.tsx`, `Navbar.modules/permissions/tenantAdmin.test.tsx` all report **0/0**. `Navbar.test.tsx` reports 26 `@typescript-eslint/no-explicit-any` errors, all at lines 181–779, i.e. entirely below the added hunk at lines 52–78; the staged addition introduces no new problem.
- [x] **R18** — `git diff --cached --name-only | grep '^backend/'` matched nothing (nine paths, all under `docs/tasks/` and `frontend/src/`), and `git diff --name-only` is empty.
- [x] **R19** — `docs/tasks/APRAS-110-spec.md:91` is headed **"The cost of the logo bytes (decided: accept, bounded, degrade)"**. It names `@limiter.limit("30/minute")` per IP at `public_branding.py:98-135`, states "**no `Cache-Control` and no `ETag`**", gives the volume as "one logo request per full document load per user, plus at most one retry per document load, and zero per in-app navigation", and states the explicit decision: "**Decision: accept it in this task, unmitigated, and degrade gracefully**", with the remedy tracked as APRAS-124. Behaviour state 5 lists "a **429 from the route's `30/minute` per-IP limit**" among its four causes.
- [x] **R20** — `docs/tasks/APRAS-110-mock.html`, 316 lines, plain HTML opened directly with no build step (Tailwind and lucide via CDN `<script src>`, logos as inline data SVG, no bundler). `#states` renders **five** `labelled(...)` cards for the six states — square logo; extreme 10:1 aspect ratio; one card for states 2+3+4 which render identically; the broken-bytes state, driven for real with a 3 s retry; and the dark scheme with the card. The two question sections render below, each labelled with the operator's answer: *"Question 1 … Answered: A"* and *"Question 2 … Answered: B"*, with the non-chosen option drawn and marked "(not chosen)".

## Mutation probes

Every mutation was made against a scratchpad copy of the pristine file, run, restored, and verified byte-identical with `cmp`.

| # | Mutation | Result | Assertion that caught it |
|---|---|---|---|
| M1 | `dark:bg-foreground` → `bg-foreground` (paints unconditionally) | FAIL, 1 test | R11 plate token equality: `expected [ Array(5) ] to deeply equal [ 'dark:bg-foreground', …(4) ]` |
| M2 | JS branch: `cn("…", document.querySelector(".dark") ? "bg-foreground" : undefined)` | FAIL, 1 test | R11 token equality on the light render (4 tokens, no paint token) |
| M3 | plate made a **sibling** of the image (self-closing `<span/>` before the `<img>`) | FAIL, 1 test | R11 `img.parentElement === plate` — the parent is the `<a>` |
| M4 | no card rendered at all | FAIL, 1 test | R11 `getByTestId("tenant-header-logo-plate")` — `Unable to find an element by: [data-testid="tenant-header-logo-plate"]` |
| M5 | plate wrapped around the **fallback** mark as well | FAIL, **4 tests** | R12's four absence cases: no-logo, pending, error, and latched-incl-dark, each `expected <span …> to be null` |
| M6 | React `key` removed **and** handler switched to `event.currentTarget.src` | FAIL, 1 test | R9: `expected <img …> not to be <img …> // Object.is equality` — i.e. `first === second` |
| M7 | retry never fires (`shouldRetry = false`) | FAIL, 1 test | R8 step (b): `Unable to find an accessible element with the role "img"` after the 61 s advance |
| M8 | retry unbounded (`current.failures >= 1`) | FAIL, 1 test | R8 step (c): `expected <img …> to be null` after the second failure + 120 s |
| M9 | `dark:invert filter` added to the image's class | FAIL, 2 tests | R10 in both schemes: `expected [ Array(6) ] to deeply equal [ 'h-7', 'max-w-32', …(2) ]` |
| M10 | test-side: one `act(() => vi.advanceTimersByTime(2_000))` unwrapped | FAIL, 1 test | R8 step (b) fails for the correct implementation, confirming the `act` wrapping is load-bearing under React 19, not decoration |

## The known R11 hole — confirmed, and slightly worse than stated

The implementation does use a **single literal string**: `className="inline-flex items-center px-1 rounded-md dark:bg-foreground"`. It does not assemble the token.

Nothing enforces that. I replaced it with `` className={`inline-flex items-center px-1 rounded-md dark:bg-${"foreground"}`} `` and the suite stayed **18 passed** — jsdom has no Tailwind and no test reads a computed background, so the class-list equality is satisfied by a token that Tailwind's scanner would never see.

One addition to the stated hole, found while probing it: a *compiled-CSS* check would not close it either. `.dark\:bg-foreground:is(.dark *){background-color:var(--color-foreground)}` is present in `dist/assets/*.css` **even under the dynamic-token mutation**, because `TenantHeaderLogo.test.tsx:281` and the component's own doc comment both contain the literal string and Tailwind v4 scans those files too. So the rule's presence in the bundle proves nothing about the component. The discipline here is **observed, not enforced** — held only by the literal in the source and by review. (The shipped, pristine build does emit the rule, and `--foreground` is `oklch(0.98 0.01 160)` in `.dark`, so the card is the near-white surface the operator chose as option B.)

## Blocking Findings

None.

## Suggestions

1. **R11's dynamic-token hole is unguarded.** If this card pattern spreads, a cheap guard would be a source sweep asserting that `TenantHeaderLogo.tsx` contains the literal `dark:bg-foreground` inside a `className="…"` and no template literal in a `className`. The project already has several `readFileSync` sweeps in `src/__tests__/` (`themeTokenCompile`, `brandTextRole`, `themeTokenMigration`) that this would sit beside naturally. Non-blocking: the current code is correct and the gap is documented here.
2. The same 27-line `useTenantProfile` mock block is now duplicated verbatim in four Navbar test files. A shared helper under `src/test/` would keep the four from drifting, though the existing files already duplicate their other mocks the same way, so this is a pre-existing house style rather than something this task introduced.

## Worktree left as found

`git status --porcelain` after all probes: the same nine staged paths (2 `A`, 4 `M` tests, 1 `A` test, 1 `M` `Navbar.tsx`, 1 `A` `TenantHeaderLogo.tsx`), the single pre-existing untracked `frontend/.vitest/json/output.json`, nothing unstaged, `HEAD` still `ea37e9a`. Both mutated files verified byte-identical to their pristine copies with `cmp`. No `git stash`, no staging, no commit, no Meridian write.
