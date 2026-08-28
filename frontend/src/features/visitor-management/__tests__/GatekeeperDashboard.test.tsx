import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { GatekeeperDashboard } from "../components/GatekeeperDashboard";
import * as visitorsApi from "../../../api/visitors";
import * as lotsHook from "../../lot-management/hooks/useLots";

vi.mock("../../../api/visitors");
vi.mock("../../lot-management/hooks/useLots");

const mockScannerStart = vi.fn();
const mockScannerStop = vi.fn();
const mockScannerClear = vi.fn();

vi.mock("html5-qrcode", () => ({
  Html5Qrcode: vi.fn().mockImplementation(function MockHtml5Qrcode(this: any) {
    this.start = mockScannerStart;
    this.stop = mockScannerStop;
    this.clear = mockScannerClear;
  }),
}));


const mockVisitors = {
  items: [
    {
      id: "v-1",
      full_name: "Mariana Rios",
      cpf: "52998224725",
      company_name: "Painter Co",
      vehicle_plate: "XYZ-1234",
    },
  ],
  total: 1,
  skip: 0,
  limit: 100,
};

const mockAccessLogs = {
  items: [
    {
      id: "log-1",
      visitor_id: "v-1",
      lot_id: "lot-1",
      entry_time: "2026-08-25T14:00:00Z",
      exit_time: null,
      visitor: {
        id: "v-1",
        full_name: "Mariana Rios",
        company_name: "Painter Co",
      },
    },
  ],
  total: 1,
  skip: 0,
  limit: 100,
};

const mockLots = {
  items: [{ id: "lot-1", block: "A", lot_number: "101" }],
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
      <GatekeeperDashboard />
    </QueryClientProvider>
  );
};

const mockScannedAuth = {
  id: "22222222-2222-2222-2222-222222222222",
  visitor_id: "v-1",
  lot_id: "lot-1",
  authorizer_user_id: "user-1",
  auth_type: "SINGLE",
  allowed_days_json: "[]",
  allowed_shifts_json: "[]",
  allowed_days: [],
  allowed_shifts: [],
  status: "ACTIVE",
  created_at: "2026-08-25T10:00:00Z",
  updated_at: "2026-08-25T10:00:00Z",
  visitor: {
    id: "v-1",
    full_name: "Mariana Rios",
    cpf: "52998224725",
    company_name: "Painter Co",
    vehicle_plate: "XYZ-1234",
  },
};

