import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../components/Navbar";
import * as AuthHook from "../context/AuthContext";
import * as TenantHook from "../context/useTenant";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { ALL_PERMISSIONS, PERMISSIONS_BY_ROLE, settledPermissions,  } from "../../../test/permissionFixtures";
import { type User } from "../../../types/auth";

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({
    data: [
      { id: "type-1", name: "Test Type" },
    ],
  })),
}));

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

// APRAS-110. `Navbar` renders `TenantHeaderLogo`, which reads
// `useTenantProfile()`. Mocked here because this file renders `Navbar` with no
// `QueryClientProvider` of its own, so an unmocked `useQuery` throws and every
// case in the file fails.
//
// The default is the **no-logo** answer, so the banner keeps showing today's
// generic appName mark and every existing case stands unchanged. The
// implementation is passed to `vi.fn(impl)` rather than installed afterwards
// with `mockReturnValue`: `vitest.config.ts` sets neither `restoreMocks` nor
// `clearMocks`, a sibling file calls `vi.restoreAllMocks()` in `beforeEach`,
// and only a factory implementation survives that.
vi.mock("../../../hooks/useTenantProfile", () => ({
  useTenantProfile: vi.fn(() => ({
    data: {
      id: "tenant-test",
      name: "Condomínio Teste",
      slug: "condominio-teste",
      is_active: true,
      logo_url: null,
      brand_theme: null,
      theme: null,
    },
    isPending: false,
    isError: false,
  })),
}));

const TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

/** A RESIDENT holding `is_tenant_admin` on tenant A and nothing on B. */
const SYNDIC: Partial<User> = {
  id: "u-syndic",
  email: "syndic@test.com",
  full_name: "Síndico",
  is_active: true,
  roles: [{ id: "type-1", name: "Test Type" }],
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
  // IAM F3: `get_effective_permissions` answers an acting tenant_admin the
  // whole catalogue **in the granting tenant only**, and their own role's
  // bundle everywhere else. That is now the only thing the Navbar reads.
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions(
      isActingTenantAdmin
        ? ALL_PERMISSIONS
        : PERMISSIONS_BY_ROLE["RESIDENT"],
    ) as never,
  );
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
