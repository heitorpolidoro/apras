import { render, waitFor, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider, useAuth } from "../context/AuthContext";
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

const TestComponent = () => {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  if (isLoading) return <div>Loading...</div>;
  return (
    <div>
      <div data-testid="auth-status">
        {isAuthenticated ? "Authenticated" : "Not Authenticated"}
      </div>
      {user && <div data-testid="username">{user.email}</div>}
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it("initially shows as not authenticated if no token exists", async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.queryByText("Loading...")).toBeNull());
    expect(screen.getByTestId("auth-status").textContent).toBe(
      "Not Authenticated",
    );
  });

  it("fetches user if token exists in localStorage", async () => {
    const mockUser = {
      id: 1,
      email: "testuser@example.com",
      role: "FUNCIONARIO",
      is_active: true,
    };
    localStorage.setItem("accessToken", "fake-token");
    (apiClient.get as any).mockResolvedValue({ data: mockUser });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("auth-status").textContent).toBe(
        "Authenticated",
      ),
    );
    expect(screen.getByTestId("username").textContent).toBe("testuser@example.com");
    expect(apiClient.get).toHaveBeenCalledWith("/auth/me");
  });

  it("logs out and clears both storages", async () => {
    const mockUser = {
      id: 1,
      email: "testuser@example.com",
      role: "FUNCIONARIO",
      is_active: true,
    };
    localStorage.setItem("accessToken", "fake-token");
    sessionStorage.setItem("accessToken", "fake-token");
    (apiClient.get as any).mockResolvedValue({ data: mockUser });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("auth-status").textContent).toBe(
        "Authenticated",
      ),
    );

    fireEvent.click(screen.getByText("Logout"));

    await waitFor(() =>
      expect(screen.getByTestId("auth-status").textContent).toBe(
        "Not Authenticated",
      ),
    );
    expect(localStorage.getItem("accessToken")).toBeNull();
    expect(sessionStorage.getItem("accessToken")).toBeNull();
  });

  it("clears storage if fetchUser fails", async () => {
    localStorage.setItem("accessToken", "invalid-token");
    (apiClient.get as any).mockRejectedValue(new Error("Unauthorized"));

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.queryByText("Loading...")).toBeNull());
    expect(screen.getByTestId("auth-status").textContent).toBe(
      "Not Authenticated",
    );
    expect(localStorage.getItem("accessToken")).toBeNull();
  });

  it("sets token in sessionStorage if remember is false", async () => {
    const mockUser = {
      id: 1,
      email: "testuser@example.com",
      role: "FUNCIONARIO",
      is_active: true,
    };
    (apiClient.get as any).mockResolvedValue({ data: mockUser });

    const LoginTestComponent = () => {
      const { login } = useAuth();
      return <button onClick={() => login("fake-token", false)}>Login</button>;
    };

    render(
      <AuthProvider>
        <LoginTestComponent />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByText("Login"));

    await waitFor(() =>
      expect(sessionStorage.getItem("accessToken")).toBe("fake-token"),
    );
    expect(localStorage.getItem("accessToken")).toBeNull();
  });

  it("sets token in localStorage if remember is true", async () => {
    const mockUser = {
      id: 1,
      email: "testuser@example.com",
      role: "FUNCIONARIO",
      is_active: true,
    };
    (apiClient.get as any).mockResolvedValue({ data: mockUser });

    const LoginTestComponent = () => {
      const { login } = useAuth();
      return <button onClick={() => login("fake-token", true)}>Login</button>;
    };

    render(
      <AuthProvider>
        <LoginTestComponent />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByText("Login"));

    await waitFor(() =>
      expect(localStorage.getItem("accessToken")).toBe("fake-token"),
    );
    expect(sessionStorage.getItem("accessToken")).toBeNull();
  });

  it("throws error if useAuth is used outside AuthProvider", () => {
    // Suppress console.error for this test as we expect an error to be thrown
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<TestComponent />)).toThrow(
      "useAuth must be used within an AuthProvider",
    );

    consoleSpy.mockRestore();
  });
});
