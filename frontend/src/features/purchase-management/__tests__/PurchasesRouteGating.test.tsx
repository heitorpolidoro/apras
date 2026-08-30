import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Navbar from "../../user-administration/components/Navbar";
import ProtectedRoute from "../../user-administration/components/ProtectedRoute";
import * as AuthHook from "../../user-administration/context/AuthContext";
import { UserRole } from "../../user-administration/context/AuthContext";

/**
 * Gating for `/purchases` and the "Cotações de Compra" navbar entry (APRAS-37):
 * ADMINISTRATOR, DIRECTOR and MANAGER only. These are the exact
 * `requiredRoles` App.tsx attaches to the route.
 */
vi.mock("../../user-administration/context/SimulationContext", () => ({
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
    data: [
      { id: "type-1", name: "Test Type", allowed_menus: ["tasks", "categories"] },
    ],
  })),
}));

export const PURCHASES_ROLES = [
  UserRole.ADMINISTRATOR,
  UserRole.DIRECTOR,
  UserRole.MANAGER,
];

const mockAuth = (role: UserRole) => {
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
};

const renderPurchasesRoute = () =>
  render(
    <MemoryRouter initialEntries={["/purchases"]}>
      <Routes>
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
        <Route
          path="/purchases"
          element={
            <ProtectedRoute requiredRoles={PURCHASES_ROLES}>
              <div>Purchases Page</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );

describe("/purchases route gating", () => {
  it.each(PURCHASES_ROLES)("renders the page for %s", (role) => {
    mockAuth(role);
    renderPurchasesRoute();
    expect(screen.getByText("Purchases Page")).toBeInTheDocument();
  });

  it.each([UserRole.RESIDENT, UserRole.PORTEIRO, UserRole.GUEST])(
    "redirects %s to /dashboard",
    (role) => {
      mockAuth(role);
      renderPurchasesRoute();
      expect(screen.queryByText("Purchases Page")).toBeNull();
      expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    },
  );
});

describe("navbar entry for purchase quotations", () => {
  it.each(PURCHASES_ROLES)("shows the link for %s", (role) => {
    mockAuth(role);
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    const link = screen.getByRole("link", { name: "Cotações de Compra" });
    expect(link).toHaveAttribute("href", "/purchases");
  });

  it.each([UserRole.RESIDENT, UserRole.PORTEIRO, UserRole.GUEST])(
    "hides the link for %s",
    (role) => {
      mockAuth(role);
      render(
        <MemoryRouter>
          <Navbar />
        </MemoryRouter>,
      );
      expect(
        screen.queryByRole("link", { name: "Cotações de Compra" }),
      ).toBeNull();
    },
  );
});
