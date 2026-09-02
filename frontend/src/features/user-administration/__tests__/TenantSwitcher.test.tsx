import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import apiClient from "../../../api/client";
import Navbar from "../components/Navbar";
import * as AuthHook from "../context/AuthContext";
import * as TenantHook from "../context/useTenant";
import { UserRole, type Tenant, type User } from "../../../types/auth";
import { PERMISSIONS_BY_ROLE } from "../../../test/permissionFixtures";
import pt from "../../../i18n/locales/pt.json";
import en from "../../../i18n/locales/en.json";

/**
 * IAM F4: `Navbar` calls `useMyPermissions()`, a real TanStack query, so the
 * bare mount below needs a `QueryClientProvider` and a `/permissions/me`
 * fixture — without them it throws `No QueryClient set`. The fixture is
 * **identical across every render in this file**, which the third case
 * depends on: it byte-compares `container.textContent` between the
 * zero-tenant and single-tenant renders.
 */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

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

const TENANT_A: Tenant = {
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  name: "Condomínio A",
  is_active: true,
};
const TENANT_B: Tenant = {
  id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  name: "Condomínio B",
  is_active: true,
};

const USER: Partial<User> = {
  id: "u1",
  email: "resident@test.com",
  full_name: "Morador",
  role: UserRole.RESIDENT,
  is_active: true,
  user_types: [{ id: "type-1", name: "Test Type", allowed_menus: ["tasks"] }],
};

const setActingTenant = vi.fn();

const mockTenant = (tenants: Tenant[]) => {
  vi.spyOn(TenantHook, "useTenant").mockReturnValue({
    tenants,
    actingTenantId: tenants[0]?.id ?? null,
    actingTenant: tenants[0] ?? null,
    isActingTenantAdmin: false,
    isLoading: false,
    setActingTenant,
  });
};

const renderNavbar = () => {
  vi.mocked(apiClient.get).mockImplementation(((url: string) =>
    url === "/permissions/me"
      ? Promise.resolve({
          data: {
            tenant_id: TENANT_A.id,
            permissions: PERMISSIONS_BY_ROLE[UserRole.RESIDENT],
          },
        })
      : Promise.resolve({ data: [] })) as never);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("Navbar tenant switcher", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setActingTenant.mockClear();
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: USER as User,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn() as never,
      logout: vi.fn(),
    });
  });

  it("renders the switcher with one option per tenant for a two-tenant user", () => {
    mockTenant([TENANT_A, TENANT_B]);

    renderNavbar();

    const switcher = screen.getByRole("combobox", { name: /condom/i });
    expect(switcher).toHaveValue(TENANT_A.id);
    const options = screen.getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      "Condomínio A",
      "Condomínio B",
    ]);
  });

  it("does not render the switcher for a single-tenant user", () => {
    mockTenant([TENANT_A]);

    renderNavbar();

    expect(screen.queryByRole("combobox", { name: /condom/i })).toBeNull();
  });

  it("renders no switcher and no message for a user with zero tenants", () => {
    // The zero-option state is also the state of every bare Navbar test and of
    // the routing smoke test, so the Navbar must render *nothing* extra here:
    // any placeholder would be new text inside those pre-existing trees.
    mockTenant([TENANT_A]);
    const single = renderNavbar().container.textContent;

    vi.restoreAllMocks();
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: USER as User,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn() as never,
      logout: vi.fn(),
    });
    mockTenant([]);
    const none = renderNavbar().container.textContent;

    expect(screen.queryByRole("combobox", { name: /condom/i })).toBeNull();
    expect(none).toBe(single);
  });

  it("defines tenant.switcherLabel in both pt and en, and defines no tenant.noAccess", () => {
    expect(pt.tenant.switcherLabel).toBe("Condomínio");
    expect(en.tenant.switcherLabel).toBe("Building");
    expect("noAccess" in pt.tenant).toBe(false);
    expect("noAccess" in en.tenant).toBe(false);
  });
});
