import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AssetMovementHistoryModal } from "../components/AssetMovementHistoryModal";
import type { Asset } from "../../../types/asset";
import { AssetCategory, AssetCondition, MovementType } from "../../../types/asset";
import * as useAssetsModule from "../hooks/useAssets";

vi.mock("../hooks/useAssets");

const mockAsset: Asset = {
  id: "asset-1",
  name: "Câmera Bullet IP",
  category: AssetCategory.SEGURANCA,
  serial_number: "SN-CAM-1",
  asset_tag: "PAT-001",
  location: "Portaria 1",
  acquisition_date: "2026-01-10",
  acquisition_value: 1200,
  condition: AssetCondition.BOM,
  is_consumable: false,
  current_quantity: 5,
  min_quantity: 2,
  unit_of_measure: "un",
  notes: null,
  is_low_stock: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("AssetMovementHistoryModal component", () => {
  it("renders null when isOpen is false", () => {
    vi.spyOn(useAssetsModule, "useAsset").mockReturnValue({
      data: undefined,
      isLoading: false,
    } as any);

    const { container } = render(
      <AssetMovementHistoryModal
        isOpen={false}
        onClose={vi.fn()}
        asset={mockAsset}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders loading state when isLoading is true", () => {
    vi.spyOn(useAssetsModule, "useAsset").mockReturnValue({
      data: undefined,
      isLoading: true,
    } as any);

    render(
      <AssetMovementHistoryModal
        isOpen={true}
        onClose={vi.fn()}
        asset={mockAsset}
      />
    );

    expect(screen.getByText("Histórico de Movimentações")).toBeInTheDocument();
    expect(screen.getByText(/Carregando/i)).toBeInTheDocument();
  });

  it("renders empty movements message", () => {
    vi.spyOn(useAssetsModule, "useAsset").mockReturnValue({
      data: { ...mockAsset, movements: [] } as any,
      isLoading: false,
    } as any);

    render(
      <AssetMovementHistoryModal
        isOpen={true}
        onClose={vi.fn()}
        asset={mockAsset}
      />
    );

    expect(
      screen.getByText("Nenhuma movimentação registrada para este item.")
    ).toBeInTheDocument();
  });

  it("renders list of movements with badges and details", () => {
    const movements = [
      {
        id: "mov-1",
        asset_id: "asset-1",
        movement_type: MovementType.ENTRADA,
        quantity: 5,
        previous_quantity: 0,
        new_quantity: 5,
        performed_by_id: "u-1",
        performed_by_name: "Admin User",
        reason: "Compra inicial",
        document_number: "NF-100",
        created_at: "2026-01-10T10:00:00Z",
      },
      {
        id: "mov-2",
        asset_id: "asset-1",
        movement_type: MovementType.SAIDA,
        quantity: 2,
        previous_quantity: 5,
        new_quantity: 3,
        performed_by_id: "u-2",
        performed_by_name: "Manager User",
        reason: "Uso na guarita",
        document_number: null,
        created_at: "2026-01-11T14:00:00Z",
      },
      {
        id: "mov-3",
        asset_id: "asset-1",
        movement_type: MovementType.AJUSTE_INVENTARIO,
        quantity: 4,
        previous_quantity: 3,
        new_quantity: 4,
        performed_by_id: "u-1",
        performed_by_name: "Admin User",
        reason: "Ajuste de contagem",
        document_number: null,
        created_at: "2026-01-12T09:00:00Z",
      },
      {
        id: "mov-4",
        asset_id: "asset-1",
        movement_type: MovementType.BAIXA_PATRIMONIAL,
        quantity: 1,
        previous_quantity: 4,
        new_quantity: 3,
        performed_by_id: "u-1",
        performed_by_name: "Admin User",
        reason: "Descarte por defeito",
        document_number: "LAUDO-99",
        created_at: "2026-01-13T11:00:00Z",
      },
    ];

    vi.spyOn(useAssetsModule, "useAsset").mockReturnValue({
      data: { ...mockAsset, movements } as any,
      isLoading: false,
    } as any);

    const onClose = vi.fn();
    render(
      <AssetMovementHistoryModal
        isOpen={true}
        onClose={onClose}
        asset={mockAsset}
      />
    );

    expect(screen.getByText("Compra inicial")).toBeInTheDocument();
    expect(screen.getByText("Uso na guarita")).toBeInTheDocument();
    expect(screen.getByText("Ajuste de contagem")).toBeInTheDocument();
    expect(screen.getByText("Descarte por defeito")).toBeInTheDocument();
    expect(screen.getByText("NF-100")).toBeInTheDocument();
    expect(screen.getByText("LAUDO-99")).toBeInTheDocument();

    const closeBtn = screen.getByRole("button", { name: "Fechar" });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });
});
