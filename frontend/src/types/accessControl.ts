export type AccessDeviceStatus = "ONLINE" | "OFFLINE" | "MAINTENANCE";
export type FacialTemplateSyncStatus = "PENDING" | "SYNCED" | "FAILED";

export interface AccessDevice {
  id: string;
  name: string;
  location?: string | null;
  status: AccessDeviceStatus;
  last_seen_at?: string | null;
  created_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface AccessDeviceWithKey extends AccessDevice {
  device_key: string;
}

export interface AccessDeviceCreate {
  name: string;
  location?: string | null;
}

export interface AccessDeviceStatusUpdate {
  status: AccessDeviceStatus;
}

export interface PaginatedAccessDeviceRead {
  items: AccessDevice[];
  total: number;
}

export interface FacialTemplate {
  id: string;
  resident_id: string;
  media_asset_id: string;
  sync_status: FacialTemplateSyncStatus;
  synced_at?: string | null;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FacialAccessEvent {
  id: string;
  device_id: string;
  resident_id?: string | null;
  matched: boolean;
  confidence_score?: number | null;
  access_granted: boolean;
  event_time: string;
  raw_payload?: string | null;
}

export interface PaginatedFacialAccessEventRead {
  items: FacialAccessEvent[];
  total: number;
  skip: number;
  limit: number;
}
