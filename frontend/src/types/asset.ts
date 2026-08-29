export const AssetCategory = {
  ELETRONICOS: "ELETRONICOS",
  FERRAMENTAS: "FERRAMENTAS",
  MOBILIARIO: "MOBILIARIO",
  SEGURANCA: "SEGURANCA",
  LIMPEZA: "LIMPEZA",
  MANUTENCAO: "MANUTENCAO",
  OUTROS: "OUTROS",
} as const;
export type AssetCategory = (typeof AssetCategory)[keyof typeof AssetCategory];

export const AssetCondition = {
  NOVO: "NOVO",
  BOM: "BOM",
  REGULAR: "REGULAR",
  RUIM: "RUIM",
  DANIFICADO: "DANIFICADO",
  BAIXADO: "BAIXADO",
} as const;
export type AssetCondition = (typeof AssetCondition)[keyof typeof AssetCondition];

export const MovementType = {
  ENTRADA: "ENTRADA",
  SAIDA: "SAIDA",
  AJUSTE_INVENTARIO: "AJUSTE_INVENTARIO",
  BAIXA_PATRIMONIAL: "BAIXA_PATRIMONIAL",
} as const;
export type MovementType = (typeof MovementType)[keyof typeof MovementType];

export interface Asset {
  id: string;
  name: string;
  category: AssetCategory;
  serial_number: string | null;
  asset_tag: string | null;
  location: string;
  acquisition_date: string | null;
  acquisition_value: number | null;
  condition: AssetCondition;
  is_consumable: boolean;
  current_quantity: number;
  min_quantity: number | null;
  unit_of_measure: string | null;
  notes: string | null;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryMovement {
  id: string;
  asset_id: string;
  movement_type: MovementType;
  quantity: number;
  previous_quantity: number;
  new_quantity: number;
  performed_by_id: string;
  performed_by_name?: string | null;
  asset_name?: string | null;
  reason: string;
  document_number: string | null;
  created_at: string;
}

export interface AssetDetail extends Asset {
  movements: InventoryMovement[];
}

export interface AssetSummary {
  total_assets: number;
  total_consumables: number;
  low_stock_count: number;
  total_patrimonial_value: number;
}

export interface PaginatedAssets {
  items: Asset[];
  total: number;
  skip: number;
  limit: number;
}

export interface PaginatedInventoryMovements {
  items: InventoryMovement[];
  total: number;
  skip: number;
  limit: number;
}

export interface AssetFormData {
  name: string;
  category: AssetCategory;
  serial_number?: string | null;
  asset_tag?: string | null;
  location: string;
  acquisition_date?: string | null;
  acquisition_value?: number | null;
  condition?: AssetCondition;
  is_consumable: boolean;
  current_quantity?: number;
  min_quantity?: number | null;
  unit_of_measure?: string | null;
  notes?: string | null;
}

export interface MovementFormData {
  movement_type: MovementType;
  quantity: number;
  reason: string;
  document_number?: string | null;
}

export interface AssetFilterParams {
  category?: AssetCategory;
  location?: string;
  is_consumable?: boolean;
  condition?: AssetCondition;
  search?: string;
  low_stock_only?: boolean;
  skip?: number;
  limit?: number;
}
