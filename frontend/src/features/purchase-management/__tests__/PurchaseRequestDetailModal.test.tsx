import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PurchaseRequestDetailModal } from "../components/PurchaseRequestDetailModal";
import * as purchasesApi from "../../../api/purchases";
import type { PurchaseRequestDetail } from "../../../types/purchase";
import { PurchaseRequestStatus } from "../../../types/purchase";

import { PERMISSIONS_BY_ROLE } from "../../../test/permissionFixtures";

/**
 * The permission predicate a retired role value carried (IAM F5, §10.2).
 *
 * `PERMISSIONS_BY_ROLE` is the recorded legacy bundle, so a case that mocked
 * `role: "MANAGER"` and now mocks `hasOf("MANAGER")` asserts the **same**
 * outcome it always did — which is what makes this a re-expression rather
 * than a new claim.
 */
const hasOf = (profile: string) => (permission: string) =>
    (PERMISSIONS_BY_ROLE[profile] ?? []).includes(permission);


vi.mock("../../../api/purchases");

let mockUserRole: string = "DIRECTOR";

vi.mock("../../user-administration/access/useCanAccess", () => ({
  useEffectivePermissionSet: () => ({ has: hasOf(mockUserRole) }),
}));

const baseDetail: PurchaseRequestDetail = {
  id: "req-1",
  title: "Troca das bombas d'água",
  description: "Duas bombas submersas",
  general_notes: "Falar com o zelador antes de contratar",
  status: PurchaseRequestStatus.OPEN,
  requested_by_id: "user-1",
  requested_by_name: "Gerente Silva",
  quote_count: 2,
  lowest_quote_total: 2400,
  selected_quote_id: null,
  selected_quote_total: null,
  decision_justification: null,
  decided_at: null,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
  quotes: [
    {
      id: "quote-cheap",
      purchase_request_id: "req-1",
      supplier_name: "Bombas & Cia",
      supplier_contact: "(11) 3333-0000",
      unit_price: 1200,
      quantity: 2,
      notes: null,
      extra_fields: [{ label: "Prazo de entrega", value: "15 dias" }],
      total_price: 2400,
      created_by_id: "user-1",
      created_by_name: "Gerente Silva",
      is_selected: false,
      is_lowest_price: true,
      created_at: "2026-08-01T00:00:00Z",
      updated_at: "2026-08-01T00:00:00Z",
    },
    {
      id: "quote-expensive",
      purchase_request_id: "req-1",
      supplier_name: "Hidráulica Central",
      supplier_contact: null,
      unit_price: 1500,
      quantity: 2,
      notes: null,
      extra_fields: [],
      total_price: 3000,
      created_by_id: "user-2",
      created_by_name: "Diretor Souza",
      is_selected: false,
      is_lowest_price: false,
      created_at: "2026-08-02T00:00:00Z",
      updated_at: "2026-08-02T00:00:00Z",
    },
  ],
  decisions: [],
  current_decision: null,
};

const decidedDetail: PurchaseRequestDetail = {
  ...baseDetail,
  status: PurchaseRequestStatus.DECIDED,
  selected_quote_id: "quote-expensive",
  selected_quote_total: 3000,
  decision_justification: "Revisão da diretoria: o mais barato não atende à NBR.",
  decided_at: "2026-08-03T00:00:00Z",
  quotes: [
    { ...baseDetail.quotes[0], is_selected: false },
    { ...baseDetail.quotes[1], is_selected: true },
  ],
  decisions: [
    {
      id: "dec-2",
      quote_id: "quote-expensive",
      quote_supplier_name: "Hidráulica Central",
      quote_total_price: 3000,
      justification: "Revisão da diretoria: o mais barato não atende à NBR.",
      decided_by_id: "user-2",
      decided_by_name: "Diretor Souza",
      decided_at: "2026-08-03T00:00:00Z",
      is_current: true,
    },
    {
      id: "dec-1",
      quote_id: "quote-cheap",
      quote_supplier_name: "Bombas & Cia",
      quote_total_price: 2400,
      justification: "Primeira escolha: menor preço absoluto.",
      decided_by_id: "user-1",
      decided_by_name: "Admin Costa",
      decided_at: "2026-08-02T12:00:00Z",
      is_current: false,
    },
  ],
  current_decision: {
    id: "dec-2",
    quote_id: "quote-expensive",
    quote_supplier_name: "Hidráulica Central",
    quote_total_price: 3000,
    justification: "Revisão da diretoria: o mais barato não atende à NBR.",
    decided_by_id: "user-2",
    decided_by_name: "Diretor Souza",
    decided_at: "2026-08-03T00:00:00Z",
    is_current: true,
  },
};

const renderModal = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <PurchaseRequestDetailModal isOpen onClose={vi.fn()} requestId="req-1" />
    </QueryClientProvider>,
  );
};

