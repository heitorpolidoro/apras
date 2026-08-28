import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import { UserRole } from "../context/AuthContext";
import * as AuthHook from "../context/AuthContext";

// These tests exercise the exact `requiredRoles` arrays App.tsx now attaches
// to /gate and to the six previously-unguarded routes (/lots,
// /authorizations, /occurrences, /documents, /projects, /announcements),
// per the APRAS-12 spec. ProtectedRoute always calls useMenuAccess (rules of
// hooks) even though these routes don't pass `requiredMenu`, so mock its
// dependencies the same way ProtectedRoute.test.tsx does.
vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRole: null,
    simulatedUserTypeIds: [],
    isSimulating: false,
    setSimulatedRole: vi.fn(),
    setSimulatedUserTypeIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

vi.mock("../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({ data: [] })),
}));

const GATE_ROLES = [
  UserRole.ADMINISTRATOR,
  UserRole.DIRECTOR,
  UserRole.MANAGER,
  UserRole.PORTEIRO,
];

const SIX_ROUTES_ROLES = [
  UserRole.ADMINISTRATOR,
  UserRole.DIRECTOR,
  UserRole.MANAGER,
  UserRole.RESIDENT,
  UserRole.GUEST,
];

const mockUser = (role: UserRole) => ({
  isAuthenticated: true,
  isLoading: false,
  user: {
    id: "user-1",
    email: "user@example.com",
    full_name: "Test User",
    role,
    is_active: true,
  } as any,
  login: vi.fn() as any,
  logout: vi.fn(),
});

const renderGuardedRoute = (path: string, requiredRoles: UserRole[]) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
        <Route
          path={path}
          element={
            <ProtectedRoute requiredRoles={requiredRoles}>
              <div>Guarded Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );

describe("/gate route gating (previously unguarded)", () => {
  it.each([
    UserRole.ADMINISTRATOR,
    UserRole.DIRECTOR,
    UserRole.MANAGER,
    UserRole.PORTEIRO,
  ])("allows %s", (role) => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue(mockUser(role));
    renderGuardedRoute("/gate", GATE_ROLES);
    expect(screen.getByText("Guarded Content")).toBeInTheDocument();
  });

  it.each([UserRole.GUEST, UserRole.RESIDENT])(
    "blocks %s (new restriction, no prior test coverage)",
    (role) => {
      vi.spyOn(AuthHook, "useAuth").mockReturnValue(mockUser(role));
      renderGuardedRoute("/gate", GATE_ROLES);
      expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
      expect(screen.queryByText("Guarded Content")).toBeNull();
    },
  );
});

describe.each([
  ["/lots", "LotsPage"],
  ["/authorizations", "VisitorAuthPage"],
  ["/occurrences", "OccurrenceBookPage"],
  ["/documents", "DocumentCenterPage"],
  ["/projects", "ConstructionTrackerPage"],
  ["/announcements", "AnnouncementFeedPage"],
])("%s route gating (previously unguarded, now excludes PORTEIRO)", (path) => {
  it.each([
    UserRole.ADMINISTRATOR,
    UserRole.DIRECTOR,
    UserRole.MANAGER,
    UserRole.RESIDENT,
    UserRole.GUEST,
  ])(`still allows %s (regression)`, (role) => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue(mockUser(role));
    renderGuardedRoute(path, SIX_ROUTES_ROLES);
    expect(screen.getByText("Guarded Content")).toBeInTheDocument();
  });

  it("blocks PORTEIRO", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue(mockUser(UserRole.PORTEIRO));
    renderGuardedRoute(path, SIX_ROUTES_ROLES);
    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    expect(screen.queryByText("Guarded Content")).toBeNull();
  });
});

// Spot-check: /finance already excluded PORTEIRO by construction before
// this task (Non-Goals) — confirm it's still blocked, as a representative
// sample of "every route that already had a requiredRole/requiredRoles
// allowlist... excludes PORTEIRO by construction".
describe("/finance route (already excluded PORTEIRO by construction)", () => {
  const FINANCE_ROLES = [
    UserRole.ADMINISTRATOR,
    UserRole.DIRECTOR,
    UserRole.MANAGER,
    UserRole.RESIDENT,
  ];

  it("blocks PORTEIRO", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue(mockUser(UserRole.PORTEIRO));
    renderGuardedRoute("/finance", FINANCE_ROLES);
    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    expect(screen.queryByText("Guarded Content")).toBeNull();
  });
});
