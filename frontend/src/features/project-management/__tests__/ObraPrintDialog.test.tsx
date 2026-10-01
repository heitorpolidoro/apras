import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ObraPrintDialog from "../components/ObraPrintDialog";

/**
 * APRAS-118 — the obra selector. The keyboard claims are the reason this
 * component exists rather than a bare `<ul>`: `alert-modal.tsx` supplies
 * `role="dialog"`, the backdrop and Escape, and the two things it lacks —
 * a focus trap and focus restore — are added here and pinned below.
 */

const OBRAS = [
  { index: 0, title: "Sede Social — Reforma", kind: "Edificação" },
  { index: 1, title: "Portarias — Ampliação", kind: "Reforma" },
];

const Harness: React.FC<{
  obras: typeof OBRAS;
  onSelect?: (index: number) => void;
}> = ({ obras, onSelect = vi.fn() }) => {
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Abrir para impressão
      </button>
      <ObraPrintDialog
        open={open}
        obras={obras}
        onClose={() => setOpen(false)}
        onSelect={onSelect}
      />
    </>
  );
};

const openDialog = async () => {
  const user = userEvent.setup();
  const opener = screen.getByRole("button", { name: /impress/i });
  await user.click(opener);
  await screen.findByRole("dialog");
  return { user, opener };
};

describe("ObraPrintDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists every obra with its title and its kind", async () => {
    render(<Harness obras={OBRAS} />);
    await openDialog();

    expect(
      screen.getByRole("button", { name: /Sede Social/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Portarias/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Edificação")).toBeInTheDocument();
    expect(screen.getByText("Reforma")).toBeInTheDocument();
  });

  it("shows a title-only row for an obra whose hero carries no kind", async () => {
    // `_hero_html` writes `Obra 01` with no separator when the project has no
    // kind, so `listObrasFromReport` yields `kind: ""` and the row must not
    // render an empty second line.
    render(<Harness obras={[{ index: 0, title: "Quadra", kind: "" }]} />);
    await openDialog();

    const row = screen.getByRole("button", { name: /Quadra/ });
    expect(row.querySelectorAll("span > span")).toHaveLength(1);
  });

  it("reports the chosen obra's index and closes", async () => {
    const onSelect = vi.fn();
    render(<Harness obras={OBRAS} onSelect={onSelect} />);
    const { user } = await openDialog();

    await user.click(screen.getByRole("button", { name: /Portarias/ }));

    expect(onSelect).toHaveBeenCalledWith(1);
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
  });

  it("opens onto the empty state with no obra and offers no print row", async () => {
    render(<Harness obras={[]} />);
    await openDialog();

    expect(
      screen.getByText("Nenhuma obra publicada neste condomínio."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("still opens, and prints nothing unprompted, with exactly one obra", async () => {
    const onSelect = vi.fn();
    render(<Harness obras={[OBRAS[0]]} onSelect={onSelect} />);
    await openDialog();

    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("moves focus into the dialog on open", async () => {
    render(<Harness obras={OBRAS} />);
    await openDialog();

    const dialog = screen.getByRole("dialog");
    await waitFor(() =>
      expect(dialog.contains(document.activeElement)).toBe(true),
    );
  });

  it("traps Tab inside the dialog, wrapping both ways", async () => {
    render(<Harness obras={OBRAS} />);
    const { user } = await openDialog();
    const dialog = screen.getByRole("dialog");

    // Scoped to the panel, not the dialog: the scrim is a `tabIndex={-1}`
    // button outside the panel and is deliberately not a stop in the cycle.
    const panel = within(dialog).getByTestId("obra-print-panel");
    const focusable = Array.from(panel.querySelectorAll<HTMLElement>("button"));
    expect(focusable.length).toBeGreaterThan(1);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    last.focus();
    await user.tab();
    expect(document.activeElement).toBe(first);

    await user.tab({ shift: true });
    expect(document.activeElement).toBe(last);
  });

  it("closes on Escape and returns focus to the control that opened it", async () => {
    render(<Harness obras={OBRAS} />);
    const { user, opener } = await openDialog();

    await user.keyboard("{Escape}");

    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await waitFor(() => expect(document.activeElement).toBe(opener));
  });

  it("returns focus to the opener after a completed print too", async () => {
    render(<Harness obras={OBRAS} />);
    const { user, opener } = await openDialog();

    await user.click(screen.getByRole("button", { name: /Sede Social/ }));

    await waitFor(() => expect(document.activeElement).toBe(opener));
  });

  it("restores nothing when what had focus was not an HTML element", async () => {
    // The component captures the opener as
    // `activeElement instanceof HTMLElement ? activeElement : null`, and every
    // case above opens from a `<button>`, so the `null` side has never run. An
    // SVG element is focusable and is **not** an `HTMLElement`, which is the
    // ordinary way to reach it: an icon-only control drawn as inline SVG.
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("tabindex", "0");
    document.body.append(svg);

    try {
      const onClose = vi.fn();
      const { rerender } = render(
        <ObraPrintDialog
          open={false}
          obras={OBRAS}
          onClose={onClose}
          onSelect={vi.fn()}
        />,
      );

      // The premise, asserted rather than assumed: this really is focused, and
      // really is not an `HTMLElement`. Without both, the expectation at the end
      // would hold for reasons that have nothing to do with the branch.
      (svg as unknown as { focus: () => void }).focus();
      expect(document.activeElement).toBe(svg);
      expect(svg instanceof HTMLElement).toBe(false);

      rerender(
        <ObraPrintDialog
          open
          obras={OBRAS}
          onClose={onClose}
          onSelect={vi.fn()}
        />,
      );

      // The dialog took focus, so the opener was captured by now -- as `null`.
      const panel = await screen.findByTestId("obra-print-panel");
      await waitFor(() =>
        expect(panel.contains(document.activeElement)).toBe(true),
      );

      rerender(
        <ObraPrintDialog
          open={false}
          obras={OBRAS}
          onClose={onClose}
          onSelect={vi.fn()}
        />,
      );

      // Nothing to restore to. Widening the guard to `Element` would send focus
      // back to the SVG here, which is what makes this assertion bite.
      expect(document.activeElement).not.toBe(svg);
    } finally {
      svg.remove();
    }
  });
});
