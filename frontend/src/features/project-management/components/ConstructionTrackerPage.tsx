import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft,
  Building2,
  HardHat,
  Plus,
  RefreshCw,
} from 'lucide-react';
import { useEffectiveIdentity } from '../../user-administration/context/useEffectiveIdentity';
import type {
  ConstructionProject,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  ProjectCreatePayload,
  ProjectMilestone,
  ProjectStatus,
  ProjectUpdate,
  ProjectUpdateCreatePayload,
  ProjectUpdatePayload,
} from '../../../types/project';
import {
  useCreateMilestone,
  useCreateProject,
  useCreateProjectUpdate,
  useDeleteMilestone,
  useDeleteProject,
  useDeleteProjectUpdate,
  useProjectDetail,
  useProjects,
  useUpdateMilestone,
  useUpdateProject,
} from '../hooks/useProjects';
import { ProjectSummaryCard } from './ProjectSummaryCard';
import { BudgetVsActualProgressBar } from './BudgetVsActualProgressBar';
import { MilestoneTimeline } from './MilestoneTimeline';
import { ProjectUpdateFeed } from './ProjectUpdateFeed';
import { ProjectFormModal } from './ProjectFormModal';
import { MilestoneFormModal } from './MilestoneFormModal';
import { ProjectUpdateModal } from './ProjectUpdateModal';
import { Button } from '../../../components/ui/button';
import { AlertModal } from '../../../components/ui/alert-modal';

type FilterStatus = 'ALL' | ProjectStatus;

