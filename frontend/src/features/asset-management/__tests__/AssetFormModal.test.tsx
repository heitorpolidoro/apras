import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AssetFormModal } from "../components/AssetFormModal";
import type { Asset } from "../../../types/asset";
import { AssetCategory, AssetCondition } from "../../../types/asset";

const mockAsset: Asset = {
  id: "asset-1",
  name: "Cortador de Grama",
  category: AssetCategory.FERRAMENTAS,
  serial_number: "SN-12345",
  asset_tag: "PAT-001",
  location: "Oficina",
  acquisition_date: "2026-01-15",
  acquisition_value: 2500,
  condition: AssetCondition.BOM,
  is_consumable: false,
  current_quantity: 1,
  min_quantity: null,
  unit_of_measure: "un",
  notes: "Nota teste",
  is_low_stock: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("AssetFormModal component", () => {
  it("renders null when isOpen is false", () => {
    const { container } = render(
      <AssetFormModal
        isOpen={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders create form and submits valid payload", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <AssetFormModal
        isOpen={true}
        onClose={onClose}
        onSubmit={onSubmit}
        initialData={null}
      />
    );

    expect(screen.getByText("Novo Ativo / Item de Estoque")).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText(
      "Ex: Cortador de grama, Lâmpada LED"
    );
    fireEvent.change(nameInput, { target: { value: "Projetor HDMI" } });

    const locationInput = screen.getByPlaceholderText(
      "Ex: Almoxarifado, Portaria 1, DML"
    );
    fireEvent.change(locationInput, { target: { value: "Salão Nobre" } });

    fireEvent.click(screen.getByText("Cadastrar Item"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Projetor HDMI",
          location: "Salão Nobre",
          category: AssetCategory.OUTROS,
        })
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("shows error when name or location is empty", async () => {
    const onSubmit = vi.fn();
    render(
      <AssetFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
        initialData={null}
      />
    );

    fireEvent.click(screen.getByText("Cadastrar Item"));
    expect(
      screen.getByText("O nome do item é obrigatório.")
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();

    const nameInput = screen.getByPlaceholderText(
      "Ex: Cortador de grama, Lâmpada LED"
    );
    fireEvent.change(nameInput, { target: { value: "Projetor" } });
    fireEvent.click(screen.getByText("Cadastrar Item"));
    expect(
      screen.getByText("A localização é obrigatória.")
    ).toBeInTheDocument();
  });

  it("renders edit form with initialData and updates fields", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <AssetFormModal
        isOpen={true}
        onClose={onClose}
        onSubmit={onSubmit}
        initialData={mockAsset}
      />
    );

    expect(screen.getByText("Editar Ativo / Item")).toBeInTheDocument();
    const locationInput = screen.getByDisplayValue("Oficina");
    fireEvent.change(locationInput, { target: { value: "Galpão Principal" } });

    fireEvent.click(screen.getByRole("button", { name: "Salvar Alterações" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Cortador de Grama",
          location: "Galpão Principal",
        })
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("handles consumable toggle and field changes", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <AssetFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
        initialData={null}
      />
    );

    const consumableCheckbox = screen.getByRole("checkbox");
    fireEvent.click(consumableCheckbox);

    const nameInput = screen.getByPlaceholderText(
      "Ex: Cortador de grama, Lâmpada LED"
    );
    fireEvent.change(nameInput, { target: { value: "Lâmpada LED" } });
    const locationInput = screen.getByPlaceholderText(
      "Ex: Almoxarifado, Portaria 1, DML"
    );
    fireEvent.change(locationInput, { target: { value: "Depósito Elétrica" } });

    fireEvent.click(screen.getByText("Cadastrar Item"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Lâmpada LED",
          is_consumable: true,
        })
      );
    });
  });

  it("displays submission error when onSubmit throws", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("Falha na API"));
    render(
      <AssetFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
        initialData={null}
      />
    );

    const nameInput = screen.getByPlaceholderText(
      "Ex: Cortador de grama, Lâmpada LED"
    );
    fireEvent.change(nameInput, { target: { value: "Projetor" } });
    const locationInput = screen.getByPlaceholderText(
      "Ex: Almoxarifado, Portaria 1, DML"
    );
    fireEvent.change(locationInput, { target: { value: "Auditório" } });

    fireEvent.click(screen.getByText("Cadastrar Item"));

    await waitFor(() => {
      expect(screen.getByText("Falha na API")).toBeInTheDocument();
    });
  });
});
