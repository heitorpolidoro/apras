import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GroupDetailPage from "../pages/GroupDetailPage";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";
import { UserRole } from "../../../types/auth";

/** `/admin/groups/:groupId` (APRAS-48 §6.3, ER-1 and ER-4). */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const CATALOGUE = [
  { permission: "categories:read", module: "categories", action: "read", superuser_only: false },
  { permission: "finance:read", module: "finance", action: "read", superuser_only: false },
  { permission: "finance:transaction_create", module: "finance", action: "transaction_create", superuser_only: false },
  { permission: "tasks:read", module: "tasks", action: "read", superuser_only: false },
  { permission: "tasks:delete", module: "tasks", action: "delete", superuser_only: false },
  { permission: "tenants:create", module: "tenants", action: "create", superuser_only: true },
  { permission: "tenants:update", module: "tenants", action: "update", superuser_only: true },
  { permission: "tenants:members_manage", module: "tenants", action: "members_manage", superuser_only: true },
  { permission: "tenants:members_set_admin", module: "tenants", action: "members_set_admin", superuser_only: true },
];

/** What the *author* holds — the mirror of `assert_can_grant`. */
const MY_PERMISSIONS = [
  "categories:read",
  "finance:read",
  "tasks:read",
  "user_types:update",
];

const CUSTOM_GROUP = {
  id: "g-custom",
  name: "Conselho Fiscal",
  allowed_menus: [] as string[],
  role: null,
  permissions: ["finance:read"],
};

const mockedGet = vi.mocked(apiClient.get);
const mockedPatch = vi.mocked(apiClient.patch);

let groups: unknown[] = [];

const install = () => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/user-types/") return Promise.resolve({ data: groups });
    if (url === "/permissions/") return Promise.resolve({ data: CATALOGUE });
    if (url === "/permissions/me") {
      return Promise.resolve({
        data: { tenant_id: "t-1", permissions: MY_PERMISSIONS },
      });
    }
    if (url === "/users/") return Promise.resolve({ data: [] });
    return Promise.resolve({ data: [] });
  }) as never);
};

