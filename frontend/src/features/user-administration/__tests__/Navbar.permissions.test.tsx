import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Navbar from "../components/Navbar";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { PERMISSIONS_BY_ROLE } from "../../../test/permissionFixtures";
import { UserRole, type User, type UserType } from "../../../types/auth";

/**
 * ER-2's menu half: a link is shown iff its `ROUTE_ACCESS` rule is satisfied
 * by the set `GET /permissions/me` returned for the acting tenant.
 *
 * `apiClient` is the only mock on the data path, so `api/permissions.ts`,
 * `usePermissionQueries.ts`, `useCanAccess.ts` and `Navbar` all run for real.
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
  useUserTypes: vi.fn(() => ({ data: [] })),
}));

const MENU_TYPE: UserType = {
  id: "type-menus",
  name: "Com menus",
  allowed_menus: ["tasks", "categories"],
};

const mockedGet = vi.mocked(apiClient.get);

const renderNavbar = (
  role: UserRole,
  permissions: readonly string[],
  userTypes: UserType[] = [MENU_TYPE],
) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: {
      id: "u-1",
      email: "u@test.com",
      full_name: "Usuário",
      role,
      is_active: true,
      user_types: userTypes,
    } as User,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  vi.mocked(useUserTypes).mockReturnValue({ data: userTypes } as never);
  mockedGet.mockImplementation(((url: string) =>
    url === "/permissions/me"
      ? Promise.resolve({
          data: { tenant_id: "t-1", permissions: [...permissions] },
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

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Navbar gating on /permissions/me", () => {
  it("shows a morador exactly the links their permissions allow", async () => {
    renderNavbar(UserRole.RESIDENT, PERMISSIONS_BY_ROLE[UserRole.RESIDENT]);

    // Held: the resident-facing modules.
    expect(
      await screen.findByRole("link", { name: "Tarefas" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Financeiro" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Comunicados" })).toBeInTheDocument();
    // Not held: `users:update` (administration) and `spaces:create` (spaces).
    expect(screen.queryByRole("link", { name: "Administração" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Espaços" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Grupos" })).toBeNull();
  });

  it("shows a porteiro the Portaria link and not Comunicados/Financeiro/Administração", async () => {
    renderNavbar(UserRole.PORTEIRO, PERMISSIONS_BY_ROLE[UserRole.PORTEIRO], []);

    expect(
      await screen.findByRole("link", { name: "Portaria" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Comunicados" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Financeiro" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Administração" })).toBeNull();
    // Menu-gated and this porteiro holds no menu key.
    expect(screen.queryByRole("link", { name: "Tarefas" })).toBeNull();
  });

  it("hides Financeiro from a custom group with no finance permission", async () => {
    // A group-only identity: no legacy bundle at all, just what the group grants.
    renderNavbar(UserRole.GUEST, ["occurrences:read", "documents:read"], []);

    expect(
      await screen.findByRole("link", { name: "Livro de Ocorrências" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Central de Documentos" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Financeiro" })).toBeNull();
  });

  it("shows Grupos to a user holding user_types:update", async () => {
    renderNavbar(UserRole.RESIDENT, ["user_types:update"], []);

    expect(
      await screen.findByRole("link", { name: "Grupos" }),
    ).toHaveAttribute("href", "/admin/groups");
    // …and only that one: nothing else is held.
    expect(screen.queryByRole("link", { name: "Administração" })).toBeNull();
  });
});
