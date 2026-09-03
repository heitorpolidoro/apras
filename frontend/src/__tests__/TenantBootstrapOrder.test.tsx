import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "../App";
import apiClient from "../api/client";
import { clearActingTenantId, getActingTenantId,  } from "../features/user-administration/context/tenantState";
import { ALL_PERMISSIONS, PERMISSIONS_BY_ROLE,  } from "../test/permissionFixtures";

/**
 * Bootstrap ordering for the acting tenant, on the **real `App`**.
 *
 * Only `src/api/client` is mocked, and its `get` records
 * `{url, actingTenantId}` — the acting tenant *at the moment the request was
 * issued*, i.e. exactly what the real Axios interceptor would have read to
 * build `X-Tenant-Id`. Nothing under `src/features/**` is mocked, so the real
 * `AuthProvider`, `TenantProvider`, `Navbar` and `ProtectedRoute` are the ones
 * under test.
 *
 * The two invariants pinned here are the ones that are false without this
 * task's changes:
 *
 * 1. no tenant-scoped request leaves before the acting tenant is resolved
 *    (`enabled: useActingTenantReady()` on `useRoles`) — without it the
 *    recorded order is `["/roles/", "/auth/me"]`, the scoped request goes
 *    out headerless, the APRAS-42 resolver answers 400, and because the query
 *    is then *errored* rather than stale nothing ever refetches it;
 * 2. no commit observes a stale acting tenant (`TenantContext` reading the
 *    mirror through `useSyncExternalStore`) — with a `useState` + `useEffect`
 *    re-sync there is exactly one commit in which `user` is set, `isLoading`
 *    is false and the acting tenant is still `null`, and `ProtectedRoute`
 *    evaluates its rule in that commit.
 *
 * Since IAM F4 (APRAS-48) the client also answers `/permissions/me`, the
 * scoped read `ProtectedRoute` and `Navbar` now gate on. It is per-tenant, so
 * the `navigations` sentinel additionally proves that the extra query does not
 * cause a redirect while it is in flight.
 */

const TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

const TENANTS = [
  { id: TENANT_A, name: "Condomínio A", is_active: true },
  { id: TENANT_B, name: "Condomínio B", is_active: true },
];

/** Everything that is not one of the three global routes is tenant-scoped. */
const GLOBAL_PATHS = ["/auth/me", "/auth/dev-users", "/tenants"];

/** The Role that grants the `tasks` menu to the RESIDENT fixtures. */
const RESIDENT_TYPE = {
  id: "type-resident",
  name: "Morador do Condomínio A",
  permissions: [],
};

/** What `GET /permissions/me` answers per acting tenant, per fixture. */
const PERMISSIONS_BY_TENANT: Record<string, Record<string, string[]>> = {
  "u-dual": {
    [TENANT_A]: PERMISSIONS_BY_ROLE["RESIDENT"],
    [TENANT_B]: PERMISSIONS_BY_ROLE["RESIDENT"],
  },
  // IAM F3: the capability is the whole catalogue, in the granting tenant.
  "u-syndic": { [TENANT_A]: ALL_PERMISSIONS },
};

const membership = (
  tenantId: string,
  name: string,
  isTenantAdmin = false,
) => ({
  tenant_id: tenantId,
  name,
  is_active: true,
  is_tenant_admin: isTenantAdmin,
});

/** A dual-membership RESIDENT: the state that produced the APRAS-42 400. */
const DUAL_MEMBERSHIP_RESIDENT = {
  id: "u-dual",
  email: "dual@test.com",
  full_name: "Morador Duplo",
  is_active: true,
  roles: [RESIDENT_TYPE],
  tenants: [
    membership(TENANT_A, "Condomínio A"),
    membership(TENANT_B, "Condomínio B"),
  ],
};

/** A non-ADMINISTRATOR holding `is_tenant_admin` on its single tenant. */
const TENANT_ADMIN_OF_A = {
  id: "u-syndic",
  email: "syndic@test.com",
  full_name: "Síndico",
  is_active: true,
  roles: [RESIDENT_TYPE],
  tenants: [membership(TENANT_A, "Condomínio A", true)],
};

const USERS = [
  {
    id: "u-listed",
    email: "listed@test.com",
    full_name: "Usuário Listado",
    is_active: true,
    roles: [],
  },
];

vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockedGet = vi.mocked(apiClient.get);

interface Call {
  url: string;
  actingTenantId: string | null;
}

