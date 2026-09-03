import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import { useCreateRole, useDeleteRole, useSetUserRoles, useUpdateRole,  } from "../hooks/useRoleMutations";

/** The role writes and what each of them evicts (APRAS-48 §6). */
vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

let client: QueryClient;
let invalidated: unknown[][];

const wrapper = (): React.FC<{ children: React.ReactNode }> => {
  client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  invalidated = [];
  vi.spyOn(client, "invalidateQueries").mockImplementation(((
    filters?: { queryKey?: unknown[] },
  ) => {
    invalidated.push(filters?.queryKey ?? []);
    return Promise.resolve();
  }) as never);
  return ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
};

const PAYLOAD = { name: "Zeladoria", permissions: [] };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(apiClient.post).mockResolvedValue({ data: {} } as never);
  vi.mocked(apiClient.patch).mockResolvedValue({ data: {} } as never);
  vi.mocked(apiClient.delete).mockResolvedValue({ data: {} } as never);
});

describe("role mutations invalidate the author's own permissions", () => {
  it.each([
    [
      "create",
      () => useCreateRole(),
      (mutate: (v: unknown) => void) => mutate(PAYLOAD),
    ],
    [
      "update",
      () => useUpdateRole(),
      (mutate: (v: unknown) => void) =>
        mutate({ roleId: "g-1", payload: PAYLOAD }),
    ],
    [
      "delete",
      () => useDeleteRole(),
      (mutate: (v: unknown) => void) => mutate("g-1"),
    ],
  ])("%s evicts roles, users and [me, permissions]", async (
    _label,
    useHook,
    fire,
  ) => {
    const { result } = renderHook(useHook as never, { wrapper: wrapper() });

    fire((result.current as { mutate: (v: unknown) => void }).mutate);

    await waitFor(() => expect(invalidated.length).toBe(3));
    expect(invalidated).toContainEqual(["roles"]);
    expect(invalidated).toContainEqual(["users"]);
    // The author's own effective set can change with the very role they just
    // edited, so the payload `ProtectedRoute` and `Navbar` decide on must not
    // survive the write.
    expect(invalidated).toContainEqual(["me", "permissions"]);
  });

  it("a membership change evicts users and nothing else", async () => {
    const { result } = renderHook(() => useSetUserRoles(), {
      wrapper: wrapper(),
    });

    result.current.mutate({ userId: "u-1", roleIds: ["g-1"] });

    await waitFor(() => expect(invalidated.length).toBe(1));
    // Assigning a *different* user to a role changes that user's set, not the
    // author's, so `["me","permissions"]` is deliberately left alone.
    expect(invalidated).toEqual([["users"]]);
  });
});

describe("the role payload after the enum", () => {
  it("carries no allowed_menus, and `deriveAllowedMenus` is gone with it", async () => {
    // IAM F5 (APRAS-49 §4.1) deleted the `allowed_menus` column and the
    // derivation that kept it additive. The successor statement is that the
    // editor stops *sending* the field — hand-off item 5 of F4's list, and
    // the one a grep almost misses.
    const module = await import("../hooks/useRoleMutations");
    expect("deriveAllowedMenus" in module).toBe(false);

    const { result } = renderHook(() => useCreateRole(), {
      wrapper: wrapper(),
    });
    result.current.mutate({ name: "Zeladoria", permissions: ["tasks:read"] });
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());

    const [, payload] = vi.mocked(apiClient.post).mock.calls[0];
    expect(payload).not.toHaveProperty("allowed_menus");
  });
});