describe("PurchaseRequestDetailModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUserRole = "DIRECTOR";
    vi.mocked(purchasesApi.getPurchaseRequestById).mockResolvedValue(baseDetail);
    vi.mocked(purchasesApi.addQuote).mockResolvedValue(baseDetail.quotes[0]);
    vi.mocked(purchasesApi.updateQuote).mockResolvedValue(baseDetail.quotes[0]);
    vi.mocked(purchasesApi.deleteQuote).mockResolvedValue(undefined);
    vi.mocked(purchasesApi.selectQuote).mockResolvedValue(
      decidedDetail.decisions[0],
    );
  });

  it("renders the request header, notes and the quotes in the order given", async () => {
    renderModal();

    expect(
      await screen.findByText("Troca das bombas d'água"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Falar com o zelador antes de contratar"),
    ).toBeInTheDocument();
    expect(screen.getByText("Duas bombas submersas")).toBeInTheDocument();

    const rows = screen.getAllByTestId(/quote-row-/);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("Bombas & Cia");
    expect(rows[1]).toHaveTextContent("Hidráulica Central");

    // The lowest-price badge is on the cheapest quote only.
    expect(rows[0]).toHaveTextContent("Menor preço");
    expect(rows[1]).not.toHaveTextContent("Menor preço");

    // Extra fields are rendered as label/value pairs.
    expect(screen.getByText("Prazo de entrega")).toBeInTheDocument();
    expect(screen.getByText("15 dias")).toBeInTheDocument();
  });

  it("shows the empty state for the decision panel while open", async () => {
    renderModal();
    expect(
      await screen.findByText("Nenhum orçamento escolhido até agora."),
    ).toBeInTheDocument();
  });

  it("renders the choose control for a DIRECTOR and opens the decision modal", async () => {
    renderModal();

    const chooseButtons = await screen.findAllByTitle("Escolher este Orçamento");
    expect(chooseButtons).toHaveLength(2);

    fireEvent.click(chooseButtons[0]);
    expect(screen.getByText("Escolher Orçamento")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Justificativa da escolha *"), {
      target: { value: "Menor preço e mesmo prazo de entrega." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar Escolha" }));

    await waitFor(() => {
      expect(purchasesApi.selectQuote).toHaveBeenCalledWith("req-1", {
        quote_id: "quote-cheap",
        justification: "Menor preço e mesmo prazo de entrega.",
      });
    });
  });

  it("does not render the choose control for a MANAGER", async () => {
    mockUserRole = "MANAGER";
    renderModal();

    await screen.findByText("Troca das bombas d'água");
    expect(screen.queryAllByTitle("Escolher este Orçamento")).toHaveLength(0);
  });

  it("shows the current decision and preserves the superseded one", async () => {
    vi.mocked(purchasesApi.getPurchaseRequestById).mockResolvedValue(decidedDetail);
    renderModal();

    expect(
      await screen.findByText(
        "Revisão da diretoria: o mais barato não atende à NBR.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Diretor Souza/)).toBeInTheDocument();
    expect(screen.getByText("Decisões anteriores")).toBeInTheDocument();
    expect(
      screen.getByText("Primeira escolha: menor preço absoluto."),
    ).toBeInTheDocument();

    const rows = screen.getAllByTestId(/quote-row-/);
    expect(rows[1]).toHaveTextContent("Escolhido");
    expect(rows[0]).not.toHaveTextContent("Escolhido");
  });

  it("hides quote editing once the request is decided", async () => {
    vi.mocked(purchasesApi.getPurchaseRequestById).mockResolvedValue(decidedDetail);
    renderModal();

    await screen.findByText("Troca das bombas d'água");
    expect(screen.queryByRole("button", { name: "Novo Orçamento" })).toBeNull();
    expect(screen.queryAllByTitle("Editar Orçamento")).toHaveLength(0);
    expect(screen.getByText("Os orçamentos deste pedido estão congelados.")).toBeInTheDocument();
  });

  it("adds, edits and deletes a quote while the request is open", async () => {
    renderModal();

    await screen.findByText("Troca das bombas d'água");

    fireEvent.click(screen.getByRole("button", { name: "Novo Orçamento" }));
    fireEvent.change(screen.getByLabelText("Fornecedor *"), {
      target: { value: "Terceiro Fornecedor" },
    });
    fireEvent.change(screen.getByLabelText("Preço unitário (R$) *"), {
      target: { value: "500" },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    await waitFor(() => {
      expect(purchasesApi.addQuote).toHaveBeenCalledWith(
        "req-1",
        expect.objectContaining({ supplier_name: "Terceiro Fornecedor" }),
      );
    });

    fireEvent.click(screen.getAllByTitle("Editar Orçamento")[0]);
    fireEvent.change(screen.getByLabelText("Quantidade *"), {
      target: { value: "5" },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    await waitFor(() => {
      expect(purchasesApi.updateQuote).toHaveBeenCalledWith(
        "req-1",
        "quote-cheap",
        expect.objectContaining({ quantity: 5 }),
      );
    });

    fireEvent.click(screen.getAllByTitle("Excluir Orçamento")[0]);
    await waitFor(() => {
      expect(purchasesApi.deleteQuote).toHaveBeenCalledWith("req-1", "quote-cheap");
    });
  });

  it("renders nothing when closed or without a request id", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <PurchaseRequestDetailModal isOpen={false} onClose={vi.fn()} requestId="req-1" />
      </QueryClientProvider>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the empty-quotes state", async () => {
    vi.mocked(purchasesApi.getPurchaseRequestById).mockResolvedValue({
      ...baseDetail,
      quotes: [],
      quote_count: 0,
      lowest_quote_total: null,
    });
    renderModal();

    expect(
      await screen.findByText("Nenhum orçamento registrado neste pedido."),
    ).toBeInTheDocument();
  });
});
