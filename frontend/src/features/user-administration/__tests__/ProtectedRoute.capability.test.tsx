import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import * as AuthHook from "../context/AuthContext";
import * as TenantHook from "../context/useTenant";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { ROUTE_ACCESS } from "../access/routeAccess";
import {
  ALL_PERMISSIONS,
  PERMISSIONS_BY_ROLE,
  settledPermissions,
} from "../../../test/permissionFixtures";
import { UserRole, type User } from "../../../types/auth";

/**
 * The APRAS-43 admin *capability*, restated over permissions (APRAS-48 §2.4).
 *
 * The `requiredCapability` prop is gone: under IAM F3 an `is_tenant_admin` of
 * the acting tenant and an `is_superuser` both hold the **whole catalogue**,
 * so the capability is no longer a separate predicate — it is simply the set
 * `/permissions/me` answers. The scenarios below are unchanged; only the
 * mechanism that expresses "this caller is a tenant_admin here" moved from a
 * boolean to a permission payload.
 */
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

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
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

/** What `/permissions/me` answers in the acting tenant. */
const holding = (permissions: readonly string[]) => {
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(permissions) as never,
  );
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
            <ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/users"]}>
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
              requiredAccess={ROUTE_ACCESS["/users/contact-info"]}
            >
              <div>Contatos</div>
            </ProtectedRoute>
          }
        />
        <Route path="/dashboard" element={<div>Painel de Tarefas</div>} />
      </Routes>
    </MemoryRouter>,
  );

describe("ProtectedRoute admin capability, as permissions", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders /admin/users for a tenant_admin acting in the granting tenant", () => {
    mockAuth(TENANT_ADMIN_OF_A);
    mockTenant(TENANT_A, true);
    // IAM F3: in the granting tenant the capability *is* the whole catalogue.
    holding(ALL_PERMISSIONS);

    renderAdminUsers();

    expect(screen.getByText("Painel de Administração")).toBeInTheDocument();
  });

  it("denies a tenant_admin acting in another tenant", () => {
    mockAuth(TENANT_ADMIN_OF_A);
    mockTenant(TENANT_B, false);
    // Outside the granting tenant they hold only their own role's bundle.
    holding(PERMISSIONS_BY_ROLE[UserRole.RESIDENT]);

    renderAdminUsers();

    expect(screen.queryByText("Painel de Administração")).toBeNull();
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
  });

  it("still renders /admin/users for a global ADMINISTRATOR", () => {
    mockAuth({ id: "u-admin", role: UserRole.ADMINISTRATOR, tenants: [] });
    // Not a tenant_admin anywhere: the legacy bundle alone must carry it.
    mockTenant(TENANT_B, false);
    holding(PERMISSIONS_BY_ROLE[UserRole.ADMINISTRATOR]);

    renderAdminUsers();

    expect(screen.getByText("Painel de Administração")).toBeInTheDocument();
  });

  it("a MANAGER passes contact-info on users:update_contact alone", () => {
    mockAuth({ id: "u-manager", role: UserRole.MANAGER, tenants: [] });
    mockTenant(TENANT_A, false);
    holding(PERMISSIONS_BY_ROLE[UserRole.MANAGER]);

    renderContactInfo();

    expect(screen.getByText("Contatos")).toBeInTheDocument();
  });

  it("lets a capability holder who is not a MANAGER pass contact-info", () => {
    mockAuth(TENANT_ADMIN_OF_A);
    mockTenant(TENANT_A, true);
    holding(ALL_PERMISSIONS);

    renderContactInfo();

    expect(screen.getByText("Contatos")).toBeInTheDocument();
  });

  it("denies a user with neither the role's bundle nor the capability", () => {
    mockAuth({ id: "u-resident", role: UserRole.RESIDENT, tenants: [] });
    mockTenant(TENANT_A, false);
    holding(PERMISSIONS_BY_ROLE[UserRole.RESIDENT]);

    renderContactInfo();

    expect(screen.queryByText("Contatos")).toBeNull();
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument();
  });
});
