import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PurchaseRequestFormModal } from "../components/PurchaseRequestFormModal";
import type { PurchaseRequest } from "../../../types/purchase";
import { PurchaseRequestStatus } from "../../../types/purchase";

const request: PurchaseRequest = {
  id: "req-1",
  title: "Troca das bombas",
  description: "Duas bombas submersas",
  general_notes: "Falar com o zelador",
  status: PurchaseRequestStatus.OPEN,
  requested_by_id: "user-1",
  requested_by_name: "Diretor",
  items: [
    { id: "ri-a", description: "Bomba submersa", quantity: 2, position: 0 },
    { id: "ri-b", description: "Mão de obra", quantity: 1, position: 1 },
  ],
  quote_count: 0,
  lowest_quote_total: null,
  selected_quote_id: null,
  selected_quote_total: null,
  decision_justification: null,
  decided_at: null,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("PurchaseRequestFormModal", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <PurchaseRequestFormModal
        isOpen={false}
        onClose={vi.fn()}
        request={null}
        onSubmit={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("submits title, description and general notes", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={onClose}
        request={null}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByText("Novo Pedido de Compra")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Título do Pedido *"), {
      target: { value: "  Compra de lâmpadas  " },
    });
    fireEvent.change(
      screen.getByLabelText("Descrição do que será comprado"),
      { target: { value: "50 lâmpadas LED 9W" } },
    );
    fireEvent.change(screen.getByLabelText("Anotações gerais do pedido"), {
      target: { value: "Prazo até sexta" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        title: "Compra de lâmpadas",
        description: "50 lâmpadas LED 9W",
        general_notes: "Prazo até sexta",
      });
    });
    // An enumeration nobody touched must not travel: the server skips the
    // frozen-quote guard only when the key is absent, and `items: []` is not
    // absent (D7).
    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty("items");
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("requires a title", async () => {
    const onSubmit = vi.fn();
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={null}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    expect(
      await screen.findByText("O título do pedido é obrigatório."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("prefills and sends nulls for cleared optional fields when editing", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={request}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByText("Editar Pedido de Compra")).toBeInTheDocument();
    expect(screen.getByLabelText("Título do Pedido *")).toHaveValue(
      "Troca das bombas",
    );

    fireEvent.change(screen.getByLabelText("Anotações gerais do pedido"), {
      target: { value: "" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        title: "Troca das bombas",
        description: "Duas bombas submersas",
        general_notes: null,
      });
    });
    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty("items");
  });

  it("sends the whole enumeration once a line is edited", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={request}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByTestId("request-item-quantity-0"), {
      target: { value: "3" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          items: [
            { id: "ri-a", description: "Bomba submersa", quantity: 3 },
            { id: "ri-b", description: "Mão de obra", quantity: 1 },
          ],
        }),
      );
    });
  });

  it.each([
    PurchaseRequestStatus.DECIDED,
    PurchaseRequestStatus.CANCELLED,
  ])("edits the free text of a %s request without touching its lines", async (
    status,
  ) => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={{ ...request, status }}
        quoteCount={2}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Título do Pedido *"), {
      target: { value: "Troca das bombas d'água" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        title: "Troca das bombas d'água",
        description: "Duas bombas submersas",
        general_notes: "Falar com o zelador",
      });
    });
    // The server refuses `items` on a request whose quotes are frozen; sending
    // the key at all would turn this free-text edit into a 409.
    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty("items");
  });

  it.each([
    PurchaseRequestStatus.DECIDED,
    PurchaseRequestStatus.CANCELLED,
  ])("shows the lines of a %s request read-only", (status) => {
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={{ ...request, status }}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Adicionar item" })).toBeNull();
    expect(screen.queryByTestId("request-item-description-0")).toBeNull();
    expect(screen.queryByRole("button", { name: "Remover item" })).toBeNull();
    expect(screen.getByTestId("request-items-locked")).toHaveTextContent(
      "Os itens de um pedido decidido ou cancelado não podem ser alterados.",
    );
    expect(screen.getByTestId("request-item-readonly-ri-a")).toHaveTextContent(
      "2 × Bomba submersa",
    );
  });

  it("adds a line, renumbering nothing client-side", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={null}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Título do Pedido *"), {
      target: { value: "Instalação de CFTV" },
    });
    const add = screen.getByRole("button", { name: "Adicionar item" });
    fireEvent.click(add);
    fireEvent.click(add);
    fireEvent.change(screen.getByTestId("request-item-description-0"), {
      target: { value: "  Câmeras IP 4MP  " },
    });
    fireEvent.change(screen.getByTestId("request-item-quantity-0"), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByTestId("request-item-description-1"), {
      target: { value: "Instalação" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          items: [
            { description: "Câmeras IP 4MP", quantity: 4 },
            { description: "Instalação", quantity: 1 },
          ],
        }),
      );
    });
  });

  it("refuses a line with no description or a zero quantity", async () => {
    const onSubmit = vi.fn();
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={null}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Título do Pedido *"), {
      target: { value: "Pedido" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar item" }));
    fireEvent.submit(screen.getByTestId("purchase-request-form"));
    expect(
      await screen.findByText("Todo item avulso precisa de uma descrição."),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByTestId("request-item-description-0"), {
      target: { value: "Câmeras" },
    });
    fireEvent.change(screen.getByTestId("request-item-quantity-0"), {
      target: { value: "0" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));
    expect(
      await screen.findByText("A quantidade deve ser maior que zero."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("warns before submit when a line quotes priced is removed", () => {
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={request}
        quoteCount={3}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("request-item-removal-warning")).toBeNull();

    fireEvent.click(screen.getAllByRole("button", { name: "Remover item" })[0]);

    expect(screen.getByTestId("request-item-removal-warning")).toHaveTextContent(
      "Ao remover este item, os preços já lançados por 3 orçamento(s) para "
        + "ele serão apagados.",
    );
  });

  it("surfaces submission errors", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("Erro do servidor"));
    render(
      <PurchaseRequestFormModal
        isOpen
        onClose={vi.fn()}
        request={null}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Título do Pedido *"), {
      target: { value: "Pedido" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    expect(await screen.findByText("Erro do servidor")).toBeInTheDocument();
  });
});
