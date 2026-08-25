import apiClient from "./client";
import type {
  AccessLog,
  AccessLogCheckIn,
  AccessLogCheckOut,
  PaginatedAccessLogRead,
  PaginatedAuthorizationRead,
  PaginatedVisitorRead,
  Visitor,
  VisitorAuthorization,
  VisitorAuthorizationCreate,
  VisitorCreate,
  VisitorUpdate,
} from "../types/visitor";

export async function searchVisitors(
  q?: string,
  skip?: number,
  limit?: number
): Promise<PaginatedVisitorRead> {
  const response = await apiClient.get<PaginatedVisitorRead>("/visitors", {
    params: { q, skip, limit },
  });
  return response.data;
}

export async function createVisitor(data: VisitorCreate): Promise<Visitor> {
  const response = await apiClient.post<Visitor>("/visitors", data);
  return response.data;
}

export async function getVisitor(id: string): Promise<Visitor> {
  const response = await apiClient.get<Visitor>(`/visitors/${id}`);
  return response.data;
}

export async function updateVisitor(
  id: string,
  data: VisitorUpdate
): Promise<Visitor> {
  const response = await apiClient.put<Visitor>(`/visitors/${id}`, data);
  return response.data;
}

export async function getLotAuthorizations(
  lotId: string,
  statusFilter?: string,
  skip?: number,
  limit?: number
): Promise<PaginatedAuthorizationRead> {
  const response = await apiClient.get<PaginatedAuthorizationRead>(
    `/lots/${lotId}/authorizations`,
    { params: { status_filter: statusFilter, skip, limit } }
  );
  return response.data;
}

export async function createLotAuthorization(
  lotId: string,
  data: VisitorAuthorizationCreate
): Promise<VisitorAuthorization> {
  const response = await apiClient.post<VisitorAuthorization>(
    `/lots/${lotId}/authorizations`,
    data
  );
  return response.data;
}

export async function revokeAuthorization(
  authId: string,
  reason?: string
): Promise<VisitorAuthorization> {
  const response = await apiClient.put<VisitorAuthorization>(
    `/authorizations/${authId}/revoke`,
    { reason }
  );
  return response.data;
}

export async function checkInVisitor(data: AccessLogCheckIn): Promise<AccessLog> {
  const response = await apiClient.post<AccessLog>("/access-logs/check-in", data);
  return response.data;
}

export async function checkOutVisitor(data: AccessLogCheckOut): Promise<AccessLog> {
  const response = await apiClient.post<AccessLog>("/access-logs/check-out", data);
  return response.data;
}

export async function getAccessLogs(params?: {
  lot_id?: string;
  visitor_id?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedAccessLogRead> {
  const response = await apiClient.get<PaginatedAccessLogRead>("/access-logs", {
    params,
  });
  return response.data;
}
