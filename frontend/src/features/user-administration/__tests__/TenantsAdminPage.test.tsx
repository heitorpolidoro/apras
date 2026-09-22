import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import TenantsAdminPage from "../pages/TenantsAdminPage";
import ProtectedRoute from "../components/ProtectedRoute";
import { ROUTE_ACCESS } from "../access/routeAccess";
import * as AuthHook from "../context/AuthContext";
import { useMyPermissions } from "../../../hooks/usePermissionQueries";
import { ALL_PERMISSIONS, settledPermissions } from "../../../test/permissionFixtures";
import type { User } from "../../../types/auth";

/**
 * The superuser condominium screen behind `/admin/tenants` (APRAS-70).
 *
 * The screen is **frontend only**: it reads the existing `GET /api/v1/tenants`
 * and creates through the existing `POST /api/v1/tenants`, so `apiClient` is
 * the mock boundary here — the assertions are about the wire calls the screen
 * makes, not about an intermediate wrapper.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
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

vi.mock("../../../hooks/usePermissionQueries", () => ({
  useMyPermissions: vi.fn(),
  usePermissionCatalogue: vi.fn(() => ({ data: [], isPending: false })),
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

const AURORA = {
  id: "t-aurora",
  name: "Edifício Aurora",
  slug: "edificio-aurora",
  is_active: true,
  created_at: "2026-09-20T13:45:09",
};
const AGUAS = {
  id: "t-aguas",
  name: "Parque das Águas",
  slug: "parque-das-aguas",
  is_active: false,
  created_at: "2026-08-12T08:00:00",
};
const SERRA = {
  id: "t-serra",
  name: "Residencial Altos da Serra",
  slug: "residencial-altos-da-serra",
  is_active: true,
  created_at: "2026-07-02T10:15:00",
};
const TENANTS = [AURORA, AGUAS, SERRA];

/** The one formatting rule the column is specified by (D9). */
const asDate = (isoString: string) =>
  new Date(isoString).toLocaleDateString("pt");

const answerList = (tenants: unknown[] = TENANTS) => {
  mockedGet.mockImplementation(((url: string) =>
    url === "/tenants"
      ? Promise.resolve({ data: tenants })
      : Promise.resolve({ data: [] })) as never);
};

const newClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderPage = (client = newClient()) => {
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, ...render(<TenantsAdminPage />, { wrapper: Wrapper }) };
};

const openForm = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(
    await screen.findByRole("button", { name: t("tenantsAdmin.new") }),
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPost.mockReset();
  answerList();
  vi.mocked(useMyPermissions).mockReturnValue(
    settledPermissions([]) as never,
  );
});

describe("TenantsAdminPage list", () => {
  it("renders one row per tenant with name, slug, status badge and creation date", async () => {
    renderPage();

    const rows = await screen.findAllByRole("row");
    // One header row plus one row per tenant.
    expect(rows).toHaveLength(TENANTS.length + 1);

    const aurora = within(screen.getByTestId(`tenant-row-${AURORA.id}`));
    expect(aurora.getByText(AURORA.name)).toBeInTheDocument();
    expect(aurora.getByText(AURORA.slug)).toBeInTheDocument();
    expect(aurora.getByText(t("tenantsAdmin.activeBadge"))).toBeInTheDocument();
    expect(aurora.getByText(asDate(AURORA.created_at))).toBeInTheDocument();

    // Date only: `toLocaleDateString` never renders a time component, and a
    // regression to `toLocaleString` would put one here.
    const dateCell = screen.getByTestId(`tenant-created-${AURORA.id}`);
    expect(dateCell.textContent).toBe(asDate(AURORA.created_at));
    expect(dateCell.textContent).not.toMatch(/\d:\d/);

    // An inactive tenant's badge differs from an active one's.
    const aguas = within(screen.getByTestId(`tenant-row-${AGUAS.id}`));
    expect(aguas.getByText(t("tenantsAdmin.inactiveBadge"))).toBeInTheDocument();
    expect(aguas.queryByText(t("tenantsAdmin.activeBadge"))).toBeNull();
  });

  it("filters by name and by slug, and narrows by status", async () => {
    const user = userEvent.setup();
    renderPage();

    const filter = await screen.findByLabelText(t("tenantsAdmin.filterLabel"));

    await user.type(filter, "aurora");
    expect(screen.getByTestId(`tenant-row-${AURORA.id}`)).toBeInTheDocument();
    expect(screen.queryByTestId(`tenant-row-${SERRA.id}`)).toBeNull();

    // The slug arm: "altos-da" appears in the slug and in no tenant's name.
    await user.clear(filter);
    await user.type(filter, "altos-da");
    expect(screen.getByTestId(`tenant-row-${SERRA.id}`)).toBeInTheDocument();
    expect(screen.queryByTestId(`tenant-row-${AURORA.id}`)).toBeNull();

    await user.clear(filter);
    const status = screen.getByLabelText(t("tenantsAdmin.statusLabel"));
    await user.selectOptions(status, "inactive");
    expect(screen.getByTestId(`tenant-row-${AGUAS.id}`)).toBeInTheDocument();
    expect(screen.queryByTestId(`tenant-row-${AURORA.id}`)).toBeNull();

    await user.selectOptions(status, "active");
    expect(screen.queryByTestId(`tenant-row-${AGUAS.id}`)).toBeNull();
    expect(screen.getByTestId(`tenant-row-${AURORA.id}`)).toBeInTheDocument();
    expect(screen.getByTestId(`tenant-row-${SERRA.id}`)).toBeInTheDocument();
  });

  it("shows the filter empty state, the load error and the empty installation", async () => {
    const user = userEvent.setup();
    const { unmount } = renderPage();

    await user.type(
      await screen.findByLabelText(t("tenantsAdmin.filterLabel")),
      "nenhum condomínio se chama assim",
    );
    expect(screen.getByText(t("tenantsAdmin.noResults"))).toBeInTheDocument();
    unmount();

    answerList([]);
    const { unmount: unmountEmpty } = renderPage();
    expect(await screen.findByText(t("tenantsAdmin.empty"))).toBeInTheDocument();
    unmountEmpty();

    mockedGet.mockImplementation((() =>
      Promise.reject(new Error("500"))) as never);
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      t("tenantsAdmin.loadError"),
    );
  });
});

