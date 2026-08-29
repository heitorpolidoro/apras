import apiClient from './client';
import type {
  ConstructionProject,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  PaginatedProjects,
  ProjectCreatePayload,
  ProjectDetail,
  ProjectMilestone,
  ProjectStatus,
  ProjectUpdate,
  ProjectUpdateCreatePayload,
  ProjectUpdatePayload,
} from '../types/project';

export interface ProjectFilterParams {
  status?: ProjectStatus;
  skip?: number;
  limit?: number;
}

export const getProjects = async (
  params?: ProjectFilterParams
): Promise<PaginatedProjects> => {
  const response = await apiClient.get<PaginatedProjects>('/projects', {
    params,
  });
  return response.data;
};

export const getProjectDetail = async (id: string): Promise<ProjectDetail> => {
  const response = await apiClient.get<ProjectDetail>(`/projects/${id}`);
  return response.data;
};

export const createProject = async (
  payload: ProjectCreatePayload
): Promise<ConstructionProject> => {
  const response = await apiClient.post<ConstructionProject>('/projects', payload);
  return response.data;
};

export const updateProject = async (
  id: string,
  payload: ProjectUpdatePayload
): Promise<ConstructionProject> => {
  const response = await apiClient.put<ConstructionProject>(`/projects/${id}`, payload);
  return response.data;
};

export const deleteProject = async (id: string): Promise<void> => {
  await apiClient.delete(`/projects/${id}`);
};

export const createMilestone = async (
  projectId: string,
  payload: MilestoneCreatePayload
): Promise<ProjectMilestone> => {
  const response = await apiClient.post<ProjectMilestone>(
    `/projects/${projectId}/milestones`,
    payload
  );
  return response.data;
};

export const updateMilestone = async (
  projectId: string,
  milestoneId: string,
  payload: MilestoneUpdatePayload
): Promise<ProjectMilestone> => {
  const response = await apiClient.put<ProjectMilestone>(
    `/projects/${projectId}/milestones/${milestoneId}`,
    payload
  );
  return response.data;
};

export const deleteMilestone = async (
  projectId: string,
  milestoneId: string
): Promise<void> => {
  await apiClient.delete(`/projects/${projectId}/milestones/${milestoneId}`);
};

export const createProjectUpdate = async (
  projectId: string,
  payload: ProjectUpdateCreatePayload
): Promise<ProjectUpdate> => {
  const response = await apiClient.post<ProjectUpdate>(
    `/projects/${projectId}/updates`,
    payload
  );
  return response.data;
};

export const deleteProjectUpdate = async (
  projectId: string,
  updateId: string
): Promise<void> => {
  await apiClient.delete(`/projects/${projectId}/updates/${updateId}`);
};
