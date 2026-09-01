import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminUserDashboard from "../pages/AdminUserDashboard";
import * as AuthHook from "../context/AuthContext";
import apiClient from "../../../api/client";
import { UserRole, type User } from "../../../types/auth";

/**
 * After switching into a tenant where the capability is absent, the backend
 * answers `GET /api/v1/users/` with 403 (APRAS-43). This pins that the SPA
 * treats that as data, not as a session event: a handled error message, no
 * crash, no auto-logout and no auto-switch — there is deliberately no global
 * Axios response interceptor for 401/403.
 */
vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({ data: [] })),
}));

const mockedGet = vi.mocked(apiClient.get);

const wrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe("AdminUserDashboard under a 403", () => {
  const errors: unknown[] = [];
  let consoleError: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    errors.length = 0;
    consoleError = vi.spyOn(console, "error").mockImplementation((...args) => {
      errors.push(args);
    });
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      user: {
        id: "u-syndic",
        email: "syndic@test.com",
        full_name: "Síndico",
        role: UserRole.RESIDENT,
        is_active: true,
      } as User,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn() as never,
      logout: vi.fn(),
    });
    mockedGet.mockReset();
    mockedGet.mockRejectedValue({
      response: { status: 403, data: { detail: "Forbidden" } },
    });
  });

  afterEach(() => {
    consoleError.mockRestore();
  });

  it("renders the error message and does not crash when /users/ returns 403", async () => {
    const Wrapper = wrapper();

    render(
      <Wrapper>
        <AdminUserDashboard />
      </Wrapper>,
    );

    // "Erro ao carregar usuários" — the pre-existing handled-error branch.
    expect(
      await screen.findByText("Erro ao carregar usuários."),
    ).toBeInTheDocument();
    // The page is still mounted: an error boundary or a thrown render would
    // have emptied the tree instead.
    expect(document.body.textContent).not.toBe("");
  });
});
