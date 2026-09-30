/**
 * The focus trap's own cases (APRAS-118).
 *
 * These exist because the same decisions, made inside `ObraPrintDialog`'s
 * keydown closure, were unreachable from a test: the panel always carries its
 * close button, so an empty focusable list was impossible, and the edge cases
 * could only be driven through `userEvent.tab()` with the real browser
 * deciding what focus does next. Here the container is the input.
 *
 * Each case asserts the *return value* — the element focus moved to, or `null`
 * — and not merely that `preventDefault` was called. A spy on
 * `preventDefault` would pass equally for "moved focus to the wrong end".
 */

import { afterEach, describe, expect, it } from "vitest";
import {
  FOCUSABLE_SELECTOR,
  cycleTabWithin,
  focusableWithin,
} from "../lib/focusTrap";

/** A panel with `count` real buttons, attached so `activeElement` works. */
const panelWith = (count: number): HTMLDivElement => {
  const panel = document.createElement("div");
  for (let i = 0; i < count; i += 1) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `b${i}`;
    panel.append(button);
  }
  document.body.append(panel);
  return panel;
};

const buttons = (panel: HTMLElement): HTMLElement[] =>
  Array.from(panel.querySelectorAll("button"));

const tab = (shiftKey: boolean) => ({
  shiftKey,
  prevented: false,
  preventDefault(this: { prevented: boolean }) {
    this.prevented = true;
  },
});

afterEach(() => {
  document.body.replaceChildren();
});

describe("focusableWithin", () => {
  it("returns the panel's focusable elements in document order", () => {
    const panel = panelWith(3);

    expect(focusableWithin(panel).map((el) => el.textContent)).toEqual([
      "b0",
      "b1",
      "b2",
    ]);
  });

  it("returns an empty list for no panel, rather than throwing", () => {
    expect(focusableWithin(null)).toEqual([]);
  });

  it("skips a tabindex=-1 element, which is how the scrim stays out", () => {
    const panel = panelWith(1);
    const scrim = document.createElement("button");
    scrim.type = "button";
    scrim.tabIndex = -1;
    panel.append(scrim);

    // Positive first: the selector does match something here, so the exclusion
    // below is a real exclusion and not an empty query.
    expect(focusableWithin(panel)).toHaveLength(1);
    expect(focusableWithin(panel)).not.toContain(scrim);
    expect(panel.querySelectorAll(FOCUSABLE_SELECTOR)).toHaveLength(1);
  });
});

describe("cycleTabWithin", () => {
  it("wraps forward from the last element to the first", () => {
    const panel = panelWith(3);
    const items = buttons(panel);
    items[2].focus();

    const event = tab(false);
    expect(cycleTabWithin(event, panel)).toBe(items[0]);
    expect(document.activeElement).toBe(items[0]);
    expect(event.prevented).toBe(true);
  });

  it("wraps backward from the first element to the last", () => {
    const panel = panelWith(3);
    const items = buttons(panel);
    items[0].focus();

    const event = tab(true);
    expect(cycleTabWithin(event, panel)).toBe(items[2]);
    expect(document.activeElement).toBe(items[2]);
    expect(event.prevented).toBe(true);
  });

  it("leaves a Tab in the middle of the list to the browser", () => {
    const panel = panelWith(3);
    const items = buttons(panel);
    items[1].focus();

    const event = tab(false);
    expect(cycleTabWithin(event, panel)).toBeNull();
    expect(document.activeElement).toBe(items[1]);
    expect(event.prevented).toBe(false);
  });

  it("pulls focus back in when it has escaped the panel", () => {
    const panel = panelWith(2);
    const items = buttons(panel);
    const stray = document.createElement("button");
    stray.type = "button";
    document.body.append(stray);
    stray.focus();
    expect(panel.contains(document.activeElement)).toBe(false);

    const event = tab(false);
    expect(cycleTabWithin(event, panel)).toBe(items[0]);
    expect(document.activeElement).toBe(items[0]);
  });

  it("re-enters at the last element when focus escaped and Shift is held", () => {
    const panel = panelWith(2);
    const items = buttons(panel);
    const stray = document.createElement("button");
    stray.type = "button";
    document.body.append(stray);
    stray.focus();

    expect(cycleTabWithin(tab(true), panel)).toBe(items[1]);
  });

  it("does nothing when the panel holds nothing focusable", () => {
    const panel = document.createElement("div");
    panel.textContent = "no controls here";
    document.body.append(panel);

    const event = tab(false);
    expect(cycleTabWithin(event, panel)).toBeNull();
    expect(event.prevented).toBe(false);
  });

  // This pins the composition, not a branch of its own: a missing panel reaches
  // `cycleTabWithin` as `focusableWithin`'s empty list, and that handling is
  // pinned by `focusableWithin`'s own case above. What is asserted here is that
  // the two compose without throwing.
  it("does nothing when there is no panel at all", () => {
    const event = tab(false);
    expect(cycleTabWithin(event, null)).toBeNull();
    expect(event.prevented).toBe(false);
  });

  it("treats a single focusable element as both edges", () => {
    const panel = panelWith(1);
    const only = buttons(panel)[0];
    only.focus();

    // Forward and backward both land back on it, which is what a one-control
    // dialog must do: the trap may never hand focus to the page behind it.
    expect(cycleTabWithin(tab(false), panel)).toBe(only);
    expect(cycleTabWithin(tab(true), panel)).toBe(only);
    expect(document.activeElement).toBe(only);
  });
});
