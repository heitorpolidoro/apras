import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ContactInfoDashboard from "../pages/ContactInfoDashboard";
import * as AuthHook from "../context/AuthContext";
import { UserRole } from "../context/AuthContext";
import apiClient from "../../../api/client";

vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
    patch: vi.fn(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}));

const mockCurrentUser = {
  id: "manager-1",
  email: "manager@example.com",
  full_name: "Manager User",
  role: UserRole.MANAGER,
  is_active: true,
};

const mockUsers = [
  {
    id: "user-1",
    email: "user1@example.com",
    full_name: "User One",
    role: UserRole.DIRECTOR,
    is_active: true,
    phone: "11999998888",
    address: "Rua A, 123",
  },
  {
    id: "user-2",
    email: "user2@example.com",
    full_name: "User Two",
    role: UserRole.ADMINISTRATOR,
    is_active: true,
    phone: null,
    address: null,
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

describe("ContactInfoDashboard", () => {
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

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    expect(screen.getByText("Carregando usuários...")).toBeDefined();
  });

  it("renders error state when fetch fails", async () => {
    (apiClient.get as any).mockRejectedValue(new Error("Network error"));

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Erro ao carregar usuários.")).toBeDefined();
    });
  });

  it("renders user table with phone and address columns", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User One")).toBeDefined();
    });

    expect(screen.getByText("user1@example.com")).toBeDefined();
    expect(screen.getByText("11999998888")).toBeDefined();
    expect(screen.getByText("Rua A, 123")).toBeDefined();
  });

  it("shows a dash for users with no phone/address", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("User Two")).toBeDefined();
    });

    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it("opens edit modal with pre-filled phone and address", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);

    expect(screen.getByDisplayValue("11999998888")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Rua A, 123")).toBeInTheDocument();
  });

  it("updates phone and address inputs in the modal", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);

    const phoneInput = screen.getByDisplayValue("11999998888");
    fireEvent.change(phoneInput, { target: { value: "11977776666" } });
    expect((phoneInput as HTMLInputElement).value).toBe("11977776666");

    const addressInput = screen.getByDisplayValue("Rua A, 123");
    fireEvent.change(addressInput, { target: { value: "Rua Nova, 456" } });
    expect((addressInput as HTMLInputElement).value).toBe("Rua Nova, 456");
  });

  it("saves contact info via PATCH /users/{id}/contact-info and invalidates users query", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockResolvedValue({ data: mockUsers[0] });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    fireEvent.change(screen.getByDisplayValue("11999998888"), {
      target: { value: "11977776666" },
    });
    fireEvent.click(screen.getByText("Salvar"));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        "/users/user-1/contact-info",
        expect.objectContaining({ phone: "11977776666", address: "Rua A, 123" }),
      );
    });

    // Modal closes on success
    await waitFor(() => {
      expect(screen.queryByText("Editar Informações de Contato")).toBeNull();
    });
  });

  it("closes the edit modal on Cancel", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    expect(screen.getByText("Editar Informações de Contato")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancelar"));
    expect(screen.queryByText("Editar Informações de Contato")).toBeNull();
  });

  it("closes the edit modal when backdrop is clicked", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    expect(screen.getByText("Editar Informações de Contato")).toBeInTheDocument();

    const backdrop = document.querySelector(".fixed.inset-0.z-50") as HTMLElement;
    fireEvent.click(backdrop);

    expect(screen.queryByText("Editar Informações de Contato")).toBeNull();
  });

  it("closes the edit modal when Escape is pressed", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    const backdrop = document.querySelector(".fixed.inset-0.z-50") as HTMLElement;
    fireEvent.keyDown(backdrop, { key: "Escape" });

    expect(screen.queryByText("Editar Informações de Contato")).toBeNull();
  });

  it("shows an error alert when the mutation fails with a detail message", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockRejectedValue({
      response: { data: { detail: "Permission denied" } },
    });

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    fireEvent.click(screen.getByText("Salvar"));

    await waitFor(() => {
      expect(screen.getByText("Permission denied")).toBeInTheDocument();
    });
  });

  it("shows a generic error alert when the mutation fails without detail", async () => {
    (apiClient.get as any).mockResolvedValue({ data: mockUsers });
    (apiClient.patch as any).mockRejectedValue(new Error("network"));

    render(<ContactInfoDashboard />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("User One")).toBeDefined());

    fireEvent.click(screen.getAllByText("Editar")[0]);
    fireEvent.click(screen.getByText("Salvar"));

    await waitFor(() => {
      expect(
        screen.getByText("Erro ao atualizar informações de contato"),
      ).toBeInTheDocument();
    });
  });
});
