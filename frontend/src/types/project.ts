export type ProjectStatus = 'PLANNED' | 'IN_PROGRESS' | 'PAUSED' | 'COMPLETED';

export type MilestoneStatus = 'DONE' | 'IN_PROGRESS' | 'NEXT_STEPS';

export interface ConstructionProject {
  id: string;
  title: string;
  description?: string | null;
  contractor_name?: string | null;
  total_budget: number;
  executed_budget: number;
  physical_progress_pct: number;
  start_date?: string | null;
  estimated_completion_date?: string | null;
  actual_completion_date?: string | null;
  status: ProjectStatus;
  /**
   * Storage truth: exactly what the storage provider returned (APRAS-104 §A).
   *
   * **Not a display URL.** The Blob store is configured with private access,
   * so an `<img src>` pointed at this loads nothing -- for an anonymous reader
   * and for a signed-in administrator alike, because neither `<img>` carries a
   * credential of ours. Render `cover_photo_display_url` instead.
   */
  cover_photo_url?: string | null;
  /**
   * Which URL to load for this obra's cover photo, derived on read and never
   * stored (APRAS-104 §B).
   *
   * Our public cover route when the provider owns the stored value, the stored
   * value verbatim when it is a third-party URL (the Drive sync writes those),
   * and `null` when there is no cover -- in which case the caller draws its own
   * placeholder.
   */
  cover_photo_display_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectMilestone {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  status: MilestoneStatus;
  due_date?: string | null;
  completion_date?: string | null;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface AuthorSummary {
  id: string;
  full_name: string;
  email: string;
}

export interface ProjectUpdate {
  id: string;
  project_id: string;
  author_id: string;
  author?: AuthorSummary | null;
  title: string;
  content: string;
  photos: string[];
  cost_impact?: number | null;
  created_at: string;
}

export interface ProjectDetail extends ConstructionProject {
  milestones: ProjectMilestone[];
  updates: ProjectUpdate[];
}

export interface PaginatedProjects {
  items: ConstructionProject[];
  total: number;
  skip: number;
  limit: number;
}

export interface ProjectCreatePayload {
  title: string;
  description?: string | null;
  contractor_name?: string | null;
  total_budget?: number;
  executed_budget?: number;
  physical_progress_pct?: number;
  start_date?: string | null;
  estimated_completion_date?: string | null;
  actual_completion_date?: string | null;
  status?: ProjectStatus;
  cover_photo_url?: string | null;
}

export interface ProjectUpdatePayload {
  title?: string;
  description?: string | null;
  contractor_name?: string | null;
  total_budget?: number;
  executed_budget?: number;
  physical_progress_pct?: number;
  start_date?: string | null;
  estimated_completion_date?: string | null;
  actual_completion_date?: string | null;
  status?: ProjectStatus;
  cover_photo_url?: string | null;
}

export interface MilestoneCreatePayload {
  title: string;
  description?: string | null;
  status?: MilestoneStatus;
  due_date?: string | null;
  completion_date?: string | null;
  display_order?: number;
}

export interface MilestoneUpdatePayload {
  title?: string;
  description?: string | null;
  status?: MilestoneStatus;
  due_date?: string | null;
  completion_date?: string | null;
  display_order?: number;
}

export interface ProjectUpdateCreatePayload {
  title: string;
  content: string;
  photos?: string[];
  cost_impact?: number | null;
}
