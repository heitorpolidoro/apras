import apiClient from './client';
import type {
  EntityType,
  MediaAssetRead,
  MediaAssetListResponse,
} from '../types/media_asset';

export async function uploadPhoto(
  file: File | Blob,
  entityType: EntityType,
  entityId?: string
): Promise<MediaAssetRead> {
  const formData = new FormData();
  const filename = file instanceof File ? file.name : 'webcam_capture.jpg';
  formData.append('file', file, filename);
  formData.append('entity_type', entityType);
  if (entityId) {
    formData.append('entity_id', entityId);
  }

  const response = await apiClient.post<MediaAssetRead>('/uploads/photo', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

export async function getPendingPhotos(
  page: number = 1,
  limit: number = 20
): Promise<MediaAssetListResponse> {
  const response = await apiClient.get<MediaAssetListResponse>('/uploads/photos/pending', {
    params: { page, limit },
  });
  return response.data;
}

export async function approvePhoto(photoId: string): Promise<MediaAssetRead> {
  const response = await apiClient.put<MediaAssetRead>(`/uploads/photos/${photoId}/approve`);
  return response.data;
}

export async function rejectPhoto(
  photoId: string,
  rejectionReason: string
): Promise<MediaAssetRead> {
  const response = await apiClient.put<MediaAssetRead>(`/uploads/photos/${photoId}/reject`, {
    rejection_reason: rejectionReason,
  });
  return response.data;
}

export async function deletePhoto(photoId: string): Promise<void> {
  await apiClient.delete(`/uploads/photos/${photoId}`);
}

export async function getPhotoMetadata(photoId: string): Promise<MediaAssetRead> {
  const response = await apiClient.get<MediaAssetRead>(`/uploads/photos/${photoId}`);
  return response.data;
}
