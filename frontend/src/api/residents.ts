import apiClient from "./client";
import type {
  LinkUserPayload,
  PaginatedResidentRead,
  Resident,
  ResidentCreatePayload,
  ResidentDetail,
  ResidentUpdatePayload,
} from "../types/resident";

export async function getLotResidents(
  lotId: string,
  skip?: number,
  limit?: number
): Promise<PaginatedResidentRead> {
  const response = await apiClient.get<PaginatedResidentRead>(
    `/lots/${lotId}/residents`,
    { params: { skip, limit } }
  );
  return response.data;
}

export async function createResident(
  lotId: string,
  data: ResidentCreatePayload
): Promise<Resident> {
  const response = await apiClient.post<Resident>(
    `/lots/${lotId}/residents`,
    data
  );
  return response.data;
}

export async function getResidentDetail(
  residentId: string
): Promise<ResidentDetail> {
  const response = await apiClient.get<ResidentDetail>(
    `/residents/${residentId}`
  );
  return response.data;
}

export async function updateResident(
  residentId: string,
  data: ResidentUpdatePayload
): Promise<Resident> {
  const response = await apiClient.put<Resident>(
    `/residents/${residentId}`,
    data
  );
  return response.data;
}

export async function deleteResident(residentId: string): Promise<void> {
  await apiClient.delete(`/residents/${residentId}`);
}

export async function linkResidentUser(
  residentId: string,
  userId: string
): Promise<Resident> {
  const payload: LinkUserPayload = { user_id: userId };
  const response = await apiClient.post<Resident>(
    `/residents/${residentId}/link-user`,
    payload
  );
  return response.data;
}

export async function unlinkResidentUser(
  residentId: string
): Promise<Resident> {
  const response = await apiClient.post<Resident>(
    `/residents/${residentId}/unlink-user`
  );
  return response.data;
}
