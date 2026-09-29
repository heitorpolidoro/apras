import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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

    const focusable = Array.from(
      dialog.querySelectorAll<HTMLElement>("button"),
    );
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
});
