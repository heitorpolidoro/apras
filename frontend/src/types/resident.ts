export const ResidentRelationship = {
  TITULAR: "TITULAR",
  CONJUGE: "CONJUGE",
  FILHO_DEPENDENTE: "FILHO_DEPENDENTE",
  INQUILINO: "INQUILINO",
  PARENTE: "PARENTE",
  OUTRO: "OUTRO",
} as const;

export type ResidentRelationship =
  (typeof ResidentRelationship)[keyof typeof ResidentRelationship];

export interface ResidentUserSummary {
  id: string;
  full_name: string;
  email: string;
  role: string;
}

export interface ResidentLotSummary {
  id: string;
  block: string;
  lot_number: string;
}

export interface Resident {
  id: string;
  lot_id: string;
  user_id?: string | null;
  full_name: string;
  cpf: string;
  rg?: string | null;
  birth_date?: string | null;
  phone?: string | null;
  email?: string | null;
  relationship_type: ResidentRelationship;
  is_active: boolean;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResidentDetail extends Resident {
  user?: ResidentUserSummary | null;
  lot?: ResidentLotSummary | null;
}

export interface ResidentCreatePayload {
  full_name: string;
  cpf: string;
  rg?: string;
  birth_date?: string;
  phone?: string;
  email?: string;
  relationship_type?: ResidentRelationship;
  notes?: string;
}

export interface ResidentUpdatePayload {
  full_name?: string;
  cpf?: string;
  rg?: string;
  birth_date?: string;
  phone?: string;
  email?: string;
  relationship_type?: ResidentRelationship;
  is_active?: boolean;
  notes?: string;
}

export interface LinkUserPayload {
  user_id: string;
}

export interface PaginatedResidentRead {
  items: ResidentDetail[];
  total: number;
  skip: number;
  limit: number;
}
