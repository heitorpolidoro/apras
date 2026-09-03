import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import Navbar from "../components/Navbar";
import ProtectedRoute from "../components/ProtectedRoute";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import { ROUTE_ACCESS } from "../access/routeAccess";
import { ALL_PERMISSIONS, PERMISSIONS_BY_ROLE,  } from "../../../test/permissionFixtures";
import { type User, type Role } from "../../../types/auth";

/**
 * ER-2's route half, through the real query stack.
 *
 * The last case is the one that proves §2.7's two-set design: authorization
 * reads the **real** set while the menu reads the **simulated** one, from one
 * `ROUTE_ACCESS` rule.
 */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({ data: [] })),
}));

const NOT_SIMULATING = {
  simulatedRoleIds: [],
  isSimulating: false,
  setSimulatedRoleIds: vi.fn(),
  stopSimulation: vi.fn(),
};

const mockedGet = vi.mocked(apiClient.get);

const answer = (permissions: readonly string[], pending = false) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/permissions/me") {
      return pending
        ? new Promise(() => undefined)
        : Promise.resolve({
            data: { tenant_id: "t-1", permissions: [...permissions] },
          });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

const authAs = (role: string, roles: Role[] = []) => {
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
};

const withClient = (ui: React.ReactElement) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

const renderRoute = (path: string, label: string) =>
  withClient(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path={path}
          element={
            <ProtectedRoute requiredAccess={ROUTE_ACCESS[path]}>
              <div>{label}</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useSimulation).mockReturnValue(NOT_SIMULATING);
});

describe("ProtectedRoute gating on /permissions/me", () => {
  it("renders the page when the rule's module permission is held", async () => {
    authAs("RESIDENT");
    answer(["finance:read"]);

    renderRoute("/finance", "Financeiro");

    expect(await screen.findByText("Financeiro")).toBeInTheDocument();
  });

  it('renders "Acesso restrito" when it is not', async () => {
    authAs("RESIDENT");
    answer(["tasks:read"]);

    renderRoute("/finance", "Financeiro");

    expect(await screen.findByText("Acesso restrito")).toBeInTheDocument();
    expect(screen.queryByText("Financeiro")).toBeNull();
  });

  it("renders the spinner while /permissions/me is pending", () => {
    authAs("RESIDENT");
    answer([], true);

    const { container } = renderRoute("/finance", "Financeiro");

    expect(container.querySelector(".animate-spin")).not.toBeNull();
    expect(screen.queryByText("Acesso restrito")).toBeNull();
    expect(screen.queryByText("Financeiro")).toBeNull();
  });

  it("admits a tenant_admin holding the whole catalogue to /admin/users", async () => {
    // IAM F3: the capability is not a role, it is the whole catalogue in the
    // granting tenant — so a RESIDENT síndico passes a `users:update` rule.
    authAs("RESIDENT");
    answer(ALL_PERMISSIONS);

    renderRoute("/admin/users", "Administração");

    expect(await screen.findByText("Administração")).toBeInTheDocument();
  });

  it("admits an administrator to /admin/photo-approvals", async () => {
    // A pre-existing bug, corrected: the old DIRECTOR-only prop locked out the
    // very administrator the Navbar was already offering the link to.
    authAs("ADMINISTRATOR");
    answer(PERMISSIONS_BY_ROLE["ADMINISTRATOR"]);

    renderRoute("/admin/photo-approvals", "Aprovações");

    expect(await screen.findByText("Aprovações")).toBeInTheDocument();
  });

  it("keeps route access on the real permission set while simulating", async () => {
    const RESIDENT_TYPE: Role = {
      id: "type-resident",
      name: "Morador (papel)",
      // The simulated roles grant no `roles:*` at all.
      permissions: ["occurrences:read"],
    };
    authAs("ADMINISTRATOR", [RESIDENT_TYPE]);
    // The real administrator holds the role-administration permission.
    answer(["roles:update", "occurrences:read"]);
    vi.mocked(useSimulation).mockReturnValue({
      ...NOT_SIMULATING,
      simulatedRoleIds: ["type-resident"],
      isSimulating: true,
    });

    withClient(
      <MemoryRouter initialEntries={["/admin/roles"]}>
        <Navbar />
        <Routes>
          <Route
            path="/admin/roles"
            element={
              <ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/roles"]}>
                <div>Editor de Papéis</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    // Authorization reads the REAL set: the page renders.
    expect(await screen.findByText("Editor de Papéis")).toBeInTheDocument();
    // …and the Navbar in the same tree shows the RESIDENT menu set, i.e. the
    // simulated roles' permissions and nothing the real admin holds beyond
    // them. One ROUTE_ACCESS rule, two hooks, two answers — by design.
    expect(
      screen.getByRole("link", { name: "Livro de Ocorrências" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Papéis" })).toBeNull();
  });
});
