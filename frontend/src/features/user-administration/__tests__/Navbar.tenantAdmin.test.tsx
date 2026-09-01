import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../components/Navbar";
import * as AuthHook from "../context/AuthContext";
import * as TenantHook from "../context/useTenant";
import { UserRole, type User } from "../../../types/auth";

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
    data: [
      { id: "type-1", name: "Test Type", allowed_menus: ["tasks", "categories"] },
    ],
  })),
}));

const TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

/** A RESIDENT holding `is_tenant_admin` on tenant A and nothing on B. */
const SYNDIC: Partial<User> = {
  id: "u-syndic",
  email: "syndic@test.com",
  full_name: "Síndico",
  role: UserRole.RESIDENT,
  is_active: true,
  user_types: [{ id: "type-1", name: "Test Type", allowed_menus: ["tasks"] }],
  tenants: [
    {
      tenant_id: TENANT_A,
      name: "Condomínio A",
      is_active: true,
      is_tenant_admin: true,
    },
    {
      tenant_id: TENANT_B,
      name: "Condomínio B",
      is_active: true,
      is_tenant_admin: false,
    },
  ],
};

const mockTenant = (actingTenantId: string, isActingTenantAdmin: boolean) => {
  vi.spyOn(TenantHook, "useTenant").mockReturnValue({
    tenants: [],
    actingTenantId,
    actingTenant: null,
    isActingTenantAdmin,
    isLoading: false,
    setActingTenant: vi.fn(),
  });
};

const renderNavbar = () =>
  render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>,
  );

describe("Navbar admin entry for a tenant_admin", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: SYNDIC as User,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn() as never,
      logout: vi.fn(),
    });
  });

  it("shows the Administração entry to a tenant_admin acting in the granting tenant", () => {
    mockTenant(TENANT_A, true);

    renderNavbar();

    expect(screen.getByRole("link", { name: "Administração" })).toHaveAttribute(
      "href",
      "/admin/users",
    );
    // The contact-info entry rides on the same capability.
    expect(screen.getByRole("link", { name: "Informações de Contato" })).toBeInTheDocument();
  });

  it("hides it when the same user acts in the other tenant", () => {
    mockTenant(TENANT_B, false);

    renderNavbar();

    expect(screen.queryByRole("link", { name: "Administração" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Informações de Contato" })).toBeNull();
  });
});
