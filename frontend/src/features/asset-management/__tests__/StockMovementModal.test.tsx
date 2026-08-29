import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StockMovementModal } from "../components/StockMovementModal";
import type { Asset } from "../../../types/asset";
import { AssetCategory, AssetCondition, MovementType } from "../../../types/asset";

const mockAsset: Asset = {
  id: "asset-1",
  name: "Cimento CP II 50kg",
  category: AssetCategory.MANUTENCAO,
  serial_number: null,
  asset_tag: null,
  location: "Galpão",
  acquisition_date: null,
  acquisition_value: 40,
  condition: AssetCondition.NOVO,
  is_consumable: true,
  current_quantity: 10,
  min_quantity: 5,
  unit_of_measure: "sc",
  notes: null,
  is_low_stock: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("StockMovementModal component", () => {
  it("submits valid movement data", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <StockMovementModal
        isOpen={true}
        onClose={onClose}
        asset={mockAsset}
        canManageAdjustments={true}
        onSubmit={onSubmit}
      />
    );

    expect(screen.getByText("Registrar Movimentação")).toBeInTheDocument();
    expect(screen.getByText(/Saldo atual:/)).toBeInTheDocument();

    const quantityInput = screen.getByDisplayValue("1");
    fireEvent.change(quantityInput, { target: { value: "3" } });

    const reasonInput = screen.getByPlaceholderText(
      "Descreva a finalidade da movimentação, setor ou destino..."
    );
    fireEvent.change(reasonInput, { target: { value: "Compra adicional" } });

    const submitBtn = screen.getByText("Confirmar Movimentação");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("asset-1", {
        movement_type: MovementType.ENTRADA,
        quantity: 3,
        reason: "Compra adicional",
        document_number: null,
      });
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("blocks SAIDA when quantity exceeds stock", async () => {
    const onSubmit = vi.fn();
    render(
      <StockMovementModal
        isOpen={true}
        onClose={vi.fn()}
        asset={mockAsset}
        canManageAdjustments={false}
        onSubmit={onSubmit}
      />
    );

    // Select SAIDA
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: MovementType.SAIDA } });

    // Set quantity = 50 (> 10 current)
    const quantityInput = screen.getByDisplayValue("1");
    fireEvent.change(quantityInput, { target: { value: "50" } });

    const reasonInput = screen.getByPlaceholderText(
      "Descreva a finalidade da movimentação, setor ou destino..."
    );
    fireEvent.change(reasonInput, { target: { value: "Uso" } });

    fireEvent.click(screen.getByText("Confirmar Movimentação"));

    expect(
      screen.getByText(
        "A quantidade de saída não pode ser maior que o saldo atual em estoque."
      )
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("restricts adjustment options when canManageAdjustments is false", () => {
    render(
      <StockMovementModal
        isOpen={true}
        onClose={vi.fn()}
        asset={mockAsset}
        canManageAdjustments={false}
        onSubmit={vi.fn()}
      />
    );

    expect(screen.getByText("Entrada")).toBeInTheDocument();
    expect(screen.getByText("Saída")).toBeInTheDocument();
    expect(screen.queryByText("Ajuste de Inventário")).not.toBeInTheDocument();
    expect(screen.queryByText("Baixa Patrimonial")).not.toBeInTheDocument();
  });
});
