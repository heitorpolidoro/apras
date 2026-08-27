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
  cover_photo_url?: string | null;
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
