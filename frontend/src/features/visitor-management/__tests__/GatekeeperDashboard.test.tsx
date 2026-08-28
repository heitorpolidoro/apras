import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { GatekeeperDashboard } from "../components/GatekeeperDashboard";
import * as visitorsApi from "../../../api/visitors";
import * as packagesApi from "../../../api/packages";
import * as lotsHook from "../../lot-management/hooks/useLots";

vi.mock("../../../api/visitors");
vi.mock("../../../api/packages");
vi.mock("../../lot-management/hooks/useLots");


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

const mockPackageQueue = {
  items: [
    {
      id: "pkg-1",
      lot_id: "lot-1",
      lot_summary: { id: "lot-1", block: "A", lot_number: "101" },
      description: "Caixa Amazon",
      carrier: "Correios",
      received_at: "2026-08-27T10:00:00Z",
      status: "AWAITING_PICKUP",
    },
  ],
  total: 1,
  skip: 0,
  limit: 100,
};

describe("GatekeeperDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(visitorsApi.searchVisitors).mockResolvedValue(mockVisitors as any);
    vi.mocked(visitorsApi.getAccessLogs).mockResolvedValue(mockAccessLogs as any);
    vi.mocked(lotsHook.useLots).mockReturnValue({ data: mockLots as any, isLoading: false } as any);
    vi.mocked(packagesApi.getPackageQueue).mockResolvedValue(mockPackageQueue as any);
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

  it("renders the Encomendas section with the log-arrival form and awaiting-pickup queue", async () => {
    renderComponent();

    expect(await screen.findByText("Registrar Encomenda")).toBeInTheDocument();
    expect(await screen.findByText("Caixa Amazon")).toBeInTheDocument();
  });

  it("log-arrival button is disabled until a lot is selected, then submits with the right payload", async () => {
    vi.mocked(packagesApi.createPackage).mockResolvedValue({ id: "pkg-2" } as any);

    renderComponent();
    await screen.findByText("Caixa Amazon");

    const registerButton = screen.getByRole("button", { name: "Registrar Encomenda" });
    expect(registerButton).toBeDisabled();

    const lotSelects = screen.getAllByRole("combobox");
    fireEvent.change(lotSelects[0], { target: { value: "lot-1" } });

    expect(registerButton).not.toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText("Descrição"), {
      target: { value: "Encomenda nova" },
    });
    fireEvent.change(screen.getByPlaceholderText("Transportadora"), {
      target: { value: "Sedex" },
    });
    fireEvent.click(registerButton);

    await waitFor(() => {
      expect(packagesApi.createPackage).toHaveBeenCalledWith({
        lot_id: "lot-1",
        description: "Encomenda nova",
        carrier: "Sedex",
      });
    });
  });

  it("confirms pickup for a queued package with optional notes", async () => {
    vi.mocked(packagesApi.markPackagePickedUp).mockResolvedValue({
      id: "pkg-1",
      status: "PICKED_UP",
    } as any);

    renderComponent();
    await screen.findByText("Caixa Amazon");

    fireEvent.change(screen.getByPlaceholderText("Retirado por: ___"), {
      target: { value: "Retirado pelo morador" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar Retirada" }));

    await waitFor(() => {
      expect(packagesApi.markPackagePickedUp).toHaveBeenCalledWith("pkg-1", {
        picked_up_by_notes: "Retirado pelo morador",
      });
    });
  });
});
