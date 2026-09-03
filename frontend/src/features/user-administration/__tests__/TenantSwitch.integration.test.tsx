import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import apiClient from "../../../api/client";
import Navbar from "../components/Navbar";
import TaskDashboard from "../../task-management/components/TaskDashboard";
import * as AuthHook from "../context/AuthContext";
import { TenantProvider } from "../context/TenantContext";
import { clearActingTenantId, getActingTenantId, setActingTenantId,  } from "../context/tenantState";
import { type User } from "../../../types/auth";

/**
 * Navbar + TaskDashboard under a real `TenantProvider`, with the mocked client
 * answering `/tasks/` **from `getActingTenantId()`** — i.e. from the exact
 * value the Axios interceptor would put in `X-Tenant-Id`. Combined with
 * `client.tenantHeader.test.ts`, which pins mirror → header, that is what makes
 * this an end-to-end statement about the tenant the backend would receive.
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

const TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

const TENANTS = [
  { id: TENANT_A, name: "Condomínio A", is_active: true },
  { id: TENANT_B, name: "Condomínio B", is_active: true },
];

const TASKS_BY_TENANT: Record<string, string> = {
  [TENANT_A]: "Tarefa A",
  [TENANT_B]: "Tarefa B",
};

const task = (title: string) => ({
  id: `task-${title}`,
  title,
  description: "",
  status: "PENDING",
  priority: "MEDIUM",
  is_deleted: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  visible_to: [],
});

const mockedGet = vi.mocked(apiClient.get);

const USER_TYPES = [
  { id: "type-1", name: "Test Type" },
];

/**
 * `/permissions/me` per tenant (IAM F4, ER-3): tenant A grants
 * `finance:read`, tenant B does not. The key is `["me","permissions"]`, which
 * does not start with `"tenants"`, so `setActingTenant`'s `resetQueries`
 * sweep evicts and refetches it under the new header — no reload.
 */
const PERMISSIONS_BY_TENANT: Record<string, string[]> = {
  [TENANT_A]: ["tasks:read", "categories:read", "finance:read"],
  [TENANT_B]: ["tasks:read", "categories:read"],
};

const installClient = () => {
  mockedGet.mockReset();
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/tenants") return Promise.resolve({ data: TENANTS });
    if (url === "/roles/") return Promise.resolve({ data: USER_TYPES });
    if (url === "/permissions/me") {
      const acting = getActingTenantId();
      return Promise.resolve({
        data: {
          tenant_id: acting,
          permissions: acting ? PERMISSIONS_BY_TENANT[acting] ?? [] : [],
        },
      });
    }
    if (url === "/tasks/") {
      const acting = getActingTenantId();
      const title = acting ? TASKS_BY_TENANT[acting] : undefined;
      return Promise.resolve({ data: title ? [task(title)] : [] });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

const mockAuth = (user: Partial<User>) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: user as User,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
};

const renderApp = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TenantProvider>
          <Navbar />
          <TaskDashboard />
        </TenantProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("tenant switch integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    clearActingTenantId();
    installClient();
    sessionStorage.setItem("accessToken", "token");
    setActingTenantId(TENANT_A);
  });

  it("shows only the acting tenant's tasks after switching, with no stale rows", async () => {
    mockAuth({
      id: "u1",
      full_name: "Morador",
      roles: USER_TYPES,
      tenants: [
        {
          tenant_id: TENANT_A,
          name: "Condomínio A",
          is_active: true,
          is_tenant_admin: false,
        },
        {
          tenant_id: TENANT_B,
          name: "Condomínio B",
          is_active: true,
          is_tenant_admin: false,
        },
      ],
    });

    renderApp();

    expect(await screen.findByText("Tarefa A")).toBeInTheDocument();
    expect(screen.queryByText("Tarefa B")).toBeNull();

    const switcher = await screen.findByRole("combobox", { name: /condom/i });
    await userEvent.selectOptions(switcher, TENANT_B);

    // Eviction, not invalidation: the previous tenant's row must not be
    // readable at any point after the switch.
    expect(await screen.findByText("Tarefa B")).toBeInTheDocument();
    expect(screen.queryByText("Tarefa A")).toBeNull();
    expect(getActingTenantId()).toBe(TENANT_B);
  });

  it("an ADMINISTRATOR can switch into a tenant they are not a member of and sees its data", async () => {
    // Zero memberships, yet GET /tenants offers every tenant: global vision is
    // a property of sending the header, not of holding a membership.
    mockAuth({
      id: "u-admin",
      full_name: "Admin",
      is_superuser: true,
      roles: USER_TYPES,
      tenants: [],
    });

    renderApp();

    expect(await screen.findByText("Tarefa A")).toBeInTheDocument();

    const switcher = await screen.findByRole("combobox", { name: /condom/i });
    await userEvent.selectOptions(switcher, TENANT_B);

    expect(await screen.findByText("Tarefa B")).toBeInTheDocument();
    expect(screen.queryByText("Tarefa A")).toBeNull();

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith("/tasks/", expect.anything());
    });
  });

  it("re-evaluates menus after a tenant switch without a reload", async () => {
    mockAuth({
      id: "u1",
      full_name: "Morador",
      roles: USER_TYPES,
      tenants: [
        {
          tenant_id: TENANT_A,
          name: "Condomínio A",
          is_active: true,
          is_tenant_admin: false,
        },
        {
          tenant_id: TENANT_B,
          name: "Condomínio B",
          is_active: true,
          is_tenant_admin: false,
        },
      ],
    });

    // jsdom will not let `location.reload` be redefined, so the sentinel is
    // the URL itself: any reload or assignment would move it.
    const originalHref = window.location.href;
    const originalPath = window.location.pathname;

    renderApp();

    // Tenant A grants `finance:read`, so the Financeiro link is shown.
    expect(
      await screen.findByRole("link", { name: "Financeiro" }),
    ).toBeInTheDocument();

    const switcher = await screen.findByRole("combobox", { name: /condom/i });
    await userEvent.selectOptions(switcher, TENANT_B);

    // Tenant B does not, and the link disappears with no page reload: the
    // permission query was evicted and refetched under the new header.
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Financeiro" })).toBeNull(),
    );
    expect(screen.getByRole("link", { name: "Tarefas" })).toBeInTheDocument();
    expect(window.location.href).toBe(originalHref);
    expect(window.location.pathname).toBe(originalPath);
    expect(getActingTenantId()).toBe(TENANT_B);
  });
});
