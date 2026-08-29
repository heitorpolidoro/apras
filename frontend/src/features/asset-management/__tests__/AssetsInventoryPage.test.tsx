import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AssetsInventoryPage } from "../components/AssetsInventoryPage";
import * as assetsApi from "../../../api/assets";
import { UserRole } from "../../../types/auth";
import type { Asset, AssetSummary } from "../../../types/asset";
import { AssetCategory, AssetCondition } from "../../../types/asset";

vi.mock("../../../api/assets");

let mockUserRole: UserRole = UserRole.ADMINISTRATOR;

vi.mock("../../user-administration/context/useEffectiveIdentity", () => ({
  useEffectiveIdentity: () => ({
    role: mockUserRole,
    userTypes: [],
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, gcTime: 0 } },
});

const renderPage = () => {
  return render(
    <QueryClientProvider client={queryClient}>
      <AssetsInventoryPage />
    </QueryClientProvider>
  );
};

const mockAsset: Asset = {
  id: "asset-1",
  name: "Câmera Bullet IP",
  category: AssetCategory.SEGURANCA,
  serial_number: "SN-CAM-1",
  asset_tag: "PAT-001",
  location: "Portaria 1",
  acquisition_date: "2026-01-01",
  acquisition_value: 350,
  condition: AssetCondition.BOM,
  is_consumable: false,
  current_quantity: 1,
  min_quantity: null,
  unit_of_measure: "un",
  notes: null,
  is_low_stock: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockSummary: AssetSummary = {
  total_assets: 1,
  total_consumables: 0,
  low_stock_count: 0,
  total_patrimonial_value: 350,
};

describe("AssetsInventoryPage component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUserRole = UserRole.ADMINISTRATOR;
    vi.mocked(assetsApi.getAssets).mockResolvedValue({
      items: [mockAsset],
      total: 1,
      skip: 0,
      limit: 100,
    });
    vi.mocked(assetsApi.getAssetSummary).mockResolvedValue(mockSummary);
    vi.mocked(assetsApi.getAssetById).mockResolvedValue({
      ...mockAsset,
      movements: [],
    });
    vi.mocked(assetsApi.deleteAsset).mockResolvedValue(undefined);
  });

  it("renders header, summary metrics, tabs, and asset table", async () => {
    renderPage();

    expect(screen.getByText("Patrimônio & Estoque")).toBeInTheDocument();
    expect(screen.getByText("Novo Item / Ativo")).toBeInTheDocument();
    expect(screen.getByText("Todos os Itens")).toBeInTheDocument();
    expect(screen.getByText("Bens Patrimoniais")).toBeInTheDocument();
    expect(screen.getByText("Itens de Consumo / Estoque")).toBeInTheDocument();
    expect(screen.getByText("Alertas de Estoque Baixo")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Câmera Bullet IP")).toBeInTheDocument();
      expect(screen.getByText("PAT-001")).toBeInTheDocument();
    });
  });

  it("filters assets by tab and search query", async () => {
    renderPage();

    const searchInput = screen.getByPlaceholderText(
      "Buscar por nome, tag, serial ou local..."
    );
    fireEvent.change(searchInput, { target: { value: "Câmera" } });

    const consumableTab = screen.getByText("Itens de Consumo / Estoque");
    fireEvent.click(consumableTab);

    await waitFor(() => {
      expect(assetsApi.getAssets).toHaveBeenCalledWith(
        expect.objectContaining({
          search: "Câmera",
          is_consumable: true,
        })
      );
    });
  });

  it("opens create modal on button click", async () => {
    renderPage();

    const createBtn = screen.getByText("Novo Item / Ativo");
    fireEvent.click(createBtn);

    expect(screen.getByText("Novo Ativo / Item de Estoque")).toBeInTheDocument();
  });

  it("opens stock movement modal on table action click", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Câmera Bullet IP")).toBeInTheDocument();
    });

    const movementBtn = screen.getByTitle("Movimentar");
    fireEvent.click(movementBtn);

    expect(screen.getByText("Registrar Movimentação")).toBeInTheDocument();
  });

  it("opens history modal on history action click", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Câmera Bullet IP")).toBeInTheDocument();
    });

    const historyBtn = screen.getByTitle("Histórico");
    fireEvent.click(historyBtn);

    expect(screen.getByText("Histórico de Movimentações")).toBeInTheDocument();
  });

  it("handles delete flow with confirmation alert modal", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Câmera Bullet IP")).toBeInTheDocument();
    });

    const deleteBtn = screen.getByTitle("Excluir");
    fireEvent.click(deleteBtn);

    expect(screen.getByText("Excluir Item do Patrimônio")).toBeInTheDocument();
    const confirmBtn = screen.getByText("Confirmar");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(assetsApi.deleteAsset).toHaveBeenCalledWith("asset-1");
    });
  });

  it("hides create button for Manager role", async () => {
    mockUserRole = UserRole.MANAGER;
    renderPage();

    expect(screen.queryByText("Novo Item / Ativo")).not.toBeInTheDocument();
  });
});