describe("TenantsAdminPage creation", () => {
  it("posts { name } only, shows the slug from the response and invalidates ['tenants']", async () => {
    const created = {
      id: "t-new",
      name: "Residencial Altos da Serra VI",
      slug: "residencial-altos-da-serra-vi-2",
      is_active: true,
      created_at: "2026-09-21T09:00:00",
    };
    mockedPost.mockResolvedValue({ data: created } as never);
    const user = userEvent.setup();
    const { client } = renderPage();
    const invalidate = vi.spyOn(client, "invalidateQueries");

    await openForm(user);
    await user.type(
      screen.getByLabelText(t("tenantsAdmin.nameLabel")),
      created.name,
    );
    await user.click(
      screen.getByRole("button", { name: t("tenantsAdmin.submit") }),
    );

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1));
    const [url, body] = mockedPost.mock.calls[0];
    expect(url).toBe("/tenants");
    // `{ name }` and nothing else: `TenantCreate` has no `slug` field and
    // `is_active` is the backend's default (D1, D5).
    expect(body).toEqual({ name: created.name });

    // The slug is read from the 201 body, never derived in the client (D2).
    expect(
      await screen.findByText(created.slug),
    ).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["tenants"] });
  });

  it("renders the translated duplicate-name message on 409 and keeps the dialog open", async () => {
    mockedPost.mockRejectedValue({
      response: { status: 409, data: { detail: "Tenant already exists" } },
    } as never);
    const user = userEvent.setup();
    const { client } = renderPage();
    const invalidate = vi.spyOn(client, "invalidateQueries");

    await openForm(user);
    const field = screen.getByLabelText(t("tenantsAdmin.nameLabel"));
    await user.type(field, "Condomínio Padrão");
    await user.click(
      screen.getByRole("button", { name: t("tenantsAdmin.submit") }),
    );

    expect(
      await screen.findByText(t("tenantsAdmin.duplicateName")),
    ).toBeInTheDocument();
    // Not the backend's English `detail` string (D6).
    expect(screen.queryByText("Tenant already exists")).toBeNull();
    // The dialog stays open with the typed value, and the list is not reloaded.
    expect(screen.getByLabelText(t("tenantsAdmin.nameLabel"))).toHaveValue(
      "Condomínio Padrão",
    );
    expect(invalidate).not.toHaveBeenCalled();
    expect(mockedGet).toHaveBeenCalledTimes(1);
  });

  it("falls back to the generic message on any other failure", async () => {
    mockedPost.mockRejectedValue({ response: { status: 500 } } as never);
    const user = userEvent.setup();
    renderPage();

    await openForm(user);
    await user.type(
      screen.getByLabelText(t("tenantsAdmin.nameLabel")),
      "Condomínio Torto",
    );
    await user.click(
      screen.getByRole("button", { name: t("tenantsAdmin.submit") }),
    );

    expect(
      await screen.findByText(t("tenantsAdmin.genericError")),
    ).toBeInTheDocument();
  });

  it("disables submit for an empty name and while the mutation is pending", async () => {
    let resolvePost: ((value: unknown) => void) | undefined;
    mockedPost.mockReturnValue(
      new Promise((resolve) => {
        resolvePost = resolve;
      }) as never,
    );
    const user = userEvent.setup();
    renderPage();

    await openForm(user);
    const submit = screen.getByRole("button", {
      name: t("tenantsAdmin.submit"),
    });
    expect(submit).toBeDisabled();

    await user.type(
      screen.getByLabelText(t("tenantsAdmin.nameLabel")),
      "Condomínio Novo",
    );
    expect(submit).toBeEnabled();

    await user.click(submit);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: t("tenantsAdmin.submitting") }),
      ).toBeDisabled(),
    );

    resolvePost?.({
      data: {
        id: "t-novo",
        name: "Condomínio Novo",
        slug: "condominio-novo",
        is_active: true,
        created_at: "2026-09-21T09:00:00",
      },
    });
    expect(await screen.findByText("condominio-novo")).toBeInTheDocument();
  });

  it("copies the created slug and closes the success panel", async () => {
    const created = {
      id: "t-new",
      name: "Condomínio Novo",
      slug: "condominio-novo",
      is_active: true,
      created_at: "2026-09-21T09:00:00",
    };
    mockedPost.mockResolvedValue({ data: created } as never);
    const user = userEvent.setup();
    // After `setup()`: user-event installs its own clipboard stub, so a
    // spy defined before it would be the one that gets replaced.
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    renderPage();

    await openForm(user);
    await user.type(
      screen.getByLabelText(t("tenantsAdmin.nameLabel")),
      created.name,
    );
    await user.click(
      screen.getByRole("button", { name: t("tenantsAdmin.submit") }),
    );

    await user.click(
      await screen.findByRole("button", { name: t("tenantsAdmin.copy") }),
    );
    expect(writeText).toHaveBeenCalledWith(created.slug);

    await user.click(
      screen.getByRole("button", { name: t("tenantsAdmin.backToList") }),
    );
    expect(screen.queryByText(t("tenantsAdmin.createdTitle"))).toBeNull();
  });

  it("closes the form without posting when the operator cancels", async () => {
    const user = userEvent.setup();
    renderPage();

    await openForm(user);
    await user.click(
      screen.getByRole("button", { name: t("tenantsAdmin.cancel") }),
    );

    expect(screen.queryByLabelText(t("tenantsAdmin.nameLabel"))).toBeNull();
    expect(mockedPost).not.toHaveBeenCalled();
  });
});

