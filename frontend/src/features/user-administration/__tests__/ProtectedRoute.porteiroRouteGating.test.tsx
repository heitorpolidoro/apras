import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import * as AuthHook from "../context/AuthContext";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { ROUTE_ACCESS } from "../access/routeAccess";
import { PERMISSIONS_BY_ROLE, settledPermissions,  } from "../../../test/permissionFixtures";

/**
 * The routes APRAS-12 gated, re-expressed over `ROUTE_ACCESS` (APRAS-48 §5.2).
 *
 * `ALLOWED_ROLES` is the spec's "Rule ⇒ roles" column, written out
 * independently of the implementation, so this file states *which roles reach
 * which page* rather than re-deriving the rule. Two rows differ from the
 * pre-F4 `requiredRoles` arrays, and both are §5.2 deltas the backend already
 * enforced:
 *
 *  * `/lots` — `lots:read` is A/D/M/P, so RESIDENT and GUEST lose a link the
 *    backend answered 403 to anyway, and PORTEIRO gains one it always held;
 *  * `/projects` — `projects:read` is A/D/M/R, so GUEST loses a 403.
 *
 * ProtectedRoute used to call the menu gate on every route, `legacyMenu` or
 * not, because the rules of hooks required it. IAM F5 (APRAS-49 §4.1) deleted
 * the gate; the dependencies are still mocked the same way
 * `ProtectedRoute.test.tsx` mocks them.
 */
vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({ data: [] })),
}));

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

const ALL_ROLES = [
  "ADMINISTRATOR",
  "DIRECTOR",
  "MANAGER",
  "RESIDENT",
  "GUEST",
  "PORTEIRO",
];

const A = "ADMINISTRATOR";
const D = "DIRECTOR";
const M = "MANAGER";
const R = "RESIDENT";
const G = "GUEST";
const P = "PORTEIRO";

/** §5.2's "Rule ⇒ roles" column, transcribed. */
const ALLOWED_ROLES: Record<string, string[]> = {
  "/gate": [A, D, M, P],
  "/lots": [A, D, M, P],
  "/authorizations": [A, D, M, R, G],
  "/occurrences": [A, D, M, R, G],
  "/documents": [A, D, M, R, G],
  "/projects": [A, D, M, R],
  "/announcements": [A, D, M, R, G],
  "/finance": [A, D, M, R],
};

const mockUser = (role: string) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: {
      id: "user-1",
      email: "user@example.com",
      full_name: "Test User",
      role,
      is_active: true,
    } as never,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(PERMISSIONS_BY_ROLE[role]) as never,
  );
};

const renderGuardedRoute = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
        <Route
          path={path}
          element={
            <ProtectedRoute requiredAccess={ROUTE_ACCESS[path]}>
              <div>Guarded Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );

describe.each(Object.keys(ALLOWED_ROLES))("%s route gating", (path) => {
  it.each(ALL_ROLES)("decides %s exactly as ROUTE_ACCESS says", (role) => {
    mockUser(role);
    renderGuardedRoute(path);

    if (ALLOWED_ROLES[path].includes(role)) {
      expect(screen.getByText("Guarded Content")).toBeInTheDocument();
    } else {
      // §2.4: denial is in place, never a bounce to /dashboard.
      expect(screen.queryByText("Guarded Content")).toBeNull();
      expect(screen.queryByText("Dashboard Page")).toBeNull();
      expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
    }
  });
});
