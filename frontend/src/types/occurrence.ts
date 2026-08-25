export type OccurrenceCategory =
  | 'NOISE'
  | 'MAINTENANCE'
  | 'SECURITY'
  | 'PARKING'
  | 'RULES_VIOLATION'
  | 'OTHER';

export type OccurrenceStatus =
  | 'OPEN'
  | 'UNDER_REVIEW'
  | 'IN_PROGRESS'
  | 'RESOLVED'
  | 'REJECTED';

export type OccurrencePriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export interface Occurrence {
  id: string;
  protocol_number: string;
  lot_id?: string | null;
  lot_summary?: string | null;
  reporter_user_id?: string | null;
  reporter_name?: string | null;
  is_anonymous: boolean;
  is_public: boolean;
  category: OccurrenceCategory;
  title: string;
  description: string;
  photo_urls: string[];
  status: OccurrenceStatus;
  priority: OccurrencePriority;
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
  resolution_notes?: string | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
}

export interface OccurrenceTimeline {
  id: string;
  occurrence_id: string;
  actor_id: string;
  actor_name?: string | null;
  status_from?: OccurrenceStatus | null;
  status_to?: OccurrenceStatus | null;
  note: string;
  is_internal_only: boolean;
  created_at: string;
}

export interface OccurrenceDetail extends Occurrence {
  timeline: OccurrenceTimeline[];
}

export interface OccurrenceCreatePayload {
  lot_id?: string | null;
  is_anonymous?: boolean;
  is_public?: boolean;
  category: OccurrenceCategory;
  title: string;
  description: string;
  photo_urls?: string[] | null;
}

export interface OccurrenceStatusUpdatePayload {
  status?: OccurrenceStatus | null;
  priority?: OccurrencePriority | null;
  assigned_to_id?: string | null;
  resolution_notes?: string | null;
}

export interface TimelineNoteCreatePayload {
  note: string;
  is_internal_only?: boolean;
  status_to?: OccurrenceStatus | null;
}

export interface PaginatedOccurrencesResponse {
  items: Occurrence[];
  total: number;
  skip: number;
  limit: number;
}

export interface OccurrenceFilterParams {
  category?: OccurrenceCategory;
  status?: OccurrenceStatus;
  is_public?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}