describe("/admin/tenants access", () => {
  const mockAuth = (user: Partial<User>) => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: user as User,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn() as never,
      logout: vi.fn(),
    });
  };

  const renderRoute = () =>
    render(
      <QueryClientProvider client={newClient()}>
        <MemoryRouter initialEntries={["/admin/tenants"]}>
          <Routes>
            <Route
              path="/admin/tenants"
              element={
                <ProtectedRoute
                  requiredAccess={ROUTE_ACCESS["/admin/tenants"]}
                >
                  <TenantsAdminPage />
                </ProtectedRoute>
              }
            />
            <Route path="/dashboard" element={<div>Painel de Tarefas</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

  it("is ruled exactly { superuser: true }", () => {
    expect(ROUTE_ACCESS["/admin/tenants"]).toEqual({ superuser: true });
  });

  it("renders the condominium table for a superuser", async () => {
    mockAuth({ id: "root", is_superuser: true, tenants: [] });

    renderRoute();

    expect(
      await screen.findByTestId(`tenant-row-${AURORA.id}`),
    ).toBeInTheDocument();
    expect(screen.queryByText("Acesso restrito")).toBeNull();
  });

  it("renders RestrictedAccessMessage in place for a whole-catalogue non-superuser", async () => {
    // A tenant_admin holds every catalogue string and still gets 403 from
    // `POST /tenants`, so the screen must refuse them — in place, with no
    // navigation: `/dashboard` is mounted above and must never render.
    mockAuth({ id: "u-tenant-admin", is_superuser: false, tenants: [] });
    vi.mocked(useMyPermissions).mockReturnValue(
      settledPermissions(ALL_PERMISSIONS) as never,
    );

    renderRoute();

    expect(await screen.findByText("Acesso restrito")).toBeInTheDocument();
    expect(screen.queryByText("Painel de Tarefas")).toBeNull();
    expect(screen.queryByTestId(`tenant-row-${AURORA.id}`)).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
  });
});
