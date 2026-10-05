import React from "react";

import { cycleTabWithin, focusableWithin } from "../lib/focusTrap";

/**
 * The three keyboard behaviours a modal owes its user, in one place (APRAS-98).
 *
 * Extracted verbatim in behaviour from `ObraPrintDialog`, which in turn mirrors
 * the shape of `src/components/ui/alert-modal.tsx`'s document-level Escape
 * effect. `AlertModal`'s effect is a few lines inside a component body and is
 * not exported, so there was nothing to import and that component keeps its
 * own; this hook is the copy, made once, that every other dialog calls instead
 * of growing a fourth.
 *
 * While `open`:
 *
 * - focus moves to the first focusable element inside `panelRef`;
 * - `Escape` calls `onClose`;
 * - `Tab`/`Shift+Tab` cycle within the panel, delegated to `../lib/focusTrap`;
 * - on close — by any exit path, because the restore runs from the effect's
 *   cleanup — focus returns to whatever element had it when the dialog opened.
 *
 * **`onClose` lives in a ref and the keydown effect depends on `[open]` alone**
 * (APRAS-98 Decision 3b). With `[open, onClose]` deps, a call site passing an
 * inline arrow would tear the effect down on every re-render while the dialog
 * is open: the cleanup would run `opener?.focus()`, the setup would drag focus
 * back to the first control, and "the opener" would be re-captured from
 * whatever was focused at that instant. Holding the callback in a ref makes an
 * inline arrow safe, so correctness does not depend on every future caller
 * remembering a `useCallback`.
 */
export const useDialogFocus = (
  open: boolean,
  onClose: () => void,
  panelRef: React.RefObject<HTMLElement | null>,
): void => {
  const onCloseRef = React.useRef(onClose);

  // Its own effect, and never a bare assignment during render: a render may be
  // discarded, and writing a ref from one is the mutation React does not
  // promise to keep.
  React.useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  React.useEffect(() => {
    // `undefined` and not a bare `return`: this callback's other exit hands back
    // a cleanup function, and mixing an implicit and an explicit return is what
    // DeepSource's JS-0045 objects to. `null` is not an option -- React types
    // the callback as returning `void | Destructor`.
    if (!open) return undefined;

    const opener =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    focusableWithin(panelRef.current)[0]?.focus();

    // Escape closes, Tab cycles, everything else is the browser's. The cycling
    // itself lives in `../lib/focusTrap` — see that module for why.
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        // Read at event time, which is what lets the deps stay `[open]`.
        onCloseRef.current();
      } else if (event.key === "Tab") {
        cycleTabWithin(event, panelRef.current);
      }
    };

    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      opener?.focus();
    };
    // `panelRef` is a ref object and stable for the holder's lifetime; `onClose`
    // is deliberately absent, per Decision 3b above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
};

export default useDialogFocus;
