import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useUsers, useAssignableUsers } from "../useUsers";
import apiClient from "../../api/client";
import React from "react";

vi.mock("../../api/client");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("useUsers", () => {
  it("fetches users successfully", async () => {
    const mockUsers = [
      { id: "1", username: "user1", is_active: true },
      { id: "2", username: "user2", is_superuser: true, is_active: true },
    ];
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockUsers });

    const { result } = renderHook(() => useUsers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockUsers);
    expect(apiClient.get).toHaveBeenCalledWith("/users/");
  });
});

describe("useAssignableUsers", () => {
  const mockType = { id: "type-1", name: "Analista" };

  it("includes a superuser with roles in the assignable list (§10.5 c)", async () => {
    // The exclusion is **dropped**: after IAM F5 the frontend cannot know who
    // is an administrator without leaking `is_superuser` on `UserRead`
    // (§8.3), and being assignable a task is not a privilege. The
    // `roles?.length > 0` clause is kept, which is what the next case pins.
    const mockUsers = [
      {
        id: "1",
        username: "user1",
        is_active: true,
        roles: [mockType],
      },
      {
        id: "2",
        username: "admin",
        is_superuser: true,
        is_active: true,
        roles: [mockType],
      },
    ];
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockUsers });

    const { result } = renderHook(() => useAssignableUsers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockUsers);
  });

  it("filters out users without a role", async () => {
    const mockUsers = [
      {
        id: "1",
        username: "with-type",
        is_active: true,
        roles: [mockType],
      },
      {
        id: "2",
        username: "no-type",
        is_active: true,
        roles: [],
      },
      { id: "3", username: "no-type-undef", is_active: true, roles: [] },
    ];
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockUsers });

    const { result } = renderHook(() => useAssignableUsers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([
      {
        id: "1",
        username: "with-type",
        is_active: true,
        roles: [mockType],
      },
    ]);
  });
});
