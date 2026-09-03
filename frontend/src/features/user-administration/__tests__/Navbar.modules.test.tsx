import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import Navbar from "../components/Navbar";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import { useTenant } from "../context/useTenant";
import pt from "../../../i18n/locales/pt.json";
import { type User } from "../../../types/auth";

/**
 * ER-3's first half needs **no** navigation code (APRAS-39 §10.4).
 *
 * `NAV_ITEMS` is gated by `useCanShowMenu` over the permission set, and the
 * backend strip has already removed a disabled module's permissions from
 * `/permissions/me` — so the item is simply absent. These cases pin that the
 * mechanism really is only the strip, with no `disabled_modules` read on the
 * menu path at all.
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

vi.mock("../context/useTenant", () => ({
  useTenant: vi.fn(),
  useActingTenantReady: vi.fn(() => true),
}));

const mockedGet = vi.mocked(apiClient.get);

const NOT_SIMULATING = {
  simulatedRoleIds: [],
  isSimulating: false,
  setSimulatedRoleIds: vi.fn(),
  stopSimulation: vi.fn(),
};

const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

const answer = (permissions: string[], disabled: string[] = []) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/permissions/me") {
      return Promise.resolve({
        data: {
          tenant_id: "t-1",
          permissions,
          landing_path: null,
          disabled_modules: disabled,
        },
      });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

const auth = (isSuperuser = false) => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: {
      id: "u-1",
      email: "u@test.com",
      full_name: "Usuário",
      is_active: true,
      is_superuser: isSuperuser,
      roles: [],
    } as User,
    login: vi.fn() as never,
    logout: vi.fn(),
  } as never);
};

const renderNavbar = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return render(<Navbar />, { wrapper: Wrapper });
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  vi.mocked(useSimulation).mockReturnValue(NOT_SIMULATING);
  vi.mocked(useRoles).mockReturnValue({ data: [] } as never);
  vi.mocked(useTenant).mockReturnValue({
    tenants: [],
    actingTenantId: "t-1",
    setActingTenant: vi.fn(),
    actingTenant: null,
    isTenantAdminHere: false,
    isLoading: false,
  } as never);
  auth();
});

describe("Navbar and a disabled module", () => {
  it("hides the /finance link when the stripped payload carries no finance:*", async () => {
    answer(["tasks:read"], ["finance"]);

    renderNavbar();

    await waitFor(() =>
      expect(screen.getByText(t("nav.tasks"))).toBeInTheDocument(),
    );
    expect(screen.queryByText(t("nav.finance"))).toBeNull();
  });

  it("shows the /finance link when the module is active and the permission held", async () => {
    answer(["tasks:read", "finance:read"]);

    renderNavbar();

    expect(await screen.findByText(t("nav.finance"))).toBeInTheDocument();
  });

  it("shows the module-switch item only to a superuser", async () => {
    answer(["tenants:update", "tenants:members_set_admin"]);

    renderNavbar();

    await waitFor(() => expect(mockedGet).toHaveBeenCalled());
    // A tenant_admin holds `tenants:update` through the whole-catalogue
    // short-circuit and is still answered 403 by the API, so the menu must
    // read the flag rather than the permission.
    expect(screen.queryByText(t("nav.modules"))).toBeNull();

    auth(true);
    renderNavbar();

    expect(await screen.findByText(t("nav.modules"))).toBeInTheDocument();
  });
});
