import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as purchasesApi from "../../../api/purchases";
import { useAddQuote, useCancelPurchaseRequest, useCreatePurchaseRequest, useDeletePurchaseRequest, useDeleteQuote, usePurchaseRequest, usePurchaseRequests, usePurchaseSummary, useSelectQuote, useUpdatePurchaseRequest, useUpdateQuote,  } from "../hooks/usePurchaseRequests";
import { PurchaseRequestStatus } from "../../../types/purchase";

vi.mock("../../../api/purchases");

const request = {
  id: "req-1",
  title: "Pedido",
  description: null,
  general_notes: null,
  status: PurchaseRequestStatus.OPEN,
  requested_by_id: "user-1",
  requested_by_name: "Admin",
  quote_count: 0,
  lowest_quote_total: null,
  selected_quote_id: null,
  selected_quote_total: null,
  decision_justification: null,
  decided_at: null,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

const quote = {
  id: "quote-1",
  purchase_request_id: "req-1",
  supplier_name: "Fornecedor",
  supplier_contact: null,
  unit_price: 10,
  quantity: 2,
  notes: null,
  extra_fields: [],
  total_price: 20,
  created_by_id: "user-1",
  created_by_name: "Admin",
  is_selected: false,
  is_lowest_price: true,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

const decision = {
  id: "dec-1",
  quote_id: "quote-1",
  quote_supplier_name: "Fornecedor",
  quote_total_price: 20,
  justification: "Justificativa longa o bastante.",
  decided_by_id: "user-1",
  decided_by_name: "Admin",
  decided_at: "2026-08-02T00:00:00Z",
  is_current: true,
};

const wrapper = ({ children }: { children: ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("usePurchaseRequests hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(purchasesApi.getPurchaseRequests).mockResolvedValue({
      items: [request],
      total: 1,
      skip: 0,
      limit: 100,
    });
    vi.mocked(purchasesApi.getPurchaseSummary).mockResolvedValue({
      open_count: 1,
      decided_count: 0,
      cancelled_count: 0,
      total_selected_value: 0,
    });
    vi.mocked(purchasesApi.getPurchaseRequestById).mockResolvedValue({
      ...request,
      quotes: [],
      decisions: [],
      current_decision: null,
    });
    vi.mocked(purchasesApi.createPurchaseRequest).mockResolvedValue(request);
    vi.mocked(purchasesApi.updatePurchaseRequest).mockResolvedValue(request);
    vi.mocked(purchasesApi.deletePurchaseRequest).mockResolvedValue(undefined);
    vi.mocked(purchasesApi.addQuote).mockResolvedValue(quote);
    vi.mocked(purchasesApi.updateQuote).mockResolvedValue(quote);
    vi.mocked(purchasesApi.deleteQuote).mockResolvedValue(undefined);
    vi.mocked(purchasesApi.selectQuote).mockResolvedValue(decision);
    vi.mocked(purchasesApi.cancelPurchaseRequest).mockResolvedValue(request);
  });

  it("fetches the request list, the summary and one detail", async () => {
    const list = renderHook(() => usePurchaseRequests({ search: "x" }), { wrapper });
    await waitFor(() => expect(list.result.current.isSuccess).toBe(true));
    expect(purchasesApi.getPurchaseRequests).toHaveBeenCalledWith({ search: "x" });

    const summary = renderHook(() => usePurchaseSummary(), { wrapper });
    await waitFor(() => expect(summary.result.current.isSuccess).toBe(true));

    const detail = renderHook(() => usePurchaseRequest("req-1"), { wrapper });
    await waitFor(() => expect(detail.result.current.isSuccess).toBe(true));
    expect(purchasesApi.getPurchaseRequestById).toHaveBeenCalledWith("req-1");
  });

  it("does not fetch a detail without an id", () => {
    const { result } = renderHook(() => usePurchaseRequest(null), { wrapper });
    expect(result.current.fetchStatus).toBe("idle");
    expect(purchasesApi.getPurchaseRequestById).not.toHaveBeenCalled();
  });

  it("runs every mutation against the API client", async () => {
    const create = renderHook(() => useCreatePurchaseRequest(), { wrapper });
    await create.result.current.mutateAsync({ title: "Pedido" });
    expect(purchasesApi.createPurchaseRequest).toHaveBeenCalledWith({ title: "Pedido" });

    const update = renderHook(() => useUpdatePurchaseRequest(), { wrapper });
    await update.result.current.mutateAsync({ id: "req-1", data: { title: "Novo" } });
    expect(purchasesApi.updatePurchaseRequest).toHaveBeenCalledWith("req-1", {
      title: "Novo",
    });

    const remove = renderHook(() => useDeletePurchaseRequest(), { wrapper });
    await remove.result.current.mutateAsync("req-1");
    expect(purchasesApi.deletePurchaseRequest).toHaveBeenCalledWith("req-1");

    const add = renderHook(() => useAddQuote(), { wrapper });
    await add.result.current.mutateAsync({
      requestId: "req-1",
      data: {
        supplier_name: "Fornecedor",
        unit_price: 10,
        quantity: 2,
        extra_fields: [],
      },
    });
    expect(purchasesApi.addQuote).toHaveBeenCalled();

    const editQuote = renderHook(() => useUpdateQuote(), { wrapper });
    await editQuote.result.current.mutateAsync({
      requestId: "req-1",
      quoteId: "quote-1",
      data: { quantity: 5 },
    });
    expect(purchasesApi.updateQuote).toHaveBeenCalledWith("req-1", "quote-1", {
      quantity: 5,
    });

    const removeQuote = renderHook(() => useDeleteQuote(), { wrapper });
    await removeQuote.result.current.mutateAsync({
      requestId: "req-1",
      quoteId: "quote-1",
    });
    expect(purchasesApi.deleteQuote).toHaveBeenCalledWith("req-1", "quote-1");

    const select = renderHook(() => useSelectQuote(), { wrapper });
    await select.result.current.mutateAsync({
      requestId: "req-1",
      data: { quote_id: "quote-1", justification: "Justificativa longa." },
    });
    expect(purchasesApi.selectQuote).toHaveBeenCalledWith("req-1", {
      quote_id: "quote-1",
      justification: "Justificativa longa.",
    });

    const cancel = renderHook(() => useCancelPurchaseRequest(), { wrapper });
    await cancel.result.current.mutateAsync("req-1");
    expect(purchasesApi.cancelPurchaseRequest).toHaveBeenCalledWith("req-1");
  });
});
