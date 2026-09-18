import apiClient from "./client";
import type {
  DecisionFormData,
  PaginatedPurchaseRequests,
  PurchaseDecision,
  PurchaseFilterParams,
  PurchaseQuote,
  PurchaseRequest,
  PurchaseRequestDetail,
  PurchaseRequestFormData,
  PurchaseSummary,
  QuoteFormData,
} from "../types/purchase";

/**
 * `PurchaseService.ATTACHMENT_MAX_FILE_SIZE` — 5 MiB, the cap the backend
 * imports from `media_service.MAX_FILE_SIZE` rather than re-typing.
 *
 * The three constants below are **one half of a two-sided pin**, the shape
 * `src/api/tenantProfile.ts` established: neither side can import the other,
 * so each states the constant and names the other. The backend half is
 * `backend/tests/test_purchase_quote_attachment.py::test_the_attachment_contract_matches_the_frontend_client`,
 * which reads `PurchaseService` and `ROUTE_PERMISSIONS` and fails with this
 * file's name in the message.
 */
export const QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;

/**
 * `PurchaseService.ATTACHMENT_ALLOWED_MIME_TYPES`.
 *
 * `image/webp` is absent because no supplier sends one, and `image/svg+xml`
 * for the same active-content reason as APRAS-61 D2: an SVG served
 * same-origin from `/static/uploads/` is a stored-XSS surface without a
 * sanitiser.
 */
export const QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
] as const;

/** The `accept=` of the file input, derived from the set above — never retyped. */
export const QUOTE_ATTACHMENT_ACCEPT =
  QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES.join(",");

export const getPurchaseRequests = async (
  params?: PurchaseFilterParams,
): Promise<PaginatedPurchaseRequests> => {
  const response = await apiClient.get<PaginatedPurchaseRequests>(
    "/purchase-requests",
    { params },
  );
  return response.data;
};

export const getPurchaseSummary = async (): Promise<PurchaseSummary> => {
  const response = await apiClient.get<PurchaseSummary>(
    "/purchase-requests/summary",
  );
  return response.data;
};

export const getPurchaseRequestById = async (
  id: string,
): Promise<PurchaseRequestDetail> => {
  const response = await apiClient.get<PurchaseRequestDetail>(
    `/purchase-requests/${id}`,
  );
  return response.data;
};

export const createPurchaseRequest = async (
  data: PurchaseRequestFormData,
): Promise<PurchaseRequest> => {
  const response = await apiClient.post<PurchaseRequest>(
    "/purchase-requests",
    data,
  );
  return response.data;
};

export const updatePurchaseRequest = async (
  id: string,
  data: Partial<PurchaseRequestFormData>,
): Promise<PurchaseRequest> => {
  const response = await apiClient.put<PurchaseRequest>(
    `/purchase-requests/${id}`,
    data,
  );
  return response.data;
};

export const deletePurchaseRequest = async (id: string): Promise<void> => {
  await apiClient.delete(`/purchase-requests/${id}`);
};

export const addQuote = async (
  requestId: string,
  data: QuoteFormData,
): Promise<PurchaseQuote> => {
  const response = await apiClient.post<PurchaseQuote>(
    `/purchase-requests/${requestId}/quotes`,
    data,
  );
  return response.data;
};

export const updateQuote = async (
  requestId: string,
  quoteId: string,
  data: Partial<QuoteFormData>,
): Promise<PurchaseQuote> => {
  const response = await apiClient.put<PurchaseQuote>(
    `/purchase-requests/${requestId}/quotes/${quoteId}`,
    data,
  );
  return response.data;
};

export const deleteQuote = async (
  requestId: string,
  quoteId: string,
): Promise<void> => {
  await apiClient.delete(`/purchase-requests/${requestId}/quotes/${quoteId}`);
};

/**
 * Attach the supplier's document to one quote. The response body *is* the
 * quote, carrying the new `attachment_url` and `attachment_filename`.
 */
export const uploadQuoteAttachment = async (
  requestId: string,
  quoteId: string,
  file: File,
): Promise<PurchaseQuote> => {
  const formData = new FormData();
  formData.append("file", file, file.name);
  const response = await apiClient.put<PurchaseQuote>(
    `/purchase-requests/${requestId}/quotes/${quoteId}/attachment`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data;
};

/** Remove it. Idempotent: a quote with no document is still a 200. */
export const deleteQuoteAttachment = async (
  requestId: string,
  quoteId: string,
): Promise<PurchaseQuote> => {
  const response = await apiClient.delete<PurchaseQuote>(
    `/purchase-requests/${requestId}/quotes/${quoteId}/attachment`,
  );
  return response.data;
};

export const selectQuote = async (
  requestId: string,
  data: DecisionFormData,
): Promise<PurchaseDecision> => {
  const response = await apiClient.post<PurchaseDecision>(
    `/purchase-requests/${requestId}/decision`,
    data,
  );
  return response.data;
};

export const cancelPurchaseRequest = async (
  requestId: string,
): Promise<PurchaseRequest> => {
  const response = await apiClient.post<PurchaseRequest>(
    `/purchase-requests/${requestId}/cancel`,
  );
  return response.data;
};
