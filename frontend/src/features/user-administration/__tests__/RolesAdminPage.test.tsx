import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import RolesAdminPage from "../pages/RolesAdminPage";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { CANNOT_GRANT_PREFIX } from "../utils/permissionErrors";

/** `/admin/roles` (APRAS-48 §6.1, ER-1). */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const ROLES = [
  {
    id: "g-custom",
    name: "Conselho Fiscal",
    role: null,
    permissions: ["finance:read", "finance:summary_read"],
  },
  {
    id: "g-role",
    name: "Diretor (papel)",
    permissions: ["tasks:read"],
  },
];

const USERS = [
  {
    id: "u-1",
    email: "a@test.com",
    full_name: "Ana",
    is_active: true,
    roles: [ROLES[0]],
  },
  {
    id: "u-2",
    email: "b@test.com",
    full_name: "Bruno",
    is_active: true,
    roles: [],
  },
];

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedDelete = vi.mocked(apiClient.delete);

const wrapper = (): React.FC<{ children: React.ReactNode }> => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }) => (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: { id: "admin", is_superuser: true } as never,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/roles/") return Promise.resolve({ data: ROLES });
    if (url === "/users/") return Promise.resolve({ data: USERS });
    return Promise.resolve({ data: [] });
  }) as never);
});

const renderPage = () => render(<RolesAdminPage />, { wrapper: wrapper() });

describe("RolesAdminPage", () => {
  it("lists roles with their permission and member counts", async () => {
    renderPage();

    const row = (await screen.findByText("Conselho Fiscal")).closest("tr");
    expect(row).not.toBeNull();
    // Two permissions, one member (Ana).
    expect(row).toHaveTextContent("2");
    expect(row).toHaveTextContent("1");

    const roleRow = screen.getByText("Diretor (papel)").closest("tr");
    // One permission, zero members.
    expect(roleRow).toHaveTextContent("1");
    expect(roleRow).toHaveTextContent("0");
  });

  it("offers a delete control on every row, historically named or not", async () => {
    // The inversion (IAM F5, APRAS-49 §13): the `role` column that made six
    // rows undeletable is gone, and with it the doctrine of "role-linked
    // types that cannot be deleted or renamed". Deleting `Diretor (papel)`
    // strips every director, and that is the operator's prerogative — so
    // there is no badge to show and no button to withhold.
    renderPage();

    await screen.findByText("Diretor (papel)");
    expect(screen.queryByText("Papel legado")).toBeNull();
    expect(
      screen.getByRole("button", { name: "Excluir Diretor (papel)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Excluir Conselho Fiscal" }),
    ).toBeInTheDocument();
  });

  it("counts an absent bundle as zero permissions", async () => {
    // `permissions` is optional on `Role` so every pre-F2 fixture keeps
    // type-checking; the listing must read its absence as an empty bundle.
    mockedGet.mockImplementation(((url: string) => {
      if (url === "/roles/")
        return Promise.resolve({ data: [{ id: "g-bare", name: "Sem bundle" }] });
      if (url === "/users/") return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    }) as never);
    renderPage();

    await screen.findByText("Sem bundle");
    const row = screen.getByText("Sem bundle").closest("tr")!;
    expect(row.textContent).toContain("0");
  });

  it("creates a role", async () => {
    mockedPost.mockResolvedValue({ data: { id: "g-new" } } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.type(screen.getByLabelText("Nome do papel"), "Zeladoria");
    await userEvent.click(screen.getByRole("button", { name: "Criar" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/roles/", {
        name: "Zeladoria",
        permissions: [],
      }),
    );
  });

  it("clones a role with its permission bundle pre-filled", async () => {
    mockedPost.mockResolvedValue({ data: { id: "g-clone" } } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.click(
      screen.getByRole("button", { name: "Clonar Conselho Fiscal" }),
    );

    const input = screen.getByLabelText("Nome do papel") as HTMLInputElement;
    expect(input.value).toBe("Conselho Fiscal (cópia)");

    await userEvent.click(screen.getByRole("button", { name: "Criar" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/roles/", {
        name: "Conselho Fiscal (cópia)",
        // The source's bundle, verbatim; the clone carries no `role`.
        permissions: ["finance:read", "finance:summary_read"],
      }),
    );
  });

  it("shows a friendly message when the API answers 403", async () => {
    mockedPost.mockRejectedValue({
      response: {
        status: 403,
        data: { detail: `${CANNOT_GRANT_PREFIX}finance:read` },
      },
    } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.type(screen.getByLabelText("Nome do papel"), "Zeladoria");
    await userEvent.click(screen.getByRole("button", { name: "Criar" }));

    const alert = await screen.findByRole("alert");
    // Localised, and by the permission's *label*, never the raw sentence.
    expect(alert).toHaveTextContent("Ver");
    expect(alert.textContent).not.toContain(CANNOT_GRANT_PREFIX);
  });

  it("confirms before deleting a role, and does nothing when cancelled", async () => {
    const confirm = vi
      .spyOn(window, "confirm")
      .mockReturnValue(false);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.click(
      screen.getByRole("button", { name: "Excluir Conselho Fiscal" }),
    );

    expect(confirm).toHaveBeenCalledWith(
      "Excluir este papel? Os usuários perdem as permissões que ele concede.",
    );
    // Deleting a role revokes permissions from every member at once, so a
    // declined confirmation must not reach the API at all.
    expect(mockedDelete).not.toHaveBeenCalled();
  });

  it("deletes the role once the confirmation is accepted", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockedDelete.mockResolvedValue({ data: undefined } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.click(
      screen.getByRole("button", { name: "Excluir Conselho Fiscal" }),
    );

    await waitFor(() =>
      expect(mockedDelete).toHaveBeenCalledWith("/roles/g-custom"),
    );
  });

  it("shows a friendly message when deleting a role-linked role is refused", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockedDelete.mockRejectedValue({
      response: {
        status: 403,
        data: { detail: "Role-linked roles cannot be deleted" },
      },
    } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.click(
      screen.getByRole("button", { name: "Excluir Conselho Fiscal" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Role-linked roles cannot be deleted",
    );
  });

  it("renders the empty state when there is no role at all", async () => {
    mockedGet.mockImplementation(((url: string) =>
      url === "/roles/"
        ? Promise.resolve({ data: [] })
        : Promise.resolve({ data: [] })) as never);

    renderPage();

    expect(await screen.findByText("Nenhum papel ainda.")).toBeInTheDocument();
  });
});
