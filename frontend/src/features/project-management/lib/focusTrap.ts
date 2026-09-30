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
 * that could never be false. Indexing is typed `T` under this project's
 * `tsconfig`, so after the emptiness check there is nothing left to narrow.
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
export const cycleTabWithin = (
  event: Pick<KeyboardEvent, "shiftKey" | "preventDefault">,
  panel: HTMLElement | null,
): HTMLElement | null => {
  const items = focusableWithin(panel);
  if (items.length === 0) return null;

  const first = items[0];
  const last = items[items.length - 1];

  const active = panel?.ownerDocument.activeElement ?? null;
  const outside = !panel?.contains(active);
  const atEdge = event.shiftKey ? active === first : active === last;
  if (!atEdge && !outside) return null;

  const target = event.shiftKey ? last : first;
  event.preventDefault();
  target.focus();
  return target;
};
