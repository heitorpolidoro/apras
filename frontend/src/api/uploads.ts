import apiClient from './client';
import type {
  EntityType,
  MediaAssetRead,
  MediaAssetListResponse,
} from '../types/media_asset';

/**
 * The four facts `POST /api/v1/uploads/photo` states about itself, declared on
 * this side of the language boundary.
 *
 * **This is one half of a two-sided pin**, the shape the repo already uses for
 * `lotSelectContract.test.tsx` ↔
 * `test_infractions.py::test_the_lots_route_ceiling_matches_the_lot_selects_limit`
 * and `i18n/__tests__/index.test.ts` ↔ `test_module_vocabulary.py`: neither
 * side can import the other, so each states the constant and names the other.
 * The backend half is
 * `backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`,
 * which reads `media_service`, `EntityType`, `ROUTE_PERMISSIONS` and the live
 * route's `dependant` and fails with this file's name in the message.
 *
 * Constants and not literals scattered over the callers, for the same reason
 * `LOT_SELECT_LIMIT` is exported: a number that is a contract with a route has
 * to be assertable by a test rather than by a reader's memory.
 */

/** `media_service.MAX_FILE_SIZE` — 5 MiB. */
export const UPLOAD_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;

/** `media_service.ALLOWED_MIME_TYPES`. The endpoint accepts image only. */
export const UPLOAD_ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
] as const;

/** The `accept=` of a file input, derived from the set above — never retyped. */
export const UPLOAD_ACCEPT = UPLOAD_ALLOWED_MIME_TYPES.join(',');

/**
 * The permission the route demands since APRAS-51
 * (`core/permissions.py` ↔ `require_permission` in `endpoints/uploads.py`).
 * Read by the infraction attachment control's gate.
 */
export const UPLOAD_PHOTO_PERMISSION = 'uploads:photo_create';

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
