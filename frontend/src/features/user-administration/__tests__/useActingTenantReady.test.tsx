import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useActingTenantReady } from "../context/useTenant";
import { useAuth } from "../context/AuthContext";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

/**
 * `useActingTenantReady` gates every tenant-scoped query that can subscribe
 * above the auth guard (`useRoles`, `useMyPermissions` via `Navbar` and
 * `ProtectedRoute`). "Boot finished with nobody logged in" must read as NOT
 * ready: on `/login` the old `!isLoading` gate let `/roles/` and
 * `/permissions/me` leave without a token and come back 401, retried.
 */
describe("useActingTenantReady", () => {
  const mockAuth = (isLoading: boolean, isAuthenticated: boolean) =>
    (useAuth as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      isLoading,
      isAuthenticated,
      user: isAuthenticated ? { id: "u1" } : null,
      login: vi.fn(),
      logout: vi.fn(),
    });

  it("is false while auth is still booting", () => {
    mockAuth(true, false);
    expect(renderHook(() => useActingTenantReady()).result.current).toBe(false);
  });

  it("is false when boot finished with nobody logged in", () => {
    mockAuth(false, false);
    expect(renderHook(() => useActingTenantReady()).result.current).toBe(false);
  });

  it("is true once boot finished with an authenticated user", () => {
    mockAuth(false, true);
    expect(renderHook(() => useActingTenantReady()).result.current).toBe(true);
  });
});
