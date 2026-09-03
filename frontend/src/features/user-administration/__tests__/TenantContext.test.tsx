import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useEffect, type FC } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { TenantProvider } from "../context/TenantContext";
import { useTenant } from "../context/useTenant";
import { getActingTenantId, clearActingTenantId, setActingTenantId,  } from "../context/tenantState";
import { type User } from "../../../types/auth";

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn() },
}));

const TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
const TENANT_INACTIVE = "cccccccc-cccc-cccc-cccc-cccccccccccc";

const TENANTS = [
  { id: TENANT_A, name: "Condomínio A", is_active: true },
  { id: TENANT_B, name: "Condomínio B", is_active: true },
  { id: TENANT_INACTIVE, name: "Condomínio Desativado", is_active: false },
];

const mockedGet = vi.mocked(apiClient.get);

const mockAuth = (user: Partial<User> | null) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    user: user as User | null,
    isAuthenticated: user !== null,
    isLoading: false,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
};

/** Prints the whole context value, so every assertion reads one rendered DOM. */
const Probe: FC = () => {
  const tenant = useTenant();
  return (
    <div>
      <span data-testid="options">
        {tenant.tenants.map((t) => t.name).join("|")}
      </span>
      <span data-testid="acting">{tenant.actingTenantId ?? "none"}</span>
      <span data-testid="acting-name">{tenant.actingTenant?.name ?? "none"}</span>
      <span data-testid="is-admin">{String(tenant.isActingTenantAdmin)}</span>
    </div>
  );
};

const renderProbe = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TenantProvider>
        <Probe />
      </TenantProvider>
    </QueryClientProvider>,
  );
};

describe("TenantContext", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    clearActingTenantId();
    mockedGet.mockReset();
    mockedGet.mockResolvedValue({ data: TENANTS });
  });

  it("lists every tenant returned by GET /tenants for an ADMINISTRATOR", async () => {
    mockAuth({ id: "u1", is_superuser: true, tenants: [] });
    sessionStorage.setItem("accessToken", "token");
    setActingTenantId(TENANT_A);

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("options")).toHaveTextContent(
        "Condomínio A|Condomínio B",
      );
    });
    // No trailing slash: /tenants is mounted at "" and a slash costs a 307.
    expect(mockedGet).toHaveBeenCalledWith("/tenants");
  });

  it("filters inactive tenants out of the options", async () => {
    mockAuth({ id: "u1", is_superuser: true, tenants: [] });
    sessionStorage.setItem("accessToken", "token");
    setActingTenantId(TENANT_A);

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("options")).toHaveTextContent("Condomínio A");
    });
    expect(screen.getByTestId("options")).not.toHaveTextContent(
      "Condomínio Desativado",
    );
  });

  it("reports isActingTenantAdmin only for the acting membership", async () => {
    mockAuth({
      id: "u1",
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
    });
    sessionStorage.setItem("accessToken", "token");
    setActingTenantId(TENANT_A);

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("acting-name")).toHaveTextContent(
        "Condomínio A",
      );
    });
    expect(screen.getByTestId("is-admin")).toHaveTextContent("true");

    act(() => {
      setActingTenantId(TENANT_B);
    });

    await waitFor(() => {
      expect(screen.getByTestId("is-admin")).toHaveTextContent("false");
    });
  });

  it("reconciles a stored tenant id that is no longer an option", async () => {
    mockAuth({ id: "u1", is_superuser: true, tenants: [] });
    sessionStorage.setItem("accessToken", "token");
    // A tenant that was deactivated, or whose membership was revoked.
    setActingTenantId("dddddddd-dddd-dddd-dddd-dddddddddddd");

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("acting")).toHaveTextContent(TENANT_A);
    });
    expect(getActingTenantId()).toBe(TENANT_A);
  });

  it("selects the first option for a zero-membership ADMINISTRATOR with no stored id", async () => {
    mockAuth({ id: "u1", is_superuser: true, tenants: [] });
    sessionStorage.setItem("accessToken", "token");

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("acting")).toHaveTextContent(TENANT_A);
    });
  });

  it("leaves a zero-option user on the backend fallback (no selection)", async () => {
    mockAuth({ id: "u1", tenants: [] });
    sessionStorage.setItem("accessToken", "token");
    mockedGet.mockResolvedValue({ data: [] });

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("options")).toHaveTextContent("");
    });
    expect(screen.getByTestId("acting")).toHaveTextContent("none");
    expect(getActingTenantId()).toBeNull();
  });

  it("does not query /tenants when unauthenticated", async () => {
    mockAuth(null);

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("acting")).toHaveTextContent("none");
    });
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it("useTenant returns the fail-closed zero value without a provider", () => {
    mockAuth({ id: "u1", is_superuser: true });

    render(<Probe />);

    expect(screen.getByTestId("options")).toHaveTextContent("");
    expect(screen.getByTestId("acting")).toHaveTextContent("none");
    expect(screen.getByTestId("is-admin")).toHaveTextContent("false");
  });

  it("the zero value's setActingTenant is an inert no-op", () => {
    mockAuth({ id: "u1", is_superuser: true });
    // A mutable holder written from an effect, not an outer `let` assigned
    // during render: the render body must stay free of side effects.
    const captured: { setActingTenant: ((id: string) => void) | null } = {
      setActingTenant: null,
    };
    const Capture: FC = () => {
      const { setActingTenant } = useTenant();
      useEffect(() => {
        captured.setActingTenant = setActingTenant;
      }, [setActingTenant]);
      return null;
    };

    render(<Capture />);
    // With no provider there is nothing to switch: calling it must neither
    // throw nor quietly start sending a tenant header.
    expect(captured.setActingTenant).not.toBeNull();
    expect(() => captured.setActingTenant?.(TENANT_A)).not.toThrow();
    expect(getActingTenantId()).toBeNull();
  });
});
