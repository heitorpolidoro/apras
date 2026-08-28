export enum PackageStatus {
  AWAITING_PICKUP = "AWAITING_PICKUP",
  PICKED_UP = "PICKED_UP",
}

export interface LotSummary {
  id: string;
  block: string;
  lot_number: string;
}

export interface Package {
  id: string;
  lot_id: string;
  lot_summary: LotSummary | null;
  received_by_id: string | null;
  received_by_name: string | null;
  description: string | null;
  carrier: string | null;
  received_at: string;
  status: PackageStatus;
  picked_up_at: string | null;
  picked_up_by_id: string | null;
  picked_up_by_name: string | null;
  picked_up_by_notes: string | null;
}

export interface PackageCreate {
  lot_id: string;
  description?: string;
  carrier?: string;
}

export interface PackagePickup {
  picked_up_by_notes?: string;
}

export interface PaginatedPackages {
  items: Package[];
  total: number;
  skip: number;
  limit: number;
}