export const ConstructionTrackerPage: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();
  const canManage = role === 'ADMINISTRATOR' || role === 'DIRECTOR';
  const canPostUpdate =
    role === 'ADMINISTRATOR' || role === 'DIRECTOR' || role === 'MANAGER';

  // Filters & Selected State
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('ALL');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  // Modal States
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<ConstructionProject | null>(null);

  const [milestoneModalOpen, setMilestoneModalOpen] = useState(false);
  const [editingMilestone, setEditingMilestone] = useState<ProjectMilestone | null>(null);

  const [updateModalOpen, setUpdateModalOpen] = useState(false);

  // Alert / Deletion Confirmation States
  const [deleteConfirmProject, setDeleteConfirmProject] = useState<ConstructionProject | null>(null);
  const [deleteConfirmMilestone, setDeleteConfirmMilestone] = useState<ProjectMilestone | null>(null);
  const [deleteConfirmUpdate, setDeleteConfirmUpdate] = useState<ProjectUpdate | null>(null);

  // Queries
  const {
    data: projectsData,
    isLoading: isLoadingProjects,
    refetch: refetchProjects,
  } = useProjects({
    status: statusFilter === 'ALL' ? undefined : statusFilter,
  });

  const {
    data: selectedProjectDetail,
    isLoading: isLoadingDetail,
  } = useProjectDetail(selectedProjectId);

  // Mutations
  const createProjectMutation = useCreateProject();
  const updateProjectMutation = useUpdateProject();
  const deleteProjectMutation = useDeleteProject();

  const createMilestoneMutation = useCreateMilestone();
  const updateMilestoneMutation = useUpdateMilestone();
  const deleteMilestoneMutation = useDeleteMilestone();

  const createUpdateMutation = useCreateProjectUpdate();
  const deleteUpdateMutation = useDeleteProjectUpdate();

  // Handlers: Project
  const handleSaveProject = async (
    payload: ProjectCreatePayload | ProjectUpdatePayload
  ) => {
    if (editingProject) {
      await updateProjectMutation.mutateAsync({
        id: editingProject.id,
        payload,
      });
    } else {
      await createProjectMutation.mutateAsync(payload as ProjectCreatePayload);
    }
  };

  const handleConfirmDeleteProject = async () => {
    if (!deleteConfirmProject) return;
    await deleteProjectMutation.mutateAsync(deleteConfirmProject.id);
    if (selectedProjectId === deleteConfirmProject.id) {
      setSelectedProjectId(null);
    }
    setDeleteConfirmProject(null);
  };

  // Handlers: Milestone
  const handleSaveMilestone = async (
    payload: MilestoneCreatePayload | MilestoneUpdatePayload
  ) => {
    if (!selectedProjectId) return;
    if (editingMilestone) {
      await updateMilestoneMutation.mutateAsync({
        projectId: selectedProjectId,
        milestoneId: editingMilestone.id,
        payload,
      });
    } else {
      await createMilestoneMutation.mutateAsync({
        projectId: selectedProjectId,
        payload: payload as MilestoneCreatePayload,
      });
    }
  };

  const handleConfirmDeleteMilestone = async () => {
    if (!deleteConfirmMilestone || !selectedProjectId) return;
    await deleteMilestoneMutation.mutateAsync({
      projectId: selectedProjectId,
      milestoneId: deleteConfirmMilestone.id,
    });
    setDeleteConfirmMilestone(null);
  };

  // Handlers: Project Update
  const handleSaveUpdate = async (payload: ProjectUpdateCreatePayload) => {
    if (!selectedProjectId) return;
    await createUpdateMutation.mutateAsync({
      projectId: selectedProjectId,
      payload,
    });
  };

  const handleConfirmDeleteUpdate = async () => {
    if (!deleteConfirmUpdate || !selectedProjectId) return;
    await deleteUpdateMutation.mutateAsync({
      projectId: selectedProjectId,
      updateId: deleteConfirmUpdate.id,
    });
    setDeleteConfirmUpdate(null);
  };

  const projects = projectsData?.items || [];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
        <div>
          <div className="flex items-center gap-2.5">
            <HardHat className="w-7 h-7 text-indigo-600 dark:text-indigo-400" />
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {t('projects.pageTitle', 'Acompanhamento de Obras')}
            </h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t(
              'projects.pageSubtitle',
              'Acompanhe o andamento físico, metas e execução financeira das reformas e melhorias do condomínio.'
            )}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchProjects()}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="hidden sm:inline">Atualizar</span>
          </Button>

          {canManage && (
            <Button
              onClick={() => {
                setEditingProject(null);
                setProjectModalOpen(true);
              }}
              className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              <Plus className="w-4 h-4" />
              <span>{t('projects.newProject', 'Nova Obra')}</span>
            </Button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {selectedProjectId ? (
        isLoadingDetail || !selectedProjectDetail ? (
          <div className="flex items-center justify-center p-12">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
          </div>
        ) : (
        /* Detailed Project View */
        <div className="space-y-6">
          {/* Detail Top Navigation Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedProjectId(null)}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Voltar para Lista de Obras</span>
            </Button>

            <div className="flex items-center gap-2">
              {canManage && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEditingProject(selectedProjectDetail);
                      setProjectModalOpen(true);
                    }}
                  >
                    Editar Obra
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDeleteConfirmProject(selectedProjectDetail)}
                    className="text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-950"
                  >
                    Excluir
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Project Overview Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div className="space-y-2">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {selectedProjectDetail.title}
                </h2>
                {selectedProjectDetail.contractor_name && (
                  <div className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400">
                    <HardHat className="w-4 h-4 text-slate-500" />
                    <span>
                      {t('projects.card.contractor', 'Empreiteira')}:{' '}
                      <strong className="font-semibold text-slate-900 dark:text-slate-100">
                        {selectedProjectDetail.contractor_name}
                      </strong>
                    </span>
                  </div>
                )}
                {selectedProjectDetail.description && (
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed max-w-3xl">
                    {selectedProjectDetail.description}
                  </p>
                )}
              </div>

              {/* Physical Gauge */}
              <div className="bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-100 dark:border-indigo-900 rounded-xl p-4 flex flex-col items-center justify-center min-w-[160px] text-center">
                <div className="text-xs text-indigo-700 dark:text-indigo-300 font-semibold mb-1">
                  {t('projects.card.physicalProgress', 'Progresso Físico')}
                </div>
                <div className="text-3xl font-extrabold text-indigo-900 dark:text-indigo-100">
                  {selectedProjectDetail.physical_progress_pct}%
                </div>
                <div className="w-full bg-indigo-200 dark:bg-indigo-800 rounded-full h-1.5 mt-2 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-full transition-all duration-300"
                    style={{
                      width: `${Math.min(
                        selectedProjectDetail.physical_progress_pct,
                        100
                      )}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Financial Bar */}
          <BudgetVsActualProgressBar
            totalBudget={selectedProjectDetail.total_budget}
            executedBudget={selectedProjectDetail.executed_budget}
          />

          {/* Milestones Workflow Board */}
          <MilestoneTimeline
            milestones={selectedProjectDetail.milestones || []}
            canManage={canManage}
            onAddMilestone={() => {
              setEditingMilestone(null);
              setMilestoneModalOpen(true);
            }}
            onEditMilestone={(m) => {
              setEditingMilestone(m);
              setMilestoneModalOpen(true);
            }}
            onDeleteMilestone={(m) => {
              setDeleteConfirmMilestone(m);
            }}
          />

          {/* Updates Feed */}
          <ProjectUpdateFeed
            updates={selectedProjectDetail.updates || []}
            canPostUpdate={canPostUpdate}
            canDeleteUpdate={canManage}
            onAddUpdate={() => setUpdateModalOpen(true)}
            onDeleteUpdate={(u) => setDeleteConfirmUpdate(u)}
          />
        </div>
        )
      ) : (
        /* Projects List / Grid View */
        <div className="space-y-6">
          {/* Status Filter Tabs */}
          <div className="flex flex-wrap gap-2">
            {(
              [
                { key: 'ALL', labelKey: 'projects.allStatuses', defaultLabel: 'Todos os Status' },
                { key: 'IN_PROGRESS', labelKey: 'projects.status.IN_PROGRESS', defaultLabel: 'Em Andamento' },
                { key: 'PLANNED', labelKey: 'projects.status.PLANNED', defaultLabel: 'Planejada' },
                { key: 'PAUSED', labelKey: 'projects.status.PAUSED', defaultLabel: 'Pausada' },
                { key: 'COMPLETED', labelKey: 'projects.status.COMPLETED', defaultLabel: 'Concluída' },
              ] as const
            ).map((filter) => (
              <button
                key={filter.key}
                onClick={() => setStatusFilter(filter.key)}
                className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
                  statusFilter === filter.key
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                {t(filter.labelKey, filter.defaultLabel)}
              </button>
            ))}
          </div>

          {/* Project Grid */}
          {isLoadingProjects ? (
            <div className="flex items-center justify-center p-12">
              <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
            </div>
          ) : projects.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
              <Building2 className="h-12 w-12 text-slate-300 dark:text-slate-600 mb-3" />
              <h4 className="text-base font-semibold text-slate-800 dark:text-slate-200">
                {t('projects.noProjectsFound', 'Nenhuma obra cadastrada')}
              </h4>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
                {t(
                  'projects.noProjectsDescription',
                  'Não há obras correspondentes ao filtro selecionado.'
                )}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((p) => (
                <ProjectSummaryCard
                  key={p.id}
                  project={p}
                  canManage={canManage}
                  onSelect={(proj) => setSelectedProjectId(proj.id)}
                  onEdit={(proj) => {
                    setEditingProject(proj);
                    setProjectModalOpen(true);
                  }}
                  onDelete={(proj) => setDeleteConfirmProject(proj)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <ProjectFormModal
        open={projectModalOpen}
        onClose={() => {
          setProjectModalOpen(false);
          setEditingProject(null);
        }}
        onSubmit={handleSaveProject}
        project={editingProject}
      />

      <MilestoneFormModal
        open={milestoneModalOpen}
        onClose={() => {
          setMilestoneModalOpen(false);
          setEditingMilestone(null);
        }}
        onSubmit={handleSaveMilestone}
        milestone={editingMilestone}
      />

      <ProjectUpdateModal
        open={updateModalOpen}
        onClose={() => setUpdateModalOpen(false)}
        onSubmit={handleSaveUpdate}
      />

      {/* Delete Confirmation Alerts */}
      <AlertModal
        open={Boolean(deleteConfirmProject)}
        onClose={() => setDeleteConfirmProject(null)}
        title={t('projects.card.delete', 'Excluir Obra')}
        message={
          <div>
            <p>
              {t(
                'projects.card.confirmDelete',
                'Tem certeza que deseja excluir esta obra e todos os seus marcos e atualizações?'
              )}
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setDeleteConfirmProject(null)}>
                Cancelar
              </Button>
              <Button variant="destructive" size="sm" onClick={handleConfirmDeleteProject}>
                Excluir Obra
              </Button>
            </div>
          </div>
        }
        variant="destructive"
      />

      <AlertModal
        open={Boolean(deleteConfirmMilestone)}
        onClose={() => setDeleteConfirmMilestone(null)}
        title={t('projects.milestones.delete', 'Excluir Marco')}
        message={
          <div>
            <p>
              {t(
                'projects.milestones.confirmDelete',
                'Tem certeza que deseja excluir este marco?'
              )}
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setDeleteConfirmMilestone(null)}>
                Cancelar
              </Button>
              <Button variant="destructive" size="sm" onClick={handleConfirmDeleteMilestone}>
                Excluir Marco
              </Button>
            </div>
          </div>
        }
        variant="destructive"
      />

      <AlertModal
        open={Boolean(deleteConfirmUpdate)}
        onClose={() => setDeleteConfirmUpdate(null)}
        title={t('projects.updates.delete', 'Excluir Atualização')}
        message={
          <div>
            <p>
              {t(
                'projects.updates.confirmDelete',
                'Tem certeza que deseja excluir esta publicação?'
              )}
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setDeleteConfirmUpdate(null)}>
                Cancelar
              </Button>
              <Button variant="destructive" size="sm" onClick={handleConfirmDeleteUpdate}>
                Excluir
              </Button>
            </div>
          </div>
        }
        variant="destructive"
      />
    </div>
  );
};
