import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
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
  useUserTypes: vi.fn(() => ({ data: [] })),
}));

const TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

const mockAuth = (user: Partial<User>) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: user as User,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
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

/**
 * A tenant_admin of tenant A only. `isActingTenantAdmin` is what actually
 * varies per acting tenant; the membership list is carried so the fixture
 * reads as the real thing.
 */
const TENANT_ADMIN_OF_A: Partial<User> = {
  id: "u-syndic",
  role: UserRole.RESIDENT,
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

const renderAdminUsers = () =>
  render(
    <MemoryRouter initialEntries={["/admin/users"]}>
      <Routes>
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute requiredCapability="admin">
              <div>Painel de Administração</div>
            </ProtectedRoute>
          }
        />
        <Route path="/dashboard" element={<div>Painel de Tarefas</div>} />
      </Routes>
    </MemoryRouter>,
  );

const renderContactInfo = () =>
  render(
    <MemoryRouter initialEntries={["/users/contact-info"]}>
      <Routes>
        <Route
          path="/users/contact-info"
          element={
            <ProtectedRoute
              requiredRoles={[UserRole.MANAGER]}
              requiredCapability="admin"
            >
              <div>Contatos</div>
            </ProtectedRoute>
          }
        />
        <Route path="/dashboard" element={<div>Painel de Tarefas</div>} />
      </Routes>
    </MemoryRouter>,
  );

describe("ProtectedRoute requiredCapability", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders /admin/users for a tenant_admin acting in the granting tenant", () => {
    mockAuth(TENANT_ADMIN_OF_A);
    mockTenant(TENANT_A, true);

    renderAdminUsers();

    expect(screen.getByText("Painel de Administração")).toBeInTheDocument();
  });

  it("redirects a tenant_admin acting in another tenant to /dashboard", () => {
    mockAuth(TENANT_ADMIN_OF_A);
    mockTenant(TENANT_B, false);

    renderAdminUsers();

    expect(screen.queryByText("Painel de Administração")).toBeNull();
    expect(screen.getByText("Painel de Tarefas")).toBeInTheDocument();
  });

  it("still renders /admin/users for a global ADMINISTRATOR", () => {
    mockAuth({ id: "u-admin", role: UserRole.ADMINISTRATOR, tenants: [] });
    // Not a tenant_admin anywhere: the role alone must carry the capability.
    mockTenant(TENANT_B, false);

    renderAdminUsers();

    expect(screen.getByText("Painel de Administração")).toBeInTheDocument();
  });

  it("requiredCapability ORs with requiredRoles (MANAGER passes contact-info without the capability)", () => {
    mockAuth({ id: "u-manager", role: UserRole.MANAGER, tenants: [] });
    mockTenant(TENANT_A, false);

    renderContactInfo();

    expect(screen.getByText("Contatos")).toBeInTheDocument();
  });

  it("lets the capability alone pass a route that also lists roles", () => {
    // A tenant_admin who is not a MANAGER: the OR must be a real OR, not an
    // AND that only the role arm can satisfy.
    mockAuth(TENANT_ADMIN_OF_A);
    mockTenant(TENANT_A, true);

    renderContactInfo();

    expect(screen.getByText("Contatos")).toBeInTheDocument();
  });

  it("denies a user with neither the role nor the capability", () => {
    mockAuth({ id: "u-resident", role: UserRole.RESIDENT, tenants: [] });
    mockTenant(TENANT_A, false);

    renderContactInfo();

    expect(screen.queryByText("Contatos")).toBeNull();
    expect(screen.getByText("Painel de Tarefas")).toBeInTheDocument();
  });
});
