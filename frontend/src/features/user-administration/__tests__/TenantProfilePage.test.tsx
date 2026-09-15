import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import TenantProfilePage from "../pages/TenantProfilePage";
import ProtectedRoute from "../components/ProtectedRoute";
import * as AuthHook from "../context/AuthContext";
import { useSimulation } from "../context/SimulationContext";
import { useRoles } from "../../../hooks/useRoles";
import { ROUTE_ACCESS } from "../access/routeAccess";
import {
  TENANT_LOGO_ALLOWED_MIME_TYPES,
  TENANT_LOGO_MAX_FILE_SIZE_BYTES,
  TENANT_PROFILE_PERMISSION,
} from "../../../api/tenantProfile";
import type { User, Role } from "../../../types/auth";

/**
 * The condominium profile screen (APRAS-61).
 *
 * Two halves are pinned here and nowhere else: the **client-side refusal** —
 * an `image/svg+xml` or an over-cap file must never reach the network, because
 * the whole point of D2 is that those bytes are not served from our origin —
 * and the **denial**, which is `ProtectedRoute` rendering
 * `RestrictedAccessMessage` in place, never a redirect.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock("../context/SimulationContext", () => ({
  useSimulation: vi.fn(),
}));

vi.mock("../../../hooks/useRoles", () => ({
  useRoles: vi.fn(() => ({ data: [] })),
}));

/** The suite's `t` resolves against `pt.json` (`src/test/setup.ts`), so the
 *  assertions name the key and read the same string the component renders. */
const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

const mockedGet = vi.mocked(apiClient.get);
const mockedPut = vi.mocked(apiClient.put);
const mockedDelete = vi.mocked(apiClient.delete);

const PROFILE = {
  id: "8f1c0f2e-5e5c-4a0f-9c1e-1c2a3b4d5e6f",
  name: "Residencial Altos da Serra VI",
  is_active: true,
  logo_url: null as string | null,
};

const serve = (logoUrl: string | null) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/tenant-profile") {
      return Promise.resolve({ data: { ...PROFILE, logo_url: logoUrl } });
    }
    return Promise.resolve({ data: [] });
  }) as never);
};

const renderPage = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(<TenantProfilePage />, { wrapper: Wrapper });
};

const file = (name: string, type: string, bytes: number): File =>
  new File([new Uint8Array(bytes)], name, { type });

const pickLogo = async (selected: File) => {
  // `applyAccept: false` on purpose: the control carries the real `accept=`,
  // and letting userEvent enforce it would make the SVG case pass without the
  // component ever refusing anything. The refusal under test is the
  // component's, not the browser's file-picker filter — which is advisory and
  // trivially bypassed by a drag-drop or a scripted client.
  const user = userEvent.setup({ applyAccept: false });
  const input = await screen.findByLabelText(t("tenantProfile.fileInputLabel"));
  await user.upload(input, selected);
  return user;
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  vi.mocked(useSimulation).mockReturnValue({
    simulatedRoleIds: [],
    isSimulating: false,
    setSimulatedRoleIds: vi.fn(),
    stopSimulation: vi.fn(),
  });
});

