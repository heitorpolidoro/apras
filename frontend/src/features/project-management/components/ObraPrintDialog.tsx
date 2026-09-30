import React from "react";
import { useTranslation } from "react-i18next";
import { HardHat, Printer, X } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { ObraEntry } from "../lib/obraPrintDocument";

interface ObraPrintDialogProps {
  open: boolean;
  obras: ObraEntry[];
  onClose: () => void;
  /** Called with the chosen obra's index; the dialog then closes itself. */
  onSelect: (index: number) => void;
}

const FOCUSABLE =
  'button:not([tabindex="-1"]), [href], [tabindex]:not([tabindex="-1"])';

/**
 * APRAS-118 — the obra selector behind the public report's print control.
 *
 * It follows `src/components/ui/alert-modal.tsx` for `role="dialog"`,
 * `aria-modal`, the backdrop and the Escape listener, and adds the two things
 * that component lacks and that this one is required to have: focus moves into
 * the dialog on open and `Tab`/`Shift+Tab` cycle within it, and on close focus
 * returns to whatever had it when the dialog opened. The restore runs from the
 * effect's cleanup, so every exit takes it — Escape, the backdrop, the close
 * button, and a completed print alike.
 *
 * With exactly **one** obra the dialog still opens and lists it rather than
 * printing straight away: the control's contract is "opens a modal listing the
 * obras" for every condominium, and nothing is printed without a click. With
 * none it opens onto a short empty state.
 */
const ObraPrintDialog: React.FC<ObraPrintDialogProps> = ({
  open,
  obras,
  onClose,
  onSelect,
}) => {
  const { t } = useTranslation();
  const panelRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;

    const opener =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    const focusable = (): HTMLElement[] =>
      Array.from(
        panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [],
      );

    focusable()[0]?.focus();

    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const items = focusable();
      const first = items[0];
      const last = items.at(-1);
      // The panel always carries the close button, so both ends exist whenever
      // the dialog is open; the narrowing is for the type, not for a case.
      if (!first || !last) return;

      // The trap: only the two edges need handling, and a focus that escaped
      // the panel entirely is pulled back to the near edge.
      const outside = !panelRef.current?.contains(document.activeElement);
      const atEdge = event.shiftKey
        ? document.activeElement === first
        : document.activeElement === last;
      if (atEdge || outside) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      }
    };

    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      opener?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  const handleSelect = (index: number) => {
    onSelect(index);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("projects.publicReport.printTitle")}
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/*
        The scrim, and a real `<button>` rather than a `<div onClick>`: the
        click-outside affordance then needs no keyboard handler of its own and no
        `stopPropagation` on the panel, because the panel is its sibling and not
        its child. `tabIndex={-1}` keeps it out of the focus trap, which reads
        the panel only — a blank full-screen tab stop would be worse than none.

        Its colour: `alert-modal.tsx` uses a raw black palette literal, logged as
        a `GAP-OVERLAY` row; `project-management/` is a migrated directory and
        APRAS-85's guard denies new ones there, so this is the app's own
        background at 80% — which also dims correctly in both themes, where a
        fixed black does not. The literal is deliberately not written even in
        this comment: the guard scans source text, not JSX.
      */}
      <button
        type="button"
        tabIndex={-1}
        aria-label={t("projects.publicReport.printClose")}
        onClick={onClose}
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
      />
      <div
        ref={panelRef}
        data-testid="obra-print-panel"
        className="relative z-10 w-full max-w-sm mx-4 bg-card rounded-xl border border-border shadow-xl p-5"
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <h3 className="text-base font-semibold text-foreground">
            {t("projects.publicReport.printTitle")}
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("projects.publicReport.printClose")}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="size-4" />
          </button>
        </div>

        {obras.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <HardHat className="size-6 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              {t("projects.publicReport.printEmpty")}
            </p>
          </div>
        ) : (
          <>
            <p className="mb-4 text-sm text-muted-foreground">
              {t("projects.publicReport.printDescription")}
            </p>
            <ul className="space-y-2">
              {obras.map((obra) => (
                <li key={obra.index}>
                  <button
                    type="button"
                    onClick={() => handleSelect(obra.index)}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-left",
                      "hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    )}
                  >
                    <span>
                      <span className="block text-sm font-medium text-foreground">
                        {obra.title}
                      </span>
                      {obra.kind && (
                        <span className="block text-xs text-muted-foreground">
                          {obra.kind}
                        </span>
                      )}
                    </span>
                    <Printer className="size-4 text-muted-foreground" />
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
};

ObraPrintDialog.displayName = "ObraPrintDialog";

export default ObraPrintDialog;
export type { ObraPrintDialogProps };
