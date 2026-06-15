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

    expect(screen.getByText("user1")).toBeDefined();
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

  it("changes user role via select", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockResolvedValue({
      data: { ...mockUsers[0], role: UserRole.ADMINISTRATOR },
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
    });

    const roleSelects = screen.getAllByRole("combobox", { name: "Cargo" });
    fireEvent.change(roleSelects[0], { target: { value: UserRole.ADMINISTRATOR } });

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith("/users/user-1", {
        role: UserRole.ADMINISTRATOR,
      });
    });
  });

  it("changes ADMINISTRATOR user role to DIRECTOR via select", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockResolvedValue({
      data: { ...mockUsers[1], role: UserRole.DIRECTOR },
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User Two")).toBeDefined();
    });

    const roleSelects = screen.getAllByRole("combobox", { name: "Cargo" });
    fireEvent.change(roleSelects[1], { target: { value: UserRole.DIRECTOR } });

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith("/users/user-2", {
        role: UserRole.DIRECTOR,
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

  it("prevents current user from changing their own role", async () => {
    const usersWithCurrentUser = [{ ...mockCurrentUser }, ...mockUsers];
    (apiClient.get as any).mockResolvedValue({ data: usersWithCurrentUser });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Admin User")).toBeDefined();
    });

    // The current user's role select is disabled, but we can still trigger handleRoleSelect
    // by forcing a change event on it
    const roleSelects = screen.getAllByRole("combobox", { name: "Cargo" });
    fireEvent.change(roleSelects[0], { target: { value: UserRole.DIRECTOR } });

    await waitFor(() => {
      expect(
        screen.getByText("Você não pode alterar seu próprio cargo."),
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

    // Click close
    const closeButton = screen.getByLabelText("Fechar");
    fireEvent.click(closeButton);

    expect(
      screen.queryByText("Você não pode desativar sua própria conta."),
    ).toBeNull();
  });

  // ── User type badge & empty list ────────────────────────────────────────

  it("renders user type badge when user has a type", async () => {
    const usersWithType = [{ ...mockUsers[0], type: { id: "type-1", name: "Manager" } }];
    (apiClient.get as any).mockResolvedValue({ data: usersWithType });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Manager")).toBeInTheDocument();
    });
  });

  it("shows 'no types yet' message when user types list is empty", async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: [] });
      return Promise.resolve({ data: mockUsers });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Nenhum tipo cadastrado.")).toBeInTheDocument();
    });
  });

  // ── Add type form ────────────────────────────────────────────────────────

  it("updates newTypeName state when input changes", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    const input = screen.getByPlaceholderText("Nome do tipo");
    fireEvent.change(input, { target: { value: "Finance" } });
    expect((input as HTMLInputElement).value).toBe("Finance");
  });

  it("creates a user type on form submit", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.post as any).mockResolvedValue({ data: { id: "type-new", name: "Finance" } });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    const input = screen.getByPlaceholderText("Nome do tipo");
    fireEvent.change(input, { target: { value: "Finance" } });
    fireEvent.click(screen.getByText("Adicionar tipo"));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/user-types/", { name: "Finance" });
    });
  });

  it("does not create a type when name is empty", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    const form = screen.getByPlaceholderText("Nome do tipo").closest("form") as HTMLFormElement;
    fireEvent.submit(form);

    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it("shows error when creating a type fails", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.post as any).mockRejectedValue({
      response: { data: { detail: "Nome duplicado" } },
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    const input = screen.getByPlaceholderText("Nome do tipo");
    fireEvent.change(input, { target: { value: "Finance" } });
    fireEvent.click(screen.getByText("Adicionar tipo"));

    await waitFor(() => {
      expect(screen.getByText("Nome duplicado")).toBeInTheDocument();
    });
  });

  it("shows fallback error when creating a type fails without detail", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.post as any).mockRejectedValue(new Error("network"));

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    const input = screen.getByPlaceholderText("Nome do tipo");
    fireEvent.change(input, { target: { value: "Finance" } });
    fireEvent.click(screen.getByText("Adicionar tipo"));

    await waitFor(() => {
      expect(screen.getByText("Erro ao criar tipo.")).toBeInTheDocument();
    });
  });

  // ── Delete type ──────────────────────────────────────────────────────────

  it("deletes a user type when confirm dialog is accepted", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });
    (apiClient.delete as any).mockResolvedValue({});

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("Manager")).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText("delete Manager"));

    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith("/user-types/type-1");
    });
  });

  it("does not delete a type when confirm dialog is cancelled", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("Manager")).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText("delete Manager"));

    expect(apiClient.delete).not.toHaveBeenCalled();
  });

  it("shows error when deleting a type fails", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });
    (apiClient.delete as any).mockRejectedValue({
      response: { data: { detail: "Tipo em uso" } },
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("Manager")).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText("delete Manager"));

    await waitFor(() => {
      expect(screen.getByText("Tipo em uso")).toBeInTheDocument();
    });
  });

  it("shows fallback error when deleting a type fails without detail", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });
    (apiClient.delete as any).mockRejectedValue(new Error("network"));

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("Manager")).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText("delete Manager"));

    await waitFor(() => {
      expect(screen.getByText("Erro ao excluir tipo.")).toBeInTheDocument();
    });
  });

  // ── Edit modal ───────────────────────────────────────────────────────────

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

  it("changes type in modal select", async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: mockUsers });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);

    // The type select inside the modal does not have an aria-label="Cargo", so
    // we grab the last combobox that is NOT a role select (aria-label Cargo)
    const selects = screen.getAllByRole("combobox");
    const nonRoleSelects = selects.filter(
      (s) => (s as HTMLSelectElement).getAttribute("aria-label") !== "Cargo",
    );
    const typeSelect = nonRoleSelects[nonRoleSelects.length - 1];
    fireEvent.change(typeSelect, { target: { value: "type-1" } });
    expect((typeSelect as HTMLSelectElement).value).toBe("type-1");
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

  it("saves edit with empty full name (sends undefined)", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockResolvedValue({ data: mockUsers[0] });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    fireEvent.change(screen.getByDisplayValue("User One"), { target: { value: "" } });
    fireEvent.click(screen.getByText("Salvar"));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        "/users/user-1",
        expect.objectContaining({ full_name: undefined, type_id: null }),
      );
    });
  });

  // ── Role select ─────────────────────────────────────────────────────────

  it("renders a role select for each user in the table", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    const roleSelects = screen.getAllByRole("combobox", { name: "Cargo" });
    expect(roleSelects).toHaveLength(mockUsers.length);
  });

  it("role select shows 3 options: Administrator, Director, Manager", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    const roleSelects = screen.getAllByRole("combobox", { name: "Cargo" });
    const firstSelect = roleSelects[0] as HTMLSelectElement;
    expect(firstSelect.options).toHaveLength(4);
    expect(firstSelect.options[0].value).toBe(UserRole.ADMINISTRATOR);
    expect(firstSelect.options[1].value).toBe(UserRole.DIRECTOR);
    expect(firstSelect.options[2].value).toBe(UserRole.MANAGER);
    expect(firstSelect.options[3].value).toBe(UserRole.GUEST);
  });

  it("pre-fills type_id when user has a type", async () => {
    const userWithType = { ...mockUsers[0], type: { id: "type-1", name: "Manager" } };
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === "/user-types/") return Promise.resolve({ data: mockUserTypes });
      return Promise.resolve({ data: [userWithType, mockUsers[1]] });
    });

    render(<AdminUserDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);

    const selects = screen.getAllByRole("combobox");
    const nonRoleSelects = selects.filter(
      (s) => (s as HTMLSelectElement).getAttribute("aria-label") !== "Cargo",
    );
    const typeSelect = nonRoleSelects[nonRoleSelects.length - 1];
    expect((typeSelect as HTMLSelectElement).value).toBe("type-1");
  });
});
