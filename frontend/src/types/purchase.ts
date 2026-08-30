export const PurchaseRequestStatus = {
  OPEN: "OPEN",
  DECIDED: "DECIDED",
  CANCELLED: "CANCELLED",
} as const;
export type PurchaseRequestStatus =
  (typeof PurchaseRequestStatus)[keyof typeof PurchaseRequestStatus];

export interface QuoteExtraField {
  label: string;
  value: string;
}

export interface PurchaseQuote {
  id: string;
  purchase_request_id: string;
  supplier_name: string;
  supplier_contact: string | null;
  unit_price: number;
  quantity: number;
  notes: string | null;
  extra_fields: QuoteExtraField[];
  total_price: number;
  created_by_id: string;
  created_by_name?: string | null;
  is_selected: boolean;
  is_lowest_price: boolean;
  created_at: string;
  updated_at: string;
}

export interface PurchaseDecision {
  id: string;
  quote_id: string;
  quote_supplier_name?: string | null;
  quote_total_price?: number | null;
  justification: string;
  decided_by_id: string;
  decided_by_name?: string | null;
  decided_at: string;
  is_current: boolean;
}

export interface PurchaseRequest {
  id: string;
  title: string;
  description: string | null;
  general_notes: string | null;
  status: PurchaseRequestStatus;
  requested_by_id: string;
  requested_by_name?: string | null;
  quote_count: number;
  lowest_quote_total: number | null;
  selected_quote_id: string | null;
  selected_quote_total: number | null;
  decision_justification: string | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PurchaseRequestDetail extends PurchaseRequest {
  quotes: PurchaseQuote[];
  decisions: PurchaseDecision[];
  current_decision: PurchaseDecision | null;
}

export interface PurchaseSummary {
  open_count: number;
  decided_count: number;
  cancelled_count: number;
  total_selected_value: number;
}

export interface PaginatedPurchaseRequests {
  items: PurchaseRequest[];
  total: number;
  skip: number;
  limit: number;
}

export interface PurchaseRequestFormData {
  title: string;
  description?: string | null;
  general_notes?: string | null;
}

export interface QuoteFormData {
  supplier_name: string;
  supplier_contact?: string | null;
  unit_price: number;
  quantity: number;
  notes?: string | null;
  extra_fields: QuoteExtraField[];
}

export interface DecisionFormData {
  quote_id: string;
  justification: string;
}

export interface PurchaseFilterParams {
  status?: PurchaseRequestStatus;
  requested_by_id?: string;
  search?: string;
  skip?: number;
  limit?: number;
}
