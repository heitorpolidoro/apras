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


/**
 * Mock the *functions* of the client and keep its **constants** real.
 *
 * A bare `vi.mock("../../../api/purchases")` automocks every export, which
 * silently empties `QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES` — and the
 * comparison table reads it to decide whether a picked file may be sent, so
 * every upload would be refused by a test artefact rather than by the rule
 * under test.
 */
vi.mock("../../../api/purchases", async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return Object.fromEntries(
    Object.entries(actual).map(([key, value]) => [
      key,
      typeof value === "function" ? vi.fn() : value,
    ]),
  );
});

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
  items: [
    {
      id: "ri-pump",
      description: "Bomba submersa",
      quantity: 2,
      position: 0,
    },
  ],
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
      items: [
        {
          id: "qi-cheap",
          request_item_id: "ri-pump",
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
      extra_fields: [{ label: "Prazo de entrega", value: "15 dias" }],
      attachment_url: null,
      attachment_filename: null,
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
      items: [
        {
          id: "qi-expensive",
          request_item_id: "ri-pump",
          model: null,
          unit_price: 1500,
          description: "Bomba submersa",
          quantity: 2,
          position: 0,
          line_total: 3000,
        },
      ],
      quoted_item_count: 1,
      is_complete: true,
      notes: null,
      extra_fields: [],
      attachment_url: null,
      attachment_filename: null,
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
    vi.mocked(purchasesApi.uploadQuoteAttachment).mockResolvedValue(
      baseDetail.quotes[0],
    );
    vi.mocked(purchasesApi.deleteQuoteAttachment).mockResolvedValue(
      baseDetail.quotes[0],
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
    fireEvent.change(screen.getByTestId("quote-line-price-ri-pump"), {
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
    fireEvent.change(screen.getByTestId("quote-line-price-ri-pump"), {
      target: { value: "1100" },
    });
    fireEvent.submit(screen.getByTestId("quote-form"));

    await waitFor(() => {
      expect(purchasesApi.updateQuote).toHaveBeenCalledWith(
        "req-1",
        "quote-cheap",
        expect.objectContaining({
          items: [
            { request_item_id: "ri-pump", model: null, unit_price: 1100 },
          ],
        }),
      );
    });

    fireEvent.click(screen.getAllByTitle("Excluir Orçamento")[0]);
    await waitFor(() => {
      expect(purchasesApi.deleteQuote).toHaveBeenCalledWith("req-1", "quote-cheap");
    });
  });

  // --- APRAS-63: the comparison, the decision context and the attachment ---

  it("compares the quotes in one table with the extra labels aligned", async () => {
    renderModal();

    await screen.findByText("Troca das bombas d'água");

    // One column per supplier, the fixed rows, and the union label once —
    // not once per supplier, which is what the stacked cards used to do.
    expect(screen.getAllByTestId(/quote-row-/)).toHaveLength(2);
    // APRAS-73 D9: the single-price row is gone; the items grid has
    // one row per request line and one cell per supplier instead.
    expect(screen.queryByText("Unitário × qtd.")).toBeNull();
    // Twice on purpose: the request's own line list at the top of the
    // detail, and the grid row the suppliers are compared across.
    expect(screen.getAllByText("2 × Bomba submersa")).toHaveLength(2);
    expect(
      screen.getByTestId("grid-cell-ri-pump-quote-cheap"),
    ).toHaveAttribute("data-quoted", "true");
    expect(screen.getAllByText("Prazo de entrega")).toHaveLength(1);
    expect(screen.getByText("15 dias")).toBeInTheDocument();

    // Hidráulica Central filled neither the label nor a contact.
    expect(
      screen.getAllByTitle("Não informado por este fornecedor").length,
    ).toBeGreaterThan(0);
  });

  it("states the gap against the lowest quote when a dearer one is chosen", async () => {
    renderModal();

    const chooseButtons = await screen.findAllByTitle("Escolher este Orçamento");
    // The second column is Hidráulica Central at 3000, against 2400.
    fireEvent.click(chooseButtons[1]);

    const panel = screen.getByTestId("decision-gap");
    expect(panel).toHaveTextContent("Este não é o menor orçamento.");
    expect(panel).toHaveTextContent("Bombas & Cia");
    expect(panel).toHaveTextContent("R$ 600,00");
    expect(panel).toHaveTextContent("25.0%");
  });

  it("renders no gap panel when the lowest quote is the one being chosen", async () => {
    renderModal();

    const chooseButtons = await screen.findAllByTitle("Escolher este Orçamento");
    fireEvent.click(chooseButtons[0]);

    expect(screen.queryByTestId("decision-gap")).toBeNull();
  });

  it("uploads and removes the supplier document through the two routes", async () => {
    vi.mocked(purchasesApi.uploadQuoteAttachment).mockResolvedValue({
      ...baseDetail.quotes[0],
      attachment_url: "/static/uploads/2026/09/abc.pdf",
      attachment_filename: "orcamento.pdf",
    });
    vi.mocked(purchasesApi.deleteQuoteAttachment).mockResolvedValue(
      baseDetail.quotes[0],
    );
    renderModal();

    await screen.findByText("Troca das bombas d'água");

    const file = new File(["%PDF-"], "orcamento.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(screen.getByTestId("attachment-input-quote-cheap"), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(purchasesApi.uploadQuoteAttachment).toHaveBeenCalledWith(
        "req-1",
        "quote-cheap",
        file,
      );
    });
  });

  it("links a stored document in the detail and offers removing it", async () => {
    vi.mocked(purchasesApi.getPurchaseRequestById).mockResolvedValue({
      ...baseDetail,
      quotes: [
        {
          ...baseDetail.quotes[0],
          attachment_url: "/static/uploads/2026/09/abc.pdf",
          attachment_filename: "orcamento-bombas.pdf",
        },
        baseDetail.quotes[1],
      ],
    });
    vi.mocked(purchasesApi.deleteQuoteAttachment).mockResolvedValue(
      baseDetail.quotes[0],
    );
    renderModal();

    expect(
      await screen.findByRole("link", { name: /orcamento-bombas\.pdf/ }),
    ).toHaveAttribute("href", "/static/uploads/2026/09/abc.pdf");

    fireEvent.click(screen.getByTitle("Remover"));
    await waitFor(() => {
      expect(purchasesApi.deleteQuoteAttachment).toHaveBeenCalledWith(
        "req-1",
        "quote-cheap",
      );
    });
  });

  it("shows no upload control to a caller without purchases:quote_update", async () => {
    mockUserRole = "RESIDENT";
    renderModal();

    await screen.findByText("Troca das bombas d'água");
    expect(screen.queryAllByTestId(/attachment-input-/)).toHaveLength(0);
    expect(screen.queryByTitle("Anexar documento")).toBeNull();
  });

  it("shows the comparison but no choose control without purchases:decide", async () => {
    mockUserRole = "MANAGER";
    renderModal();

    await screen.findByText("Troca das bombas d'água");
    expect(screen.getAllByTestId(/quote-row-/)).toHaveLength(2);
    expect(screen.queryAllByTitle("Escolher este Orçamento")).toHaveLength(0);
    // …but a Manager holds `purchases:quote_update`, so the upload stays.
    expect(screen.queryAllByTestId(/attachment-input-/)).toHaveLength(2);
  });

  it("shows the frozen document read-only, with no upload control", async () => {
    vi.mocked(purchasesApi.getPurchaseRequestById).mockResolvedValue({
      ...decidedDetail,
      quotes: [
        {
          ...decidedDetail.quotes[0],
          attachment_url: "/static/uploads/2026/09/abc.pdf",
          attachment_filename: "orcamento-bombas.pdf",
        },
        decidedDetail.quotes[1],
      ],
    });
    renderModal();

    expect(
      await screen.findByRole("link", { name: /orcamento-bombas\.pdf/ }),
    ).toBeInTheDocument();
    expect(screen.queryAllByTestId(/attachment-input-/)).toHaveLength(0);
    expect(screen.getByText("somente leitura")).toBeInTheDocument();

    // The recorded decision is untouched by any of this.
    expect(
      screen.getByText("Revisão da diretoria: o mais barato não atende à NBR."),
    ).toBeInTheDocument();
    expect(screen.getByText(/Diretor Souza/)).toBeInTheDocument();
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
