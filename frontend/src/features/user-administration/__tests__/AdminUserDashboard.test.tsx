import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminUserDashboard from "../pages/AdminUserDashboard";
import * as AuthHook from "../context/AuthContext";
import { UserRole } from "../context/AuthContext";
import apiClient from "../../../api/client";

vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}));

const mockCurrentUser = {
  id: "admin-1",
  username: "admin",
  email: "admin@example.com",
  full_name: "Admin User",
  role: UserRole.ADMINISTRATOR,
  is_active: true,
};

const mockUserTypes = [
  { id: "type-1", name: "Manager" },
  { id: "type-2", name: "Employee" },
];

const mockUsers = [
  {
    id: "user-1",
    username: "user1",
    email: "user1@example.com",
    full_name: "User One",
    role: UserRole.DIRECTOR,
    is_active: true,
  },
  {
    id: "user-2",
    username: "user2",
    email: "user2@example.com",
    full_name: "User Two",
    role: UserRole.ADMINISTRATOR,
    is_active: false,
  },
];

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe("AdminUserDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: mockCurrentUser,
      login: vi.fn() as any,
      logout: vi.fn(),
    });
  });

  it("renders loading state initially", () => {
    (apiClient.get as any).mockImplementation(() => new Promise(() => {}));

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    expect(screen.getByText("Carregando usuários...")).toBeDefined();
  });

  it("renders error state when fetch fails", async () => {
    (apiClient.get as any).mockRejectedValue(new Error("Network error"));

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Erro ao carregar usuários.")).toBeDefined();
    });
  });

  it("renders user table with users", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
      expect(screen.getByText("User Two")).toBeDefined();
    });

    expect(screen.getByText("user1@example.com")).toBeDefined();
    expect(screen.getByText("Gerenciamento de Usuários")).toBeDefined();
  });

  it("filters by active status", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
    });

    const select = screen.getByRole("combobox", { name: /Filtrar por status/i });
    fireEvent.change(select, { target: { value: "active" } });

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith("/users/", {
        params: { is_active: true },
      });
    });
  });

  it("filters by inactive status", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
    });

    const select = screen.getByRole("combobox", { name: /Filtrar por status/i });
    fireEvent.change(select, { target: { value: "inactive" } });

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith("/users/", {
        params: { is_active: false },
      });
    });
  });

  it("toggles user active status", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockResolvedValue({
      data: { ...mockUsers[0], is_active: false },
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
    });

    const desativarButtons = screen.getAllByText("Desativar");
    fireEvent.click(desativarButtons[0]);

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith("/users/user-1", {
        is_active: false,
      });
    });
  });

  it("approves an inactive user", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockResolvedValue({
      data: { ...mockUsers[1], is_active: true },
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User Two")).toBeDefined();
    });

    const aprovarButton = screen.getByText("Aprovar");
    fireEvent.click(aprovarButton);

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith("/users/user-2", {
        is_active: true,
      });
    });
  });

  it("prevents current user from deactivating their own account", async () => {
    const usersWithCurrentUser = [{ ...mockCurrentUser }, ...mockUsers];
    (apiClient.get as any).mockResolvedValue({ data: usersWithCurrentUser });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Admin User")).toBeDefined();
    });

    const desativarButtons = screen.getAllByText("Desativar");
    fireEvent.click(desativarButtons[0]);

    await waitFor(() => {
      expect(
        screen.getByText("Você não pode desativar sua própria conta."),
      ).toBeDefined();
    });
    expect(apiClient.patch).not.toHaveBeenCalled();
  });

  it("shows alert on mutation error", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockRejectedValue({
      response: { data: { detail: "Permission denied" } },
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
    });

    const desativarButtons = screen.getAllByText("Desativar");
    fireEvent.click(desativarButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Permission denied")).toBeDefined();
    });
  });

  it("shows generic alert when mutation error has no detail", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockRejectedValue(new Error("Network error"));

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
    });

    const desativarButtons = screen.getAllByText("Desativar");
    fireEvent.click(desativarButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Erro ao atualizar usuário")).toBeDefined();
    });
  });

  it("calls logout when Sair button is clicked", async () => {
    const mockLogout = vi.fn();
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: mockCurrentUser,
      login: vi.fn() as any,
      logout: mockLogout,
    });

    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
    });

    fireEvent.click(screen.getByText("Sair"));
    expect(mockLogout).toHaveBeenCalledOnce();
  });

  it("closes the error alert when close button is clicked", async () => {
    const usersWithCurrentUser = [{ ...mockCurrentUser }, ...mockUsers];
    (apiClient.get as any).mockResolvedValue({ data: usersWithCurrentUser });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Admin User")).toBeDefined();
    });

    // Trigger an error
    const desativarButtons = screen.getAllByText("Desativar");
    fireEvent.click(desativarButtons[0]);

    await waitFor(() => {
      expect(
        screen.getByText("Você não pode desativar sua própria conta."),
      ).toBeDefined();
    });

    // Click OK button on the AlertModal to close it
    const okButton = screen.getByRole("button", { name: "OK" });
    fireEvent.click(okButton);

    expect(
      screen.queryByText("Você não pode desativar sua própria conta."),
    ).toBeNull();
  });

  // ── User type badge & empty list ────────────────────────────────────────

  it("renders user type badge when user has a type", async () => {
    const usersWithType = [{ ...mockUsers[0], user_types: [{ id: "type-1", name: "Manager" }] }];
    (apiClient.get as any).mockResolvedValue({ data: usersWithType });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Manager")).toBeInTheDocument();
    });
  });

  it("opens edit modal when Edit button is clicked", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);

    expect(screen.getByText("Editar Usuário")).toBeInTheDocument();
  });

  it("pre-fills full name and closes on Cancel", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    expect(screen.getByDisplayValue("User One")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancelar"));
    expect(screen.queryByText("Editar Usuário")).toBeNull();
  });

  it("closes edit modal when backdrop is clicked", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers }); // skipcq: JS-0323

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    expect(screen.getByText("Editar Usuário")).toBeInTheDocument();

    const backdrop = document.querySelector(".fixed.inset-0.z-50") as HTMLElement;
    fireEvent.click(backdrop);

    expect(screen.queryByText("Editar Usuário")).toBeNull();
  });

  it("closes edit modal when Escape key is pressed on backdrop", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers }); // skipcq: JS-0323

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    expect(screen.getByText("Editar Usuário")).toBeInTheDocument();

    const backdrop = document.querySelector(".fixed.inset-0.z-50") as HTMLElement;
    fireEvent.keyDown(backdrop, { key: "Tab" });
    expect(screen.getByText("Editar Usuário")).toBeInTheDocument();

    fireEvent.keyDown(backdrop, { key: "Escape" });
    expect(screen.queryByText("Editar Usuário")).toBeNull();
  });

  it("updates full name in modal input", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);

    const nameInput = screen.getByDisplayValue("User One");
    fireEvent.change(nameInput, { target: { value: "User One Updated" } });
    expect((nameInput as HTMLInputElement).value).toBe("User One Updated");
  });

  it("changes user types in modal checklist", async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);

    const checkbox = screen.getByLabelText("Manager") as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });

  it("saves edit with updated full name", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockResolvedValue({ data: mockUsers[0] });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    fireEvent.change(screen.getByDisplayValue("User One"), {
      target: { value: "User One Updated" },
    });
    fireEvent.click(screen.getByText("Salvar"));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        "/users/user-1",
        expect.objectContaining({ full_name: "User One Updated" }),
      );
    });
  });

  it("saves edit with empty full name (omits the field)", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockResolvedValue({ data: mockUsers[0] });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    fireEvent.change(screen.getByDisplayValue("User One"), { target: { value: "" } });
    fireEvent.click(screen.getByText("Salvar"));

    // `useSetUserGroups` omits `full_name` rather than sending it as
    // `undefined`; the two are byte-identical on the wire (JSON drops it), and
    // `UserUpdate.full_name` is optional, so the backend behaviour is the same.
    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith("/users/user-1", {
        user_type_ids: [],
      });
    });
  });

  it("pre-fills type checkboxes when user has types", async () => {
    const userWithType = { ...mockUsers[0], user_types: [{ id: "type-1", name: "Manager" }] };
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: [userWithType, mockUsers[1]] });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);

    const checkbox = screen.getByLabelText("Manager") as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  // ── IAM F4 (APRAS-48 §7) ────────────────────────────────────────────────

  it("renders no role select at all: the write surface for user.role is gone", async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());
    expect(screen.queryAllByLabelText("Cargo")).toHaveLength(0);
    expect(screen.queryAllByRole("combobox", { name: "Cargo" })).toHaveLength(0);
  });

  it("shows the role read-only under the legacy column heading", async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());
    expect(screen.getByText("Cargo (legado)")).toBeInTheDocument();
    expect(screen.getByText(UserRole.DIRECTOR)).toBeInTheDocument();
  });

  it("links to /admin/groups instead of editing groups inline", async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());
    expect(
      screen.getByRole("link", { name: "Gerenciar grupos" }),
    ).toHaveAttribute("href", "/admin/groups");
    // The inline create-a-type form is gone with it.
    expect(screen.queryByPlaceholderText("Nome do grupo")).toBeNull();
  });

  it("heads the edit modal's checkbox list with admin.editGroups", async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());
    fireEvent.click(screen.getAllByText("Editar")[0]);

    expect(screen.getByText("Grupos")).toBeInTheDocument();
  });

  it("never sends role in the edit-user PATCH", async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });
    (apiClient.patch as any).mockResolvedValue({ data: {} });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());
    fireEvent.click(screen.getAllByText("Editar")[0]);
    fireEvent.click(screen.getByText("Salvar"));

    await waitFor(() => expect(apiClient.patch).toHaveBeenCalled());
    const [, body] = (apiClient.patch as any).mock.calls[0];
    expect(body).not.toHaveProperty("role");
    expect(body).toHaveProperty("user_type_ids");
  });
});