describe("GatekeeperDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(visitorsApi.searchVisitors).mockResolvedValue(mockVisitors as any);
    vi.mocked(visitorsApi.getAccessLogs).mockResolvedValue(mockAccessLogs as any);
    vi.mocked(lotsHook.useLots).mockReturnValue({ data: mockLots as any, isLoading: false } as any);
    mockScannerStart.mockResolvedValue(null);
    mockScannerStop.mockResolvedValue(undefined);
  });


  it("renders gatekeeper interface with active counter and visitor list", async () => {
    renderComponent();

    expect(await screen.findByText("Portaria - Controle de Acesso")).toBeInTheDocument();
    expect(screen.getByText("Visitantes Ativos")).toBeInTheDocument();
    const names = await screen.findAllByText("Mariana Rios");
    expect(names.length).toBeGreaterThan(0);
  });

  it("executes check-out for on-site visitor", async () => {
    vi.mocked(visitorsApi.checkOutVisitor).mockResolvedValue({ id: "log-1", exit_time: "2026-08-25T15:00:00Z" } as any);

    renderComponent();

    const names = await screen.findAllByText("Mariana Rios");
    expect(names.length).toBeGreaterThan(0);

    const checkOutButton = screen.getByRole("button", { name: "Registrar Saída" });
    fireEvent.click(checkOutButton);

    await waitFor(() => {
      expect(visitorsApi.checkOutVisitor).toHaveBeenCalledWith({ access_log_id: "log-1" });
    });
  });

  it("opens check-in entry modal and submits entry", async () => {
    vi.mocked(visitorsApi.checkInVisitor).mockResolvedValue({ id: "log-2" } as any);

    renderComponent();

    const names = await screen.findAllByText("Mariana Rios");
    expect(names.length).toBeGreaterThan(0);

    // Select lot first
    const lotSelect = screen.getByRole("combobox");
    fireEvent.change(lotSelect, { target: { value: "lot-1" } });


    const checkInButton = screen.getByRole("button", { name: "Registrar Entrada" });
    fireEvent.click(checkInButton);

    expect(screen.getByRole("heading", { name: "Confirmar Entrada" })).toBeInTheDocument();

    const submitButtons = screen.getAllByRole("button", { name: "Registrar Entrada" });
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(visitorsApi.checkInVisitor).toHaveBeenCalledWith({
        visitor_id: "v-1",
        lot_id: "lot-1",
        entry_notes: undefined,
      });
    });
  });

  const openScanner = async () => {
    const scanButton = screen.getByRole("button", { name: "Escanear QR" });
    fireEvent.click(scanButton);
    await waitFor(() => expect(mockScannerStart).toHaveBeenCalledTimes(1));
  };

  const triggerScan = (decodedText: string) => {
    const successCallback = mockScannerStart.mock.calls[
      mockScannerStart.mock.calls.length - 1
    ][2];
    successCallback(decodedText);
  };

  it("opens the entry modal pre-filled and syncs the lot selector after a valid scan", async () => {
    vi.mocked(visitorsApi.getAuthorization).mockResolvedValue(mockScannedAuth as any);

    renderComponent();
    await screen.findAllByText("Mariana Rios");

    await openScanner();
    triggerScan(mockScannedAuth.id);

    await waitFor(() => {
      expect(visitorsApi.getAuthorization).toHaveBeenCalledWith(mockScannedAuth.id);
    });

    expect(await screen.findByRole("heading", { name: "Confirmar Entrada" })).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toHaveValue("lot-1");
  });

  it("passes the scanned authorization_id through to check-in", async () => {
    vi.mocked(visitorsApi.getAuthorization).mockResolvedValue(mockScannedAuth as any);
    vi.mocked(visitorsApi.checkInVisitor).mockResolvedValue({ id: "log-3" } as any);

    renderComponent();
    await screen.findAllByText("Mariana Rios");

    await openScanner();
    triggerScan(mockScannedAuth.id);

    await screen.findByRole("heading", { name: "Confirmar Entrada" });

    const submitButtons = screen.getAllByRole("button", { name: "Registrar Entrada" });
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(visitorsApi.checkInVisitor).toHaveBeenCalledWith({
        visitor_id: "v-1",
        lot_id: "lot-1",
        entry_notes: undefined,
        authorization_id: mockScannedAuth.id,
      });
    });
  });

  it("shows an error and makes no API call when the scanned text is not a UUID", async () => {
    renderComponent();
    await screen.findAllByText("Mariana Rios");

    await openScanner();
    triggerScan("not-a-valid-qr-payload");

    expect(await screen.findByText("Isso não parece ser um QR Code válido.")).toBeInTheDocument();
    expect(visitorsApi.getAuthorization).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "Confirmar Entrada" })).not.toBeInTheDocument();
  });

  it("shows a not-found error when the scanned UUID does not match any authorization", async () => {
    vi.mocked(visitorsApi.getAuthorization).mockRejectedValue({
      response: { status: 404, data: { detail: "Not found" } },
    });

    renderComponent();
    await screen.findAllByText("Mariana Rios");

    await openScanner();
    triggerScan("33333333-3333-3333-3333-333333333333");

    expect(
      await screen.findByText("Nenhuma autorização encontrada para esse QR Code.")
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Confirmar Entrada" })).not.toBeInTheDocument();
  });

  it("clears the scanned authorization id when the entry modal is cancelled", async () => {
    vi.mocked(visitorsApi.getAuthorization).mockResolvedValue(mockScannedAuth as any);
    vi.mocked(visitorsApi.checkInVisitor).mockResolvedValue({ id: "log-4" } as any);

    renderComponent();
    await screen.findAllByText("Mariana Rios");

    await openScanner();
    triggerScan(mockScannedAuth.id);

    await screen.findByRole("heading", { name: "Confirmar Entrada" });

    const cancelButton = screen.getByRole("button", { name: "Cancelar" });
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Confirmar Entrada" })).not.toBeInTheDocument();
    });

    // A subsequent manual-search check-in must not reuse the stale scanned id.
    const checkInButton = screen.getAllByRole("button", { name: "Registrar Entrada" })[0];
    fireEvent.click(checkInButton);

    const submitButtons = screen.getAllByRole("button", { name: "Registrar Entrada" });
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(visitorsApi.checkInVisitor).toHaveBeenCalledWith({
        visitor_id: "v-1",
        lot_id: "lot-1",
        entry_notes: undefined,
        authorization_id: undefined,
      });
    });
  });
});
