import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CycleCloseModal } from "../components/CycleCloseModal";
import type {
  InfractionRuleSummary,
  ResidentSummary,
} from "../../../types/infraction";

const rule: InfractionRuleSummary = {
  id: "rule-1",
  article: "art. 12",
  origin: "REGIMENTO_INTERNO",
  description: "Sossego",
};

const responsible: ResidentSummary = {
  id: "res-1",
  full_name: "Maria Souza",
  lot_id: "lot-1",
};

const renderModal = (props: Record<string, unknown> = {}) =>
  render(
    <CycleCloseModal
      rule={rule}
      responsible={responsible}
      onClose={vi.fn()}
      onSubmit={vi.fn()}
      {...props}
    />,
  );

describe("CycleCloseModal", () => {
  it("pins the (rule, responsible) pair instead of offering a choice", () => {
    renderModal();

    // A cycle *is* `(rule, responsible)` (§6.2), and this modal is reached
    // from an infraction of that pair. An earlier draft offered a rule select,
    // which invited closing a cycle other than the one on screen -- one click
    // away, and silent, because a close against the wrong rule is a valid row.
    const pair = screen.getByTestId("cycle-close-pair");
    expect(pair).toHaveTextContent("art. 12");
    expect(pair).toHaveTextContent("Maria Souza");
    expect(screen.queryByLabelText("Regra")).not.toBeInTheDocument();
  });

  it("keeps submit disabled until a justification is typed (ER-9)", () => {
    renderModal();

    expect(screen.getByTestId("submit-cycle-close")).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Justificativa"), {
      target: { value: "   " },
    });
    // Whitespace is not a justification, and the API answers 422 for it.
    expect(screen.getByTestId("submit-cycle-close")).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Justificativa"), {
      target: { value: "Troca de inquilino." },
    });
    expect(screen.getByTestId("submit-cycle-close")).toBeEnabled();
  });

  it("says, in the confirmation, that nothing is deleted", () => {
    renderModal();

    expect(screen.getByTestId("cycle-close-warning")).toHaveTextContent(
      /Nada é apagado/,
    );
  });

  it("sends `lot_id: null` unless the audit-context box is ticked", () => {
    const onSubmit = vi.fn();
    renderModal({ lotId: "lot-1", onSubmit });

    fireEvent.change(screen.getByLabelText("Justificativa"), {
      target: { value: "Troca de inquilino." },
    });
    fireEvent.click(screen.getByTestId("submit-cycle-close"));

    expect(onSubmit).toHaveBeenCalledWith({
      rule_id: "rule-1",
      responsible_resident_id: "res-1",
      lot_id: null,
      justification: "Troca de inquilino.",
    });

    fireEvent.click(
      screen.getByLabelText("Registrar o lote como contexto de auditoria"),
    );
    fireEvent.click(screen.getByTestId("submit-cycle-close"));

    expect(onSubmit).toHaveBeenLastCalledWith(
      expect.objectContaining({ lot_id: "lot-1" }),
    );
  });

  it("offers no lot checkbox when there is no lot to record", () => {
    renderModal();

    expect(
      screen.queryByLabelText("Registrar o lote como contexto de auditoria"),
    ).not.toBeInTheDocument();
  });

  it("surfaces a refusal from the server", () => {
    renderModal({ error: "justification must not be empty" });

    expect(screen.getByTestId("cycle-close-error")).toHaveTextContent(
      "justification must not be empty",
    );
  });
});
