import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import { UserRole } from "../context/AuthContext";
import * as AuthHook from "../context/AuthContext";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { ROUTE_ACCESS } from "../access/routeAccess";
import { settledPermissions } from "../../../test/permissionFixtures";

// ProtectedRoute always calls useMenuAccess (rules of hooks), which combines
// useEffectiveIdentity (real user + useSimulation) with useUserTypes, and it
// now also calls useMyPermissions through useCanAccess. Mocking the query hook
// rather than the decision module keeps `useCanAccess` running for real while
// still needing no QueryClientProvider.
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
  useUserTypes: vi.fn(() => ({
    data: [{ id: "type-1", name: "Test Type", allowed_menus: ["tasks", "categories"] }],
  })),
}));

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

const holding = (...permissions: string[]) => {
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(permissions) as never,
  );
};

const authAs = (role: UserRole, extra: Record<string, unknown> = {}) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: { id: "1", username: "test", role, is_active: true, ...extra } as never,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
};

beforeEach(() => {
  holding();
  vi.mocked(useUserTypes).mockReturnValue({
    data: [
      { id: "type-1", name: "Test Type", allowed_menus: ["tasks", "categories"] },
    ],
  } as never);
});

describe("ProtectedRoute", () => {
  it("redirects to login if not authenticated", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      login: vi.fn() as never,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Login Page")).toBeDefined();
    expect(screen.queryByText("Protected Content")).toBeNull();
  });

  it("renders children if authenticated and the route carries no rule", () => {
    authAs(UserRole.DIRECTOR);

    render(
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Protected Content")).toBeDefined();
  });

  it("denies in place when the rule's anyOf permission is not held", () => {
    authAs(UserRole.DIRECTOR);
    holding("tasks:read");

    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <Routes>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute
                requiredAccess={ROUTE_ACCESS["/admin/photo-approvals"]}
              >
                <div>Admin Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    // §2.4: denial is in place, never a redirect — no redirect loop is
    // possible when /dashboard also denies.
    expect(screen.queryByText("Dashboard")).toBeNull();
    expect(screen.queryByText("Admin Content")).toBeNull();
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
  });

  it("allows access when one of the anyOf permissions is held", () => {
    authAs(UserRole.MANAGER);
    holding("users:update_contact");

    render(
      <MemoryRouter initialEntries={["/contact-info"]}>
        <Routes>
          <Route
            path="/contact-info"
            element={
              <ProtectedRoute
                requiredAccess={ROUTE_ACCESS["/users/contact-info"]}
              >
                <div>Contact Info Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Contact Info Content")).toBeDefined();
  });

  it("denies a user holding no permission of the rule's module", () => {
    authAs(UserRole.GUEST);
    holding("tasks:read");

    render(
      <MemoryRouter initialEntries={["/finance"]}>
        <Routes>
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

    expect(screen.queryByText("Finance Content")).toBeNull();
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
  });

  it("renders loading spinner when isLoading is true", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      user: null,
      login: vi.fn() as never,
      logout: vi.fn(),
    });

    const { container } = render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(container.querySelector(".animate-spin")).toBeDefined();
    expect(screen.queryByText("Protected Content")).toBeNull();
  });

  it("renders the spinner while /permissions/me is still pending", () => {
    authAs(UserRole.DIRECTOR);
    vi.mocked(useMyPermissions).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as never);

    const { container } = render(
      <MemoryRouter initialEntries={["/finance"]}>
        <Routes>
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

    expect(container.querySelector(".animate-spin")).not.toBeNull();
    expect(screen.queryByText("Acesso restrito")).toBeNull();
    expect(screen.queryByText("Finance Content")).toBeNull();
  });

  // ── the legacyMenu leg, TRANSITIONAL (IAM F4 -> F5) ───────────────────

  it("renders children when the user's UserType grants the required menu", () => {
    authAs(UserRole.DIRECTOR, { user_types: [{ id: "type-1", name: "Board" }] });
    holding("tasks:read");
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Board", allowed_menus: ["tasks"] }],
    } as never);

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
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

    expect(screen.getByText("Tasks Content")).toBeDefined();
  });

  it("renders the restricted-access message (no redirect) when the menu is denied", () => {
    authAs(UserRole.DIRECTOR);
    holding("tasks:read");
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as never);

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
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

    // Denied: stays on /dashboard showing the restricted-access message,
    // does NOT redirect anywhere.
    expect(screen.queryByText("Tasks Content")).toBeNull();
    expect(screen.queryByText("Login Page")).toBeNull();
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
  });

  it("ADMINISTRATOR always passes the legacy menu leg regardless of UserTypes", () => {
    authAs(UserRole.ADMINISTRATOR);
    holding("categories:read");
    vi.mocked(useUserTypes).mockReturnValue({ data: [] } as never);

    render(
      <MemoryRouter initialEntries={["/categories"]}>
        <Routes>
          <Route
            path="/categories"
            element={
              <ProtectedRoute requiredAccess={ROUTE_ACCESS["/categories"]}>
                <div>Categories Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Categories Content")).toBeDefined();
  });
});
