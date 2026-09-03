import type React from "react";

/**
 * The full-page "still resolving" placeholder.
 *
 * Extracted from `ProtectedRoute` (APRAS-39, code review round 1 finding 3)
 * because `RootRedirect` needs the same behaviour for the same reason: both
 * decide *where the caller goes* from the permission set, and both must hold
 * the render until that set arrives rather than navigate on a guess. A
 * `<Navigate>` during the pending window is not a slower answer, it is a
 * wrong one — the component unmounts and never re-evaluates.
 */
export const Spinner: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

export default Spinner;
