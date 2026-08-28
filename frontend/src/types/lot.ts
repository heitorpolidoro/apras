import { UserRole } from "./auth";

export const LotStatus = {
  VACANT: "VACANT",
  OCCUPIED: "OCCUPIED",
  UNDER_CONSTRUCTION: "UNDER_CONSTRUCTION",
} as const;

export type LotStatus = (typeof LotStatus)[keyof typeof LotStatus];

export const LotAssociationType = {
  PROPRIETARIO: "PROPRIETARIO",
  INQUILINO: "INQUILINO",
  RESPONSAVEL_FINANCEIRO: "RESPONSAVEL_FINANCEIRO",
  OUTRO: "OUTRO",
} as const;

export type LotAssociationType = (typeof LotAssociationType)[keyof typeof LotAssociationType];

export interface Lot {
  id: string;
  block: string;
  lot_number: string;
  address?: string | null;
  postal_code?: string | null;
  area_sqm?: number | null;
  fraction_ideal?: number | null;
  status: LotStatus;
  notes?: string | null;
  is_deleted: boolean;
  is_delinquent?: boolean;
  delinquency_updated_at?: string | null;
  delinquency_updated_by_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserSummary {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
}

export interface UserLotLink {
  id: string;
  user_id: string;
  lot_id: string;
  association_type: LotAssociationType;
  is_primary: boolean;
  start_date?: string | null;
  end_date?: string | null;
  created_at: string;
  user: UserSummary;
}

export interface LotDetail extends Lot {
  users: UserLotLink[];
}

export interface LotCreate {
  block: string;
  lot_number: string;
  address?: string | null;
  postal_code?: string | null;
  area_sqm?: number | null;
  fraction_ideal?: number | null;
  status?: LotStatus;
  notes?: string | null;
}

export interface LotUpdate {
  block?: string;
  lot_number?: string;
  address?: string | null;
  postal_code?: string | null;
  area_sqm?: number | null;
  fraction_ideal?: number | null;
  status?: LotStatus;
  notes?: string | null;
}

export interface UserLotLinkCreate {
  user_id: string;
  association_type?: LotAssociationType;
  is_primary?: boolean;
  start_date?: string | null;
  end_date?: string | null;
}

export interface PaginatedLotRead {
  items: Lot[];
  total: number;
  skip: number;
  limit: number;
}
