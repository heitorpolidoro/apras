import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QuoteFormModal } from "../components/QuoteFormModal";
import type { PurchaseQuote } from "../../../types/purchase";

const existingQuote: PurchaseQuote = {
  id: "quote-1",
  purchase_request_id: "req-1",
  supplier_name: "Bombas & Cia",
  supplier_contact: "(11) 3333-0000",
  unit_price: 300,
  quantity: 3,
  notes: "Frete incluso",
  extra_fields: [{ label: "Prazo", value: "20 dias" }],
  total_price: 900,
  created_by_id: "user-1",
  created_by_name: "Gerente",
  is_selected: false,
  is_lowest_price: false,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("QuoteFormModal", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <QuoteFormModal isOpen={false} onClose={vi.fn()} quote={null} onSubmit={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("computes the total live from unit price and quantity", () => {
    render(<QuoteFormModal isOpen onClose={vi.fn()} quote={null} onSubmit={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Preço unitário (R$) *"), {
      target: { value: "125.5" },
    });
    fireEvent.change(screen.getByLabelText("Quantidade *"), {
      target: { value: "4" },
    });

    expect(screen.getByTestId("quote-total")).toHaveTextContent("502");
  });

  it("requires a supplier name", async () => {
    const onSubmit = vi.fn();
    render(<QuoteFormModal isOpen onClose={vi.fn()} quote={null} onSubmit={onSubmit} />);

    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(
      await screen.findByText("O nome do fornecedor é obrigatório."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("adds and removes extra-field rows and submits them", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<QuoteFormModal isOpen onClose={vi.fn()} quote={null} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Fornecedor *"), {
      target: { value: "Playground Kids" },
    });
    fireEvent.change(screen.getByLabelText("Preço unitário (R$) *"), {
      target: { value: "10" },
    });
    fireEvent.change(screen.getByLabelText("Quantidade *"), { target: { value: "2" } });

    const addButton = screen.getByRole("button", { name: "Adicionar campo" });
    fireEvent.click(addButton);
    fireEvent.click(addButton);
    fireEvent.click(addButton);
    expect(screen.getAllByTestId(/extra-field-label-/)).toHaveLength(3);

    fireEvent.click(screen.getAllByRole("button", { name: "Remover campo" })[2]);
    expect(screen.getAllByTestId(/extra-field-label-/)).toHaveLength(2);

    fireEvent.change(screen.getByTestId("extra-field-label-0"), {
      target: { value: " Prazo de entrega " },
    });
    fireEvent.change(screen.getByTestId("extra-field-value-0"), {
      target: { value: " 15 dias " },
    });
    fireEvent.change(screen.getByTestId("extra-field-label-1"), {
      target: { value: "Garantia" },
    });

    fireEvent.submit(screen.getByTestId("quote-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        supplier_name: "Playground Kids",
        supplier_contact: null,
        unit_price: 10,
        quantity: 2,
        notes: null,
        extra_fields: [
          { label: "Prazo de entrega", value: "15 dias" },
          { label: "Garantia", value: "" },
        ],
      });
    });
  });

  it("rejects a blank extra-field label before calling the API", async () => {
    const onSubmit = vi.fn();
    render(<QuoteFormModal isOpen onClose={vi.fn()} quote={null} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Fornecedor *"), {
      target: { value: "Fornecedor" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar campo" }));
    fireEvent.change(screen.getByTestId("extra-field-label-0"), {
      target: { value: "   " },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(
      await screen.findByText("Todo campo extra precisa de um rótulo."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects duplicate extra-field labels ignoring case and spaces", async () => {
    const onSubmit = vi.fn();
    render(<QuoteFormModal isOpen onClose={vi.fn()} quote={null} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Fornecedor *"), {
      target: { value: "Fornecedor" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar campo" }));
    fireEvent.click(screen.getByRole("button", { name: "Adicionar campo" }));
    fireEvent.change(screen.getByTestId("extra-field-label-0"), {
      target: { value: "Prazo" },
    });
    fireEvent.change(screen.getByTestId("extra-field-label-1"), {
      target: { value: " prazo " },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(
      await screen.findByText("Há rótulos repetidos entre os campos extras."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("stops adding extra fields at twenty rows", () => {
    render(<QuoteFormModal isOpen onClose={vi.fn()} quote={null} onSubmit={vi.fn()} />);

    const addButton = screen.getByRole("button", { name: "Adicionar campo" });
    for (let i = 0; i < 25; i += 1) {
      fireEvent.click(addButton);
    }

    expect(screen.getAllByTestId(/extra-field-label-/)).toHaveLength(20);
    expect(addButton).toBeDisabled();
    expect(
      screen.getByText("Um orçamento aceita no máximo 20 campos extras."),
    ).toBeInTheDocument();
  });

  it("prefills the form when editing an existing quote", () => {
    render(
      <QuoteFormModal isOpen onClose={vi.fn()} quote={existingQuote} onSubmit={vi.fn()} />,
    );

    expect(screen.getByText("Editar Orçamento")).toBeInTheDocument();
    expect(screen.getByLabelText("Fornecedor *")).toHaveValue("Bombas & Cia");
    expect(screen.getByLabelText("Quantidade *")).toHaveValue(3);
    expect(screen.getByTestId("extra-field-label-0")).toHaveValue("Prazo");
    expect(screen.getByTestId("extra-field-value-0")).toHaveValue("20 dias");
  });

  it("surfaces submission errors", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("409 congelado"));
    render(<QuoteFormModal isOpen onClose={vi.fn()} quote={null} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Fornecedor *"), {
      target: { value: "Fornecedor" },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(await screen.findByText("409 congelado")).toBeInTheDocument();
  });
});
