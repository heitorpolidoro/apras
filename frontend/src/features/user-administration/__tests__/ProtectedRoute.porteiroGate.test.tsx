import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { ROUTE_ACCESS } from "../access/routeAccess";
import { PERMISSIONS_BY_ROLE, settledPermissions,  } from "../../../test/permissionFixtures";

// Mirrors ProtectedRoute.guestWelcome.test.tsx: the PORTEIRO->/gate landing
// redirect (APRAS-12), which IAM F4 keeps role-shaped on exactly the two
// routes carrying `landingRedirect` (§2.4) — a PORTEIRO genuinely holds
// `tasks:read`, so no permission predicate can express "pin them to the gate".
vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({
    data: [{ id: "type-1", name: "Test Type" }],
  })),
}));

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

const notSimulating = {
  simulatedRoleIds: [],
  isSimulating: false,
  setSimulatedRoleIds: vi.fn(),
  stopSimulation: vi.fn(),
};

const authAs = (role: string, id: string) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: {
      id,
      email: `${id}@example.com`,
      full_name: id,
      is_superuser: role === "ADMINISTRATOR",
      is_active: true,
    } as never,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  // IAM F5 (APRAS-49 §10.4): the landing is data on the role row, delivered
  // by `/permissions/me`. `Porteiro (papel)` is the row migration `0033`
  // backfilled `/gate` onto, so a caller whose roles include it lands there.
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(
      PERMISSIONS_BY_ROLE[role],
      { PORTEIRO: "/gate", GUEST: "/welcome" }[role] ?? null,
    ) as never,
  );
};

const renderDashboard = () =>
  render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/gate" element={<div>Gate Page</div>} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute requiredAccess={ROUTE_ACCESS["/dashboard"]}>
              <div>Tasks Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );

describe("ProtectedRoute — PORTEIRO gate redirect (landingRedirect routes)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "type-1", name: "Test Type" }],
    } as never);
  });

  it("redirects a real PORTEIRO away from /dashboard to /gate instead of showing the restricted-access message", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    authAs("PORTEIRO", "porteiro-1");

    renderDashboard();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
    expect(screen.queryByText("Acesso restrito")).toBeNull();
    expect(screen.queryByText("Tasks Content")).toBeNull();
  });

  it("redirects an Administrator simulating PORTEIRO (effective role) to /gate, even though the real role is ADMINISTRATOR", () => {
    vi.mocked(useSimulation).mockReturnValue({
      simulatedRoleIds: [],
      isSimulating: true,
      setSimulatedRoleIds: vi.fn(),
      stopSimulation: vi.fn(),
    });
    authAs("ADMINISTRATOR", "admin-1");
    // `/permissions/me` is the **effective**-set endpoint, so while the
    // administrator simulates the porteiro it answers the porteiro's payload
    // — landing included (IAM F5, §10.4). That is safe precisely because
    // route *access* stays on the real set
    // (`ProtectedRoute.permissions.test.tsx`).
    authAs("PORTEIRO", "admin-1");

    renderDashboard();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
    expect(screen.queryByText("Tasks Content")).toBeNull();
  });

  it("does not redirect a real ADMINISTRATOR (no simulation) away from /dashboard", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    authAs("ADMINISTRATOR", "admin-1");

    renderDashboard();

    expect(screen.getByText("Tasks Content")).toBeInTheDocument();
    expect(screen.queryByText("Gate Page")).toBeNull();
  });

  it("does not redirect PORTEIRO to /gate on a route without landingRedirect", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    authAs("PORTEIRO", "porteiro-1");

    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <Routes>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
          <Route path="/gate" element={<div>Gate Page</div>} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/users"]}>
                <div>Admin Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    // §2.4: denial is in place. The route neither lands the PORTEIRO on /gate
    // nor bounces them to /dashboard.
    expect(screen.queryByText("Gate Page")).toBeNull();
    expect(screen.queryByText("Dashboard")).toBeNull();
    expect(screen.queryByText("Admin Content")).toBeNull();
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
  });

  it("denies a PORTEIRO on /finance in place, with no hop through /dashboard at all", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    authAs("PORTEIRO", "porteiro-1");

    render(
      <MemoryRouter initialEntries={["/finance"]}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requiredAccess={ROUTE_ACCESS["/dashboard"]}>
                <div>Tasks Content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/gate" element={<div>Gate Page</div>} />
          <Route
            path="/finance"
            element={
              <ProtectedRoute requiredAccess={ROUTE_ACCESS["/finance"]}>
                <div>Finance Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    // Before IAM F4 this settled on /gate after two redirects (deny to
    // /dashboard, then the PORTEIRO landing rule). §2.4 removes the redirect
    // entirely, which is precisely what makes the old loop hazard unreachable.
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
    expect(screen.queryByText("Finance Content")).toBeNull();
    expect(screen.queryByText("Tasks Content")).toBeNull();
    expect(screen.queryByText("Gate Page")).toBeNull();
  });
});
