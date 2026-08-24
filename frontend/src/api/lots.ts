import apiClient from "./client";
import type {
  Lot,
  LotCreate,
  LotDetail,
  LotStatus,
  LotUpdate,
  PaginatedLotRead,
  UserLotLink,
  UserLotLinkCreate,
} from "../types/lot";

export async function getLots(params?: {
  block?: string;
  status?: LotStatus;
  skip?: number;
  limit?: number;
}): Promise<PaginatedLotRead> {
  const response = await apiClient.get<PaginatedLotRead>("/lots/", { params });
  return response.data;
}

export async function createLot(data: LotCreate): Promise<Lot> {
  const response = await apiClient.post<Lot>("/lots/", data);
  return response.data;
}

export async function getLotDetail(id: string): Promise<LotDetail> {
  const response = await apiClient.get<LotDetail>(`/lots/${id}`);
  return response.data;
}

export async function updateLot(id: string, data: LotUpdate): Promise<Lot> {
  const response = await apiClient.put<Lot>(`/lots/${id}`, data);
  return response.data;
}

export async function deleteLot(id: string): Promise<void> {
  await apiClient.delete(`/lots/${id}`);
}

export async function linkUserLot(
  id: string,
  data: UserLotLinkCreate
): Promise<UserLotLink> {
  const response = await apiClient.post<UserLotLink>(`/lots/${id}/users`, data);
  return response.data;
}

export async function unlinkUserLot(id: string, userId: string): Promise<void> {
  await apiClient.delete(`/lots/${id}/users/${userId}`);
}
