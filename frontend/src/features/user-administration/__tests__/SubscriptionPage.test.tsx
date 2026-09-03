import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type React from "react";
import apiClient from "../../../api/client";
import pt from "../../../i18n/locales/pt.json";
import SubscriptionPage from "../pages/SubscriptionPage";
import type {
  ModuleEntitlement,
  Subscription,
  SubscriptionChange,
} from "../../../types/subscription";

/** The suite's `t` resolves against `pt.json` (`src/test/setup.ts`), so the
 *  assertions below name the key and read the same string the component
 *  renders — no literal is duplicated and a copy change cannot rot them. */
const t = (key: string): string =>
  key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)?.[part],
      pt,
    ) as string;

/**
 * The tenant-side subscription area (APRAS-40 §8.4).
 *
 * The module list has **exactly four mutually exclusive row states**, chosen
 * by a stated precedence — `OVERRIDE > COURTESY > PLAN > out-of-plan`, first
 * match wins — and there is one named case per state below. The one that
 * matters most is `test_the_payload_carries_only_the_contracted_set`: the
 * body is the plan-covered checkboxes and nothing else, so Save can neither
 * be a permanent 400 nor silently kill an operator override.
 */

vi.mock("../../../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPut = vi.mocked(apiClient.put);

const row = (
  module: string,
  overrides: Partial<ModuleEntitlement> = {},
): ModuleEntitlement => ({
  module,
  is_core: false,
  is_active: false,
  in_plan: false,
  courtesy: false,
  can_contract: false,
  monthly_price: null,
  source: null,
  ...overrides,
});

const PLAN = {
  id: "p-1",
  name: "Plano Básico",
  description: "Tudo o que o condomínio precisa",
  included_modules: ["documents", "finance", "projects"],
  base_price: 100,
  module_prices: { finance: 49 },
  currency: "BRL",
  is_active: true,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

/** One row per state: rule 3 (in plan), rule 2 (courtesy), rule 1 (override),
 *  rule 4 (out of plan), plus a core one and a plan-and-courtesy one. */
const MANAGED: Subscription = {
  tenant_id: "t-1",
  plan: PLAN,
  status: "ACTIVE",
  started_at: "2026-01-01T00:00:00",
  notes: null,
  estimated_monthly_total: 149,
  currency: "BRL",
  modules: [
    row("billing", { is_core: true, is_active: true, source: "CORE" }),
    row("documents", {
      in_plan: true,
      is_active: true,
      can_contract: true,
      source: "PLAN",
    }),
    row("finance", {
      in_plan: true,
      can_contract: true,
      monthly_price: 49,
      source: null,
    }),
    // In both sets: §4.7's priority makes it `"PLAN"`, so it is a rule-3
    // checkbox and it *is* in the payload.
    row("projects", {
      in_plan: true,
      courtesy: true,
      is_active: true,
      can_contract: true,
      source: "PLAN",
    }),
    row("assets", { courtesy: true, is_active: true, can_contract: true, source: "COURTESY" }),
    row("tasks", { is_active: true, source: "OVERRIDE" }),
    row("votes", {}),
  ],
};

const UNMANAGED: Subscription = {
  tenant_id: "t-1",
  plan: null,
  status: null,
  started_at: null,
  notes: null,
  estimated_monthly_total: null,
  currency: null,
  modules: [
    row("billing", { is_core: true, is_active: true, source: "CORE" }),
    row("documents", { is_active: true, source: "UNMANAGED" }),
    row("finance", { is_active: true, source: "UNMANAGED" }),
  ],
};

const HISTORY: SubscriptionChange[] = [
  {
    id: "h-1",
    kind: "CONTRACTED",
    modules_added: ["finance"],
    modules_removed: [],
    from_plan_name: null,
    to_plan_name: null,
    reason: null,
    changed_by_id: "u-1",
    changed_by_name: "Síndica",
    changed_at: "2026-02-02T10:00:00",
  },
  {
    id: "h-2",
    kind: "COURTESY_GRANT",
    modules_added: ["assets"],
    modules_removed: [],
    from_plan_name: null,
    to_plan_name: null,
    reason: "negociação",
    changed_by_id: "u-2",
    changed_by_name: "Operador",
    changed_at: "2026-02-01T10:00:00",
  },
];

const renderPage = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(<SubscriptionPage />, { wrapper: Wrapper });
};

const serve = (subscription: Subscription, history = HISTORY) => {
  mockedGet.mockImplementation(((url: string) => {
    if (url === "/subscription") return Promise.resolve({ data: subscription });
    if (url === "/subscription/history") return Promise.resolve({ data: history });
    return Promise.resolve({ data: [] });
  }) as never);
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockReset();
  mockedPut.mockReset();
  serve(MANAGED);
});