let calls: Call[];
/** Every path the router navigated to, including redirects later undone. */
let navigations: string[];
let pushState: typeof window.history.pushState;
let replaceState: typeof window.history.replaceState;

const installClient = (me: { id: string }) => {
  mockedGet.mockReset();
  mockedGet.mockImplementation(((url: string) => {
    const actingTenantId = getActingTenantId();
    calls.push({ url, actingTenantId });

    if (url === "/auth/me") return Promise.resolve({ data: me });
    if (url === "/tenants") return Promise.resolve({ data: TENANTS });
    if (url === "/roles/") {
      // The APRAS-42 header ladder, reproduced: a scoped request with no
      // acting tenant is a 400, not an empty list.
      if (actingTenantId === null) {
        return Promise.reject({
          response: {
            status: 400,
            data: { detail: "X-Tenant-Id header is required" },
          },
        });
      }
      return Promise.resolve({ data: [RESIDENT_TYPE] });
    }
    if (url === "/permissions/me") {
      if (actingTenantId === null) {
        return Promise.reject({
          response: {
            status: 400,
            data: { detail: "X-Tenant-Id header is required" },
          },
        });
      }
      return Promise.resolve({
        data: {
          tenant_id: actingTenantId,
          permissions: PERMISSIONS_BY_TENANT[me.id]?.[actingTenantId] ?? [],
        },
      });
    }
    if (url === "/users/") return Promise.resolve({ data: USERS });
    return Promise.resolve({ data: [] });
  }) as never);
};

const renderAppAt = (path: string) => {
  window.history.pushState({}, "", path);
  navigations.length = 0;
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
};

const scopedCalls = () =>
  calls.filter((call) => !GLOBAL_PATHS.includes(call.url));

describe("tenant bootstrap ordering (real App)", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    calls = [];
    navigations = [];
    // A stored token, and deliberately NOTHING under `actingTenantId` in
    // either storage: the state of the first load after this ships, and of
    // every load after a logout(). `clearActingTenantId` is what makes that
    // true — the mirror is module-level and would otherwise survive from the
    // previous test in this file, handing the next case a resolved tenant it
    // never earned and making it pass vacuously.
    clearActingTenantId();
    localStorage.setItem("accessToken", "stored-token");

    pushState = window.history.pushState.bind(window.history);
    replaceState = window.history.replaceState.bind(window.history);
    vi.spyOn(window.history, "pushState").mockImplementation(
      (data, unused, url) => {
        if (typeof url === "string") navigations.push(url);
        pushState(data, unused, url);
      },
    );
    vi.spyOn(window.history, "replaceState").mockImplementation(
      (data, unused, url) => {
        if (typeof url === "string") navigations.push(url);
        replaceState(data, unused, url);
      },
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("issues no tenant-scoped request before the acting tenant is resolved", async () => {
    installClient(DUAL_MEMBERSHIP_RESIDENT);

    renderAppAt("/dashboard");

    await waitFor(() => {
      expect(scopedCalls().length).toBeGreaterThan(0);
    });

    expect(calls[0].url).toBe("/auth/me");
    for (const call of scopedCalls()) {
      expect(call.actingTenantId).not.toBeNull();
    }
    // The pre-selection ladder lands on the first membership, ordered by
    // tenant name server-side.
    expect(getActingTenantId()).toBe(TENANT_A);
  });

  it("renders the dashboard links for a dual-membership user on first load", async () => {
    installClient(DUAL_MEMBERSHIP_RESIDENT);

    renderAppAt("/dashboard");

    // The menu genuinely depends on /roles/ returning rows: the fixture
    // is a non-ADMINISTRATOR whose single Role is what grants `tasks`.
    expect(
      await screen.findByRole("link", { name: "Tarefas" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Acesso restrito")).toBeNull();
  });

  it("renders /admin/users for a tenant_admin with no stored acting tenant", async () => {
    installClient(TENANT_ADMIN_OF_A);

    renderAppAt("/admin/users");

    expect(
      await screen.findByText("Gerenciamento de Usuários"),
    ).toBeInTheDocument();
    expect(await screen.findByText("Usuário Listado")).toBeInTheDocument();

    // The sentinel: every navigation the router performed, so a redirect that
    // happened and was later undone still fails this.
    expect(navigations).not.toContain("/dashboard");
    expect(window.location.pathname).toBe("/admin/users");

    // And it stays there once everything has settled.
    await waitFor(() => {
      expect(getActingTenantId()).toBe(TENANT_A);
    });
    expect(navigations).not.toContain("/dashboard");
    expect(window.location.pathname).toBe("/admin/users");
  });
});