const renderDetail = (groupId = "g-custom") => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/admin/groups/${groupId}`]}>
        <Routes>
          <Route path="/admin/groups/:groupId" element={<GroupDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

const box = (permission: string) =>
  document.querySelector<HTMLInputElement>(
    `input[data-permission="${permission}"]`,
  );

beforeEach(() => {
  vi.clearAllMocks();
  groups = [CUSTOM_GROUP];
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: { id: "admin", role: UserRole.ADMINISTRATOR } as never,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  install();
  mockedPatch.mockResolvedValue({ data: CUSTOM_GROUP } as never);
});

describe("GroupDetailPage", () => {
  it("groups the checkboxes by module", async () => {
    renderDetail();

    await waitFor(() => expect(box("finance:read")).not.toBeNull());
    const fieldset = document.querySelector<HTMLFieldSetElement>(
      'fieldset[data-module="finance"]',
    );
    expect(fieldset).not.toBeNull();
    expect(within(fieldset!).getByText("Financeiro")).toBeInTheDocument();
    // Both finance permissions live in that one fieldset, and nothing else does.
    expect(
      fieldset!.querySelectorAll("input[data-permission]"),
    ).toHaveLength(2);
    expect(
      document.querySelector('fieldset[data-module="tasks"]'),
    ).not.toBeNull();
  });

  it("disables permissions the author does not hold", async () => {
    renderDetail();

    await waitFor(() => expect(box("finance:read")).not.toBeNull());
    // Held → enabled.
    expect(box("finance:read")!.disabled).toBe(false);
    expect(box("tasks:read")!.disabled).toBe(false);
    // Not held → disabled, with the explaining title.
    expect(box("finance:transaction_create")!.disabled).toBe(true);
    expect(box("tasks:delete")!.disabled).toBe(true);
    expect(box("tasks:delete")!.title).toBe(
      "Você não pode conceder uma permissão que não possui.",
    );
  });

  it("disables the four superuser-only permissions", async () => {
    renderDetail();

    await waitFor(() => expect(box("tenants:create")).not.toBeNull());
    for (const permission of [
      "tenants:create",
      "tenants:update",
      "tenants:members_manage",
      "tenants:members_set_admin",
    ]) {
      expect(box(permission)!.disabled).toBe(true);
      expect(box(permission)!.title).toBe(
        "Somente o superusuário da instalação concede esta permissão.",
      );
    }
  });

  it("keeps an already-granted permission the author cannot grant checked and resends it", async () => {
    // Stored with a permission the author does NOT hold.
    groups = [{ ...CUSTOM_GROUP, permissions: ["finance:read", "tasks:delete"] }];
    renderDetail();

    await waitFor(() => expect(box("tasks:delete")).not.toBeNull());
    expect(box("tasks:delete")!.checked).toBe(true);
    expect(box("tasks:delete")!.disabled).toBe(true);

    // Only the name changes.
    await userEvent.clear(screen.getByLabelText("Nome"));
    await userEvent.type(screen.getByLabelText("Nome"), "Novo nome");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalled());
    const [url, body] = mockedPatch.mock.calls[0] as [string, { permissions: string[] }];
    expect(url).toBe("/user-types/g-custom");
    // Resent unchanged: editing a name never strips what the author cannot grant.
    expect(body.permissions).toContain("tasks:delete");
    expect(body.permissions).toContain("finance:read");
  });

  it("derives allowed_menus from the selected permissions on save", async () => {
    renderDetail();

    await waitFor(() => expect(box("tasks:read")).not.toBeNull());
    await userEvent.click(box("tasks:read")!);
    await userEvent.click(box("categories:read")!);
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalled());
    const [, body] = mockedPatch.mock.calls[0] as [
      string,
      { allowed_menus: string[]; permissions: string[] },
    ];
    expect(body.allowed_menus).toEqual(["categories", "tasks"]);
    expect(body.permissions).toEqual(
      expect.arrayContaining(["tasks:read", "categories:read"]),
    );
  });

  it("never revokes a menu key the group already had", async () => {
    // §2.3: stored with `allowed_menus: ["tasks"]` and zero `tasks:*`
    // permissions — the state of every operator-configured group today.
    groups = [
      { ...CUSTOM_GROUP, allowed_menus: ["tasks"], permissions: ["finance:read"] },
    ];
    renderDetail();

    await waitFor(() => expect(box("finance:read")).not.toBeNull());
    await userEvent.clear(screen.getByLabelText("Nome"));
    await userEvent.type(screen.getByLabelText("Nome"), "Renomeado");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalled());
    const [, body] = mockedPatch.mock.calls[0] as [
      string,
      { allowed_menus: string[] },
    ];
    expect(body.allowed_menus).toEqual(["tasks"]);
  });

  it("blocks renaming a role-linked group", async () => {
    groups = [
      {
        id: "g-role",
        name: "Diretor (papel)",
        allowed_menus: [],
        role: UserRole.DIRECTOR,
        permissions: [],
      },
    ];
    renderDetail("g-role");

    await waitFor(() => expect(box("finance:read")).not.toBeNull());
    const input = screen.getByLabelText("Nome") as HTMLInputElement;
    expect(input.readOnly).toBe(true);
    expect(screen.getByText("Grupo de papel (legado)")).toBeInTheDocument();

    // Its permissions stay editable — that is why the row is shown at all.
    expect(box("finance:read")!.disabled).toBe(false);
    await userEvent.click(box("finance:read")!);
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalled());
    const [, body] = mockedPatch.mock.calls[0] as [
      string,
      { name: string; permissions: string[] },
    ];
    expect(body.name).toBe("Diretor (papel)");
    expect(body.permissions).toEqual(["finance:read"]);
  });

  it("marks and clears a whole module without touching its locked boxes", async () => {
    renderDetail();

    await waitFor(() => expect(box("finance:read")).not.toBeNull());
    const fieldset = document.querySelector<HTMLFieldSetElement>(
      'fieldset[data-module="finance"]',
    )!;
    await userEvent.click(
      within(fieldset).getByRole("button", { name: "Marcar todos" }),
    );
    expect(box("finance:read")!.checked).toBe(true);
    expect(box("finance:transaction_create")!.checked).toBe(false);

    await userEvent.click(
      within(fieldset).getByRole("button", { name: "Desmarcar todos" }),
    );
    expect(box("finance:read")!.checked).toBe(false);
  });

  it("shows a friendly 403 and answers a missing group with a message", async () => {
    mockedPatch.mockRejectedValue({
      response: {
        status: 403,
        data: {
          detail:
            "These permissions are granted by is_superuser only: tenants:create",
        },
      },
    } as never);
    renderDetail();

    await waitFor(() => expect(box("finance:read")).not.toBeNull());
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Criar");
    expect(alert.textContent).not.toContain("is_superuser only");
  });

  it("renders a not-found message for an unknown group id", async () => {
    renderDetail("g-missing");

    expect(await screen.findByText("Grupo não encontrado.")).toBeInTheDocument();
  });
});
