import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createMilestone,
  createProject,
  createProjectUpdate,
  deleteMilestone,
  deleteProject,
  deleteProjectUpdate,
  getProjectDetail,
  getProjects,
  type ProjectFilterParams,
  updateMilestone,
  updateProject,
} from '../../../api/projects';
import type {
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  ProjectCreatePayload,
  ProjectUpdateCreatePayload,
  ProjectUpdatePayload,
} from '../../../types/project';

export const PROJECTS_QUERY_KEY = ['projects'];

export function useProjects(params?: ProjectFilterParams) {
  return useQuery({
    queryKey: [...PROJECTS_QUERY_KEY, params],
    queryFn: () => getProjects(params),
  });
}

export function useProjectDetail(projectId: string | null) {
  return useQuery({
    queryKey: [...PROJECTS_QUERY_KEY, 'detail', projectId],
    queryFn: () =>
      projectId ? getProjectDetail(projectId) : Promise.reject('No ID'),
    enabled: Boolean(projectId),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProjectCreatePayload) => createProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ProjectUpdatePayload }) =>
      updateProject(id, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...PROJECTS_QUERY_KEY, 'detail', variables.id],
      });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY });
    },
  });
}

export function useCreateMilestone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      payload,
    }: {
      projectId: string;
      payload: MilestoneCreatePayload;
    }) => createMilestone(projectId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...PROJECTS_QUERY_KEY, 'detail', variables.projectId],
      });
    },
  });
}

export function useUpdateMilestone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      milestoneId,
      payload,
    }: {
      projectId: string;
      milestoneId: string;
      payload: MilestoneUpdatePayload;
    }) => updateMilestone(projectId, milestoneId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...PROJECTS_QUERY_KEY, 'detail', variables.projectId],
      });
    },
  });
}

export function useDeleteMilestone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      milestoneId,
    }: {
      projectId: string;
      milestoneId: string;
    }) => deleteMilestone(projectId, milestoneId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...PROJECTS_QUERY_KEY, 'detail', variables.projectId],
      });
    },
  });
}

export function useCreateProjectUpdate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      payload,
    }: {
      projectId: string;
      payload: ProjectUpdateCreatePayload;
    }) => createProjectUpdate(projectId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...PROJECTS_QUERY_KEY, 'detail', variables.projectId],
      });
    },
  });
}

export function useDeleteProjectUpdate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      updateId,
    }: {
      projectId: string;
      updateId: string;
    }) => deleteProjectUpdate(projectId, updateId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: [...PROJECTS_QUERY_KEY, 'detail', variables.projectId],
      });
    },
  });
}
