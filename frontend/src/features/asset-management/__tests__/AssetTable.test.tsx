import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AssetTable } from "../components/AssetTable";
import type { Asset } from "../../../types/asset";
import { AssetCategory, AssetCondition } from "../../../types/asset";

const mockAssets: Asset[] = [
  {
    id: "a-1",
    name: "Furadeira Bosch",
    category: AssetCategory.FERRAMENTAS,
    serial_number: "SN-999",
    asset_tag: "PAT-001",
    location: "Oficina",
    acquisition_date: "2026-01-01",
    acquisition_value: 500,
    condition: AssetCondition.BOM,
    is_consumable: false,
    current_quantity: 1,
    min_quantity: null,
    unit_of_measure: "un",
    notes: null,
    is_low_stock: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "a-2",
    name: "Detergente 5L",
    category: AssetCategory.LIMPEZA,
    serial_number: null,
    asset_tag: null,
    location: "DML",
    acquisition_date: null,
    acquisition_value: 30,
    condition: AssetCondition.NOVO,
    is_consumable: true,
    current_quantity: 2,
    min_quantity: 5,
    unit_of_measure: "L",
    notes: null,
    is_low_stock: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

describe("AssetTable component", () => {
  it("renders table with assets and triggers callbacks", () => {
    const onOpenMovement = vi.fn();
    const onOpenHistory = vi.fn();
    const onEdit = vi.fn();
    const onDelete = vi.fn();

    render(
      <AssetTable
        assets={mockAssets}
        canManage={true}
        onOpenMovement={onOpenMovement}
        onOpenHistory={onOpenHistory}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );

    expect(screen.getByText("Furadeira Bosch")).toBeInTheDocument();
    expect(screen.getByText("Detergente 5L")).toBeInTheDocument();
    expect(screen.getByText("PAT-001")).toBeInTheDocument();
    expect(screen.getByText("S/N: SN-999")).toBeInTheDocument();
    expect(screen.getByText("Estoque Baixo")).toBeInTheDocument();

    // Trigger buttons
    const movementButtons = screen.getAllByTitle("Movimentar");
    fireEvent.click(movementButtons[0]);
    expect(onOpenMovement).toHaveBeenCalledWith(mockAssets[0]);

    const historyButtons = screen.getAllByTitle("Histórico");
    fireEvent.click(historyButtons[0]);
    expect(onOpenHistory).toHaveBeenCalledWith(mockAssets[0]);

    const editButtons = screen.getAllByTitle("Editar");
    fireEvent.click(editButtons[0]);
    expect(onEdit).toHaveBeenCalledWith(mockAssets[0]);

    const deleteButtons = screen.getAllByTitle("Excluir");
    fireEvent.click(deleteButtons[0]);
    expect(onDelete).toHaveBeenCalledWith(mockAssets[0]);
  });

  it("hides edit and delete buttons when canManage is false", () => {
    render(
      <AssetTable
        assets={mockAssets}
        canManage={false}
        onOpenMovement={vi.fn()}
        onOpenHistory={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(screen.queryByTitle("Editar")).not.toBeInTheDocument();
    expect(screen.queryByTitle("Excluir")).not.toBeInTheDocument();
  });

  it("renders empty message when no assets are found", () => {
    render(
      <AssetTable
        assets={[]}
        onOpenMovement={vi.fn()}
        onOpenHistory={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(
      screen.getByText("Nenhum ativo ou item encontrado.")
    ).toBeInTheDocument();
  });
});