describe("TenantProfilePage", () => {
  it("renders the condominium name and the current logo", async () => {
    serve("/static/uploads/2026/09/brasao.png");

    renderPage();

    expect(await screen.findByText(t("tenantProfile.title"))).toBeInTheDocument();
    expect(await screen.findByDisplayValue(PROFILE.name)).toBeInTheDocument();
    const logo = await screen.findByAltText(t("tenantProfile.logoAlt"));
    expect(logo).toHaveAttribute("src", "/static/uploads/2026/09/brasao.png");
  });

  it("renders a placeholder instead of a broken image when there is no logo", async () => {
    serve(null);

    renderPage();

    expect(await screen.findByText(t("tenantProfile.logoEmpty"))).toBeInTheDocument();
    expect(screen.queryByAltText(t("tenantProfile.logoAlt"))).not.toBeInTheDocument();
  });

  it("refuses an image/svg+xml before sending anything", async () => {
    serve(null);
    renderPage();

    await pickLogo(file("brasao.svg", "image/svg+xml", 128));

    expect(
      await screen.findByText(t("tenantProfile.errors.type")),
    ).toBeInTheDocument();
    expect(mockedPut).not.toHaveBeenCalled();
  });

  it("refuses a file over the cap before sending anything", async () => {
    serve(null);
    renderPage();

    await pickLogo(
      file("fachada.png", "image/png", TENANT_LOGO_MAX_FILE_SIZE_BYTES + 1),
    );

    expect(
      await screen.findByText(t("tenantProfile.errors.size")),
    ).toBeInTheDocument();
    expect(mockedPut).not.toHaveBeenCalled();
  });

  it("uploads an accepted file as multipart and re-renders the returned URL", async () => {
    serve(null);
    mockedPut.mockResolvedValue({
      data: { ...PROFILE, logo_url: "/static/uploads/2026/09/novo.png" },
    } as never);
    renderPage();

    await pickLogo(file("brasao.png", "image/png", 1024));

    await waitFor(() => expect(mockedPut).toHaveBeenCalledTimes(1));
    const [url, body, config] = mockedPut.mock.calls[0];
    expect(url).toBe("/tenant-profile/logo");
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get("file")).toBeInstanceOf(File);
    expect(
      (config as { headers?: Record<string, string> })?.headers?.[
        "Content-Type"
      ],
    ).toBe("multipart/form-data");

    const logo = await screen.findByAltText(t("tenantProfile.logoAlt"));
    expect(logo).toHaveAttribute("src", "/static/uploads/2026/09/novo.png");
  });

  it("shows a translated message when the backend refuses the bytes with 422", async () => {
    serve(null);
    mockedPut.mockRejectedValue({ response: { status: 422 } });
    renderPage();

    await pickLogo(file("logo.png", "image/png", 1024));

    expect(
      await screen.findByText(t("tenantProfile.errors.rejected")),
    ).toBeInTheDocument();
  });

  it("removes the logo through DELETE and falls back to the placeholder", async () => {
    serve("/static/uploads/2026/09/brasao.png");
    mockedDelete.mockResolvedValue({
      data: { ...PROFILE, logo_url: null },
    } as never);
    renderPage();

    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: t("tenantProfile.remove") }));

    await waitFor(() =>
      expect(mockedDelete).toHaveBeenCalledWith("/tenant-profile/logo"),
    );
    expect(await screen.findByText(t("tenantProfile.logoEmpty"))).toBeInTheDocument();
  });

  it("renames the condominium through PATCH", async () => {
    serve(null);
    mockedPut.mockResolvedValue({ data: PROFILE } as never);
    vi.mocked(apiClient.patch).mockResolvedValue({
      data: { ...PROFILE, name: "Novo Nome" },
    } as never);
    renderPage();

    const user = userEvent.setup();
    const input = await screen.findByDisplayValue(PROFILE.name);
    await user.clear(input);
    await user.type(input, "Novo Nome");
    await user.click(screen.getByRole("button", { name: t("tenantProfile.save") }));

    await waitFor(() =>
      expect(apiClient.patch).toHaveBeenCalledWith("/tenant-profile", {
        name: "Novo Nome",
      }),
    );
  });

  it("shows a translated message when the new name is already taken (409)", async () => {
    serve(null);
    vi.mocked(apiClient.patch).mockRejectedValue({ response: { status: 409 } });
    renderPage();

    const user = userEvent.setup();
    const input = await screen.findByDisplayValue(PROFILE.name);
    await user.clear(input);
    await user.type(input, "Condomínio B");
    await user.click(screen.getByRole("button", { name: t("tenantProfile.save") }));

    expect(
      await screen.findByText(t("tenantProfile.errors.conflict")),
    ).toBeInTheDocument();
  });
});

describe("the /admin/tenant-profile gate", () => {
  const authAs = (roles: Role[] = []) => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "u-1",
        email: "u@test.com",
        full_name: "Usuário",
        is_active: true,
        roles,
      } as User,
      login: vi.fn() as never,
      logout: vi.fn(),
    });
    vi.mocked(useRoles).mockReturnValue({ data: roles } as never);
  };

  const servePermissions = (permissions: string[]) => {
    mockedGet.mockImplementation(((url: string) => {
      if (url === "/permissions/me") {
        return Promise.resolve({
          data: { tenant_id: "t-1", permissions, disabled_modules: [] },
        });
      }
      if (url === "/tenant-profile") {
        return Promise.resolve({ data: PROFILE });
      }
      return Promise.resolve({ data: [] });
    }) as never);
  };

  const renderGuarded = () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/admin/tenant-profile"]}>
          <Routes>
            <Route
              path="/admin/tenant-profile"
              element={
                <ProtectedRoute
                  requiredAccess={ROUTE_ACCESS["/admin/tenant-profile"]}
                >
                  <TenantProfilePage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
  };

  it("renders RestrictedAccessMessage and no upload control without the permission", async () => {
    authAs();
    servePermissions(["tenants:read", "tenants:update"]);

    renderGuarded();

    expect(
      await screen.findByText(t("common.restrictedAccess")),
    ).toBeInTheDocument();
    expect(screen.queryByText(t("tenantProfile.title"))).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(t("tenantProfile.fileInputLabel")),
    ).not.toBeInTheDocument();
  });

  it("renders the page for a holder of the permission", async () => {
    authAs();
    servePermissions([TENANT_PROFILE_PERMISSION]);

    renderGuarded();

    expect(await screen.findByText(t("tenantProfile.title"))).toBeInTheDocument();
  });

  it("states the same four facts the backend pins from its side", () => {
    // The frontend half of the two-sided pin. Its twin is
    // `backend/tests/test_tenant_profile.py::test_the_profile_contract_matches_the_frontend_client`.
    expect(TENANT_LOGO_MAX_FILE_SIZE_BYTES).toBe(2 * 1024 * 1024);
    expect([...TENANT_LOGO_ALLOWED_MIME_TYPES]).toEqual([
      "image/png",
      "image/jpeg",
      "image/webp",
    ]);
    expect(TENANT_LOGO_ALLOWED_MIME_TYPES).not.toContain("image/svg+xml");
    expect(TENANT_PROFILE_PERMISSION).toBe("tenants:profile_update");
    expect(ROUTE_ACCESS["/admin/tenant-profile"]).toEqual({
      anyOf: [TENANT_PROFILE_PERMISSION],
    });
  });
});
