import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PurchaseRequestsPage } from "../components/PurchaseRequestsPage";
import * as purchasesApi from "../../../api/purchases";
import type {
  PurchaseRequest,
  PurchaseRequestDetail,
  PurchaseSummary,
} from "../../../types/purchase";
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

let mockUserRole: string = "ADMINISTRATOR";

vi.mock("../../user-administration/access/useCanAccess", () => ({
  useEffectivePermissionSet: () => ({ has: hasOf(mockUserRole) }),
}));

const mockRequest: PurchaseRequest = {
  id: "req-1",
  title: "Troca das bombas d'água",
  description: "Duas bombas submersas",
  general_notes: null,
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
};

const mockSummary: PurchaseSummary = {
  open_count: 1,
  decided_count: 0,
  cancelled_count: 0,
  total_selected_value: 0,
};

const mockDetail: PurchaseRequestDetail = {
  ...mockRequest,
  quotes: [],
  decisions: [],
  current_decision: null,
};

const renderPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <PurchaseRequestsPage />
    </QueryClientProvider>,
  );
};

describe("PurchaseRequestsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUserRole = "ADMINISTRATOR";
    vi.mocked(purchasesApi.getPurchaseRequests).mockResolvedValue({
      items: [mockRequest],
      total: 1,
      skip: 0,
      limit: 100,
    });
    vi.mocked(purchasesApi.getPurchaseSummary).mockResolvedValue(mockSummary);
    vi.mocked(purchasesApi.getPurchaseRequestById).mockResolvedValue(mockDetail);
    vi.mocked(purchasesApi.createPurchaseRequest).mockResolvedValue(mockRequest);
    vi.mocked(purchasesApi.updatePurchaseRequest).mockResolvedValue(mockRequest);
    vi.mocked(purchasesApi.deletePurchaseRequest).mockResolvedValue(undefined);
    vi.mocked(purchasesApi.cancelPurchaseRequest).mockResolvedValue({
      ...mockRequest,
      status: PurchaseRequestStatus.CANCELLED,
    });
  });

  it("renders the header, summary metrics, tabs and the request list", async () => {
    renderPage();

    expect(screen.getByText("Cotações de Compra")).toBeInTheDocument();
    expect(screen.getByText("Novo Pedido")).toBeInTheDocument();
    expect(screen.getByText("Todos os Pedidos")).toBeInTheDocument();
    expect(screen.getByText("Abertos")).toBeInTheDocument();
    expect(screen.getByText("Decididos")).toBeInTheDocument();
    expect(screen.getByText("Cancelados")).toBeInTheDocument();

    expect(
      await screen.findByText("Troca das bombas d'água"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Gerente Silva/)).toBeInTheDocument();
  });

  it("filters by tab and search query", async () => {
    renderPage();

    fireEvent.change(screen.getByPlaceholderText("Buscar por título ou descrição..."), {
      target: { value: "bombas" },
    });
    fireEvent.click(screen.getByText("Decididos"));

    await waitFor(() => {
      expect(purchasesApi.getPurchaseRequests).toHaveBeenCalledWith(
        expect.objectContaining({
          search: "bombas",
          status: PurchaseRequestStatus.DECIDED,
        }),
      );
    });
  });

  it("creates a purchase request from the form modal", async () => {
    renderPage();

    fireEvent.click(screen.getByText("Novo Pedido"));
    fireEvent.change(screen.getByLabelText("Título do Pedido *"), {
      target: { value: "Compra de tinta" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    await waitFor(() => {
      expect(purchasesApi.createPurchaseRequest).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Compra de tinta" }),
      );
    });
  });

  it("edits a purchase request", async () => {
    renderPage();

    await screen.findByText("Troca das bombas d'água");
    fireEvent.click(screen.getByTitle("Editar"));
    fireEvent.change(screen.getByLabelText("Título do Pedido *"), {
      target: { value: "Troca das bombas (rev)" },
    });
    fireEvent.submit(screen.getByTestId("purchase-request-form"));

    await waitFor(() => {
      expect(purchasesApi.updatePurchaseRequest).toHaveBeenCalledWith(
        "req-1",
        expect.objectContaining({ title: "Troca das bombas (rev)" }),
      );
    });
  });

  it("opens the detail modal from the list", async () => {
    renderPage();

    fireEvent.click(await screen.findByTitle("Ver Orçamentos"));

    await waitFor(() => {
      expect(purchasesApi.getPurchaseRequestById).toHaveBeenCalledWith("req-1");
    });
  });

  it("deletes a request after confirmation", async () => {
    renderPage();

    await screen.findByText("Troca das bombas d'água");
    fireEvent.click(screen.getByTitle("Excluir"));
    expect(screen.getByText("Excluir Pedido de Compra")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));

    await waitFor(() => {
      expect(purchasesApi.deletePurchaseRequest).toHaveBeenCalledWith("req-1");
    });
  });

  it("cancels a request after confirmation", async () => {
    renderPage();

    await screen.findByText("Troca das bombas d'água");
    fireEvent.click(screen.getByTitle("Cancelar Pedido"));
    expect(screen.getByText("Cancelar Pedido de Compra")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));

    await waitFor(() => {
      expect(purchasesApi.cancelPurchaseRequest).toHaveBeenCalledWith("req-1");
    });
  });

  it("hides the cancel action for a MANAGER but keeps create and edit", async () => {
    mockUserRole = "MANAGER";
    renderPage();

    await screen.findByText("Troca das bombas d'água");
    expect(screen.getByText("Novo Pedido")).toBeInTheDocument();
    expect(screen.queryByTitle("Cancelar Pedido")).toBeNull();
  });

  it("renders the empty state", async () => {
    vi.mocked(purchasesApi.getPurchaseRequests).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 100,
    });
    renderPage();

    expect(
      await screen.findByText("Nenhum pedido de compra encontrado."),
    ).toBeInTheDocument();
  });
});
