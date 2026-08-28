import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { VisitorAuthPage } from "../components/VisitorAuthPage";
import * as visitorsApi from "../../../api/visitors";
import * as lotsHook from "../../lot-management/hooks/useLots";
import apiClient from "../../../api/client";

vi.mock("../../../api/visitors");
vi.mock("../../lot-management/hooks/useLots");
vi.mock("../../../api/client", () => ({
  default: {
    get: vi.fn(),
  },
}));


const mockLots = {
  items: [
    { id: "lot-1", block: "A", lot_number: "101" },
    { id: "lot-2", block: "B", lot_number: "202" },
  ],
  total: 2,
  skip: 0,
  limit: 100,
};

const mockAuths = {
  items: [
    {
      id: "auth-1",
      visitor_id: "vis-1",
      lot_id: "lot-1",
      authorizer_user_id: "user-1",
      auth_type: "SINGLE",
      allowed_days_json: '["MON","TUE"]',
      allowed_shifts_json: '["FULL_DAY"]',
      allowed_days: ["MON", "TUE"],
      allowed_shifts: ["FULL_DAY"],
      status: "ACTIVE",
      notes: "Electrician",
      created_at: "2026-08-25T10:00:00Z",
      updated_at: "2026-08-25T10:00:00Z",
      visitor: {
        id: "vis-1",
        full_name: "Carlos visitante",
        cpf: "52998224725",
        company_name: "Alfa Tech",
        vehicle_plate: "ABC-1234",
      },
    },
  ],
  total: 1,
  skip: 0,
  limit: 100,
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

const renderComponent = () => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <VisitorAuthPage />
    </QueryClientProvider>
  );
};

describe("VisitorAuthPage", () => {
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(lotsHook.useLots).mockReturnValue({ data: mockLots as any, isLoading: false } as any);
    vi.mocked(visitorsApi.getLotAuthorizations).mockResolvedValue(mockAuths as any);
    vi.mocked(visitorsApi.searchVisitors).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 100 } as any);
    URL.createObjectURL = vi.fn(() => "blob:mock-object-url");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });


  it("renders page header and authorization table", async () => {
    renderComponent();

    expect(await screen.findByText("Pré-Autorizações de Visitantes")).toBeInTheDocument();
    expect(await screen.findByText("Carlos visitante")).toBeInTheDocument();
    expect(screen.getByText("Alfa Tech")).toBeInTheDocument();
  });

  it("opens create authorization modal", async () => {
    renderComponent();

    expect(await screen.findByText("Pré-Autorizações de Visitantes")).toBeInTheDocument();

    const newAuthButton = screen.getByRole("button", { name: "Nova Autorização" });
    fireEvent.click(newAuthButton);

    expect(screen.getAllByText("Nova Autorização").length).toBeGreaterThan(0);
  });

  it("revokes an authorization after confirmation", async () => {
    vi.mocked(visitorsApi.revokeAuthorization).mockResolvedValue({ id: "auth-1", status: "REVOKED" } as any);

    renderComponent();

    expect(await screen.findByText("Carlos visitante")).toBeInTheDocument();

    const revokeButton = screen.getByRole("button", { name: "Revogar" });
    fireEvent.click(revokeButton);

    expect(screen.getByText(/Tem certeza que deseja revogar/)).toBeInTheDocument();

    const confirmButtons = screen.getAllByRole("button", { name: "Revogar" });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(visitorsApi.revokeAuthorization).toHaveBeenCalledWith("auth-1", undefined);
    });
  });

  it("opens the QR modal and fetches the image via apiClient as a blob, rendering an object URL src", async () => {
    const mockBlob = new Blob(["fake-png-bytes"], { type: "image/png" });
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockBlob });

    renderComponent();

    expect(await screen.findByText("Carlos visitante")).toBeInTheDocument();

    const viewQrButton = screen.getByRole("button", { name: /Ver QR/ });
    fireEvent.click(viewQrButton);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith("/authorizations/auth-1/qr-code", {
        responseType: "blob",
      });
    });

    const img = await screen.findByRole("img");
    expect(img).toHaveAttribute("src", "blob:mock-object-url");
  });
});
