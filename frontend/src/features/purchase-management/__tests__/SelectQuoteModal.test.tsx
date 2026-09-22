import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SelectQuoteModal } from "../components/SelectQuoteModal";
import { computeGap } from "../utils/comparison";
import type { PurchaseQuote } from "../../../types/purchase";

const quote: PurchaseQuote = {
  id: "quote-1",
  purchase_request_id: "req-1",
  supplier_name: "Hidráulica Central",
  supplier_contact: null,
  items: [
    {
      id: "qi-1",
      request_item_id: "ri-1",
      model: null,
      unit_price: 1200,
      description: "Bomba submersa",
      quantity: 2,
      position: 0,
      line_total: 2400,
    },
  ],
  quoted_item_count: 1,
  is_complete: true,
  notes: null,
  extra_fields: [],
  attachment_url: null,
  attachment_filename: null,
  total_price: 2400,
  created_by_id: "user-1",
  created_by_name: "Gerente",
  is_selected: false,
  is_lowest_price: true,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

const lowestQuote: PurchaseQuote = {
  ...quote,
  id: "quote-lowest",
  supplier_name: "Eletro Norte",
  total_price: 2940,
  is_lowest_price: true,
};

const dearerQuote: PurchaseQuote = {
  ...quote,
  id: "quote-dearer",
  supplier_name: "Luz & Cia Elétrica",
  total_price: 3478.8,
  is_lowest_price: false,
};

describe("computeGap", () => {
  it("is null when the quote being decided is a lowest one", () => {
    expect(computeGap(lowestQuote, lowestQuote)).toBeNull();
  });

  it("is null when no lowest quote is known", () => {
    expect(computeGap(dearerQuote, null)).toBeNull();
  });

  it("is null for a tie, because both quotes carry is_lowest_price", () => {
    const tied = { ...dearerQuote, total_price: 2940, is_lowest_price: true };
    expect(computeGap(tied, lowestQuote)).toBeNull();
  });

  it("is null when the lowest total is zero, rather than dividing by it", () => {
    expect(
      computeGap(dearerQuote, { ...lowestQuote, total_price: 0 }),
    ).toBeNull();
  });

  it("is the difference in reais and in percent of the lowest total", () => {
    const gap = computeGap(dearerQuote, lowestQuote);
    expect(gap?.difference).toBeCloseTo(538.8, 2);
    expect(gap?.percent).toBeCloseTo(18.3, 1);
  });

  it("is null for an incomplete quote, however it compares (APRAS-73 D10)", () => {
    // A partial offer's distance from a full one is not a price
    // difference: the modal states the coverage instead.
    const partial = { ...dearerQuote, is_complete: false };
    expect(computeGap(partial, lowestQuote)).toBeNull();
  });
});

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

  it("states the gap in reais and in percent, naming the lowest supplier", () => {
    render(
      <SelectQuoteModal
        isOpen
        onClose={vi.fn()}
        quote={dearerQuote}
        lowestQuote={lowestQuote}
        onSubmit={vi.fn()}
      />,
    );

    const panel = screen.getByTestId("decision-gap");
    expect(panel).toHaveTextContent("Este não é o menor orçamento.");
    expect(panel).toHaveTextContent("Eletro Norte");
    expect(panel).toHaveTextContent("R$ 2.940,00");
    expect(panel).toHaveTextContent("R$ 538,80");
    expect(panel).toHaveTextContent("18.3%");
  });

  it("renders no gap panel when the quote being decided is the lowest one", () => {
    render(
      <SelectQuoteModal
        isOpen
        onClose={vi.fn()}
        quote={lowestQuote}
        lowestQuote={lowestQuote}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("decision-gap")).toBeNull();
    // …and the flow is the one that already existed.
    expect(
      screen.getByRole("button", { name: "Confirmar Escolha" }),
    ).toBeDisabled();
  });

  it("renders no gap panel when no lowest quote is passed at all", () => {
    render(
      <SelectQuoteModal
        isOpen
        onClose={vi.fn()}
        quote={dearerQuote}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("decision-gap")).toBeNull();
  });

  it("warns about coverage, and renders no gap, for an incomplete quote", () => {
    render(
      <SelectQuoteModal
        isOpen
        onClose={vi.fn()}
        quote={{ ...dearerQuote, is_complete: false, quoted_item_count: 2 }}
        lowestQuote={lowestQuote}
        requestItemCount={3}
        onSubmit={vi.fn()}
      />,
    );

    const panel = screen.getByTestId("decision-coverage-warning");
    expect(panel).toHaveTextContent("Este orçamento cobre 2 de 3 itens.");
    expect(panel).toHaveTextContent("não atende o pedido inteiro");
    expect(screen.queryByTestId("decision-gap")).toBeNull();
  });

  it("renders the gap and no coverage warning for a complete quote", () => {
    render(
      <SelectQuoteModal
        isOpen
        onClose={vi.fn()}
        quote={dearerQuote}
        lowestQuote={lowestQuote}
        requestItemCount={1}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByTestId("decision-gap")).toBeInTheDocument();
    expect(screen.queryByTestId("decision-coverage-warning")).toBeNull();
  });

  it("prints the coverage and the total in the head panel", () => {
    render(
      <SelectQuoteModal
        isOpen
        onClose={vi.fn()}
        quote={quote}
        requestItemCount={1}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByText("Hidráulica Central")).toBeInTheDocument();
    expect(screen.getByText(/Cobertura: 1 de 1 itens/)).toBeInTheDocument();
    expect(screen.getByText("R$ 2.400,00")).toBeInTheDocument();
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
