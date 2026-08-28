import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  checkInVisitor,
  checkOutVisitor,
  createLotAuthorization,
  createVisitor,
  getAccessLogs,
  getAuthorization,
  getLotAuthorizations,
  getVisitor,
  revokeAuthorization,
  searchVisitors,
  updateVisitor,
} from "../../../api/visitors";
import type {
  AccessLogCheckIn,
  AccessLogCheckOut,
  VisitorAuthorizationCreate,
  VisitorCreate,
  VisitorUpdate,
} from "../../../types/visitor";

export const useVisitors = (q?: string, skip?: number, limit?: number) => {
  return useQuery({
    queryKey: ["visitors", q, skip, limit],
    queryFn: () => searchVisitors(q, skip, limit),
  });
};

export const useVisitor = (visitorId?: string) => {
  return useQuery({
    queryKey: ["visitor", visitorId],
    queryFn: () => (visitorId ? getVisitor(visitorId) : Promise.reject("No visitor ID")),
    enabled: !!visitorId,
  });
};

export const useCreateVisitor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: VisitorCreate) => createVisitor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["visitors"] });
    },
  });
};

export const useUpdateVisitor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: VisitorUpdate }) =>
      updateVisitor(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["visitors"] });
      queryClient.invalidateQueries({ queryKey: ["visitor", variables.id] });
    },
  });
};

export const useLotAuthorizations = (
  lotId?: string,
  statusFilter?: string,
  skip?: number,
  limit?: number
) => {
  return useQuery({
    queryKey: ["lot-authorizations", lotId, statusFilter, skip, limit],
    queryFn: () =>
      lotId
        ? getLotAuthorizations(lotId, statusFilter, skip, limit)
        : Promise.reject("No lot ID provided"),
    enabled: !!lotId,
  });
};

export const useAuthorization = (authorizationId?: string) => {
  return useQuery({
    queryKey: ["authorization", authorizationId],
    queryFn: () =>
      authorizationId
        ? getAuthorization(authorizationId)
        : Promise.reject("No authorization ID provided"),
    enabled: !!authorizationId,
    retry: false,
  });
};

export const useCreateAuthorization = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      lotId,
      data,
    }: {
      lotId: string;
      data: VisitorAuthorizationCreate;
    }) => createLotAuthorization(lotId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["lot-authorizations", variables.lotId],
      });
      queryClient.invalidateQueries({ queryKey: ["visitors"] });
    },
  });
};

export const useRevokeAuthorization = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ authId, reason }: { authId: string; lotId?: string; reason?: string }) =>
      revokeAuthorization(authId, reason),
    onSuccess: (_, variables) => {
      if (variables.lotId) {
        queryClient.invalidateQueries({
          queryKey: ["lot-authorizations", variables.lotId],
        });
      } else {
        queryClient.invalidateQueries({ queryKey: ["lot-authorizations"] });
      }
    },
  });
};

export const useCheckIn = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AccessLogCheckIn) => checkInVisitor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-logs"] });
      queryClient.invalidateQueries({ queryKey: ["lot-authorizations"] });
    },
  });
};

export const useCheckOut = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AccessLogCheckOut) => checkOutVisitor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-logs"] });
    },
  });
};

export const useAccessLogs = (params?: {
  lot_id?: string;
  visitor_id?: string;
  skip?: number;
  limit?: number;
}) => {
  return useQuery({
    queryKey: ["access-logs", params],
    queryFn: () => getAccessLogs(params),
  });
};
