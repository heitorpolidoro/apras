export type EntityType =
  | 'RESIDENT'
  | 'VISITOR'
  | 'EMPLOYEE'
  | 'LOT'
  | 'ANNOUNCEMENT'
  | 'OCCURRENCE';

export type StorageProvider =
  | 'LOCAL_DISK'
  | 'VERCEL_BLOB'
  | 'AWS_S3'
  | 'CLOUDINARY';

export type PhotoApprovalStatus =
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED';

export interface MediaAssetRead {
  id: string;
  entity_type: EntityType;
  entity_id: string | null;
  storage_provider: StorageProvider;
  file_path: string;
  url: str;
  thumbnail_url: string | null;
  file_size_bytes: number;
  mime_type: string;
  width: number | null;
  height: number | null;
  status: PhotoApprovalStatus;
  rejection_reason: string | null;
  uploaded_by_id: string;
  uploaded_by_name?: string | null;
  approved_by_id?: string | null;
  approved_by_name?: string | null;
  created_at: string;
  updated_at: string;
  approved_at?: string | null;
}

export interface PhotoRejectRequest {
  rejection_reason: string;
}

export interface MediaAssetListResponse {
  items: MediaAssetRead[];
  total: number;
  pending_count: number;
}
