import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "../pages/LoginPage";
import { AuthProvider } from "../context/AuthContext";
import apiClient from "../../../api/client";

vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}));

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [],
    });
  });

  it("renders login form", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.getByLabelText(/E-mail/i)).toBeDefined();
    expect(screen.getByLabelText(/Senha/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /Entrar/i })).toBeDefined();
  });

  it("shows error message on failed login", async () => {
    (apiClient.post as unknown as ReturnType<typeof vi.fn>).mockRejectedValue({
      response: {
        data: { detail: "Incorrect username or password" },
      },
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "wronguser@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Senha/i), {
      target: { value: "wrongpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Entrar/i }));

    await waitFor(() => {
      expect(screen.getByText(/Incorrect username or password/i)).toBeDefined();
    });
  });

  it("shows specific message for inactive user", async () => {
    (apiClient.post as unknown as ReturnType<typeof vi.fn>).mockRejectedValue({
      response: {
        data: { detail: "Inactive user" },
      },
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "inactive@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Senha/i), {
      target: { value: "pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Entrar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          /Sua conta está aguardando aprovação de um administrador/i,
        ),
      ).toBeDefined();
    });
  });

  it("renders dev users and handles dev login", async () => {
    const mockDevUsers = [
      { id: "1", full_name: "devadmin", email: "devadmin@test.com", is_active: true, role: "ADMINISTRATOR" },
    ];
    (apiClient.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: mockDevUsers,
    });
    (apiClient.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { access_token: "dev-token" },
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Login Rápido \(Desenvolvimento\)/i)).toBeDefined();
    });

    const devButton = screen.getByRole("button", { name: "devadmin" });
    fireEvent.click(devButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/auth/dev-login",
        null,
        expect.objectContaining({
          params: { email: "devadmin@test.com", remember_me: false },
        }),
      );
    });
  });

  it("shows error message when detail is a list (validation error)", async () => {
    (apiClient.post as unknown as ReturnType<typeof vi.fn>).mockRejectedValue({
      response: {
        data: {
          detail: [{ msg: "Error 1" }, { msg: "Error 2" }],
        },
      },
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "user@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Senha/i), {
      target: { value: "pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Entrar/i }));

    await waitFor(() => {
      expect(screen.getByText(/Erro: Error 1, Error 2/i)).toBeDefined();
    });
  });

  it("shows error message when detail is an object", async () => {
    (apiClient.post as unknown as ReturnType<typeof vi.fn>).mockRejectedValue({
      response: {
        data: { detail: { some: "error" } },
      },
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "user@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Senha/i), {
      target: { value: "pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Entrar/i }));

    await waitFor(() => {
      expect(screen.getByText(/\{"some":"error"\}/)).toBeDefined();
    });
  });

  it("shows generic error message when no detail is provided", async () => {
    (apiClient.post as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Network Error"),
    );

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "user@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Senha/i), {
      target: { value: "pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Entrar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Ocorreu um erro ao tentar fazer login. Verifique suas credenciais./i),
      ).toBeDefined();
    });
  });

  it("handles dev login failure", async () => {
    const mockDevUsers = [
      { id: "1", full_name: "devadmin", email: "devadmin@test.com", is_active: true, role: "ADMINISTRATOR" },
    ];
    (apiClient.get as any).mockResolvedValue({ data: mockDevUsers });
    (apiClient.post as any).mockRejectedValue(new Error("Dev login failed"));

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText(/devadmin/i)).toBeDefined());
    fireEvent.click(screen.getByRole("button", { name: "devadmin" }));

    await waitFor(() => {
      expect(screen.getByText(/Dev login failed/i)).toBeDefined();
    });
  });

  it("handles failed dev users fetch silently", async () => {
    (apiClient.get as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Fetch failed"),
    );

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.queryByText(/Quick Login \(Dev Mode\)/i)).toBeNull();
    });
  });

  it("renders success message when navigated with state.message", () => {
    render(
      <MemoryRouter initialEntries={[{ pathname: "/login", state: { message: "Conta criada com sucesso!" } }]}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText("Conta criada com sucesso!")).toBeInTheDocument();
  });

  it("handles successful login and remember me", async () => {
    (apiClient.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { access_token: "test-token" },
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    const rememberMe = screen.getByLabelText(/Mantenha-me conectado/i);
    fireEvent.click(rememberMe);
    expect(rememberMe).toBeChecked();

    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "user@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Senha/i), {
      target: { value: "pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Entrar/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/auth/login?remember_me=true",
        expect.any(FormData),
        expect.any(Object),
      );
    });
  });
});
