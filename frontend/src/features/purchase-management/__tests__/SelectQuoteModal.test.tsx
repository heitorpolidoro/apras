import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SelectQuoteModal } from "../components/SelectQuoteModal";
import type { PurchaseQuote } from "../../../types/purchase";

const quote: PurchaseQuote = {
  id: "quote-1",
  purchase_request_id: "req-1",
  supplier_name: "Hidráulica Central",
  supplier_contact: null,
  unit_price: 1200,
  quantity: 2,
  notes: null,
  extra_fields: [],
  total_price: 2400,
  created_by_id: "user-1",
  created_by_name: "Gerente",
  is_selected: false,
  is_lowest_price: true,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("SelectQuoteModal", () => {
  it("renders nothing when closed or without a quote", () => {
    const { container, rerender } = render(
      <SelectQuoteModal isOpen={false} onClose={vi.fn()} quote={quote} onSubmit={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();

    rerender(
      <SelectQuoteModal isOpen onClose={vi.fn()} quote={null} onSubmit={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the quote summary and the justification hint", () => {
    render(<SelectQuoteModal isOpen onClose={vi.fn()} quote={quote} onSubmit={vi.fn()} />);

    expect(screen.getByText("Escolher Orçamento")).toBeInTheDocument();
    expect(screen.getByText("Hidráulica Central")).toBeInTheDocument();
    expect(
      screen.getByText("A justificativa precisa ter ao menos 10 caracteres."),
    ).toBeInTheDocument();
  });

  it("keeps the confirm button disabled until the justification reaches 10 characters", () => {
    render(<SelectQuoteModal isOpen onClose={vi.fn()} quote={quote} onSubmit={vi.fn()} />);

    const confirm = screen.getByRole("button", { name: "Confirmar Escolha" });
    expect(confirm).toBeDisabled();

    const textarea = screen.getByLabelText("Justificativa da escolha *");
    fireEvent.change(textarea, { target: { value: "curtinha" } });
    expect(confirm).toBeDisabled();

    // Whitespace does not count towards the 10 characters.
    fireEvent.change(textarea, { target: { value: "   ok     " } });
    expect(confirm).toBeDisabled();

    fireEvent.change(textarea, { target: { value: "Menor preço e mesmo prazo." } });
    expect(confirm).toBeEnabled();
  });

  it("submits the trimmed justification with the quote id", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();
    render(<SelectQuoteModal isOpen onClose={onClose} quote={quote} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Justificativa da escolha *"), {
      target: { value: "  Menor preço com a mesma especificação.  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar Escolha" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        quote_id: "quote-1",
        justification: "Menor preço com a mesma especificação.",
      });
    });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("surfaces submission errors and stays open", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("403 proibido"));
    const onClose = vi.fn();
    render(<SelectQuoteModal isOpen onClose={onClose} quote={quote} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Justificativa da escolha *"), {
      target: { value: "Justificativa suficientemente longa." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar Escolha" }));

    expect(await screen.findByText("403 proibido")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("closes without submitting when cancelled", () => {
    const onClose = vi.fn();
    const onSubmit = vi.fn();
    render(<SelectQuoteModal isOpen onClose={onClose} quote={quote} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onClose).toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
