import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import GroupsAdminPage from "../pages/GroupsAdminPage";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { UserRole } from "../../../types/auth";
import { CANNOT_GRANT_PREFIX } from "../utils/permissionErrors";

/** `/admin/groups` (APRAS-48 §6.1, ER-1). */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const GROUPS = [
  {
    id: "g-custom",
    name: "Conselho Fiscal",
    allowed_menus: ["tasks"],
    role: null,
    permissions: ["finance:read", "finance:summary_read"],
  },
  {
    id: "g-role",
    name: "Diretor (papel)",
    allowed_menus: [],
    role: UserRole.DIRECTOR,
    permissions: ["tasks:read"],
  },
];

const USERS = [
  {
    id: "u-1",
    email: "a@test.com",
    full_name: "Ana",
    role: UserRole.RESIDENT,
    is_active: true,
    user_types: [GROUPS[0]],
  },
  {
    id: "u-2",
    email: "b@test.com",
    full_name: "Bruno",
    role: UserRole.RESIDENT,
    is_active: true,
    user_types: [],
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
    user: { id: "admin", role: UserRole.ADMINISTRATOR } as never,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/user-types/") return Promise.resolve({ data: GROUPS });
    if (url === "/users/") return Promise.resolve({ data: USERS });
    return Promise.resolve({ data: [] });
  }) as never);
});

const renderPage = () => render(<GroupsAdminPage />, { wrapper: wrapper() });

describe("GroupsAdminPage", () => {
  it("lists groups with their permission and member counts", async () => {
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

  it("marks role-linked groups and offers no delete control", async () => {
    renderPage();

    await screen.findByText("Diretor (papel)");
    expect(screen.getByText("Grupo de papel (legado)")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Excluir Diretor (papel)" }),
    ).toBeNull();
    // The ordinary group keeps its delete control.
    expect(
      screen.getByRole("button", { name: "Excluir Conselho Fiscal" }),
    ).toBeInTheDocument();
  });

  it("creates a group", async () => {
    mockedPost.mockResolvedValue({ data: { id: "g-new" } } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.type(screen.getByLabelText("Nome do grupo"), "Zeladoria");
    await userEvent.click(screen.getByRole("button", { name: "Criar" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/user-types/", {
        name: "Zeladoria",
        permissions: [],
        allowed_menus: [],
      }),
    );
  });

  it("clones a group with its permission bundle pre-filled", async () => {
    mockedPost.mockResolvedValue({ data: { id: "g-clone" } } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.click(
      screen.getByRole("button", { name: "Clonar Conselho Fiscal" }),
    );

    const input = screen.getByLabelText("Nome do grupo") as HTMLInputElement;
    expect(input.value).toBe("Conselho Fiscal (cópia)");

    await userEvent.click(screen.getByRole("button", { name: "Criar" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/user-types/", {
        name: "Conselho Fiscal (cópia)",
        // The source's bundle, verbatim; the clone carries no `role`.
        permissions: ["finance:read", "finance:summary_read"],
        allowed_menus: [],
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

    await userEvent.type(screen.getByLabelText("Nome do grupo"), "Zeladoria");
    await userEvent.click(screen.getByRole("button", { name: "Criar" }));

    const alert = await screen.findByRole("alert");
    // Localised, and by the permission's *label*, never the raw sentence.
    expect(alert).toHaveTextContent("Ver");
    expect(alert.textContent).not.toContain(CANNOT_GRANT_PREFIX);
  });

  it("confirms before deleting a group, and does nothing when cancelled", async () => {
    const confirm = vi
      .spyOn(window, "confirm")
      .mockReturnValue(false);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.click(
      screen.getByRole("button", { name: "Excluir Conselho Fiscal" }),
    );

    expect(confirm).toHaveBeenCalledWith(
      "Excluir este grupo? Os usuários perdem as permissões que ele concede.",
    );
    // Deleting a group revokes permissions from every member at once, so a
    // declined confirmation must not reach the API at all.
    expect(mockedDelete).not.toHaveBeenCalled();
  });

  it("deletes the group once the confirmation is accepted", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockedDelete.mockResolvedValue({ data: undefined } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.click(
      screen.getByRole("button", { name: "Excluir Conselho Fiscal" }),
    );

    await waitFor(() =>
      expect(mockedDelete).toHaveBeenCalledWith("/user-types/g-custom"),
    );
  });

  it("shows a friendly message when deleting a role-linked group is refused", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockedDelete.mockRejectedValue({
      response: {
        status: 403,
        data: { detail: "Role-linked user types cannot be deleted" },
      },
    } as never);
    renderPage();
    await screen.findByText("Conselho Fiscal");

    await userEvent.click(
      screen.getByRole("button", { name: "Excluir Conselho Fiscal" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Role-linked user types cannot be deleted",
    );
  });

  it("renders the empty state when there is no group at all", async () => {
    mockedGet.mockImplementation(((url: string) =>
      url === "/user-types/"
        ? Promise.resolve({ data: [] })
        : Promise.resolve({ data: [] })) as never);

    renderPage();

    expect(await screen.findByText("Nenhum grupo ainda.")).toBeInTheDocument();
  });
});
