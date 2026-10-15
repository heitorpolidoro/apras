import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import SubscriptionPage from "../pages/SubscriptionPage";
import TenantModulesPage from "../pages/TenantModulesPage";
import { groupsCovering, unitsOf } from "../access/moduleGroups";
import type { ModuleEntitlement } from "../../../types/subscription";

/**
 * Module bundles (APRAS-128): one checkbox per bundle, driven by the backend's
 * `bundle` field, toggling every member through the existing PUT bodies. A
 * module with `bundle: null` that no presentation group names still renders.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPut = vi.mocked(apiClient.put);

const name = (module: string): string =>
  (pt.modules.names as Record<string, string>)[module];
const bundleLabel = (bundle: string): string =>
  (pt.modules.bundles as Record<string, string>)[bundle];

const wrap = (ui: React.ReactElement) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPut.mockReset();
});

describe("TenantModulesPage bundles", () => {
  const body = (disabled: string[]) => ({
    tenant_id: "t-1",
    modules: [
      { module: "tasks", bundle: "tasks", is_core: false },
      { module: "categories", bundle: "tasks", is_core: false },
      { module: "finance", bundle: null, is_core: false },
      { module: "brand_new", bundle: null, is_core: false },
      { module: "users", bundle: null, is_core: true },
    ].map((m) => ({ ...m, is_active: !disabled.includes(m.module) })),
  });

  beforeEach(() => {
    mockedGet.mockImplementation(((url: string) => {
      if (url === "/tenants")
        return Promise.resolve({
          data: [{ id: "t-1", name: "A", is_active: true }],
        });
      if (url === "/tenants/t-1/modules")
        return Promise.resolve({ data: body([]) });
      return Promise.resolve({ data: [] });
    }) as never);
  });

  it("renders one checkbox per bundle and sends every member when toggled", async () => {
    mockedPut.mockResolvedValue({ data: body(["tasks", "categories"]) });
    wrap(<TenantModulesPage />);

    const bundle = await screen.findByRole("checkbox", {
      name: bundleLabel("tasks"),
    });
    expect(screen.queryByRole("checkbox", { name: name("tasks") })).toBeNull();
    expect(
      screen.queryByRole("checkbox", { name: name("categories") }),
    ).toBeNull();
    // The bundle card lists the features it switches on together.
    const card = bundle.closest("label") as HTMLElement;
    expect(
      [...card.querySelectorAll("li")].map((li) => li.textContent),
    ).toEqual([name("tasks"), name("categories")]);
    // Unbundled modules, including one no group names, still render.
    expect(screen.getByRole("checkbox", { name: name("finance") })).toBeTruthy();
    expect(screen.getByRole("checkbox", { name: "modules.names.brand_new" })).toBeTruthy();

    await userEvent.click(bundle);
    await userEvent.click(screen.getByRole("button", { name: t("save") }));

    await waitFor(() => expect(mockedPut).toHaveBeenCalled());
    expect(mockedPut).toHaveBeenCalledWith("/tenants/t-1/modules", {
      disabled_modules: ["categories", "tasks"],
    });
  });
});

const t = (key: string): string => (pt.modules as unknown as Record<string, string>)[key];

describe("SubscriptionPage bundles", () => {
  const row = (
    module: string,
    bundle: string | null,
    overrides: Partial<ModuleEntitlement> = {},
  ): ModuleEntitlement => ({
    module,
    bundle,
    is_core: false,
    is_active: true,
    in_plan: true,
    courtesy: false,
    can_contract: true,
    monthly_price: null,
    source: "PLAN",
    ...overrides,
  });

  const serve = (modules: ModuleEntitlement[]) => {
    const plan = {
      id: "p-1",
      name: "Plano",
      description: null,
      included_modules: [],
      base_price: 1,
      module_prices: {},
      currency: "BRL",
      is_active: true,
      created_at: "2026-01-01T00:00:00",
      updated_at: "2026-01-01T00:00:00",
    };
    mockedGet.mockImplementation(((url: string) => {
      if (url === "/subscription")
        return Promise.resolve({
          data: {
            tenant_id: "t-1",
            plan,
            status: "ACTIVE",
            started_at: null,
            notes: null,
            estimated_monthly_total: 1,
            currency: "BRL",
            modules,
          },
        });
      return Promise.resolve({ data: [] });
    }) as never);
  };

  it("renders one checkbox per bundle, sums the price, and sends every member", async () => {
    serve([
      row("assets", "assets", { monthly_price: 10 }),
      row("inventory", "assets", { monthly_price: 5 }),
      row("documents", null),
      row("brand_new", null),
    ]);
    mockedPut.mockReturnValue(new Promise(() => {}));
    wrap(<SubscriptionPage />);

    const bundle = await screen.findByRole("checkbox", {
      name: bundleLabel("assets"),
    });
    expect(screen.getByText("15 BRL")).toBeTruthy();
    expect(screen.queryByRole("checkbox", { name: name("assets") })).toBeNull();
    expect(screen.getByRole("checkbox", { name: "modules.names.brand_new" })).toBeTruthy();

    await userEvent.click(bundle);
    expect((bundle as HTMLInputElement).checked).toBe(false);
    await userEvent.click(
      screen.getByRole("button", { name: pt.subscription.save }),
    );

    await waitFor(() => expect(mockedPut).toHaveBeenCalled());
    expect(mockedPut).toHaveBeenCalledWith("/subscription/modules", {
      active_modules: ["documents", "brand_new"],
    });
  });

  it("falls back to individual rows when a bundle is not wholly in the plan", async () => {
    serve([
      row("assets", "assets"),
      row("inventory", "assets", { in_plan: false, source: null }),
    ]);
    wrap(<SubscriptionPage />);

    expect(
      await screen.findByRole("checkbox", { name: name("assets") }),
    ).toBeTruthy();
    expect(screen.getByTestId("subscription-row-inventory")).toBeTruthy();
  });
});

describe("unitsOf", () => {
  it("emits a bundle once across groups and keeps unbundled modules single", () => {
    const bundleOf = (m: string) => (m === "a" || m === "b" ? "ab" : null);
    const groups = [
      { key: "g1", modules: ["a", "c"] },
      { key: "g2", modules: ["b", "d", "missing"] },
    ];
    const emitted = new Set<string>();
    const all = ["a", "b", "c", "d"];

    expect(unitsOf(groups[0], bundleOf, all, emitted)).toEqual([
      ["a", "b"],
      ["c"],
    ]);
    expect(unitsOf(groups[1], bundleOf, all, emitted)).toEqual([["d"]]);
    expect(groupsCovering(["brand_new"]).at(-1)?.modules).toEqual(["brand_new"]);
  });
});
