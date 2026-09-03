import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import PlansAdminPage from "../pages/PlansAdminPage";

const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

/**
 * The superuser plan catalogue (APRAS-40 §8.4).
 *
 * The module checklist excludes core modules: a plan cannot "include" what is
 * always on, so offering the checkbox would be offering a guaranteed 400.
 * There is no delete button either — `plan_id` is `ON DELETE RESTRICT` and
 * deactivation is the operation.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);

const PLAN = {
  id: "p-1",
  name: "Plano Básico",
  description: null,
  included_modules: ["finance"],
  base_price: 100,
  module_prices: { finance: 49 },
  currency: "BRL",
  is_active: true,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

const SUBSCRIPTION = {
  tenant_id: "t-1",
  plan: null,
  status: null,
  started_at: null,
  notes: null,
  estimated_monthly_total: null,
  currency: null,
  modules: [
    { module: "billing", is_core: true, is_active: true, in_plan: false, courtesy: false, can_contract: false, monthly_price: null, source: "CORE" },
    { module: "roles", is_core: true, is_active: true, in_plan: false, courtesy: false, can_contract: false, monthly_price: null, source: "CORE" },
    { module: "finance", is_core: false, is_active: true, in_plan: false, courtesy: false, can_contract: false, monthly_price: null, source: "UNMANAGED" },
    { module: "assets", is_core: false, is_active: true, in_plan: false, courtesy: false, can_contract: false, monthly_price: null, source: "UNMANAGED" },
  ],
};

const renderPage = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(<PlansAdminPage />, { wrapper: Wrapper });
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPost.mockReset();
  mockedPatch.mockReset();
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/plans/") return Promise.resolve({ data: [PLAN] });
    if (url === "/subscription") return Promise.resolve({ data: SUBSCRIPTION });
    return Promise.resolve({ data: [] });
  }) as never);
});

describe("PlansAdminPage", () => {
  it("lists the catalogue and excludes core modules from the checklist", async () => {
    renderPage();

    await waitFor(() =>
      expect(screen.getByText(PLAN.name)).toBeInTheDocument(),
    );
    expect(
      screen.getByLabelText(t("modules.names.finance")),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(t("modules.names.billing"))).toBeNull();
    expect(screen.queryByLabelText(t("modules.names.roles"))).toBeNull();
  });

  it("creates a plan with the checked modules and their prices", async () => {
    mockedPost.mockResolvedValue({ data: PLAN } as never);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByText(PLAN.name)).toBeInTheDocument(),
    );
    await user.type(screen.getByLabelText(t("plans.name")), "Plano Novo");
    await user.click(screen.getByLabelText(t("modules.names.assets")));
    await user.click(screen.getByRole("button", { name: t("plans.save") }));

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1));
    const [url, body] = mockedPost.mock.calls[0];
    expect(url).toBe("/plans/");
    expect(body).toMatchObject({
      name: "Plano Novo",
      included_modules: ["assets"],
      currency: "BRL",
      is_active: true,
    });
  });

  it("edits an existing plan through PATCH, including deactivation", async () => {
    mockedPatch.mockResolvedValue({ data: { ...PLAN, is_active: false } } as never);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: t("plans.edit") }));
    await user.click(screen.getByLabelText(t("plans.isActive")));
    await user.click(screen.getByRole("button", { name: t("plans.save") }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalledTimes(1));
    const [url, body] = mockedPatch.mock.calls[0];
    expect(url).toBe("/plans/p-1");
    expect(body).toMatchObject({ name: PLAN.name, is_active: false });
    // No DELETE anywhere on the screen: deactivation is the operation.
    expect(mockedPatch).toHaveBeenCalled();
  });

  it("drops a module's price when the module leaves the plan", async () => {
    mockedPatch.mockResolvedValue({ data: PLAN } as never);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: t("plans.edit") }));
    await user.click(screen.getByLabelText(t("modules.names.finance")));
    await user.click(screen.getByRole("button", { name: t("plans.save") }));

    await waitFor(() => expect(mockedPatch).toHaveBeenCalledTimes(1));
    const [, body] = mockedPatch.mock.calls[0];
    expect(body).toMatchObject({ included_modules: [], module_prices: {} });
  });

  it("sets a module price, and the New button clears the form back to a draft", async () => {
    mockedPost.mockResolvedValue({ data: PLAN } as never);
    const user = userEvent.setup();
    renderPage();

    // Start from an existing plan, then abandon it: `New` must not leave the
    // edited plan's id behind, or Save would silently PATCH the wrong row.
    await user.click(await screen.findByRole("button", { name: t("plans.edit") }));
    expect(screen.getByLabelText(t("plans.name"))).toHaveValue(PLAN.name);

    await user.click(screen.getByRole("button", { name: t("plans.new") }));
    expect(screen.getByLabelText(t("plans.name"))).toHaveValue("");

    await user.type(screen.getByLabelText(t("plans.name")), "Plano Precificado");
    await user.click(screen.getByLabelText(t("modules.names.finance")));
    const price = screen.getByLabelText(
      `${t("plans.modulePrices")} ${t("modules.names.finance")}`,
    );
    await user.clear(price);
    await user.type(price, "49");
    await user.click(screen.getByRole("button", { name: t("plans.save") }));

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1));
    expect(mockedPatch).not.toHaveBeenCalled();
    const [, body] = mockedPost.mock.calls[0];
    expect(body).toMatchObject({
      included_modules: ["finance"],
      module_prices: { finance: 49 },
    });
  });

  it("renders the empty state and then the load error", async () => {
    mockedGet.mockImplementation(((url: string) => {
      if (url === "/plans/") return Promise.resolve({ data: [] });
      if (url === "/subscription") return Promise.resolve({ data: SUBSCRIPTION });
      return Promise.resolve({ data: [] });
    }) as never);
    const { unmount } = renderPage();
    expect(await screen.findByText(t("plans.empty"))).toBeInTheDocument();
    unmount();

    mockedGet.mockImplementation(((url: string) => {
      if (url === "/plans/") return Promise.reject(new Error("500"));
      if (url === "/subscription") return Promise.resolve({ data: SUBSCRIPTION });
      return Promise.resolve({ data: [] });
    }) as never);
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      t("plans.loadError"),
    );
  });

  it("renders the error when the API refuses the plan", async () => {
    mockedPost.mockRejectedValue(new Error("400") as never);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByText(PLAN.name)).toBeInTheDocument(),
    );
    await user.type(screen.getByLabelText(t("plans.name")), "Plano Torto");
    await user.click(screen.getByRole("button", { name: t("plans.save") }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(t("plans.saveError")),
    );
  });
});
