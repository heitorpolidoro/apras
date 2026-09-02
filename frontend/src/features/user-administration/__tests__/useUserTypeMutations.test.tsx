import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import {
  deriveAllowedMenus,
  useCreateUserType,
  useDeleteUserType,
  useSetUserGroups,
  useUpdateUserType,
} from "../hooks/useUserTypeMutations";

/** The group writes and what each of them evicts (APRAS-48 §6). */
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

const PAYLOAD = { name: "Zeladoria", permissions: [], allowed_menus: [] };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(apiClient.post).mockResolvedValue({ data: {} } as never);
  vi.mocked(apiClient.patch).mockResolvedValue({ data: {} } as never);
  vi.mocked(apiClient.delete).mockResolvedValue({ data: {} } as never);
});

describe("group mutations invalidate the author's own permissions", () => {
  it.each([
    [
      "create",
      () => useCreateUserType(),
      (mutate: (v: unknown) => void) => mutate(PAYLOAD),
    ],
    [
      "update",
      () => useUpdateUserType(),
      (mutate: (v: unknown) => void) =>
        mutate({ groupId: "g-1", payload: PAYLOAD }),
    ],
    [
      "delete",
      () => useDeleteUserType(),
      (mutate: (v: unknown) => void) => mutate("g-1"),
    ],
  ])("%s evicts user-types, users and [me, permissions]", async (
    _label,
    useHook,
    fire,
  ) => {
    const { result } = renderHook(useHook as never, { wrapper: wrapper() });

    fire((result.current as { mutate: (v: unknown) => void }).mutate);

    await waitFor(() => expect(invalidated.length).toBe(3));
    expect(invalidated).toContainEqual(["user-types"]);
    expect(invalidated).toContainEqual(["users"]);
    // The author's own effective set can change with the very group they just
    // edited, so the payload `ProtectedRoute` and `Navbar` decide on must not
    // survive the write.
    expect(invalidated).toContainEqual(["me", "permissions"]);
  });

  it("a membership change evicts users and nothing else", async () => {
    const { result } = renderHook(() => useSetUserGroups(), {
      wrapper: wrapper(),
    });

    result.current.mutate({ userId: "u-1", userTypeIds: ["g-1"] });

    await waitFor(() => expect(invalidated.length).toBe(1));
    // Assigning a *different* user to a group changes that user's set, not the
    // author's, so `["me","permissions"]` is deliberately left alone.
    expect(invalidated).toEqual([["users"]]);
  });
});

describe("deriveAllowedMenus", () => {
  it("derives the two legacy menu keys from the selected permissions", () => {
    expect(deriveAllowedMenus(["tasks:read"])).toEqual(["tasks"]);
    expect(deriveAllowedMenus(["categories:read", "tasks:delete"])).toEqual([
      "categories",
      "tasks",
    ]);
    expect(deriveAllowedMenus(["finance:read"])).toEqual([]);
  });

  it("is additive: a stored key is never revoked", () => {
    // §2.3: the derivation can only add, until IAM F5 deletes the column.
    expect(deriveAllowedMenus(["finance:read"], ["tasks"])).toEqual(["tasks"]);
    expect(deriveAllowedMenus(["categories:read"], ["tasks"])).toEqual([
      "categories",
      "tasks",
    ]);
    // …and never duplicates one it derives and already had.
    expect(deriveAllowedMenus(["tasks:read"], ["tasks"])).toEqual(["tasks"]);
  });
});
