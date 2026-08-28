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

const submitLogin = async () => {
  fireEvent.change(screen.getByLabelText(/E-mail/i), {
    target: { value: "guest@example.com" },
  });
  fireEvent.change(screen.getByLabelText(/Senha/i), {
    target: { value: "pass" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Entrar/i }));
};

describe("LoginPage post-login navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [],
    });
    (apiClient.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { access_token: "test-token" },
    });
  });

  it("navigates to the explicit deep-link target when location.state.from is set (e.g. a GUEST bounced from a protected route)", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          { pathname: "/login", state: { from: { pathname: "/lots" } } },
        ]}
      >
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await submitLogin();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/lots", { replace: true });
    });
  });

  it("falls back to '/' (not '/dashboard') when there is no deep-link target", async () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await submitLogin();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });
});
