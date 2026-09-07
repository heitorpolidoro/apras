import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import type { SubscriptionChange } from "../../../types/subscription";
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

/**
 * One row per `SubscriptionChangeKind` (APRAS-52 §6.4), each with a distinct
 * author so a per-kind case can find its own row and nothing else.
 */
const HISTORY: SubscriptionChange[] = [
  {
    id: "h-1",
    kind: "COURTESY_REVOKE",
    modules_added: [],
    modules_removed: ["assets"],
    from_plan_name: null,
    to_plan_name: null,
    reason: "fim do trial",
    changed_by_id: "u-1",
    changed_by_name: "Operadora Rita",
    changed_at: "2026-05-05T10:00:00",
  },
  {
    id: "h-2",
    kind: "COURTESY_GRANT",
    modules_added: ["assets"],
    modules_removed: [],
    from_plan_name: null,
    to_plan_name: null,
    reason: "cortesia",
    changed_by_id: "u-2",
    changed_by_name: "Operador Bruno",
    changed_at: "2026-05-04T10:00:00",
  },
  {
    id: "h-3",
    kind: "OVERRIDE",
    modules_added: ["documents"],
    modules_removed: [],
    from_plan_name: null,
    to_plan_name: null,
    reason: "reparo",
    changed_by_id: "u-3",
    changed_by_name: "Operadora Célia",
    changed_at: "2026-05-03T10:00:00",
  },
  {
    id: "h-4",
    kind: "CONTRACTED",
    modules_added: ["finance"],
    modules_removed: ["projects"],
    from_plan_name: null,
    to_plan_name: null,
    reason: null,
    changed_by_id: "u-4",
    changed_by_name: "Síndica Ana",
    changed_at: "2026-05-02T10:00:00",
  },
  {
    id: "h-5",
    kind: "PLAN_CHANGE",
    modules_added: [],
    modules_removed: ["gate"],
    from_plan_name: "Plano Básico",
    to_plan_name: "Plano Pleno",
    reason: "renegociação",
    changed_by_id: "u-5",
    changed_by_name: "Operador Davi",
    changed_at: "2026-05-01T10:00:00",
  },
];

/** A page of `size` synthetic rows, for the Previous/Next cases. */
const page = (size: number, offset: number): SubscriptionChange[] =>
  Array.from({ length: size }, (_unused, index) => ({
    ...HISTORY[0],
    id: `p-${offset + index}`,
    changed_by_name: `Operador ${offset + index}`,
  }));

const historyCalls = (): number =>
  mockedGet.mock.calls.filter(
    (call) => String(call[0]).endsWith("/subscription/history"),
  ).length;