describe("SubscriptionPage", () => {
  it("renders the plan card with the inert-price notice", async () => {
    renderPage();

    await waitFor(() =>
      expect(screen.getByText(PLAN.name)).toBeInTheDocument(),
    );
    expect(screen.getByText(PLAN.description)).toBeInTheDocument();
    expect(
      screen.getByText(t("subscription.status.ACTIVE")),
    ).toBeInTheDocument();
    // ER-8: the amounts are display metadata and the screen says so.
    expect(
      screen.getAllByText(t("subscription.inertPriceNotice")).length,
    ).toBeGreaterThan(0);
  });

  it("renders a rule-3 in-plan module as an enabled checkbox", async () => {
    renderPage();

    const box = await screen.findByLabelText(t("modules.names.finance"));
    expect(box).toBeInTheDocument();
    expect(box).not.toBeChecked();
    expect((box as HTMLInputElement).disabled).toBe(false);
  });

  it("renders a rule-2 courtesy module with a badge, no checkbox and no price", async () => {
    renderPage();

    await screen.findByLabelText(t("modules.names.finance"));
    expect(screen.queryByLabelText(t("modules.names.assets"))).toBeNull();

    const courtesy = screen.getByTestId("subscription-row-assets");
    expect(courtesy).toHaveTextContent(t("subscription.courtesyBadge"));
    expect(courtesy).toHaveTextContent(t("subscription.free"));
  });

  it("renders a rule-1 override module with the operator badge and no checkbox", async () => {
    renderPage();

    await screen.findByLabelText(t("modules.names.finance"));
    expect(screen.queryByLabelText(t("modules.names.tasks"))).toBeNull();
    expect(screen.getByTestId("subscription-row-tasks")).toHaveTextContent(
      t("subscription.operatorBadge"),
    );
  });

  it("renders a rule-4 out-of-plan module with the hint and no checkbox", async () => {
    renderPage();

    await screen.findByLabelText(t("modules.names.finance"));
    expect(screen.queryByLabelText(t("modules.names.votes"))).toBeNull();
    expect(screen.getByTestId("subscription-row-votes")).toHaveTextContent(
      t("subscription.outOfPlan"),
    );
  });

  it("the payload carries only the contracted set", async () => {
    mockedPut.mockResolvedValue({ data: MANAGED } as never);
    const user = userEvent.setup();
    renderPage();

    // Tick the one in-plan module that is off. `assets` (courtesy) and
    // `tasks` (override) are active but have no checkbox, so they cannot be
    // sent; the server's `preserved` term keeps them active.
    await user.click(await screen.findByLabelText(t("modules.names.finance")));
    await user.click(screen.getByRole("button", { name: t("subscription.save") }));

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith("/subscription/modules", {
        // `projects` is in the plan *and* in the courtesy set, and §4.7 makes
        // it read `"PLAN"` -- so it is a checkbox and it IS in the payload.
        active_modules: ["documents", "finance", "projects"],
      }),
    );
    expect(mockedPut).toHaveBeenCalledTimes(1);
  });

  it("renders the not-entitled message when the PUT is refused", async () => {
    mockedPut.mockRejectedValue(new Error("400") as never);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByLabelText(t("modules.names.finance")));
    await user.click(screen.getByRole("button", { name: t("subscription.save") }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        t("subscription.notEntitled"),
      ),
    );
  });

  it("renders every module read-only and disables Save with no subscription", async () => {
    serve(UNMANAGED, []);
    renderPage();

    await waitFor(() =>
      expect(screen.getByText(t("subscription.noPlan"))).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText(t("modules.names.documents"))).toBeNull();
    expect(screen.queryByLabelText(t("modules.names.finance"))).toBeNull();
    expect(
      screen.getByRole("button", { name: t("subscription.save") }),
    ).toBeDisabled();
    expect(screen.getByText(t("subscription.empty"))).toBeInTheDocument();
  });

  it("renders one history row per kind, newest first", async () => {
    renderPage();

    await waitFor(() =>
      expect(
        screen.getByText(t("subscription.kind.CONTRACTED")),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByText(t("subscription.kind.COURTESY_GRANT")),
    ).toBeInTheDocument();
    expect(screen.getByText("Síndica")).toBeInTheDocument();
    expect(screen.getByText("negociação")).toBeInTheDocument();
  });
});
