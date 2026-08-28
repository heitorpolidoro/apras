import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import { UserRole } from "../context/AuthContext";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useUserTypes } from "../../../hooks/useUserTypes";

// Mirrors ProtectedRoute.guestWelcome.test.tsx: generalizes the requiredMenu
// GUEST->/welcome redirect (APRAS-10) to also cover PORTEIRO->/gate
// (APRAS-12).
vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({
    data: [{ id: "type-1", name: "Test Type", allowed_menus: ["tasks", "categories"] }],
  })),
}));

const notSimulating = {
  simulatedRole: null,
  simulatedUserTypeIds: [],
  isSimulating: false,
  setSimulatedRole: vi.fn(),
  setSimulatedUserTypeIds: vi.fn(),
  stopSimulation: vi.fn(),
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
            <ProtectedRoute requiredMenu="tasks">
              <div>Tasks Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );

describe("ProtectedRoute — PORTEIRO gate redirect (requiredMenu routes)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useUserTypes).mockReturnValue({
      data: [{ id: "type-1", name: "Test Type", allowed_menus: ["tasks", "categories"] }],
    } as any); // skipcq: JS-0323
  });

  it("redirects a real PORTEIRO away from /dashboard to /gate instead of showing the restricted-access message", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "porteiro-1",
        email: "porteiro@example.com",
        full_name: "Porteiro User",
        role: UserRole.PORTEIRO,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    renderDashboard();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
    expect(screen.queryByText("Acesso restrito")).toBeNull();
    expect(screen.queryByText("Tasks Content")).toBeNull();
  });

  it("redirects an Administrator simulating PORTEIRO (effective role) to /gate, even though the real role is ADMINISTRATOR", () => {
    vi.mocked(useSimulation).mockReturnValue({
      simulatedRole: UserRole.PORTEIRO,
      simulatedUserTypeIds: [],
      isSimulating: true,
      setSimulatedRole: vi.fn(),
      setSimulatedUserTypeIds: vi.fn(),
      stopSimulation: vi.fn(),
    });
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "admin-1",
        email: "admin@example.com",
        full_name: "Admin User",
        role: UserRole.ADMINISTRATOR,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    renderDashboard();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
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
        role: UserRole.ADMINISTRATOR,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    renderDashboard();

    expect(screen.getByText("Tasks Content")).toBeInTheDocument();
    expect(screen.queryByText("Gate Page")).toBeNull();
  });

  it("does not redirect PORTEIRO to /gate on a requiredRole route (only requiredMenu routes are affected)", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "porteiro-1",
        email: "porteiro@example.com",
        full_name: "Porteiro User",
        role: UserRole.PORTEIRO,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <Routes>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
          <Route path="/gate" element={<div>Gate Page</div>} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute requiredRole={UserRole.ADMINISTRATOR}>
                <div>Admin Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Gate Page")).toBeNull();
    expect(screen.queryByText("Admin Content")).toBeNull();
  });

  it("resolves a PORTEIRO denied by requiredRoles on another route to /gate in exactly one intermediate hop through /dashboard, with no loop", () => {
    vi.mocked(useSimulation).mockReturnValue(notSimulating);
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "porteiro-1",
        email: "porteiro@example.com",
        full_name: "Porteiro User",
        role: UserRole.PORTEIRO,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/finance"]}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requiredMenu="tasks">
                <div>Tasks Content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/gate" element={<div>Gate Page</div>} />
          <Route
            path="/finance"
            element={
              <ProtectedRoute
                requiredRoles={[
                  UserRole.ADMINISTRATOR,
                  UserRole.DIRECTOR,
                  UserRole.MANAGER,
                  UserRole.RESIDENT,
                ]}
              >
                <div>Finance Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    // /finance's requiredRoles check bounces PORTEIRO to /dashboard, whose
    // requiredMenu+PORTEIRO branch (this test's target behavior) then
    // bounces it again to /gate — settling there with no loop.
    expect(screen.getByText("Gate Page")).toBeInTheDocument();
    expect(screen.queryByText("Finance Content")).toBeNull();
    expect(screen.queryByText("Tasks Content")).toBeNull();
  });
});
