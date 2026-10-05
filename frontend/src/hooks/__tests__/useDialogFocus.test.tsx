import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import useDialogFocus from "../useDialogFocus";
import { focusableWithin } from "../../lib/focusTrap";

/**
 * APRAS-98 — the modal keyboard/focus hook extracted from `ObraPrintDialog`.
 *
 * Two of the cases below exist for Decision 3b (`onClose` in a ref, keydown
 * deps `[open]`) and both are written so they **fail** against the rejected
 * `[open, onClose]` alternative. The phrasings that do not discriminate are
 * named in the spec and are kept here only where they test a different bug:
 * "a later Escape invokes the new callback" passes either way, because the
 * alternative's teardown/setup pair installs a fresh closure.
 *
 * Nothing here renders under `<StrictMode>`: its intentional double invocation
 * would add listener calls belonging to neither implementation, and the suite
 * does not enable it anyway.
 */

/**
 * A panel with three focusable controls and an opener outside it.
 *
 * `renderHook` cannot be used for the 3b cases: its harness renders `null`, so
 * `panelRef` would point at nothing and there would be no element to assert
 * focus identity against.
 */
const Harness: React.FC<{
  open: boolean;
  onClose: () => void;
}> = ({ open, onClose }) => {
  const panelRef = React.useRef<HTMLDivElement>(null);
  useDialogFocus(open, onClose, panelRef);

  return (
    <>
      <button type="button" data-testid="opener">
        opener
      </button>
      {open && (
        <div ref={panelRef} data-testid="panel">
          <button type="button" data-testid="first">
            first
          </button>
          <button type="button" data-testid="middle">
            middle
          </button>
          <button type="button" data-testid="last">
            last
          </button>
        </div>
      )}
    </>
  );
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useDialogFocus", () => {
  it("focuses the panel's first focusable element when it mounts open", () => {
    render(<Harness open onClose={vi.fn()} />);

    expect(document.activeElement).toBe(screen.getByTestId("first"));
  });

  it("invokes onClose on Escape", async () => {
    const onClose = vi.fn();
    render(<Harness open onClose={onClose} />);

    await userEvent.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("ignores a key that is neither Escape nor Tab", async () => {
    const onClose = vi.fn();
    render(<Harness open onClose={onClose} />);

    await userEvent.keyboard("a");

    expect(onClose).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(screen.getByTestId("first"));
  });

  it("cycles Tab from the last control back to the first", async () => {
    render(<Harness open onClose={vi.fn()} />);
    screen.getByTestId("last").focus();

    await userEvent.tab();

    expect(document.activeElement).toBe(screen.getByTestId("first"));
  });

  it("cycles Shift+Tab from the first control to the last", async () => {
    render(<Harness open onClose={vi.fn()} />);
    expect(document.activeElement).toBe(screen.getByTestId("first"));

    await userEvent.tab({ shift: true });

    expect(document.activeElement).toBe(screen.getByTestId("last"));
  });

  it("restores focus to the opener and drops the listener when open goes false", async () => {
    const onClose = vi.fn();
    const opened = render(<Harness open={false} onClose={onClose} />);
    const opener = screen.getByTestId("opener");
    opener.focus();
    expect(document.activeElement).toBe(opener);

    opened.rerender(<Harness open onClose={onClose} />);
    expect(document.activeElement).toBe(screen.getByTestId("first"));

    opened.rerender(<Harness open={false} onClose={onClose} />);
    expect(document.activeElement).toBe(opener);

    // The listener left with the effect: a further Escape reaches nobody.
    await userEvent.keyboard("{Escape}");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("drops the listener when the holder unmounts while open", async () => {
    // Focus restore is not asserted here on purpose: unmounting this harness
    // takes the opener with it, and `.focus()` on a detached node is a no-op.
    // The restore is proven by the `open`-goes-false case above, where the
    // opener survives — which is also the shape both real call sites have.
    const onClose = vi.fn();
    const opened = render(<Harness open onClose={onClose} />);

    opened.unmount();
    await userEvent.keyboard("{Escape}");

    expect(onClose).not.toHaveBeenCalled();
  });

  describe("Decision 3b — onClose lives in a ref and the keydown deps are [open]", () => {
    it("leaves focus on a non-first control across a re-render with a new onClose identity", () => {
      const opened = render(<Harness open onClose={() => undefined} />);

      // The premise, asserted before the act: focus sits on a control that is
      // *not* the panel's first focusable element, so "focus did not move"
      // cannot pass vacuously through the alternative's
      // teardown-`opener.focus()` / setup-`first.focus()` pair.
      const middle = screen.getByTestId("middle");
      const panel = screen.getByTestId("panel");
      expect(focusableWithin(panel)[0]).not.toBe(middle);
      middle.focus();
      expect(document.activeElement).toBe(middle);

      opened.rerender(<Harness open onClose={() => undefined} />);

      expect(document.activeElement).toBe(middle);
    });

    it("adds and removes no keydown listener across a re-render with a new onClose identity", () => {
      const opened = render(<Harness open onClose={() => undefined} />);

      // Spied *after* mount, so the effect's own first `addEventListener` is
      // not counted; only the re-render's deltas are.
      const added = vi.spyOn(document, "addEventListener");
      const removed = vi.spyOn(document, "removeEventListener");
      const keydownCalls = (spy: typeof added): number =>
        spy.mock.calls.filter(([type]) => type === "keydown").length;

      opened.rerender(<Harness open onClose={() => undefined} />);

      // Under `[open, onClose]` React tears the effect down and sets it up
      // again: 1 and 1. Under `[open]` the deps did not change: 0 and 0.
      expect(keydownCalls(removed)).toBe(0);
      expect(keydownCalls(added)).toBe(0);
    });

    it("invokes the latest onClose on a later Escape (a different bug — not 3b)", async () => {
      const first = vi.fn();
      const second = vi.fn();
      const opened = render(<Harness open onClose={first} />);

      opened.rerender(<Harness open onClose={second} />);
      await userEvent.keyboard("{Escape}");

      expect(second).toHaveBeenCalledTimes(1);
      expect(first).not.toHaveBeenCalled();
    });
  });
});
