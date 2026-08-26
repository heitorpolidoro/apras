import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { AccessControlPage } from "../components/AccessControlPage";
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

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

const renderComponent = () => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <AccessControlPage />
    </QueryClientProvider>,
  );
};

describe("AccessControlPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(accessControlApi.listDevices).mockResolvedValue(mockDevices as any);
    vi.mocked(accessControlApi.getFacialTemplate).mockResolvedValue(null as any);
  });

  it("renders device list", async () => {
    renderComponent();

    expect(await screen.findByText("Portaria Principal")).toBeInTheDocument();
    expect(screen.getByText("Gate 1")).toBeInTheDocument();
  });

  it("opens register device modal and submits", async () => {
    vi.mocked(accessControlApi.createDevice).mockResolvedValue({
      id: "device-2",
      name: "Portaria Fundos",
      status: "OFFLINE",
      created_by_id: "admin-1",
      created_at: "2026-08-26T10:00:00Z",
      updated_at: "2026-08-26T10:00:00Z",
      device_key: "secret-key-abc",
    } as any);

    renderComponent();

    await screen.findByText("Portaria Principal");

    fireEvent.click(screen.getByRole("button", { name: "Registrar Dispositivo" }));

    const modal = await screen.findByTestId("register-device-modal");
    const nameInput = modal.querySelector("input") as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "Portaria Fundos" } });

    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => {
      expect(accessControlApi.createDevice).toHaveBeenCalledWith({
        name: "Portaria Fundos",
        location: undefined,
      });
    });
  });

  it("regenerates a device key and reveals it", async () => {
    vi.mocked(accessControlApi.regenerateDeviceKey).mockResolvedValue({
      id: "device-1",
      name: "Portaria Principal",
      status: "ONLINE",
      created_by_id: "admin-1",
      created_at: "2026-08-20T10:00:00Z",
      updated_at: "2026-08-26T10:00:00Z",
      device_key: "brand-new-key",
    } as any);

    renderComponent();

    await screen.findByText("Portaria Principal");
    fireEvent.click(screen.getByRole("button", { name: /Regenerar Chave/ }));

    await waitFor(() => {
      expect(accessControlApi.regenerateDeviceKey).toHaveBeenCalledWith("device-1");
    });
    expect(await screen.findByText("brand-new-key")).toBeInTheDocument();
  });

  it("searches and syncs a facial template for a resident", async () => {
    vi.mocked(accessControlApi.getFacialTemplate).mockResolvedValue({
      id: "template-1",
      resident_id: "resident-1",
      media_asset_id: "media-1",
      sync_status: "SYNCED",
      synced_at: "2026-08-26T09:00:00Z",
      created_at: "2026-08-26T09:00:00Z",
      updated_at: "2026-08-26T09:00:00Z",
    } as any);

    renderComponent();
    await screen.findByText("Portaria Principal");

    const residentInput = screen.getByPlaceholderText("ID do morador");
    fireEvent.change(residentInput, { target: { value: "resident-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));

    expect(await screen.findByText("Sincronizado")).toBeInTheDocument();
  });
});
