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
