import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "../App";

/**
 * Real-router smoke test.
 *
 * This file deliberately mocks NOTHING under `src/features/**`, nothing from
 * `react-router-dom` and no `src/api/*` module other than `src/api/client`
 * (mocked only so an unexpected request cannot reach the network). The real
 * `App` — real `BrowserRouter`, real `AuthProvider`/`SimulationProvider`, real
 * page modules — is mounted and asserted against real form controls, so a page
 * that renders an empty tree fails the suite instead of passing it.
 */
vi.mock("../api/client", () => {
  // Every verb rejects: the pages under test must survive an unreachable API
  // (LoginPage's /auth/dev-users probe already expects a 404 in production).
  const offline = () =>
    vi.fn().mockRejectedValue(new Error("network disabled in tests"));
  return {
    default: {
      get: offline(),
      post: offline(),
      put: offline(),
      patch: offline(),
      delete: offline(),
    },
  };
});

const renderAppAt = (path: string) => {
  window.history.pushState({}, "", path);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
};

describe("App routing smoke test (real router, real pages)", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("renders the real login form on /login", async () => {
    const { container } = renderAppAt("/login");

    const email = await screen.findByLabelText("E-mail");
    const password = screen.getByLabelText("Senha");

    expect(email).toHaveAttribute("type", "email");
    expect(password).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(container.querySelectorAll("input").length).toBeGreaterThanOrEqual(3);
  });

  it("renders the real signup form on /signup", async () => {
    renderAppAt("/signup");

    expect(await screen.findByLabelText("Nome Completo")).toBeInTheDocument();
    expect(screen.getByLabelText("CPF")).toBeInTheDocument();
    expect(screen.getByLabelText("E-mail")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Senha")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Confirmar Senha")).toHaveAttribute(
      "type",
      "password",
    );
    expect(
      screen.getByRole("button", { name: "Cadastrar" }),
    ).toBeInTheDocument();
  });

  it("renders the real forgot-password form on /forgot-password", async () => {
    renderAppAt("/forgot-password");

    expect(await screen.findByLabelText("E-mail")).toHaveAttribute(
      "type",
      "email",
    );
    expect(
      screen.getByRole("button", { name: "Enviar link de recuperação" }),
    ).toBeInTheDocument();
  });

  it("renders the real reset-password form when the token query param is present", async () => {
    renderAppAt("/reset-password?token=test-token");

    // The page reads the token in an effect, so the form only appears after it runs.
    expect(await screen.findByLabelText("Nova Senha")).toHaveAttribute(
      "type",
      "password",
    );
    expect(screen.getByLabelText("Confirmar Nova Senha")).toHaveAttribute(
      "type",
      "password",
    );
    expect(
      screen.getByRole("button", { name: "Redefinir Senha" }),
    ).toBeInTheDocument();
  });

  it("shows the 'Link inválido' alert and no password field on /reset-password without a token", async () => {
    renderAppAt("/reset-password");

    expect(await screen.findByText("Link inválido")).toBeInTheDocument();
    expect(screen.queryByLabelText("Nova Senha")).toBeNull();
    expect(screen.queryByLabelText("Confirmar Nova Senha")).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Redefinir Senha" }),
    ).toBeNull();
  });

  it("redirects an unauthenticated visit to /dashboard onto the login form", async () => {
    renderAppAt("/dashboard");

    expect(await screen.findByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/login");
  });
});
