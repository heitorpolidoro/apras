import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import BrandedEntryPage from "../pages/BrandedEntryPage";
import apiClient from "../../../api/client";
import { fetchPublicBranding } from "../../../api/publicBranding";
import { useAuth } from "../context/AuthContext";
import { useTenant } from "../context/useTenant";
import {
  clearActingTenantId,
  setActingTenantId,
} from "../context/tenantState";
import type { Tenant } from "../../../types/auth";

/**
 * D5: the slug **feeds** `X-Tenant-Id`, it never replaces it (APRAS-74).
 *
 * The whole chain is exercised end to end — `/c/<slug>` resolves the slug
 * against the membership list, writes the acting-tenant mirror through the
 * real `setActingTenantId`, and the **real** Axios interceptor is then run to
 * read the header off it. Nothing about the tenancy contract is special-cased
 * for this route, and this file is what would fail if it ever were.
 *
 * `api/client` is therefore deliberately **not** mocked here; the branding
 * read is stubbed at the module above it instead, so no request leaves jsdom.
 */

vi.mock("../../../api/publicBranding", () => ({
  fetchPublicBranding: vi.fn(),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("../context/useTenant", async () => {
  const actual =
    await vi.importActual<typeof import("../context/useTenant")>(
      "../context/useTenant",
    );
  return { ...actual, useTenant: vi.fn() };
});

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>(
      "react-router-dom",
    );
  return { ...actual, useNavigate: () => mockNavigate };
});

const MINE: Tenant = {
  id: "22222222-2222-2222-2222-222222222222",
  name: "Condomínio Altos da Serra",
  slug: "altos-da-serra",
  is_active: true,
  created_at: "2026-01-01T00:00:00",
};

const asMock = (fn: unknown) => fn as unknown as ReturnType<typeof vi.fn>;

/** The interceptor, exercised directly as `client.tenantHeader.test.ts` does. */
const runInterceptor = async () =>
  (await (
    apiClient.interceptors.request as unknown as {
      handlers: { fulfilled: (...args: unknown[]) => unknown }[];
    }
  ).handlers[0].fulfilled({ headers: {} })) as {
    headers: Record<string, string | undefined>;
  };

describe("BrandedEntryPage keeps X-Tenant-Id authoritative", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    clearActingTenantId();

    asMock(fetchPublicBranding).mockResolvedValue({
      slug: "altos-da-serra",
      name: "Condomínio Altos da Serra",
      logo_url: null,
      theme: null,
    });
    asMock(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    asMock(useTenant).mockReturnValue({
      tenants: [MINE],
      actingTenantId: null,
      actingTenant: null,
      isActingTenantAdmin: false,
      isLoading: false,
      // The real writer, so the mirror the interceptor reads is the one the
      // page actually wrote.
      setActingTenant: setActingTenantId,
    });
  });

  it("attaches the resolved tenant id as X-Tenant-Id on the next request", async () => {
    sessionStorage.setItem("accessToken", "token");

    render(
      <MemoryRouter initialEntries={["/c/altos-da-serra"]}>
        <Routes>
          <Route path="/c/:slug" element={<BrandedEntryPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });

    const config = await runInterceptor();

    expect(config.headers["X-Tenant-Id"]).toBe(MINE.id);
    expect(config.headers.Authorization).toBe("Bearer token");
  });
});
