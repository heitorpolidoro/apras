import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Navbar from "../components/Navbar";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { useRoles } from "../../../hooks/useRoles";
import { PERMISSIONS_BY_ROLE } from "../../../test/permissionFixtures";
import { type User, type Role } from "../../../types/auth";

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
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({ data: [] })),
}));

const MENU_TYPE: Role = {
  id: "type-menus",
  name: "Com menus",
};

const mockedGet = vi.mocked(apiClient.get);

const renderNavbar = (
  role: string,
  permissions: readonly string[],
  roles: Role[] = [MENU_TYPE],
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
      roles: roles,
    } as User,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  vi.mocked(useRoles).mockReturnValue({ data: roles } as never);
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
    renderNavbar("RESIDENT", PERMISSIONS_BY_ROLE["RESIDENT"]);

    // Held: the resident-facing modules.
    expect(
      await screen.findByRole("link", { name: "Tarefas" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Financeiro" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Comunicados" })).toBeInTheDocument();
    // Not held: `users:update` (administration) and `spaces:create` (spaces).
    expect(screen.queryByRole("link", { name: "Administração" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Espaços" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Papéis" })).toBeNull();
  });

  it("shows a porteiro the Portaria link and not Comunicados/Financeiro/Administração", async () => {
    renderNavbar("PORTEIRO", PERMISSIONS_BY_ROLE["PORTEIRO"], []);

    expect(
      await screen.findByRole("link", { name: "Portaria" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Comunicados" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Financeiro" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Administração" })).toBeNull();
    // §4.2's widening: a PORTEIRO genuinely holds `tasks:read`, and the
    // `allowed_menus` gate that hid the link in front of that permission is
    // gone. The backend has always answered 200 here.
    expect(screen.getByRole("link", { name: "Tarefas" })).toBeInTheDocument();
  });

  it("hides Financeiro from a custom role with no finance permission", async () => {
    // A role-only identity: no legacy bundle at all, just what the role grants.
    renderNavbar("GUEST", ["occurrences:read", "documents:read"], []);

    expect(
      await screen.findByRole("link", { name: "Livro de Ocorrências" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Central de Documentos" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Financeiro" })).toBeNull();
  });

  it("shows Papéis to a user holding roles:update", async () => {
    renderNavbar("RESIDENT", ["roles:update"], []);

    expect(
      await screen.findByRole("link", { name: "Papéis" }),
    ).toHaveAttribute("href", "/admin/roles");
    // …and only that one: nothing else is held.
    expect(screen.queryByRole("link", { name: "Administração" })).toBeNull();
  });
});
