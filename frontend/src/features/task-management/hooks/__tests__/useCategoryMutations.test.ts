import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { useCreateCategory, useUpdateCategory, useDeleteCategory,  } from "../useCategories";
import apiClient from "../../../../api/client";

vi.mock("../../../../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("useCreateCategory", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls POST /categories/ and returns new category", async () => {
    const newCat = { id: "cat-new", name: "Finance", color: "#ff5500", is_active: true };
    vi.mocked(apiClient.post).mockResolvedValue({ data: newCat });
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    const { result } = renderHook(() => useCreateCategory(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ name: "Finance", color: "#ff5500" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith("/categories/", { name: "Finance", color: "#ff5500" });
    expect(result.current.data).toEqual(newCat);
  });

  it("handles creation error", async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error("Conflict"));

    const { result } = renderHook(() => useCreateCategory(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ name: "Finance", color: "#ff0000" });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Conflict");
  });
});

describe("useUpdateCategory", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls PATCH /categories/{id}", async () => {
    const updated = { id: "cat-1", name: "Updated", color: "#808080", is_active: true };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: updated });
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    const { result } = renderHook(() => useUpdateCategory(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: "cat-1", data: { name: "Updated" } });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.patch).toHaveBeenCalledWith("/categories/cat-1", { name: "Updated" });
  });

  it("handles update error", async () => {
    vi.mocked(apiClient.patch).mockRejectedValue(new Error("Not found"));

    const { result } = renderHook(() => useUpdateCategory(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: "cat-999", data: { name: "Ghost" } });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useDeleteCategory", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls DELETE /categories/{id}", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({});
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    const { result } = renderHook(() => useDeleteCategory(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate("cat-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.delete).toHaveBeenCalledWith("/categories/cat-1");
  });

  it("handles delete error", async () => {
    vi.mocked(apiClient.delete).mockRejectedValue(new Error("Not found"));

    const { result } = renderHook(() => useDeleteCategory(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate("cat-999");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
