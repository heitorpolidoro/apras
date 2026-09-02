import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import Navbar from "../../user-administration/components/Navbar";
import ProtectedRoute from "../../user-administration/components/ProtectedRoute";
import * as AuthHook from "../../user-administration/context/AuthContext";
import { UserRole } from "../../user-administration/context/AuthContext";
import apiClient from "../../../api/client";
import { ROUTE_ACCESS } from "../../user-administration/access/routeAccess";
import { PERMISSIONS_BY_ROLE } from "../../../test/permissionFixtures";

/**
 * Gating for `/purchases` and the "Cotações de Compra" navbar entry
 * (APRAS-37), re-expressed over `ROUTE_ACCESS["/purchases"]`
 * (`{module:"purchases"}`). The §5.2 delta for this route is **none**: it
 * stays A/D/M and stays denied to R/P/G, which is what both `it.each`
 * parametrisations below assert over the same six roles.
 *
 * `PURCHASES_ROLES` survives as the fixture selector for the parametrisation,
 * not as anything the code reads.
 *
 * Two shapes changed with IAM F4 and both are mandatory:
 *  * denial is **in place** (§2.4), so the `/dashboard` catch-all is gone and
 *    the denial assertion is `getByText("Acesso restrito")`;
 *  * `Navbar` now calls `useMyPermissions()`, a real TanStack query, so the
 *    bare `<Navbar/>` mount needs a `QueryClientProvider` and a
 *    `/permissions/me` fixture — without them it throws `No QueryClient set`.
 */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

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

vi.mock("../../../hooks/usePermissionQueries", async () => {
  const actual = await vi.importActual<
    typeof import("../../../hooks/usePermissionQueries")
  >("../../../hooks/usePermissionQueries");
  return { ...actual, usePermissionCatalogue: vi.fn(() => ({ data: [] })) };
});

export const PURCHASES_ROLES = [
  UserRole.ADMINISTRATOR,
  UserRole.DIRECTOR,
  UserRole.MANAGER,
];

const DENIED_ROLES = [UserRole.RESIDENT, UserRole.PORTEIRO, UserRole.GUEST];

const mockedGet = vi.mocked(apiClient.get);

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
  mockedGet.mockReset();
  mockedGet.mockImplementation(((url: string) =>
    url === "/permissions/me"
      ? Promise.resolve({
          data: {
            tenant_id: "00000000-0000-0000-0000-000000000001",
            permissions: PERMISSIONS_BY_ROLE[role],
          },
        })
      : Promise.resolve({ data: [] })) as never);
};

const withQueryClient = (ui: React.ReactElement) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

const renderPurchasesRoute = () =>
  withQueryClient(
    <MemoryRouter initialEntries={["/purchases"]}>
      <Routes>
        <Route
          path="/purchases"
          element={
            <ProtectedRoute requiredAccess={ROUTE_ACCESS["/purchases"]}>
              <div>Purchases Page</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );

describe("/purchases route gating", () => {
  it.each(PURCHASES_ROLES)("renders the page for %s", async (role) => {
    mockAuth(role);
    renderPurchasesRoute();
    expect(await screen.findByText("Purchases Page")).toBeInTheDocument();
  });

  it.each(DENIED_ROLES)("denies %s with Acesso restrito", async (role) => {
    mockAuth(role);
    renderPurchasesRoute();
    expect(await screen.findByText("Acesso restrito")).toBeInTheDocument();
    expect(screen.queryByText("Purchases Page")).toBeNull();
  });
});

describe("navbar entry for purchase quotations", () => {
  it.each(PURCHASES_ROLES)("shows the link for %s", async (role) => {
    mockAuth(role);
    withQueryClient(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    const link = await screen.findByRole("link", {
      name: "Cotações de Compra",
    });
    expect(link).toHaveAttribute("href", "/purchases");
  });

  it.each(DENIED_ROLES)("hides the link for %s", async (role) => {
    mockAuth(role);
    withQueryClient(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    // Wait for the permission query to settle before asserting an absence.
    await screen.findByText("APRAS");
    expect(
      screen.queryByRole("link", { name: "Cotações de Compra" }),
    ).toBeNull();
  });
});
