import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { GateMonitorPage } from "../components/GateMonitorPage";
import * as accessControlApi from "../../../api/accessControl";

vi.mock("../../../api/accessControl");

const mockDevices = {
  items: [
    {
      id: "device-1",
      name: "Portaria Principal",
      location: "Gate 1",
      status: "ONLINE",
      last_seen_at: "2026-08-26T10:00:00Z",
      created_by_id: "admin-1",
      created_at: "2026-08-20T10:00:00Z",
      updated_at: "2026-08-26T10:00:00Z",
    },
  ],
  total: 1,
};

const mockEvents = {
  items: [
    {
      id: "event-1",
      device_id: "device-1",
      resident_id: "resident-1",
      matched: true,
      confidence_score: 0.95,
      access_granted: true,
      event_time: "2026-08-26T10:05:00Z",
    },
    {
      id: "event-2",
      device_id: "device-1",
      resident_id: null,
      matched: false,
      confidence_score: 0.2,
      access_granted: false,
      event_time: "2026-08-26T10:06:00Z",
    },
  ],
  total: 2,
  skip: 0,
  limit: 50,
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

const renderComponent = () => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <GateMonitorPage />
    </QueryClientProvider>,
  );
};

describe("GateMonitorPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(accessControlApi.listDevices).mockResolvedValue(mockDevices as any);
    vi.mocked(accessControlApi.getAccessEvents).mockResolvedValue(mockEvents as any);
  });

  it("renders device status strip and live event feed", async () => {
    renderComponent();

    expect(await screen.findByText("Portaria Principal")).toBeInTheDocument();
    expect(screen.getByText("Online")).toBeInTheDocument();

    expect(await screen.findByText("resident-1")).toBeInTheDocument();
    expect(screen.getByText("Não reconhecido")).toBeInTheDocument();
    expect(screen.getByText("Acesso Liberado")).toBeInTheDocument();
    expect(screen.getByText("Acesso Negado")).toBeInTheDocument();
  });

  it("renders empty state when there are no events", async () => {
    vi.mocked(accessControlApi.getAccessEvents).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 50,
    } as any);

    renderComponent();

    expect(await screen.findByText("Nenhum evento de acesso registrado.")).toBeInTheDocument();
  });
});
