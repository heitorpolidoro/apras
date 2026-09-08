import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
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

/**
 * The dev-login picker is a development-only affordance. In production the
 * endpoint answers 404, and the browser logs every failed XHR to the console
 * even when the promise is caught (seen live on apras.vercel.app), so the
 * request must not leave the page at all outside development builds.
 */
describe("LoginPage dev-users request", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [],
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  const renderPage = () =>
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

  it("does not request /auth/dev-users in a production build", async () => {
    vi.stubEnv("DEV", false);

    renderPage();

    await waitFor(() => {
      expect(apiClient.get).not.toHaveBeenCalledWith("/auth/dev-users");
    });
  });

  it("requests /auth/dev-users in a development build", async () => {
    vi.stubEnv("DEV", true);

    renderPage();

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith("/auth/dev-users");
    });
  });
});
