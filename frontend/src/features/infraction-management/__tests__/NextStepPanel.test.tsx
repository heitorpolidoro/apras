import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { NextStepPanel } from "../components/NextStepPanel";
import type { NextStep } from "../../../types/infraction";

const base: NextStep = {
  recidivism_count: 2,
  window_start: "2025-09-05",
  cycle_closed_at: null,
  stages_applied: 1,
  ladder_index: 4,
  suggested_step_order: 3,
  suggested_action: "MULTA",
  reason: "CLAMPED",
  defense_deadline_days: null,
  fine_amount: 250,
  fine_amount_unavailable_reason: null,
  is_saturated: true,
};

describe("NextStepPanel", () => {
  it("renders the suggestion, the recidivism count and the window", () => {
    render(<NextStepPanel nextStep={base} onApply={vi.fn()} />);

    expect(screen.getByTestId("recidivism-count")).toHaveTextContent("2");
    expect(screen.getByTestId("window-start")).toHaveTextContent("2025-09-05");
    expect(screen.getByTestId("suggested-action")).toHaveTextContent("Multa");
    expect(screen.getByTestId("suggested-fine")).toHaveTextContent("250.00");
    expect(screen.getByTestId("clamped-message")).toBeInTheDocument();
  });

  it("shows the fee-not-set message when a MULTIPLE step cannot be priced", () => {
    render(
      <NextStepPanel
        nextStep={{
          ...base,
          fine_amount: null,
          fine_amount_unavailable_reason: "CONDO_FEE_NOT_SET",
        }}
        onApply={vi.fn()}
      />,
    );

    expect(screen.getByTestId("fee-not-set")).toBeInTheDocument();
    expect(screen.queryByTestId("suggested-fine")).not.toBeInTheDocument();
  });

  it("NO_POLICY disables 'apply suggestion' but leaves the override enabled", () => {
    render(
      <NextStepPanel
        nextStep={{
          ...base,
          suggested_step_order: null,
          suggested_action: null,
          reason: "NO_POLICY",
          fine_amount: null,
          is_saturated: false,
        }}
        onApply={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("suggested-action")).not.toBeInTheDocument();
    expect(screen.getByTestId("no-policy-message")).toBeInTheDocument();
    expect(screen.getByTestId("apply-suggestion")).toBeDisabled();
    // The ladder is a suggestion engine, not a gate on staff judgement.
    expect(screen.getByTestId("override-select")).toBeEnabled();
  });

  it("applies the suggestion with a null action and the typed note", () => {
    const onApply = vi.fn();
    render(<NextStepPanel nextStep={base} onApply={onApply} />);

    fireEvent.change(screen.getByLabelText("Observação"), {
      target: { value: "Multa aplicada." },
    });
    fireEvent.click(screen.getByTestId("apply-suggestion"));

    expect(onApply).toHaveBeenCalledWith(null, "Multa aplicada.");
  });

  it("applies an explicit override with the chosen action", () => {
    const onApply = vi.fn();
    render(<NextStepPanel nextStep={base} onApply={onApply} />);

    fireEvent.change(screen.getByLabelText("Observação"), {
      target: { value: "Aviso, por decisão do síndico." },
    });
    fireEvent.change(screen.getByTestId("override-select"), {
      target: { value: "AVISO" },
    });
    fireEvent.click(screen.getByTestId("apply-override"));

    expect(onApply).toHaveBeenCalledWith("AVISO", "Aviso, por decisão do síndico.");
  });

  it("does not say the ladder is exhausted on the first application of the last step", () => {
    render(
      <NextStepPanel
        nextStep={{ ...base, ladder_index: 3, reason: "SUGGESTED" }}
        onApply={vi.fn()}
      />,
    );

    // `is_saturated` is true here and `CLAMPED` is not: they disagree at
    // exactly `ladder_index === n`, and the UI must follow `reason`.
    expect(screen.queryByTestId("clamped-message")).not.toBeInTheDocument();
    expect(screen.getByTestId("suggested-action")).toBeInTheDocument();
  });
});
