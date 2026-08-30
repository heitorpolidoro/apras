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
