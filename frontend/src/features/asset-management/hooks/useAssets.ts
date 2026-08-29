import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAsset,
  deleteAsset,
  getAssetById,
  getAssets,
  getAssetSummary,
  getInventoryMovements,
  recordMovement,
  updateAsset,
} from "../../../api/assets";
import type {
  AssetFilterParams,
  AssetFormData,
  MovementFormData,
} from "../../../types/asset";

export const useAssets = (params?: AssetFilterParams) => {
  return useQuery({
    queryKey: ["assets", params],
    queryFn: () => getAssets(params),
  });
};

export const useAssetSummary = () => {
  return useQuery({
    queryKey: ["asset-summary"],
    queryFn: getAssetSummary,
  });
};

export const useAsset = (id: string) => {
  return useQuery({
    queryKey: ["assets", id],
    queryFn: () => getAssetById(id),
    enabled: !!id,
  });
};

export const useCreateAsset = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AssetFormData) => createAsset(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-movements"] });
    },
  });
};

export const useUpdateAsset = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AssetFormData> }) =>
      updateAsset(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["assets", variables.id] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
    },
  });
};

export const useDeleteAsset = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteAsset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-movements"] });
    },
  });
};

export const useRecordMovement = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      assetId,
      data,
    }: {
      assetId: string;
      data: MovementFormData;
    }) => recordMovement(assetId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["assets", variables.assetId] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-movements"] });
    },
  });
};

export const useInventoryMovements = (params?: {
  asset_id?: string;
  movement_type?: string;
  skip?: number;
  limit?: number;
}) => {
  return useQuery({
    queryKey: ["inventory-movements", params],
    queryFn: () => getInventoryMovements(params),
  });
};
