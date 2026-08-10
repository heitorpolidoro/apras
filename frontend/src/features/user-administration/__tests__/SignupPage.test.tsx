import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import SignupPage from "../pages/SignupPage";
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

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>(
      "react-router-dom",
    );
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("SignupPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders signup form fields", () => {
    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    expect(screen.getByLabelText(/Nome Completo/i)).toBeDefined();
    expect(screen.getByLabelText(/CPF/i)).toBeDefined();
    expect(screen.getByLabelText(/E-mail/i)).toBeDefined();
    expect(screen.getByLabelText("Senha")).toBeDefined();
    expect(screen.getByLabelText(/Confirmar Senha/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /Cadastrar/i })).toBeDefined();
  });

  it("shows error when passwords do not match", async () => {
    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Nome Completo/i), {
      target: { value: "Test User", name: "full_name" },
    });
    fireEvent.change(screen.getByLabelText(/CPF/i), {
      target: { value: "529.982.247-25", name: "cpf" },
    });
    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "test@test.com", name: "email" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "password123!", name: "password" },
    });
    fireEvent.change(screen.getByLabelText(/Confirmar Senha/i), {
      target: { value: "different!", name: "confirm_password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Cadastrar/i }));

    expect(screen.getByText(/As senhas não coincidem/i)).toBeDefined();
  });

  it("shows error when password is too short", async () => {
    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Nome Completo/i), {
      target: { value: "Test User", name: "full_name" },
    });
    fireEvent.change(screen.getByLabelText(/CPF/i), {
      target: { value: "529.982.247-25", name: "cpf" },
    });
    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "test@test.com", name: "email" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "short", name: "password" },
    });
    fireEvent.change(screen.getByLabelText(/Confirmar Senha/i), {
      target: { value: "short", name: "confirm_password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Cadastrar/i }));

    expect(
      screen.getByText(/A senha deve ter pelo menos 8 caracteres/i),
    ).toBeDefined();
  });

  it("navigates to login with success message on successful signup", async () => {
    (apiClient.post as any).mockResolvedValue({ data: {} });

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Nome Completo/i), {
      target: { value: "Test User", name: "full_name" },
    });
    fireEvent.change(screen.getByLabelText(/CPF/i), {
      target: { value: "529.982.247-25", name: "cpf" },
    });
    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "test@test.com", name: "email" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "validpassword1!", name: "password" },
    });
    fireEvent.change(screen.getByLabelText(/Confirmar Senha/i), {
      target: { value: "validpassword1!", name: "confirm_password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Cadastrar/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login", {
        state: { message: expect.stringContaining("Cadastro realizado") },
      });
    });
  });

  it("shows string error detail from API on failure", async () => {
    (apiClient.post as any).mockRejectedValue({
      response: { data: { detail: "Username already registered" } },
    });

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Nome Completo/i), {
      target: { value: "Test User", name: "full_name" },
    });
    fireEvent.change(screen.getByLabelText(/CPF/i), {
      target: { value: "529.982.247-25", name: "cpf" },
    });
    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "test@test.com", name: "email" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "validpassword1!", name: "password" },
    });
    fireEvent.change(screen.getByLabelText(/Confirmar Senha/i), {
      target: { value: "validpassword1!", name: "confirm_password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Cadastrar/i }));

    await waitFor(() => {
      expect(screen.getByText("Username already registered")).toBeDefined();
    });
  });

  it("shows array validation error detail from API on failure", async () => {
    (apiClient.post as any).mockRejectedValue({
      response: {
        data: { detail: [{ msg: "field required" }, { msg: "invalid email" }] },
      },
    });

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Nome Completo/i), {
      target: { value: "Test User", name: "full_name" },
    });
    fireEvent.change(screen.getByLabelText(/CPF/i), {
      target: { value: "529.982.247-25", name: "cpf" },
    });
    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "test@test.com", name: "email" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "validpassword1!", name: "password" },
    });
    fireEvent.change(screen.getByLabelText(/Confirmar Senha/i), {
      target: { value: "validpassword1!", name: "confirm_password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Cadastrar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Erro de validação: field required, invalid email/i),
      ).toBeDefined();
    });
  });

  it("shows JSON stringified error when detail is a non-string, non-array object", async () => {
    (apiClient.post as any).mockRejectedValue({
      response: { data: { detail: { code: "UNKNOWN" } } },
    });

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Nome Completo/i), {
      target: { value: "Test User", name: "full_name" },
    });
    fireEvent.change(screen.getByLabelText(/CPF/i), {
      target: { value: "529.982.247-25", name: "cpf" },
    });
    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "test@test.com", name: "email" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "validpassword1!", name: "password" },
    });
    fireEvent.change(screen.getByLabelText(/Confirmar Senha/i), {
      target: { value: "validpassword1!", name: "confirm_password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Cadastrar/i }));

    await waitFor(() => {
      expect(screen.getByText(/UNKNOWN/i)).toBeDefined();
    });
  });

  it("shows generic error message when no detail in response", async () => {
    (apiClient.post as any).mockRejectedValue({
      response: { data: {} },
    });

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Nome Completo/i), {
      target: { value: "Test User", name: "full_name" },
    });
    fireEvent.change(screen.getByLabelText(/CPF/i), {
      target: { value: "529.982.247-25", name: "cpf" },
    });
    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "test@test.com", name: "email" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "validpassword1!", name: "password" },
    });
    fireEvent.change(screen.getByLabelText(/Confirmar Senha/i), {
      target: { value: "validpassword1!", name: "confirm_password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Cadastrar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Ocorreu um erro ao realizar o cadastro/i),
      ).toBeDefined();
    });
  });

  it("shows loading state while submitting", async () => {
    let resolvePost: (value: unknown) => void;
    (apiClient.post as any).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePost = resolve;
        }),
    );

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Nome Completo/i), {
      target: { value: "Test User", name: "full_name" },
    });
    fireEvent.change(screen.getByLabelText(/CPF/i), {
      target: { value: "529.982.247-25", name: "cpf" },
    });
    fireEvent.change(screen.getByLabelText(/E-mail/i), {
      target: { value: "test@test.com", name: "email" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "validpassword1!", name: "password" },
    });
    fireEvent.change(screen.getByLabelText(/Confirmar Senha/i), {
      target: { value: "validpassword1!", name: "confirm_password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Cadastrar/i }));

    expect(
      screen.getByRole("button", { name: /Cadastrando.../i }),
    ).toBeDefined();

    resolvePost!({ data: {} });
  });
});
