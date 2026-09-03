import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import TenantSubscriptionsPage from "../pages/TenantSubscriptionsPage";

const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

/**
 * The superuser per-tenant subscription screen (APRAS-40 §8.4).
 *
 * Two levers that do different things: assigning a plan applies the ceiling
 * shrink-only, while a courtesy grant activates. The reason is required on
 * the courtesy lever because the history row is where it has to be
 * explainable afterwards.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPut = vi.mocked(apiClient.put);

const TENANTS = [
  { id: "t-1", name: "Condomínio A", is_active: true },
  { id: "t-2", name: "Condomínio B", is_active: true },
];

const PLANS = [
  {
    id: "p-1",
    name: "Plano Básico",
    description: null,
    included_modules: ["finance"],
    base_price: 100,
    module_prices: {},
    currency: "BRL",
    is_active: true,
    created_at: "2026-01-01T00:00:00",
    updated_at: "2026-01-01T00:00:00",
  },
];

const subscriptionOf = (tenantId: string) => ({
  tenant_id: tenantId,
  plan: PLANS[0],
  status: "ACTIVE",
  started_at: "2026-01-01T00:00:00",
  notes: null,
  estimated_monthly_total: 100,
  currency: "BRL",
  modules: [
    { module: "billing", is_core: true, is_active: true, in_plan: false, courtesy: false, can_contract: false, monthly_price: null, source: "CORE" },
    { module: "finance", is_core: false, is_active: true, in_plan: true, courtesy: false, can_contract: true, monthly_price: null, source: "PLAN" },
    { module: "assets", is_core: false, is_active: false, in_plan: false, courtesy: false, can_contract: false, monthly_price: null, source: null },
  ],
});

const renderPage = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(<TenantSubscriptionsPage />, { wrapper: Wrapper });
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPut.mockReset();
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/tenants") return Promise.resolve({ data: TENANTS });
    if (url === "/plans/") return Promise.resolve({ data: PLANS });
    if (url === "/tenants/t-1/subscription") {
      return Promise.resolve({ data: subscriptionOf("t-1") });
    }
    if (url === "/tenants/t-2/subscription") {
      return Promise.resolve({ data: subscriptionOf("t-2") });
    }
    return Promise.resolve({ data: [] });
  }) as never);
});

describe("TenantSubscriptionsPage", () => {
  it("pre-selects the first tenant and refetches when the select changes", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith("/tenants/t-1/subscription"),
    );

    await user.selectOptions(
      screen.getByLabelText(t("tenantSubscriptions.tenantLabel")),
      "t-2",
    );

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith("/tenants/t-2/subscription"),
    );
  });

  it("PUTs the chosen plan, status and notes", async () => {
    mockedPut.mockResolvedValue({ data: subscriptionOf("t-1") } as never);
    const user = userEvent.setup();
    renderPage();

    await user.selectOptions(
      await screen.findByLabelText(t("tenantSubscriptions.plan")),
      "p-1",
    );
    await user.selectOptions(
      screen.getByLabelText(t("tenantSubscriptions.status")),
      "SUSPENDED",
    );
    await user.type(
      screen.getByLabelText(t("tenantSubscriptions.notes")),
      "renegociado",
    );
    await user.click(
      screen.getByRole("button", { name: t("tenantSubscriptions.save") }),
    );

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith("/tenants/t-1/subscription", {
        plan_id: "p-1",
        status: "SUSPENDED",
        notes: "renegociado",
      }),
    );
  });

  it("refuses to grant courtesy without a reason, then PUTs with it", async () => {
    mockedPut.mockResolvedValue({ data: subscriptionOf("t-1") } as never);
    const user = userEvent.setup();
    renderPage();

    await screen.findByLabelText(t("modules.names.assets"));
    await user.click(screen.getByLabelText(t("modules.names.assets")));
    await user.click(
      screen.getByRole("button", { name: t("tenantSubscriptions.grantCourtesy") }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      t("tenantSubscriptions.reasonRequired"),
    );
    expect(mockedPut).not.toHaveBeenCalled();

    await user.type(
      screen.getByLabelText(t("tenantSubscriptions.reason")),
      "negociação",
    );
    await user.click(
      screen.getByRole("button", { name: t("tenantSubscriptions.grantCourtesy") }),
    );

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith(
        "/tenants/t-1/subscription/courtesy",
        { courtesy_modules: ["assets"], reason: "negociação" },
      ),
    );
  });

  it("shows the current plan and the inert-price notice", async () => {
    renderPage();

    // The name appears twice on purpose: once on the current-plan card and
    // once as the `<option>` the operator would pick.
    await waitFor(() =>
      expect(screen.getAllByText(PLANS[0].name).length).toBeGreaterThan(1),
    );
    expect(
      screen.getByText(t("tenantSubscriptions.inertPriceNotice")),
    ).toBeInTheDocument();
    // Likewise the status label: on the card, and in the `<select>`.
    expect(
      screen.getAllByText(t("subscription.status.ACTIVE")).length,
    ).toBeGreaterThan(1);
  });
});
