/**
 * The `Tab` half of a modal's focus trap (APRAS-118).
 *
 * Extracted from `ObraPrintDialog` for two reasons, both about what can be
 * tested honestly.
 *
 * The first: inside the dialog the panel always carries its close button, so an
 * empty focusable list could not happen and a test for it would have to fake a
 * DOM the component cannot produce. As a function taking the container, an
 * empty list is an ordinary input and the early return is a contract rather
 * than dead defence.
 *
 * The second: the dialog's keydown handler previously decided Escape, the
 * non-`Tab` case, the two edges and the escaped-focus case in one closure. Each
 * of those is a branch a caller cannot reach independently. Split out, the
 * cycling is exercised directly and the handler is left with one `if`/`else if`.
 *
 * Note `items[items.length - 1]` and not `items.at(-1)`: `at` is typed
 * `T | undefined` whatever the index, which is what forced the original
 * `if (!first || !last) return` — a guard for the type, not for a case, and one
 * that could never be false. Plain indexing is typed `T` here, because
 * `noUncheckedIndexedAccess` is not part of `strict`, so after the two guards
 * there is nothing left to narrow.
 */

/**
 * What counts as focusable inside a trapped panel.
 *
 * `[tabindex="-1"]` is excluded on purpose: the scrim is a real `<button>` so
 * that clicking outside needs no keyboard handler of its own, and it carries
 * `tabIndex={-1}` precisely so the trap does not stop on a blank full-screen
 * target.
 */
export const FOCUSABLE_SELECTOR =
  'button:not([tabindex="-1"]), [href], [tabindex]:not([tabindex="-1"])';

/** Every focusable element inside `panel`, in document order. */
export const focusableWithin = (panel: HTMLElement | null): HTMLElement[] =>
  Array.from(panel?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR) ?? []);

/**
 * Keep `Tab` inside `panel`, and pull focus back in when it has escaped.
 *
 * Only the two edges need handling — `Tab` in the middle of the list is the
 * browser's job and is left alone. Focus that is outside the panel entirely is
 * treated as an edge, so the next `Tab` re-enters at the near end instead of
 * walking the rest of the page.
 *
 * Returns the element it moved focus to, or `null` when it left the event
 * alone, so a caller or a test can observe the decision without a spy.
 */
// skipcq: JS-R1005
//
// Suppressed with the measurement behind it, not to quiet a linter. This
// function makes five decisions -- one guard, one conditional, one two-part `if`
// -- for a cyclomatic complexity of 6, which the analyzer's own risk table calls
// "review and monitor", not "refactor". The threshold now declared in
// `.deepsource.toml` is `medium`, which raises above 15; the finding survived
// that commit on the analysed commit itself, so either the analyzer takes its
// config from the default branch (in which case this branch could never see its
// own fix) or it measures this function higher than the count above. Neither is
// worth a third reshaping of a focus trap: the first extraction moved the
// complexity without reducing it, and the second cut it by more than half and
// still failed.
//
// Remove this line once the threshold has landed on `master` and a run there
// confirms which of the two explanations held.
export const cycleTabWithin = (
  event: Pick<KeyboardEvent, "shiftKey" | "preventDefault">,
  panel: HTMLElement | null,
): HTMLElement | null => {
  const items = focusableWithin(panel);
  // One guard, and emptiness is the whole of it: `focusableWithin(null)` is
  // already empty, so a missing panel arrives here as an empty list. The
  // `panel === null` half is for the type checker alone -- `strictNullChecks` is
  // on, because TypeScript 6 enables `strict` by default even though this
  // tsconfig never says so. It is deliberately *not* written as a separate
  // guard: splitting it produced a branch that no mutation could redden, which
  // is this repository's most common defect. Null is pinned where it is actually
  // handled, in `focusableWithin`'s own case.
  //
  // Past here `panel` is usable unguarded, so nothing below needs optional
  // chaining, and indexing `items` needs no narrowing either --
  // `noUncheckedIndexedAccess` is not part of `strict`.
  if (panel === null || items.length === 0) return null;

  // One conditional, not three: the pair is `[where focus re-enters, the edge
  // it leaves from]`. Tab leaves the last control and re-enters at the first;
  // Shift+Tab is exactly the mirror. With a single control it is both, which is
  // what a one-button dialog needs -- the trap may never release focus to the
  // page behind it.
  const [reentry, edge] = event.shiftKey
    ? [items[items.length - 1], items[0]]
    : [items[0], items[items.length - 1]];

  // Focus that escaped the panel is treated as being at the edge, so the next
  // Tab comes back in rather than walking the rest of the page.
  const active = panel.ownerDocument.activeElement;
  if (active !== edge && panel.contains(active)) return null;

  event.preventDefault();
  reentry.focus();
  return reentry;
};