const historyRowOf = (kind: string): HTMLElement => {
  const cell = screen.getByText(t(`subscription.kind.${kind}`));
  const row = cell.closest("tr");
  if (row === null) throw new Error(`no row for ${kind}`);
  return row;
};

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
    if (url === "/tenants/t-1/subscription/history") {
      return Promise.resolve({ data: HISTORY });
    }
    if (url === "/tenants/t-2/subscription/history") {
      return Promise.resolve({ data: [] });
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

  // -- the change history (APRAS-52 §5.3) ----------------------------------

  it.each(HISTORY)(
    "renders the $kind row with its translated label, modules and author",
    async (entry) => {
      renderPage();

      await screen.findByRole("heading", {
        name: t("tenantSubscriptions.historyTitle"),
      });
      const row = historyRowOf(entry.kind);

      expect(
        within(row).getByText(t(`subscription.kind.${entry.kind}`)),
      ).toBeInTheDocument();
      expect(
        within(row).getByText(entry.changed_by_name as string),
      ).toBeInTheDocument();
      if (entry.modules_added.length > 0) {
        expect(
          within(row).getByText(entry.modules_added.join(", ")),
        ).toBeInTheDocument();
      }
      if (entry.modules_removed.length > 0) {
        expect(
          within(row).getByText(entry.modules_removed.join(", ")),
        ).toBeInTheDocument();
      }
      expect(within(row).getByText(entry.changed_at)).toBeInTheDocument();
    },
  );

  it("requests the first history page for the pre-selected tenant", async () => {
    renderPage();

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        "/tenants/t-1/subscription/history",
        { params: { skip: 0, limit: 20 } },
      ),
    );
  });

  it("renders the empty state when the tenant has no history", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("option", { name: TENANTS[1].name });
    await user.selectOptions(
      screen.getByLabelText(t("tenantSubscriptions.tenantLabel")),
      "t-2",
    );

    expect(
      await screen.findByText(t("tenantSubscriptions.historyEmpty")),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("pages with skip and limit", async () => {
    mockedGet.mockImplementation(((url: string, config?: { params?: { skip: number } }) => {
      if (url === "/tenants") return Promise.resolve({ data: TENANTS });
      if (url === "/plans/") return Promise.resolve({ data: PLANS });
      if (url === "/tenants/t-1/subscription") {
        return Promise.resolve({ data: subscriptionOf("t-1") });
      }
      if (url === "/tenants/t-1/subscription/history") {
        const skip = config?.params?.skip ?? 0;
        return Promise.resolve({ data: skip === 0 ? page(20, 0) : page(3, 20) });
      }
      return Promise.resolve({ data: [] });
    }) as never);
    const user = userEvent.setup();
    renderPage();

    const previous = await screen.findByRole("button", {
      name: t("tenantSubscriptions.previous"),
    });
    const next = screen.getByRole("button", {
      name: t("tenantSubscriptions.next"),
    });
    expect(previous).toBeDisabled();
    expect(next).toBeEnabled();
    expect(
      screen.getByText(t("tenantSubscriptions.page").replace("{{page}}", "1")),
    ).toBeInTheDocument();

    await user.click(next);

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        "/tenants/t-1/subscription/history",
        { params: { skip: 20, limit: 20 } },
      ),
    );
    expect(
      await screen.findByText(
        t("tenantSubscriptions.page").replace("{{page}}", "2"),
      ),
    ).toBeInTheDocument();
    // A short page is the last-page signal a bare list gives.
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: t("tenantSubscriptions.next") }),
      ).toBeDisabled(),
    );
    expect(
      screen.getByRole("button", { name: t("tenantSubscriptions.previous") }),
    ).toBeEnabled();

    await user.click(
      screen.getByRole("button", { name: t("tenantSubscriptions.previous") }),
    );

    expect(
      await screen.findByText(
        t("tenantSubscriptions.page").replace("{{page}}", "1"),
      ),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: t("tenantSubscriptions.previous") }),
      ).toBeDisabled(),
    );
  });

  it("resets the history page when the tenant changes", async () => {
    mockedGet.mockImplementation(((url: string, config?: { params?: { skip: number } }) => {
      if (url === "/tenants") return Promise.resolve({ data: TENANTS });
      if (url === "/plans/") return Promise.resolve({ data: PLANS });
      if (url === "/tenants/t-1/subscription") {
        return Promise.resolve({ data: subscriptionOf("t-1") });
      }
      if (url === "/tenants/t-2/subscription") {
        return Promise.resolve({ data: subscriptionOf("t-2") });
      }
      if (url === "/tenants/t-1/subscription/history") {
        const skip = config?.params?.skip ?? 0;
        return Promise.resolve({ data: skip === 0 ? page(20, 0) : page(3, 20) });
      }
      if (url === "/tenants/t-2/subscription/history") {
        return Promise.resolve({ data: HISTORY });
      }
      return Promise.resolve({ data: [] });
    }) as never);
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: t("tenantSubscriptions.next") }),
    );
    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        "/tenants/t-1/subscription/history",
        { params: { skip: 20, limit: 20 } },
      ),
    );

    await user.selectOptions(
      screen.getByLabelText(t("tenantSubscriptions.tenantLabel")),
      "t-2",
    );

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        "/tenants/t-2/subscription/history",
        { params: { skip: 0, limit: 20 } },
      ),
    );
    expect(mockedGet).not.toHaveBeenCalledWith(
      "/tenants/t-2/subscription/history",
      { params: { skip: 20, limit: 20 } },
    );
  });

  it("refreshes the history after a courtesy grant", async () => {
    mockedPut.mockResolvedValue({ data: subscriptionOf("t-1") } as never);
    const user = userEvent.setup();
    renderPage();

    await screen.findByLabelText(t("modules.names.assets"));
    await waitFor(() => expect(historyCalls()).toBe(1));

    await user.type(
      screen.getByLabelText(t("tenantSubscriptions.reason")),
      "negociação",
    );
    await user.click(
      screen.getByRole("button", {
        name: t("tenantSubscriptions.grantCourtesy"),
      }),
    );

    await waitFor(() => expect(historyCalls()).toBeGreaterThan(1));
  });

  it("refreshes the history after a plan change", async () => {
    mockedPut.mockResolvedValue({ data: subscriptionOf("t-1") } as never);
    const user = userEvent.setup();
    renderPage();

    await user.selectOptions(
      await screen.findByLabelText(t("tenantSubscriptions.plan")),
      "p-1",
    );
    await waitFor(() => expect(historyCalls()).toBe(1));

    await user.click(
      screen.getByRole("button", { name: t("tenantSubscriptions.save") }),
    );

    await waitFor(() => expect(historyCalls()).toBeGreaterThan(1));
  });
});
