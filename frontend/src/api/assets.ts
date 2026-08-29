import apiClient from "./client";
import type {
  Asset,
  AssetDetail,
  AssetFilterParams,
  AssetFormData,
  AssetSummary,
  InventoryMovement,
  MovementFormData,
  PaginatedAssets,
  PaginatedInventoryMovements,
} from "../types/asset";

export const getAssets = async (
  params?: AssetFilterParams
): Promise<PaginatedAssets> => {
  const response = await apiClient.get<PaginatedAssets>("/assets", {
    params,
  });
  return response.data;
};

export const getAssetSummary = async (): Promise<AssetSummary> => {
  const response = await apiClient.get<AssetSummary>("/assets/summary");
  return response.data;
};

export const getAssetById = async (id: string): Promise<AssetDetail> => {
  const response = await apiClient.get<AssetDetail>(`/assets/${id}`);
  return response.data;
};

export const createAsset = async (data: AssetFormData): Promise<Asset> => {
  const response = await apiClient.post<Asset>("/assets", data);
  return response.data;
};

export const updateAsset = async (
  id: string,
  data: Partial<AssetFormData>
): Promise<Asset> => {
  const response = await apiClient.put<Asset>(`/assets/${id}`, data);
  return response.data;
};

export const deleteAsset = async (id: string): Promise<void> => {
  await apiClient.delete(`/assets/${id}`);
};

export const recordMovement = async (
  assetId: string,
  data: MovementFormData
): Promise<InventoryMovement> => {
  const response = await apiClient.post<InventoryMovement>(
    `/assets/${assetId}/movements`,
    data
  );
  return response.data;
};

export const getInventoryMovements = async (params?: {
  asset_id?: string;
  movement_type?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedInventoryMovements> => {
  const response = await apiClient.get<PaginatedInventoryMovements>(
    "/inventory-movements",
    { params }
  );
  return response.data;
};
