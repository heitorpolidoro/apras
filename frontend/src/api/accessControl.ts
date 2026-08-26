import apiClient from "./client";
import type {
  AccessDeviceCreate,
  AccessDeviceStatusUpdate,
  AccessDeviceWithKey,
  FacialTemplate,
  PaginatedAccessDeviceRead,
  PaginatedFacialAccessEventRead,
} from "../types/accessControl";

export async function createDevice(
  data: AccessDeviceCreate,
): Promise<AccessDeviceWithKey> {
  const response = await apiClient.post<AccessDeviceWithKey>(
    "/access-control/devices",
    data,
  );
  return response.data;
}

export async function listDevices(): Promise<PaginatedAccessDeviceRead> {
  const response = await apiClient.get<PaginatedAccessDeviceRead>(
    "/access-control/devices",
  );
  return response.data;
}

export async function updateDeviceStatus(
  deviceId: string,
  data: AccessDeviceStatusUpdate,
): Promise<AccessDeviceWithKey> {
  const response = await apiClient.put<AccessDeviceWithKey>(
    `/access-control/devices/${deviceId}/status`,
    data,
  );
  return response.data;
}

export async function regenerateDeviceKey(
  deviceId: string,
): Promise<AccessDeviceWithKey> {
  const response = await apiClient.post<AccessDeviceWithKey>(
    `/access-control/devices/${deviceId}/regenerate-key`,
  );
  return response.data;
}

export async function syncFacialTemplate(
  residentId: string,
): Promise<FacialTemplate> {
  const response = await apiClient.post<FacialTemplate>(
    `/access-control/residents/${residentId}/facial-template/sync`,
  );
  return response.data;
}

export async function getFacialTemplate(
  residentId: string,
): Promise<FacialTemplate | null> {
  const response = await apiClient.get<FacialTemplate | null>(
    `/access-control/residents/${residentId}/facial-template`,
  );
  return response.data;
}

export async function getAccessEvents(params?: {
  device_id?: string;
  resident_id?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedFacialAccessEventRead> {
  const response = await apiClient.get<PaginatedFacialAccessEventRead>(
    "/access-control/events",
    { params },
  );
  return response.data;
}
