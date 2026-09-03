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

// Mirrors the mocking approach in ProtectedRoute.test.tsx, but exposes
// useSimulation as a controllable mock so individual tests can simulate an
// Administrator "viewing as" GUEST. The GUEST -> /welcome landing rule is now
// `AccessRule.landingRedirect`, carried by exactly the two routes of §2.4.
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

const renderDashboard = () =>
  render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/welcome" element={<div>Welcome Page</div>} />
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

describe("ProtectedRoute — GUEST welcome redirect (landingRedirect routes)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: "type-1", name: "Test Type" }],
    } as any); // skipcq: JS-0323
  });

  it("redirects an active GUEST (real role) away from /dashboard to /welcome instead of showing the restricted-access message", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "guest-1",
        email: "guest@example.com",
        full_name: "Guest User",
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(PERMISSIONS_BY_ROLE["GUEST"], "/welcome") as never,
    );

    renderDashboard();

    expect(screen.getByText("Welcome Page")).toBeInTheDocument();
    expect(screen.queryByText("Acesso restrito")).toBeNull();
    expect(screen.queryByText("Tasks Content")).toBeNull();
  });

  it("lets a DIRECTOR through, and shows the restricted message only to a caller with no tasks permission at all", () => {
    // **The frontend twin of §4.2's widening.** This case used to assert
    // "Acesso restrito" for a DIRECTOR with no qualifying menu key, because
    // `legacyMenu` ANDed the `allowed_menus` gate on top of the permission.
    // IAM F5 deleted that gate from all 12 handlers, so a DIRECTOR — who
    // genuinely holds `tasks:read` — now reaches the page, and the door and
    // the API agree. The restricted message survives for the caller it was
    // always meant for: one whose bundle carries no `tasks:*`.
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "director-1",
        email: "director@example.com",
        full_name: "Director User",
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(PERMISSIONS_BY_ROLE["DIRECTOR"]) as never,
    );
    vi.mocked(useRoles).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    renderDashboard();

    expect(screen.getByText("Tasks Content")).toBeInTheDocument();
    expect(screen.queryByText("Acesso restrito")).toBeNull();
  });

  it("shows the restricted-access message to a caller holding no tasks permission", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "director-1",
        email: "director@example.com",
        full_name: "Director User",
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    // No `tasks:*`, and no `landing_path` either — so there is nothing to
    // redirect to and the denial is shown **in place**, which is the shape
    // APRAS-48 chose over bouncing a denied user to `/dashboard`.
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(["finance:read"]) as never,
    );
    vi.mocked(useRoles).mockReturnValue({ data: [] } as any); // skipcq: JS-0323

    renderDashboard();

    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
    expect(screen.queryByText("Welcome Page")).toBeNull();
    expect(screen.queryByText("Tasks Content")).toBeNull();
  });

  it("redirects an Administrator simulating GUEST (effective role) to /welcome, even though the real role is ADMINISTRATOR", () => {
    vi.mocked(useSimulation).mockReturnValue({
      simulatedRoleIds: [],
      isSimulating: true,
      setSimulatedRoleIds: vi.fn(),
      stopSimulation: vi.fn(),
    });
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "admin-1",
        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    // The simulated identity is what `/permissions/me` answers for, so the
    // landing follows the simulation — which is the whole point of §10.4 and
    // is safe because route *access* stays on the real set.
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(PERMISSIONS_BY_ROLE["GUEST"], "/welcome") as never,
    );

    renderDashboard();

    expect(screen.getByText("Welcome Page")).toBeInTheDocument();
    expect(screen.queryByText("Tasks Content")).toBeNull();
  });

  it("does not redirect a real ADMINISTRATOR (no simulation) away from /dashboard", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "admin-1",
        email: "admin@example.com",
        full_name: "Admin User",
        is_superuser: true,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(PERMISSIONS_BY_ROLE["ADMINISTRATOR"]) as never,
    );

    renderDashboard();

    expect(screen.getByText("Tasks Content")).toBeInTheDocument();
    expect(screen.queryByText("Welcome Page")).toBeNull();
  });

  it("does not redirect GUEST to /welcome on a requiredRole route (only landingRedirect routes are affected)", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "guest-1",
        email: "guest@example.com",
        full_name: "Guest User",
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(PERMISSIONS_BY_ROLE["GUEST"], "/welcome") as never,
    );

    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <Routes>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
          <Route path="/welcome" element={<div>Welcome Page</div>} />
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

    // §2.4: denial is in place, so there is no bounce to /dashboard either.
    expect(screen.queryByText("Dashboard")).toBeNull();
    expect(screen.queryByText("Welcome Page")).toBeNull();
    expect(screen.queryByText("Admin Content")).toBeNull();
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
  });
});
