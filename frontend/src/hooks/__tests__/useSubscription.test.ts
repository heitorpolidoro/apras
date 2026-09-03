import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import apiClient from "../../api/client";
import {
  useSetSubscriptionModules,
  useSubscription,
  useSubscriptionHistory,
} from "../useSubscription";
import {
  useSetTenantCourtesy,
  useSetTenantPlan,
  useTenantSubscription,
} from "../usePlans";

/**
 * Cache-key discipline and permission invalidation (APRAS-40 §8.2).
 *
 * Two properties, and they pull in opposite directions on purpose:
 *
 * * `["subscription"]` is **acting-tenant** data — the three routes carry no
 *   `{tenant_id}` and read `X-Tenant-Id` — so `setActingTenant`'s eviction
 *   sweep (`queryKey[0] !== "tenants"`) must **reset** it on a tenant switch.
 * * `["tenants", id, "subscription"]` is keyed by an **explicit** tenant id,
 *   so the same sweep must **preserve** it.
 *
 * And every mutation that can change `tenant.disabled_modules` invalidates
 * `["me","permissions"]`: without it the navbar keeps showing a menu the API
 * has just started refusing.
 */

vi.mock("../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPut = vi.mocked(apiClient.put);

/** The predicate `TenantContext.setActingTenant` resets with, verbatim. */
const scopedOnly = (queryKey: readonly unknown[]) => queryKey[0] !== "tenants";

const wrapperFor = (client: QueryClient) =>
  function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client }, children);
  };

const newClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false } } });

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPut.mockReset();
  mockedGet.mockResolvedValue({ data: { tenant_id: "t-1", modules: [] } } as never);
  mockedPut.mockResolvedValue({ data: { tenant_id: "t-1", modules: [] } } as never);
});

describe("useSubscription cache keys", () => {
  it("keys the acting-tenant reads under 'subscription', which a tenant switch resets", async () => {
    const client = newClient();
    const wrapper = wrapperFor(client);

    renderHook(() => useSubscription(), { wrapper });
    renderHook(() => useSubscriptionHistory(), { wrapper });

    await waitFor(() =>
      expect(client.getQueryData(["subscription"])).toBeDefined(),
    );

    const keys = client
      .getQueryCache()
      .getAll()
      .map((query) => query.queryKey);
    expect(keys).toContainEqual(["subscription"]);
    expect(keys).toContainEqual(["subscription", "history"]);
    for (const key of keys) {
      expect(scopedOnly(key)).toBe(true);
    }
  });

  it("keys the superuser read under 'tenants', which a tenant switch preserves", async () => {
    const client = newClient();
    const wrapper = wrapperFor(client);

    renderHook(() => useTenantSubscription("t-9"), { wrapper });

    await waitFor(() =>
      expect(client.getQueryData(["tenants", "t-9", "subscription"])).toBeDefined(),
    );
    expect(scopedOnly(["tenants", "t-9", "subscription"])).toBe(false);
  });
});

describe("permission invalidation", () => {
  it("useSetSubscriptionModules invalidates ['me','permissions']", async () => {
    const client = newClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useSetSubscriptionModules(), {
      wrapper: wrapperFor(client),
    });

    result.current.mutate(["finance"]);

    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({
        queryKey: ["me", "permissions"],
      }),
    );
    expect(mockedPut).toHaveBeenCalledWith("/subscription/modules", {
      active_modules: ["finance"],
    });
  });

  it("useSetTenantPlan invalidates ['me','permissions']", async () => {
    const client = newClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useSetTenantPlan("t-9"), {
      wrapper: wrapperFor(client),
    });

    result.current.mutate({ plan_id: "p-1" });

    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({
        queryKey: ["me", "permissions"],
      }),
    );
    expect(mockedPut).toHaveBeenCalledWith("/tenants/t-9/subscription", {
      plan_id: "p-1",
    });
  });

  it("useSetTenantCourtesy invalidates ['me','permissions']", async () => {
    const client = newClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useSetTenantCourtesy("t-9"), {
      wrapper: wrapperFor(client),
    });

    result.current.mutate({ courtesy_modules: ["assets"], reason: "x" });

    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({
        queryKey: ["me", "permissions"],
      }),
    );
    expect(mockedPut).toHaveBeenCalledWith(
      "/tenants/t-9/subscription/courtesy",
      { courtesy_modules: ["assets"], reason: "x" },
    );
  });
});
