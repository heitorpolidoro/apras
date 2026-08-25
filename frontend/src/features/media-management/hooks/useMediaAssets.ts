import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  uploadPhoto,
  getPendingPhotos,
  approvePhoto,
  rejectPhoto,
  deletePhoto,
  getPhotoMetadata,
} from '../../../api/uploads';
import { EntityType } from '../../../types/media_asset';

export function usePendingPhotos(page: number = 1, limit: number = 20) {
  return useQuery({
    queryKey: ['pendingPhotos', page, limit],
    queryFn: () => getPendingPhotos(page, limit),
  });
}

export function useUploadPhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      entityType,
      entityId,
    }: {
      file: File | Blob;
      entityType: EntityType;
      entityId?: string;
    }) => uploadPhoto(file, entityType, entityId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingPhotos'] });
    },
  });
}

export function useApprovePhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (photoId: string) => approvePhoto(photoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingPhotos'] });
    },
  });
}

export function useRejectPhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      photoId,
      rejectionReason,
    }: {
      photoId: string;
      rejectionReason: string;
    }) => rejectPhoto(photoId, rejectionReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingPhotos'] });
    },
  });
}

export function useDeletePhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (photoId: string) => deletePhoto(photoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingPhotos'] });
    },
  });
}

export function usePhotoMetadata(photoId: string) {
  return useQuery({
    queryKey: ['photoMetadata', photoId],
    queryFn: () => getPhotoMetadata(photoId),
    enabled: !!photoId,
  });
}
