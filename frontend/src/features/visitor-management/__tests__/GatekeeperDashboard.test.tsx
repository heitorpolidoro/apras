import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { GatekeeperDashboard } from "../components/GatekeeperDashboard";
import * as visitorsApi from "../../../api/visitors";
import * as lotsHook from "../../lot-management/hooks/useLots";

vi.mock("../../../api/visitors");
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

describe("GatekeeperDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(visitorsApi.searchVisitors).mockResolvedValue(mockVisitors as any);
    vi.mocked(visitorsApi.getAccessLogs).mockResolvedValue(mockAccessLogs as any);
    vi.mocked(lotsHook.useLots).mockReturnValue({ data: mockLots as any, isLoading: false } as any);
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
});
