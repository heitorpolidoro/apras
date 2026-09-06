import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InfractionRulesPage } from "../pages/InfractionRulesPage";
import * as api from "../../../api/infractions";
import type { InfractionRule } from "../../../types/infraction";

vi.mock("../../../api/infractions");

const rule = (overrides: Partial<InfractionRule> = {}): InfractionRule => ({
  id: "rule-1",
  article: "art. 12",
  origin: "REGIMENTO_INTERNO",
  description: "Sossego",
  recidivism_window_days: 365,
  is_active: true,
  steps: [
    { id: "s1", step_order: 1, action: "AVISO" },
    {
      id: "s2",
      step_order: 2,
      action: "NOTIFICACAO",
      defense_deadline_days: 30,
    },
  ],
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  ...overrides,
});

const renderPage = () =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <InfractionRulesPage />
    </QueryClientProvider>,
  );

describe("InfractionRulesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getInfractionRules).mockResolvedValue([rule()]);
    vi.mocked(api.getInfractionSettings).mockResolvedValue({
      condo_fee_amount: null,
      updated_at: null,
      updated_by: null,
    });
  });

  it("renders the catalogue, deactivated rules included", async () => {
    vi.mocked(api.getInfractionRules).mockResolvedValue([
      rule(),
      rule({ id: "rule-2", article: "art. 30", is_active: false }),
    ]);

    renderPage();

    expect(await screen.findByTestId("rule-row-rule-1")).toBeInTheDocument();
    // A withdrawn article has to stay visible, or the síndico cannot tell an
    // absent rule from a retired one.
    expect(screen.getByTestId("rule-inactive-rule-2")).toBeInTheDocument();
    expect(screen.getByTestId("deactivate-rule-2")).toBeDisabled();
  });

  it("creates a rule from the form", async () => {
    vi.mocked(api.createInfractionRule).mockResolvedValue(rule());

    renderPage();
    await screen.findByTestId("rule-row-rule-1");

    fireEvent.change(screen.getByLabelText("Artigo"), {
      target: { value: "art. 44" },
    });
    fireEvent.change(screen.getByLabelText("Descrição"), {
      target: { value: "Uso indevido da área comum." },
    });
    fireEvent.click(screen.getByTestId("submit-new-rule"));

    await waitFor(() =>
      expect(vi.mocked(api.createInfractionRule)).toHaveBeenCalledWith({
        article: "art. 44",
        origin: "REGIMENTO_INTERNO",
        description: "Uso indevido da área comum.",
        recidivism_window_days: 365,
      }),
    );
  });

  it("adds, reorders and removes ladder steps, renumbering from 1", async () => {
    vi.mocked(api.writeInfractionPolicy).mockResolvedValue(rule());

    renderPage();
    await screen.findByTestId("rule-row-rule-1");

    fireEvent.click(screen.getByTestId("edit-policy-rule-1"));
    expect(screen.getByTestId("policy-editor")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^policy-step-/)).toHaveLength(2);

    fireEvent.click(screen.getByTestId("add-step"));
    expect(screen.getAllByTestId(/^policy-step-/)).toHaveLength(3);

    // Reordering must renumber, or "contiguous from 1" would be a lie the API
    // answers 422 for.
    fireEvent.click(screen.getByTestId("move-up-2"));
    fireEvent.click(screen.getByTestId("remove-step-0"));
    expect(screen.getAllByTestId(/^policy-step-/)).toHaveLength(2);

    fireEvent.click(screen.getByTestId("save-policy"));
    await waitFor(() =>
      expect(vi.mocked(api.writeInfractionPolicy)).toHaveBeenCalled(),
    );
    const [, steps] = vi.mocked(api.writeInfractionPolicy).mock.calls[0];
    expect(steps.map((step) => step.step_order)).toEqual([1, 2]);
  });

  it("shows the fine fields only for a MULTA step, and by mode", async () => {
    renderPage();
    await screen.findByTestId("rule-row-rule-1");
    fireEvent.click(screen.getByTestId("edit-policy-rule-1"));

    // Step 1 is an AVISO: no deadline, no fine fields.
    expect(screen.queryByLabelText("Modo da multa")).not.toBeInTheDocument();
    // Step 2 is a NOTIFICACAO: a deadline, still no fine.
    expect(screen.getByLabelText("Prazo (dias)")).toBeInTheDocument();

    const [firstAction] = screen.getAllByLabelText("Ação");
    fireEvent.change(firstAction, { target: { value: "MULTA" } });
    expect(screen.getByLabelText("Modo da multa")).toBeInTheDocument();
    expect(screen.queryByLabelText("Valor")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Modo da multa"), {
      target: { value: "FIXED" },
    });
    expect(screen.getByLabelText("Valor")).toBeInTheDocument();
    expect(screen.queryByLabelText("Multiplicador")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Modo da multa"), {
      target: { value: "MULTIPLE" },
    });
    expect(screen.getByLabelText("Multiplicador")).toBeInTheDocument();
  });

  it("writes the condominium-fee reference", async () => {
    vi.mocked(api.writeInfractionSettings).mockResolvedValue({
      condo_fee_amount: 850,
      updated_at: "2026-09-05T00:00:00",
      updated_by: { id: "u-1", full_name: "Síndico" },
    });

    renderPage();
    await screen.findByTestId("rule-row-rule-1");

    fireEvent.change(screen.getByLabelText("Valor da taxa"), {
      target: { value: "850" },
    });
    fireEvent.click(screen.getByTestId("save-settings"));

    await waitFor(() =>
      expect(vi.mocked(api.writeInfractionSettings)).toHaveBeenCalledWith(850),
    );
  });
});
