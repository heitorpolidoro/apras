import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QuoteFormModal } from "../components/QuoteFormModal";
import type {
  PurchaseQuote,
  PurchaseRequestItem,
} from "../../../types/purchase";

const requestItems: PurchaseRequestItem[] = [
  { id: "ri-cam", description: "Câmeras IP 4MP", quantity: 4, position: 0 },
  { id: "ri-install", description: "Instalação", quantity: 1, position: 1 },
];

const existingQuote: PurchaseQuote = {
  id: "quote-1",
  purchase_request_id: "req-1",
  supplier_name: "Bombas & Cia",
  supplier_contact: "(11) 3333-0000",
  items: [
    {
      id: "qi-cam",
      request_item_id: "ri-cam",
      model: "Intelbras VIP 5432",
      unit_price: 300,
      description: "Câmeras IP 4MP",
      quantity: 4,
      position: 0,
      line_total: 1200,
    },
    {
      id: "qi-extra",
      request_item_id: null,
      model: null,
      unit_price: 90,
      description: "Nobreak",
      quantity: 2,
      position: 1,
      line_total: 180,
    },
  ],
  quoted_item_count: 1,
  is_complete: false,
  notes: "Frete incluso",
  extra_fields: [{ label: "Prazo", value: "20 dias" }],
  attachment_url: null,
  attachment_filename: null,
  total_price: 1380,
  created_by_id: "user-1",
  created_by_name: "Gerente",
  is_selected: false,
  is_lowest_price: false,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

const renderForm = (
  props: Partial<React.ComponentProps<typeof QuoteFormModal>> = {},
) =>
  render(
    <QuoteFormModal
      isOpen
      onClose={vi.fn()}
      quote={null}
      requestItems={requestItems}
      onSubmit={vi.fn()}
      {...props}
    />,
  );

/** Fill the supplier and price the first request line. */
const priceFirstLine = (unitPrice = "10") => {
  fireEvent.change(screen.getByLabelText("Fornecedor *"), {
    target: { value: "Fornecedor" },
  });
  fireEvent.change(screen.getByTestId("quote-line-price-ri-cam"), {
    target: { value: unitPrice },
  });
};

describe("QuoteFormModal", () => {
  it("renders nothing when closed", () => {
    const { container } = renderForm({ isOpen: false });
    expect(container).toBeEmptyDOMElement();
  });

  it("renders one fixed row per request line, labelled quantity × description", () => {
    renderForm();

    expect(screen.getByText("4 × Câmeras IP 4MP")).toBeInTheDocument();
    expect(screen.getByText("1 × Instalação")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^quote-line-ri-/)).toHaveLength(2);
  });

  it("computes the line and the quote totals live", () => {
    renderForm();

    fireEvent.change(screen.getByTestId("quote-line-price-ri-cam"), {
      target: { value: "125.5" },
    });
    expect(screen.getByTestId("quote-line-total-ri-cam")).toHaveTextContent("502");
    expect(screen.getByTestId("quote-total")).toHaveTextContent("502");

    fireEvent.change(screen.getByTestId("quote-line-price-ri-install"), {
      target: { value: "98" },
    });
    expect(screen.getByTestId("quote-total")).toHaveTextContent("600");
  });

  it("shows `Não cotado` for a row left blank and posts no item for it", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ onSubmit });

    expect(screen.getByTestId("quote-line-total-ri-install")).toHaveTextContent(
      "Não cotado",
    );

    priceFirstLine("1450");
    fireEvent.submit(screen.getByTestId("quote-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          items: [
            { request_item_id: "ri-cam", model: null, unit_price: 1450 },
          ],
        }),
      );
    });
  });

  it("posts the offered model when the supplier named one", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ onSubmit });

    priceFirstLine("1450");
    fireEvent.change(screen.getByTestId("quote-line-model-ri-cam"), {
      target: { value: "  Intelbras VIP 5432  " },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          items: [
            {
              request_item_id: "ri-cam",
              model: "Intelbras VIP 5432",
              unit_price: 1450,
            },
          ],
        }),
      );
    });
  });

  it("adds a supplier extra line with its own description and quantity", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ onSubmit });

    priceFirstLine("100");
    fireEvent.click(screen.getByRole("button", { name: "Adicionar item" }));
    fireEvent.change(screen.getByTestId("quote-extra-description-0"), {
      target: { value: " Nobreak 1,2 kVA " },
    });
    fireEvent.change(screen.getByTestId("quote-extra-quantity-0"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByTestId("quote-extra-price-0"), {
      target: { value: "890" },
    });
    expect(screen.getByTestId("quote-extra-total-0")).toHaveTextContent("1.780");

    fireEvent.submit(screen.getByTestId("quote-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          items: [
            { request_item_id: "ri-cam", model: null, unit_price: 100 },
            {
              description: "Nobreak 1,2 kVA",
              quantity: 2,
              model: null,
              unit_price: 890,
            },
          ],
        }),
      );
    });
  });

  it("removes an extra line again", () => {
    renderForm();

    const add = screen.getByRole("button", { name: "Adicionar item" });
    fireEvent.click(add);
    fireEvent.click(add);
    expect(screen.getAllByTestId(/quote-extra-description-/)).toHaveLength(2);

    fireEvent.click(screen.getAllByRole("button", { name: "Remover item" })[1]);
    expect(screen.getAllByTestId(/quote-extra-description-/)).toHaveLength(1);
  });

  it("refuses to submit with no priced item at all", async () => {
    const onSubmit = vi.fn();
    renderForm({ onSubmit });

    fireEvent.change(screen.getByLabelText("Fornecedor *"), {
      target: { value: "Fornecedor" },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(
      await screen.findByText(
        "Informe o preço de ao menos um item para salvar o orçamento.",
      ),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("refuses an extra line with no description", async () => {
    const onSubmit = vi.fn();
    renderForm({ onSubmit });

    priceFirstLine();
    fireEvent.click(screen.getByRole("button", { name: "Adicionar item" }));
    fireEvent.change(screen.getByTestId("quote-extra-price-0"), {
      target: { value: "10" },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(
      await screen.findByText("Todo item avulso precisa de uma descrição."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("refuses an extra line whose quantity is zero", async () => {
    const onSubmit = vi.fn();
    renderForm({ onSubmit });

    priceFirstLine();
    fireEvent.click(screen.getByRole("button", { name: "Adicionar item" }));
    fireEvent.change(screen.getByTestId("quote-extra-description-0"), {
      target: { value: "Nobreak" },
    });
    fireEvent.change(screen.getByTestId("quote-extra-quantity-0"), {
      target: { value: "0" },
    });
    fireEvent.change(screen.getByTestId("quote-extra-price-0"), {
      target: { value: "10" },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(
      await screen.findByText("A quantidade deve ser maior que zero."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("requires a supplier name", async () => {
    const onSubmit = vi.fn();
    renderForm({ onSubmit });

    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(
      await screen.findByText("O nome do fornecedor é obrigatório."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("adds and removes extra-field rows and submits them", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ onSubmit });

    fireEvent.change(screen.getByLabelText("Fornecedor *"), {
      target: { value: "Playground Kids" },
    });
    fireEvent.change(screen.getByTestId("quote-line-price-ri-cam"), {
      target: { value: "10" },
    });

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
        items: [{ request_item_id: "ri-cam", model: null, unit_price: 10 }],
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
    renderForm({ onSubmit });

    priceFirstLine();
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
    renderForm({ onSubmit });

    priceFirstLine();
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
    renderForm();

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

  it("prefills the lines, the extras and the fields when editing a quote", () => {
    renderForm({ quote: existingQuote });

    expect(screen.getByText("Editar Orçamento")).toBeInTheDocument();
    expect(screen.getByLabelText("Fornecedor *")).toHaveValue("Bombas & Cia");
    expect(screen.getByTestId("quote-line-price-ri-cam")).toHaveValue(300);
    expect(screen.getByTestId("quote-line-model-ri-cam")).toHaveValue(
      "Intelbras VIP 5432",
    );
    // The line this supplier skipped comes back blank, not zero.
    expect(screen.getByTestId("quote-line-price-ri-install")).toHaveValue(null);
    expect(screen.getByTestId("quote-extra-description-0")).toHaveValue("Nobreak");
    expect(screen.getByTestId("quote-extra-quantity-0")).toHaveValue(2);
    expect(screen.getByTestId("extra-field-label-0")).toHaveValue("Prazo");
    expect(screen.getByTestId("extra-field-value-0")).toHaveValue("20 dias");
  });

  it("tells the user when the request enumerated nothing", () => {
    renderForm({ requestItems: [] });

    expect(screen.getByTestId("no-request-items")).toBeInTheDocument();
    expect(screen.queryAllByTestId(/^quote-line-ri-/)).toHaveLength(0);
  });

  it("surfaces submission errors", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("409 congelado"));
    renderForm({ onSubmit });

    priceFirstLine();
    fireEvent.submit(screen.getByTestId("quote-form"));

    expect(await screen.findByText("409 congelado")).toBeInTheDocument();
  });
});

describe("QuoteFormModal money input (APRAS-64, Decision 5)", () => {
  it("never lets a third decimal into a line price, typed or pasted", () => {
    renderForm();

    const unitPrice = screen.getByTestId("quote-line-price-ri-cam");

    // A `change` is what a keystroke and a paste both produce on a
    // controlled input, so one assertion covers both routes.
    fireEvent.change(unitPrice, { target: { value: "2.675" } });

    expect(unitPrice).toHaveValue(2.67);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/decim/i)).not.toBeInTheDocument();
  });

  it("truncates rather than rounds, and leaves two decimals alone", () => {
    renderForm();

    const unitPrice = screen.getByTestId("quote-line-price-ri-cam");

    fireEvent.change(unitPrice, { target: { value: "2.999" } });
    expect(unitPrice).toHaveValue(2.99);

    fireEvent.change(unitPrice, { target: { value: "1200.50" } });
    expect(unitPrice).toHaveValue(1200.5);
  });

  it("limits an extra line's price too", () => {
    renderForm();

    fireEvent.click(screen.getByRole("button", { name: "Adicionar item" }));
    const price = screen.getByTestId("quote-extra-price-0");
    fireEvent.change(price, { target: { value: "2.675" } });

    expect(price).toHaveValue(2.67);
  });

  it("leaves the non-money quantity input unconstrained", () => {
    renderForm();

    fireEvent.click(screen.getByRole("button", { name: "Adicionar item" }));
    const quantity = screen.getByTestId("quote-extra-quantity-0");
    fireEvent.change(quantity, { target: { value: "125" } });

    expect(quantity).toHaveValue(125);
  });
});
