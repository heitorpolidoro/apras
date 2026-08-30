import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addQuote,
  cancelPurchaseRequest,
  createPurchaseRequest,
  deletePurchaseRequest,
  deleteQuote,
  getPurchaseRequestById,
  getPurchaseRequests,
  getPurchaseSummary,
  selectQuote,
  updatePurchaseRequest,
  updateQuote,
} from "../../../api/purchases";
import type {
  DecisionFormData,
  PurchaseFilterParams,
  PurchaseRequestFormData,
  QuoteFormData,
} from "../../../types/purchase";

const LIST_KEY = "purchase-requests";
const SUMMARY_KEY = "purchase-summary";

export const usePurchaseRequests = (params?: PurchaseFilterParams) =>
  useQuery({
    queryKey: [LIST_KEY, params],
    queryFn: () => getPurchaseRequests(params),
  });

export const usePurchaseSummary = () =>
  useQuery({
    queryKey: [SUMMARY_KEY],
    queryFn: getPurchaseSummary,
  });

export const usePurchaseRequest = (id: string | null) =>
  useQuery({
    queryKey: [LIST_KEY, id],
    queryFn: () => getPurchaseRequestById(id as string),
    enabled: !!id,
  });

const useInvalidator = () => {
  const queryClient = useQueryClient();
  return (requestId?: string) => {
    queryClient.invalidateQueries({ queryKey: [LIST_KEY] });
    if (requestId) {
      queryClient.invalidateQueries({ queryKey: [LIST_KEY, requestId] });
    }
    queryClient.invalidateQueries({ queryKey: [SUMMARY_KEY] });
  };
};

export const useCreatePurchaseRequest = () => {
  const invalidate = useInvalidator();
  return useMutation({
    mutationFn: (data: PurchaseRequestFormData) => createPurchaseRequest(data),
    onSuccess: () => invalidate(),
  });
};

export const useUpdatePurchaseRequest = () => {
  const invalidate = useInvalidator();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<PurchaseRequestFormData>;
    }) => updatePurchaseRequest(id, data),
    onSuccess: (_, variables) => invalidate(variables.id),
  });
};

export const useDeletePurchaseRequest = () => {
  const invalidate = useInvalidator();
  return useMutation({
    mutationFn: (id: string) => deletePurchaseRequest(id),
    onSuccess: (_, id) => invalidate(id),
  });
};

export const useAddQuote = () => {
  const invalidate = useInvalidator();
  return useMutation({
    mutationFn: ({
      requestId,
      data,
    }: {
      requestId: string;
      data: QuoteFormData;
    }) => addQuote(requestId, data),
    onSuccess: (_, variables) => invalidate(variables.requestId),
  });
};

export const useUpdateQuote = () => {
  const invalidate = useInvalidator();
  return useMutation({
    mutationFn: ({
      requestId,
      quoteId,
      data,
    }: {
      requestId: string;
      quoteId: string;
      data: Partial<QuoteFormData>;
    }) => updateQuote(requestId, quoteId, data),
    onSuccess: (_, variables) => invalidate(variables.requestId),
  });
};

export const useDeleteQuote = () => {
  const invalidate = useInvalidator();
  return useMutation({
    mutationFn: ({
      requestId,
      quoteId,
    }: {
      requestId: string;
      quoteId: string;
    }) => deleteQuote(requestId, quoteId),
    onSuccess: (_, variables) => invalidate(variables.requestId),
  });
};

export const useSelectQuote = () => {
  const invalidate = useInvalidator();
  return useMutation({
    mutationFn: ({
      requestId,
      data,
    }: {
      requestId: string;
      data: DecisionFormData;
    }) => selectQuote(requestId, data),
    onSuccess: (_, variables) => invalidate(variables.requestId),
  });
};

export const useCancelPurchaseRequest = () => {
  const invalidate = useInvalidator();
  return useMutation({
    mutationFn: (requestId: string) => cancelPurchaseRequest(requestId),
    onSuccess: (_, requestId) => invalidate(requestId),
  });
};
