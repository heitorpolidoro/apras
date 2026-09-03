import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import RoleDetailPage from "../pages/RoleDetailPage";
import apiClient from "../../../api/client";
import * as AuthHook from "../context/AuthContext";

/** `/admin/roles/:roleId` (APRAS-48 §6.3, ER-1 and ER-4). */
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
  "roles:update",
];

const CUSTOM_ROLE = {
  id: "g-custom",
  name: "Conselho Fiscal",
  permissions: ["finance:read"],
};

const mockedGet = vi.mocked(apiClient.get);
const mockedPatch = vi.mocked(apiClient.patch);

let roles: unknown[] = [];

const install = () => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/roles/") return Promise.resolve({ data: roles });
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

const renderDetail = (roleId = "g-custom") => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/admin/roles/${roleId}`]}>
        <Routes>
          <Route path="/admin/roles/:roleId" element={<RoleDetailPage />} />
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
  roles = [CUSTOM_ROLE];
  vi.spyOn(AuthHook, "useAuth").mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: { id: "admin", is_superuser: true } as never,
    login: vi.fn() as never,
    logout: vi.fn(),
  });
  install();
  mockedPatch.mockResolvedValue({ data: CUSTOM_ROLE } as never);
});

describe("RoleDetailPage", () => {
  it("roles the checkboxes by module", async () => {
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
    roles = [{ ...CUSTOM_ROLE, permissions: ["finance:read", "tasks:delete"] }];
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
    expect(url).toBe("/roles/g-custom");
    // Resent unchanged: editing a name never strips what the author cannot grant.
    expect(body.permissions).toContain("tasks:delete");
    expect(body.permissions).toContain("finance:read");
  });

  it("opens a role whose bundle field is absent with nothing selected", async () => {
    // `permissions` is optional on `Role` so every pre-F2 fixture keeps
    // type-checking; the editor must treat its absence as an empty bundle
    // rather than crash on `.includes`.
    roles = [{ id: "g-custom", name: "Sem bundle" }];
    renderDetail();

    await waitFor(() => expect(box("finance:read")).not.toBeNull());
    expect(box("finance:read")!.checked).toBe(false);
  });

  it("offers the landing-path control and round-trips its value (§10.4)", async () => {
    // The feature §10.4 promises and the hard-coded enum switch never had:
    // an operator decides where a role's members land. It is *always* sent,
    // and `null` when "none" is picked — which is why the backend reads
    // `model_fields_set` rather than a `None` sentinel: an explicit null has
    // to stay distinguishable from an absent field (CR1).
    roles = [{ ...CUSTOM_ROLE, landing_path: "/gate" }];
    renderDetail();

    const select = (await screen.findByLabelText(
      "Página inicial do papel",
    )) as HTMLSelectElement;
    expect(select.value).toBe("/gate");

    await userEvent.selectOptions(select, "/welcome");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalled());
    const [, body] = mockedPatch.mock.calls[0] as [
      string,
      { landing_path: string | null },
    ];
    expect(body.landing_path).toBe("/welcome");
  });

  it("sends an explicit null when the operator clears the landing path", async () => {
    roles = [{ ...CUSTOM_ROLE, landing_path: "/gate" }];
    renderDetail();

    const select = (await screen.findByLabelText(
      "Página inicial do papel",
    )) as HTMLSelectElement;
    await userEvent.selectOptions(select, "");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalled());
    const [, body] = mockedPatch.mock.calls[0] as [
      string,
      { landing_path: string | null },
    ];
    expect(body.landing_path).toBeNull();
  });

  it("offers only the allowlisted paths, so the control cannot mint a redirect", async () => {
    renderDetail();

    const select = (await screen.findByLabelText(
      "Página inicial do papel",
    )) as HTMLSelectElement;
    expect([...select.options].map((option) => option.value)).toEqual([
      "",
      "/dashboard",
      "/gate",
      "/welcome",
      "/announcements",
      "/occurrences",
    ]);
  });

  it("sends no allowed_menus at all (IAM F5 §4.1)", async () => {
    // F4's editor derived the two legacy menu keys from the selected
    // permissions and sent them **unioned with the stored value**, so that a
    // rename could not silently revoke a role's backend menu access. The
    // column is gone, so the derivation goes with it — hand-off item 5 of
    // F4's list, and the one a grep almost misses.
    renderDetail();

    await waitFor(() => expect(box("tasks:read")).not.toBeNull());
    await userEvent.click(box("tasks:read")!);
    await userEvent.click(box("categories:read")!);
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalled());
    const [, body] = mockedPatch.mock.calls[0] as [
      string,
      Record<string, unknown>,
    ];
    expect(body).not.toHaveProperty("allowed_menus");
    expect(body.permissions).toEqual(
      expect.arrayContaining(["tasks:read", "categories:read"]),
    );
  });

  it("lets a historically-named role be renamed like any other", async () => {
    // The inversion (§13): the `role` column that made `Diretor (papel)`
    // read-only is gone, so the name field is an ordinary input and the
    // "Papel legado" badge has nothing left to mark.
    roles = [
      {
        id: "g-role",
        name: "Diretor (papel)",
        permissions: [],
      },
    ];
    renderDetail("g-role");

    await waitFor(() => expect(box("finance:read")).not.toBeNull());
    const input = screen.getByLabelText("Nome") as HTMLInputElement;
    expect(input.readOnly).toBe(false);
    expect(screen.queryByText("Papel legado")).toBeNull();

    await userEvent.clear(input);
    await userEvent.type(input, "Conselho");
    await userEvent.click(box("finance:read")!);
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalled());
    const [, body] = mockedPatch.mock.calls[0] as [
      string,
      { name: string; permissions: string[] },
    ];
    expect(body.name).toBe("Conselho");
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

  it("shows a friendly 403 and answers a missing role with a message", async () => {
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

  it("renders a not-found message for an unknown role id", async () => {
    renderDetail("g-missing");

    expect(await screen.findByText("Papel não encontrado.")).toBeInTheDocument();
  });
});
