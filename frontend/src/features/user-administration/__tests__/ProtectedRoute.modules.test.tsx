import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import ProtectedRoute from "../components/ProtectedRoute";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import { ROUTE_ACCESS } from "../access/routeAccess";
import pt from "../../../i18n/locales/pt.json";
import { type User } from "../../../types/auth";

/**
 * The "module not enabled" variant of the restricted-access message
 * (APRAS-39 §10.4).
 *
 * It is **presentational only**: the same component, the same zero network
 * calls, two different strings. The refusal itself is produced by the
 * backend strip, which is why no route or rule changes to get here — a
 * disabled module's permissions are simply absent from `/permissions/me`.
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

const auth = () => {
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: {
      id: "u-1",
      email: "u@test.com",
      full_name: "Usuário",
      is_active: true,
      is_superuser: false,
      roles: [],
    } as User,
    login: vi.fn() as never,
    logout: vi.fn(),
  } as never);
};

const renderAt = (path: string) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path={path}
          element={
            <ProtectedRoute requiredAccess={ROUTE_ACCESS[path]}>
              <div>Conteúdo</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
    { wrapper: Wrapper },
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  vi.mocked(useSimulation).mockReturnValue(NOT_SIMULATING);
  vi.mocked(useRoles).mockReturnValue({ data: [] } as never);
  auth();
});

describe("ProtectedRoute and a disabled module", () => {
  it("renders the module-unavailable copy when the route's module is off", async () => {
    answer([], ["finance"]);

    renderAt("/finance");

    expect(await screen.findByText(t("common.moduleUnavailable"))).toBeInTheDocument();
    expect(
      screen.getByText(t("common.moduleUnavailableMessage")),
    ).toBeInTheDocument();
    expect(screen.queryByText(t("common.restrictedAccess"))).toBeNull();
    expect(screen.queryByText("Conteúdo")).toBeNull();
  });

  it("renders the generic copy when the module is active but the permission is missing", async () => {
    answer([]);

    renderAt("/finance");

    expect(await screen.findByText(t("common.restrictedAccess"))).toBeInTheDocument();
    expect(screen.queryByText(t("common.moduleUnavailable"))).toBeNull();
  });

  it("reads the module of an { anyOf } rule from its first entry", async () => {
    // `/gate` is `{ anyOf: ["gate:checkin"] }`, so the module has to come
    // from the permission string rather than from a `{ module }` field.
    answer([], ["gate"]);

    renderAt("/gate");

    expect(await screen.findByText(t("common.moduleUnavailable"))).toBeInTheDocument();
  });

  it("renders the content when the module is on and the permission is held", async () => {
    answer(["finance:read"]);

    renderAt("/finance");

    expect(await screen.findByText("Conteúdo")).toBeInTheDocument();
  });

  it("never asks the network for anything beyond /permissions/me", async () => {
    answer([], ["finance"]);

    renderAt("/finance");

    await screen.findByText(t("common.moduleUnavailable"));
    const urls = mockedGet.mock.calls.map((call) => call[0]);
    expect(new Set(urls)).toEqual(new Set(["/permissions/me"]));
  });
});
