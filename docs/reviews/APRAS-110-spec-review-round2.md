# APRAS-110 spec review — round 2 (findings-only)

Reviewed: `docs/tasks/APRAS-110-spec.md`, `docs/tasks/APRAS-110-mock.html`, and the
18 `expected_results` recorded on the task (`.meridian/tasks/APRAS-110.json`).
Field contract read from
`/Users/heitor/workspace/meridian/plugin/plugins/meridian/references/schema.md`.
Nothing in the working tree was modified; no task field was written.

This is a findings-only round. Round 1's verification of the spec's factual
groundwork is taken as given; what follows verifies what **changed**, on my own
evidence, plus an adversarial pass over the new and the rewritten criteria.

The spec is in English. The recorded `expected_results` are 18, non-empty,
English, and correspond one-for-one and in order to the spec's Expected Results
bullets — the gate the `spec_review` → `ready_todo` transition exists for is
satisfied on all three counts (non-empty, mechanically verifiable, covered by
the spec).

---

## Finding 1 — uncached, rate-limited logo route, no decision recorded → **discharged**

Everything the new §"The cost of the logo bytes (decided: accept, bounded,
degrade)" asserts was checked against the repository rather than read.

| Claim in the revision | Verdict | Evidence |
|---|---|---|
| `@limiter.limit("30/minute")` on the logo route, per IP | **true** | `backend/app/api/v1/endpoints/public_branding.py:103`; the decorator block opens at `98` (`@router.get(`), so the spec's `98-135` range lands on the decorators, signature and docstring. The branding route at `64-65` carries the identical limit, which is why the docstring calls it "the same limit the branding route carries". |
| No `Cache-Control`, no `ETag`, deliberately, per APRAS-92 D3 | **true, verbatim from the source** | The docstring says "**No ``Cache-Control`` and no ``ETag``**, consistent with APRAS-92 D3 and for the reason stated there: a browser-held copy cannot be invalidated, and a logo replaced on the admin screen must not stay stale at a slug-stable URL." The spec paraphrases it accurately. |
| 2 MiB outbound fetch per hit; one inbound request buys one outbound | **true, verbatim** | Same docstring, lines 128-134. |
| `Navbar` is mounted by `AppChrome` above the `<Outlet/>` | **true, at the cited lines** | `App.tsx:130-137` is exactly `const AppChrome` → `<Navbar />` (132) → `<AppLayoutContent><Outlet /></AppLayoutContent>` (133-135). `Navbar` is a sibling of the outlet, not a descendant, so route changes inside the chrome re-render the outlet and leave `Navbar` mounted. |

**The volume claim is the whole basis for "accept", and it holds** — with one
imprecision that does not move the decision. Because `Navbar` sits above the
outlet, the `<img>` mounts once and survives every soft navigation *within the
chrome*, so the cost is one request per full document load plus at most one
retry, and zero per in-app navigation. The imprecision: the public routes are
deliberately **outside** `AppChrome` (`App.tsx:157-161` comment), so navigating
from an app route to `/c/<slug>/…` and back unmounts and remounts `Navbar`,
which buys a second pair of requests inside one document load. That is still
bounded by a small constant per navigation into and out of the public area, it
is nowhere near the 30/minute budget, and nothing in the accept decision depends
on the literal "once". Recorded as a suggestion, not a finding.

The two sub-checks the dispatch asked for:

- **429 enumerated as a state**: yes. §Behavior state 5 lists its four causes and
  names "a **429 from the route's `30/minute` per-IP limit**" in bold among them,
  and ER17 makes the presence of that enumeration mechanically checkable.
- **"no network request" corrected rather than deleted**: corrected. §Approach now
  reads "the header adds **no new JSON request** (it does add a request for the
  image bytes — see 'The cost of the logo bytes' below)". The true half is kept,
  the false half is replaced by a pointer to the section that quantifies it. This
  is the right repair; deleting the sentence would have lost the correct claim
  about `TenantBrandTheme` already mounting `["tenantProfile"]`.

