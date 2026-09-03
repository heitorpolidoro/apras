import { beforeEach, describe, expect, it, vi } from "vitest";
import { addQuote, cancelPurchaseRequest, createPurchaseRequest, deletePurchaseRequest, deleteQuote, getPurchaseRequestById, getPurchaseRequests, getPurchaseSummary, selectQuote, updatePurchaseRequest, updateQuote,  } from "../purchases";
import apiClient from "../client";
import { PurchaseRequestStatus } from "../../types/purchase";

vi.mock("../client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

describe("purchases api client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists purchase requests with filter params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [{ id: "req-1" }], total: 1, skip: 0, limit: 100 },
    });

    const res = await getPurchaseRequests({
      status: PurchaseRequestStatus.OPEN,
      search: "bombas",
    });

    expect(res.total).toBe(1);
    expect(apiClient.get).toHaveBeenCalledWith("/purchase-requests", {
      params: { status: "OPEN", search: "bombas" },
    });
  });

  it("fetches the summary", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        open_count: 2,
        decided_count: 1,
        cancelled_count: 0,
        total_selected_value: 900,
      },
    });

    const res = await getPurchaseSummary();
    expect(res.decided_count).toBe(1);
    expect(apiClient.get).toHaveBeenCalledWith("/purchase-requests/summary");
  });

  it("fetches a request by id", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { id: "req-1", quotes: [], decisions: [], current_decision: null },
    });

    const res = await getPurchaseRequestById("req-1");
    expect(res.id).toBe("req-1");
    expect(apiClient.get).toHaveBeenCalledWith("/purchase-requests/req-1");
  });

  it("creates, updates and deletes a request", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "req-1" } });
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "req-1" } });
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await createPurchaseRequest({ title: "Pedido" });
    expect(apiClient.post).toHaveBeenCalledWith("/purchase-requests", {
      title: "Pedido",
    });

    await updatePurchaseRequest("req-1", { title: "Novo" });
    expect(apiClient.put).toHaveBeenCalledWith("/purchase-requests/req-1", {
      title: "Novo",
    });

    await deletePurchaseRequest("req-1");
    expect(apiClient.delete).toHaveBeenCalledWith("/purchase-requests/req-1");
  });

  it("adds, updates and deletes a quote", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "quote-1" } });
    vi.mocked(apiClient.put).mockResolvedValue({ data: { id: "quote-1" } });
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    const payload = {
      supplier_name: "Fornecedor",
      unit_price: 10,
      quantity: 2,
      extra_fields: [{ label: "Prazo", value: "15 dias" }],
    };
    const created = await addQuote("req-1", payload);
    expect(created.id).toBe("quote-1");
    expect(apiClient.post).toHaveBeenCalledWith(
      "/purchase-requests/req-1/quotes",
      payload,
    );

    await updateQuote("req-1", "quote-1", { quantity: 5 });
    expect(apiClient.put).toHaveBeenCalledWith(
      "/purchase-requests/req-1/quotes/quote-1",
      { quantity: 5 },
    );

    await deleteQuote("req-1", "quote-1");
    expect(apiClient.delete).toHaveBeenCalledWith(
      "/purchase-requests/req-1/quotes/quote-1",
    );
  });

  it("records a decision and cancels a request", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: "dec-1" } });

    const decision = await selectQuote("req-1", {
      quote_id: "quote-1",
      justification: "Justificativa longa o bastante.",
    });
    expect(decision.id).toBe("dec-1");
    expect(apiClient.post).toHaveBeenCalledWith(
      "/purchase-requests/req-1/decision",
      { quote_id: "quote-1", justification: "Justificativa longa o bastante." },
    );

    await cancelPurchaseRequest("req-1");
    expect(apiClient.post).toHaveBeenCalledWith(
      "/purchase-requests/req-1/cancel",
    );
  });
});
