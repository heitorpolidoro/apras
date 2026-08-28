import apiClient from "./client";
import type {
  LotSummary,
  Package,
  PackageCreate,
  PackagePickup,
  PackageStatus,
  PaginatedPackages,
} from "../types/package";

export async function createPackage(data: PackageCreate): Promise<Package> {
  const response = await apiClient.post<Package>("/packages", data);
  return response.data;
}

export async function getPackagesForLot(
  lotId: string,
  status?: PackageStatus,
  skip?: number,
  limit?: number
): Promise<PaginatedPackages> {
  const response = await apiClient.get<PaginatedPackages>("/packages", {
    params: { lot_id: lotId, status, skip, limit },
  });
  return response.data;
}

export async function getPackageQueue(
  skip?: number,
  limit?: number
): Promise<PaginatedPackages> {
  const response = await apiClient.get<PaginatedPackages>("/packages/queue", {
    params: { skip, limit },
  });
  return response.data;
}

export async function getPackage(id: string): Promise<Package> {
  const response = await apiClient.get<Package>(`/packages/${id}`);
  return response.data;
}

export async function markPackagePickedUp(
  id: string,
  data: PackagePickup
): Promise<Package> {
  const response = await apiClient.post<Package>(`/packages/${id}/pickup`, data);
  return response.data;
}

export async function getMyPackageLots(): Promise<LotSummary[]> {
  const response = await apiClient.get<LotSummary[]>("/packages/my-lots");
  return response.data;
}
