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

/**
 * One line the request enumerates (APRAS-73 D1). `position` is assigned by
 * the server from the submitted index and is never sent by the client.
 */
export interface PurchaseRequestItem {
  id: string;
  description: string;
  quantity: number;
  position: number;
}

/**
 * One line a quote prices (APRAS-73 D2, D3).
 *
 * `description` and `quantity` are **echoed** by the backend — copied from
 * the request line when `request_item_id` is set — so the grid renders from
 * the quote payload alone. `request_item_id === null` marks a supplier's own
 * extra line, which counts toward the total and never toward coverage.
 */
export interface PurchaseQuoteItem {
  id: string;
  request_item_id: string | null;
  model: string | null;
  unit_price: number;
  description: string;
  quantity: number;
  position: number;
  line_total: number;
}

/** One line on the way in: the exclusive-or of D3, expressed as optionals. */
export interface PurchaseQuoteItemInput {
  request_item_id?: string | null;
  model?: string | null;
  unit_price: number;
  description?: string | null;
  quantity?: number | null;
}

/** One request line on the way in; `id` keeps an existing row (D7). */
export interface PurchaseRequestItemInput {
  id?: string;
  description: string;
  quantity: number;
}

export interface PurchaseQuote {
  id: string;
  purchase_request_id: string;
  supplier_name: string;
  supplier_contact: string | null;
  items: PurchaseQuoteItem[];
  /** Linked items only: an extra line never counts toward coverage (D5). */
  quoted_item_count: number;
  /** `quoted_item_count === request.items.length`, trivially true at zero. */
  is_complete: boolean;
  notes: string | null;
  extra_fields: QuoteExtraField[];
  /**
   * The supplier's own document (APRAS-63 D1): the public
   * `/static/uploads/...` URL and the original file name used as the link
   * text. Two columns on `purchase_quote`, never a `MediaAsset` row, and
   * absent from `QuoteFormData` — the file only ever travels as multipart.
   */
  attachment_url: string | null;
  attachment_filename: string | null;
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
  items: PurchaseRequestItem[];
  quote_count: number;
  /** Since APRAS-73 D10: the lowest total among the **complete** quotes. */
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
  /** Optional: a request may enumerate zero lines (D6). */
  items?: PurchaseRequestItemInput[];
}

export interface QuoteFormData {
  supplier_name: string;
  supplier_contact?: string | null;
  /** Required and never empty — a quote with no line has no price (D6). */
  items: PurchaseQuoteItemInput[];
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