The decision is recorded, bounded, and its two escape valves (graceful
degradation, a retry scheduled outside the limiter's window) are stated with
their reasons in order. ER17 makes the recorded decision the deliverable, which
is the only shape available given ER16 forbids touching `backend/`.

## Finding 2 — the `onError` latch wedged permanently → **discharged**, and round 1's proposed remedy was wrong

**Both of the reviser's claims against round 1 are correct, and I verify them
directly.**

`src/main.tsx:8-16` is exactly what the spec says it is:

```js
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 10,
    },
  },
});
```

So `refetchOnWindowFocus: false` and a five-minute `staleTime` are global, and
`["tenantProfile"]` has no refetch trigger from focus. Round 1's suggested
`dataUpdatedAt` remedy would therefore have no event to fire on for a user who
stays on one screen — the user who, per round 1's own finding, is the user this
task exists for. Round 1 proposed a remedy that wedges the same user; that was
wrong, and the reviser is right to say so and right to record why.

The structural-sharing half is also correct. The project is on
`@tanstack/react-query ^5.104.0` (`frontend/package.json:21`) with
`structuralSharing` at its default, so `replaceEqualDeep` returns the **previous**
object when a refetch yields deep-equal data. A `data`-identity variant of the
remedy would therefore fire never, even in the cases where a refetch does occur.
Independently verified reasoning, not taken on the reviser's word.

One overstatement in the rejected-alternative paragraph, which does not change
the conclusion: "no refetch of `["tenantProfile"]` occurs for a user who stays on
the app" ignores two paths. `refetchOnReconnect` defaults to `true` in v5 and is
not overridden, so a network reconnect refetches; and
`pages/TenantProfilePage.tsx:80` mounts `useTenantProfile()` itself, so visiting
that screen after `staleTime` has elapsed refetches via `refetchOnMount`. Neither
is reachable by a user sitting on the dashboard, which is the case the argument
is about, so the alternative is still correctly rejected as an *unreliable*
recovery condition rather than a literally impossible one. Suggestion.

**Does one bounded retry discharge the finding?** Yes, and on round 1's own
terms: round 1 named three acceptable remedies — "clear the latch when the
query's `data` identity changes on a refetch, **or allow one retry**, or scope
the latch to a mount". The revision takes the second, which is the only one of
the three that survives this app's query configuration. For the
single-condominium user who never navigates, the most likely failure by far is
the 429 this task itself introduces, and 60 s is chosen to exceed the limiter's
one-minute window, so that failure self-heals without any user action — which is
precisely what round 1 said was missing. If the retry also fails the slot holds
the fallback until the next full document load, and a reload is a condition the
user can actually reach. The bound at one is not timidity: it is forced by
finding 1's own accept decision, since an unbounded retry would turn the
degradation path into the amplification the spec just promised to keep at two
requests per load. The two sections are consistent with each other (`1 + 1 = 2`
requests per load, stated in both).

**Does the three-way `md:hidden` rule fix the desktop-blank consequence?** Yes,
at both breakpoints, and it is the part of round 1's finding that was easiest to
leave half-fixed. The rule is now: the logo link never carries `md:hidden`
(state 1, every breakpoint); the fallback carries it in states 2, 3 and 4, which
reproduces today's desktop left group exactly — verified against
`Navbar.tsx:83-91`, where the mark's `Link` is `md:hidden` today; and the
fallback **omits** it in state 5, so a desktop header where a logo was promised
shows the generic mark rather than nothing. Round 1's specific complaint ("on
desktop with *nothing at all*, since the fallback keeps `md:hidden`") is
addressed in exactly the state it was raised about, and ER11 asserts all three
legs.

## Finding 3 — class values now literal → **discharged**

ER10 reads:

> `classTokens(within(screen.getByRole("banner")).getByRole("img")).sort()` equals
> exactly `["h-7", "max-w-32", "object-contain", "w-auto"]`

Decidable by someone holding only the expected results: the helper
(`src/test/classTokens.ts:19`) is `element.className.split(/\s+/).filter(Boolean)`,
so the result is an exact string array; `.sort()` of the four tokens is
lexicographically `h-7` < `max-w-32` < `object-contain` < `w-auto`, which is the
order written, so the equality is literally satisfiable. Sorted set **equality**
rather than containment is the right strengthening: it subsumes the three
negative clauses that follow it (no `dark:`-prefixed token, no `invert`, no
`filter`-prefixed token) instead of relying on them, and it also forbids a
duplicate token. The same four literals are drawn in the mock
(`APRAS-110-mock.html:180`, `class="logoimg h-7 w-auto max-w-32 object-contain"`),
so the asserted and the drawn tokens cannot drift. §"Aspect ratio and layout"
now also states, in terms, that a token assertion proves four strings are present
and not that a 10:1 banner letterboxes, and points at the mock's
extreme-aspect card as where that behaviour is actually demonstrated — the
second half of round 1's finding 3, carried out.

**And the Tailwind-version trap is not a trap here, which I checked because it
would have been a silent false positive.** If the app were on Tailwind v3,
`max-w-32` would generate no rule, the clamp would do nothing, and ER10 would
still pass — a criterion green while the feature is broken. The app is on v4
(`package.json:34` `"tailwindcss": "^4.2.4"`, `@tailwindcss/vite ^4.3.3`,
`src/index.css:1` `@import "tailwindcss"`, no `tailwind.config.*` present), where
`max-w-32` is valid spelling on the 0.25rem spacing scale and resolves to 8rem.
The spec's claim that `max-w-32` is v4 spelling and that the mock's CDN build is
v3 is correct, and the mock handles it honestly: the `.logoimg` CSS rule
(`max-width: 8rem` and the other three properties) carries a comment saying
exactly why it exists, while the `<img>` still carries the four utility classes
the shipped component will use. Right call — the alternative, silently dropping
the clamp in the mock, would have made the extreme-aspect card a lie.

## Finding 4 — fallback selector → **discharged**

`data-testid="tenant-header-fallback"` on the fallback `Link`, and the count is
real: `grep -ro 'data-testid' frontend/src | wc -l` returns **180**, across 53
files. An established hook, not an invention, and the spec's figure is exact.

The spec also binds the noun once — "Throughout this spec, 'the fallback mark'
means exactly the element carrying `data-testid="tenant-header-fallback"`" — which
retires round 1's secondary complaint that ER4 and ER9 used two nouns for one
element. ER11 now selects by test id and says "never by a styling class".

Every fallback criterion asserts the discriminating pair. Checked one by one,
with the two defects each must catch:

| ER | Pair asserted | Fails when fallback absent | Fails when wrong branch renders |
|---|---|---|---|
| 4 (`logo_url: null`) | no `img` in banner + `getByTestId` + `getByRole("link", { name: "APRAS" })` | yes — `getByTestId` throws | yes — `queryByRole("img")` non-null |
| 5 (pending) | no `img` in banner + `getByTestId` (+ no `status`/`progressbar`) | yes | yes |
| 6 (profile error) | no `img` in banner + `getByTestId` | yes | yes |
| 7 (latch engages) | no `img` in banner + `getByTestId` | yes | yes |

ER4's third clause is worth keeping even though it is redundant with the test id,
because it is the clause that ties the criterion to
`Navbar.test.tsx`'s existing "exposes exactly one link in the banner, the appName
logo pointing at /" case, which must keep passing unmodified.

A check the revision did not claim but which matters for these four: an unscoped
`queryByRole("img")` is safe in this tree. `grep -n '<img\|role="img"'` over
`Navbar.tsx` and `Sidebar.tsx` returns nothing, so the logo will be the only
image anywhere in the rendered chrome and the scoped and unscoped forms agree.

## Finding 5 — which URL is latched → **discharged**

Both rules are now stated: the handler stores the URL the current render
computed, captured in that render's closure, and "**must not** read
`event.currentTarget.src`"; and the `<img>` carries a React `key` derived from the
logo URL plus the attempt count, so a slug change replaces the element instead of
mutating its `src`. The spec is explicit about which of the two actually closes
the hole ("This is what actually closes the in-flight hole; the closure rule
alone does not"), which is correct reasoning.

ER9 was constructed against both defective implementations, as the dispatch asked:

- **No `key`, URL from the render.** React reconciles the single `<img>` across the
  re-render and mutates its `src`. `first === second`, so `second !== first`
  fails. **Caught.**
- **`key` present, handler reads `event.currentTarget.src`.** `second !== first`
  passes, and `fireEvent.error(first)` on the detached node reaches no React
  handler, so nothing latches and the criterion passes. **Not caught — and not a
  defect.** With the `key` in place the old node is detached before any late
  `error` can be delivered, so the handler never sees an element carrying a URL
  other than its own render's, and `currentTarget.src` and the closure URL
  coincide. (They also coincide in string form, because `api/client.ts` gives
  `tenantLogoUrl` an absolute base, so jsdom's resolved `.src` equals the
  attribute — round 1 verified that.) The prohibition is therefore belt alongside
  enforced braces: unverifiable mechanically once the `key` exists, and harmless
  if an implementer ignores it. The spec is right to state it anyway, and right
  not to invent a criterion that cannot discriminate.

The third clause — after `fireEvent.error(first)`, the new slug's image is still
rendered and `queryByTestId("tenant-header-fallback")` is `null` — is what makes
the criterion assert the *consequence* (the switched-to condominium is not
latched) rather than only the element identity. Good shape.

---

## Adversarial pass over the new criteria

The question for each: what implementation satisfies this while the feature is
broken or absent?

**ER8, the recovery criterion — it genuinely discriminates.** This was the one
most at risk of being satisfiable by an implementation that never recovers, and
it is not. Walking the defective implementations:

| Implementation | Where it fails |
|---|---|
| never latches | (a): `queryByRole("img")` is not `null` at +59 s |
| latches, never recovers | (b): no image at +61 s |
| recovers immediately on error (no timer) | (a): image is back before +59 s |
| retry at 10 s | (a) |
| retry at 200 s | (b) |
| unbounded retry (60 s after *every* failure) | (c): the image returns 60 s after the second error, inside the 120 s advance |
| retry fired on re-render rather than on the timer | (b), because the case re-renders at no step |

The "no re-render and no prop change at any step" clause is what closes the last
row, and the 59 s/+2 s split pins the interval to `(59 s, 61 s]`. The bound is
enforced by (c) rather than asserted in prose. This is a well-built criterion.

**Is the three-advance sequence achievable in a React test?** Yes, with the
standard wrapper, and that is the one thing the criterion does not say. A
`setState` inside a `setTimeout` callback is not wrapped by anything: `fireEvent`
wraps its own dispatch in `act`, but `vi.advanceTimersByTime` does not, and under
React 19 with `IS_REACT_ACT_ENVIRONMENT` set the resulting update is scheduled
rather than flushed synchronously, so a bare
`vi.advanceTimersByTime(2_000); expect(getByRole("img"))…` can assert against a
pre-update DOM and will at minimum emit an act warning. The fix is routine —
`act(() => { vi.advanceTimersByTime(2_000); })` — and it changes nothing about
what is asserted or about whether QA can decide pass or fail. So this is a
developer-round hazard, not an unverifiable criterion: the failure mode is a
correct implementation failing, never a broken one passing. Suggestion, with the
wrapper named so the round is not spent discovering it.

**ER10** — see finding 3. Decidable, and the Tailwind-v4 check above closes the
only way it could be green while the clamp did nothing.

**ER9** — see finding 5. Catches the one defect that matters.

**ER7** — drives the mutation and asserts its effect, and now names the fallback
by test id rather than by class. Not satisfiable by a component that merely
declares an `onError` handler.

**ER17** (the spec contains §"The cost of the logo bytes" naming the limit, the
absent headers, the volume and the accept decision; state 5 names `429`) — an
unusual criterion in that its subject is the spec document, but it is the only
mechanically checkable form the finding-1 deliverable can take while ER16 forbids
any `backend/` change, and every clause of it is greppable. Verified satisfied as
written.

**ER15** (lint not worse than `370 problems (368 errors, 2 warnings)` across 64
files) — **measured on this checkout and exact**: summing `errorCount` and
`warningCount` over `npm run lint`'s report gives 368 errors, 2 warnings, 370
total, across 64 files with at least one problem. Round 1's figure was carried
over correctly, including the file count it had not itself verified.

**The unchanged criteria (ER1-ER6, ER11-ER16, ER18)** were re-read for the same
defect. None is satisfiable by a broken feature that is not already closed by
another criterion: ER1 is structural and would be satisfied by a component
rendering `null`, which ER2 forecloses; ER5 and ER6 are satisfied by a component
that always renders the fallback, which ER2 forecloses. That layering was
accepted in round 1 and nothing in the revision weakened it.

## The three recorded decisions

**`common.appName` as the fallback's accessible name in every fallback state,
including the latched one — right.** Consider what a screen-reader user hears in
the latched state: "APRAS, link", identical to the no-logo state, and the
condominium's name is not spoken. That is a real loss for a single-condominium
user, whose name is not carried by the switcher either. But it is the *same* loss
the sighted user takes, who sees a generic dot and is told nothing about which
condominium they are in — the failure state degrades identically in both
modalities, which is the coherent outcome. The alternative makes the accessible
name of one visually identical element depend on why it is rendering, which is
worse: assistive technology would announce a condominium name over a mark that is
not that condominium's artwork. "A failure state promises nothing about the
condominium's name" is the right principle. One weak supporting argument: the
spec cites `Navbar.test.tsx`'s existing case as "requiring `APRAS` on the no-logo
branch anyway", but that case renders the no-logo fixture, so naming the
*latched* fallback differently would not have broken it. The real argument stands
without it.

**The retry bounded at one, then the fallback for the document's life — right**,
and for the reason given rather than for convenience: an unbounded retry would
contradict the accept decision in §"The cost of the logo bytes", which is
explicitly quantified at two requests per load. A full reload clears it, which is
a condition the user can reach, so this is not the permanent wedge round 1 found.

**`max-w-32` as v4 spelling, replicated in CSS in the mock — right, and verified
on both sides.** The app is Tailwind v4.2.4 (so the utility is real); the mock
loads `cdn.tailwindcss.com`, which is v3 (so the utility is not), and the mock's
`.logoimg` rule supplies `height: 1.75rem; width: auto; max-width: 8rem;
object-fit: contain` with a comment naming the version gap. Both documents are
honest about which mechanism is doing the work.

## The mock

Opened and read in full (300 lines). Every claim made for it checks out.

- **Six states as five cards.** Exactly five `labelled(...)` cards in `#states`:
  logo configured (square emblem); extreme aspect ratio, a real 400×40 SVG;
  "No logo configured, and loading, and profile read failed"; logo bytes
  unavailable; dark scheme. The section's own prose says "Six states, **five
  cards**" and names the three that share one, so a reader counting cards is told
  why before counting. ER18 now enumerates five and lists them, matching.
- **The broken card is retitled to name the 429.** Its title reads "Logo bytes
  unavailable — 404, **429 from the route's 30/minute per-IP limit**, dropped
  connection, cold store read", with the 429 in bold — the same four causes
  §Behavior state 5 lists.
- **It renders the fallback without `md:hidden`.** The card calls
  `fallbackMark(true)`, which omits the hidden class, and its note says so in
  operator language: "shown here *without* `md:hidden`, so a desktop header is not
  left blank where a logo was promised".
- **The recovery is actually driven, not drawn.** `BROKEN` points at
  `./APRAS-110-this-asset-does-not-exist.png`; a live `error` listener swaps the
  slot's contents for the fallback mark, then a `window.setTimeout(…, 3000)`
  swaps the logo back in. So the card fails, shows the mark, retries and recovers
  under the operator's eye. The note labels the compression explicitly: "The
  retry is 60 s in the app (wider than the rate-limit window); it is shortened to
  3 s here so you can watch it. A second failure keeps the mark for the rest of
  the page's life, so the recovery can never become a request loop." Both the
  bound and its reason are in the mock, in words an operator reads.
- **Both question sections remain answerable with one letter.** Q1 and Q2 each
  carry an A card and a B card rendered side by side on the affected header
  strip, each titled in operator language ("A — logo on every screen size (the
  spec's pick)" / "B — phone only, as the APRAS dot is today"; "A — no card, logo
  as drawn (the spec's pick)" / "B — white card behind the logo in dark mode"),
  each prose block marking the spec's pick and closing with "**A or B is
  enough.**" Neither requires reading the spec.
- Vocabulary is used correctly: the header strip shows `Síndica` as Marta
  Ribeiro's condominium office, and nothing in spec or mock treats
  `tenant_admin` as a synonym for `síndico`. The spec states that nothing here is
  permission-gated, so the two roles see the same header.

One fidelity note, non-blocking: the no-logo card also calls `fallbackMark(true)`
— i.e. without the hidden class — explained by its note ("shown here as it
appears on a phone. On a desktop screen the slot is simply empty"). So the
no-logo card and the broken card render identically for opposite reasons, and the
three-way `md:hidden` rule, the subtlest thing in the spec, is the one thing the
mock cannot show by drawing. The prose carries it; a reader comparing the two
cards cannot see it.

## What I could not verify

Nothing material. Two items are judgements rather than measurements and are
labelled as such above: whether a single bounded retry is *enough* for a user
whose two attempts both fail (I judge yes, because a reload clears it and the
bound is forced by finding 1), and whether the `act()` omission in ER8 will cost
a round (I judge it a hazard, not a defect). The retry's anchor — 60 s after the
*error* rather than 60 s after *mount* — is stated in the spec but not
discriminated by ER8, because the test fires the error immediately after mount and
the two coincide there; see Suggestions.

---

VERDICT: APPROVED

None.

## Suggestions

- ER8 asserts `vi.advanceTimersByTime(59_000)` and `vi.advanceTimersByTime(2_000)`
  bare. A `setState` inside a `setTimeout` callback is not wrapped by anything
  RTL provides, so under React 19 the update is scheduled rather than flushed and
  a synchronous assertion immediately after the advance can read a pre-update DOM
  (and will at minimum emit an act warning). Write the advances as
  `act(() => { vi.advanceTimersByTime(59_000); })`. The assertions are right; only
  the mechanics need naming, and naming them saves a developer round.
- ER3's parenthetical — "the banner still exposes exactly one link
  (`getAllByRole("link")` has length 1)" — is unscoped, while ER2, ER7 and ER10
  scope their queries with `within(screen.getByRole("banner"))`. `Navbar` renders
  `<Sidebar />` as a sibling of the `<header>`, and the sidebar's links are why
  `Navbar.test.tsx`'s existing one-link case scopes to the banner. Write it as
  `within(screen.getByRole("banner")).getAllByRole("link")` so no reader has to
  reconcile a criterion that needs a banner in scope with one that counts every
  link on the screen.
- The spec cites `Navbar.test.tsx:912` for the "exposes exactly one link in the
  banner, the appName logo pointing at /" case. It is now at **line 995** — two
  commits landed test cases in that file since round 1 (`2cb0d48` APRAS-91,
  `1f0079b` APRAS-97). The quoted case title is exact and unique, so nothing is
  lost; drop the line number, or expect it to drift again while the task sits in
  the queue.
- ER8 opens with "(a) after the error of the previous result", inside a criterion
  that also says "one case". §Test criteria describes the same thing as a
  four-step sequence that includes the error. Restate the error as step (a) of
  this case so a QA agent holding only the expected results does not have to
  infer that ER7's `fireEvent.error` is re-performed here.
- §"The cost of the logo bytes" says the `<img>` "mounts once per full document
  load". The public routes sit outside `AppChrome` by design (`App.tsx:157-161`),
  so navigating to `/c/<slug>/…` and back unmounts and remounts `Navbar` and buys
  a second pair of requests within one document load. Still bounded by a small
  constant and nowhere near the 30/minute budget — worth a half-sentence so the
  figure is not read as a hard invariant.
- §"The latch and its recovery" says "no refetch of `["tenantProfile"]` occurs for
  a user who stays on the app". Two paths exist: `refetchOnReconnect` defaults to
  `true` in react-query v5 and is not overridden in `main.tsx`, and
  `pages/TenantProfilePage.tsx:80` mounts the hook itself, so visiting that screen
  after `staleTime` refetches. Neither is reachable by a user sitting on the
  dashboard, so the alternative is still correctly rejected — as *unreliable*
  rather than impossible. Soften the sentence rather than drop the paragraph; the
  structural-sharing half of the argument is airtight on its own.
- The spec says the retry fires "60 seconds after the first failure", which is the
  right anchor (a mount-anchored timer could fire only seconds after a slow
  failure, inside the limiter's window, and would not heal the 429 the section is
  about). ER8 cannot discriminate the two, because the case fires the error
  immediately after mount. No criterion is available for it in jsdom; leaving it
  as a stated implementation rule is correct, and worth knowing it is unasserted.
- The mock's no-logo card and broken card both call `fallbackMark(true)` and so
  render identically, for opposite reasons under the three-way `md:hidden` rule.
  The notes explain it, but the subtlest decision in the spec is the one the mock
  cannot draw. A pair of narrow strips at a simulated desktop width, or a single
  line of caption reading "same picture, different rule", would close it. Not
  needed for the operator's two questions.
- ER18 says the broken card shows "the latch and its 60 s retry", while the mock
  deliberately uses a 3 s stand-in and labels it. The spec's header line says this
  correctly; ER18 does not. Add "on a 3 s stand-in for the app's 60 s, labelled as
  such" so the criterion matches the artefact.
- §Accessible name offers `Navbar.test.tsx`'s existing `APRAS` assertion as a
  reason for keeping `common.appName` in the latched state. That case renders the
  no-logo fixture, so it would not have broken either way. The real argument — one
  visually identical element, one accessible name, regardless of why it shows — is
  sufficient and does not need the weaker one beside it.
