import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import type {
  ConstructionProject,
  ProjectCreatePayload,
  ProjectStatus,
  ProjectUpdatePayload,
} from '../../../types/project';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select } from '../../../components/ui/select';

interface ProjectFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: ProjectCreatePayload | ProjectUpdatePayload) => Promise<void>;
  project?: ConstructionProject | null;
}

interface ProjectFormInnerProps {
  onClose: () => void;
  onSubmit: (payload: ProjectCreatePayload | ProjectUpdatePayload) => Promise<void>;
  project?: ConstructionProject | null;
}

const ProjectFormInner: React.FC<ProjectFormInnerProps> = ({
  onClose,
  onSubmit,
  project,
}) => {
  const { t } = useTranslation();
  const [title, setTitle] = useState(project?.title || '');
  const [description, setDescription] = useState(project?.description || '');
  const [contractorName, setContractorName] = useState(
    project?.contractor_name || ''
  );
  const [totalBudget, setTotalBudget] = useState<number | ''>(
    project?.total_budget ?? 0
  );
  const [executedBudget, setExecutedBudget] = useState<number | ''>(
    project?.executed_budget ?? 0
  );
  const [physicalProgressPct, setPhysicalProgressPct] = useState<number | ''>(
    project?.physical_progress_pct ?? 0
  );
  const [startDate, setStartDate] = useState(
    project?.start_date ? project.start_date.split('T')[0] : ''
  );
  const [estCompletionDate, setEstCompletionDate] = useState(
    project?.estimated_completion_date
      ? project.estimated_completion_date.split('T')[0]
      : ''
  );
  const [actCompletionDate, setActCompletionDate] = useState(
    project?.actual_completion_date
      ? project.actual_completion_date.split('T')[0]
      : ''
  );
  const [status, setStatus] = useState<ProjectStatus>(
    project?.status || 'PLANNED'
  );
  const [coverPhotoUrl, setCoverPhotoUrl] = useState(
    project?.cover_photo_url || ''
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim() || null,
        contractor_name: contractorName.trim() || null,
        total_budget: typeof totalBudget === 'number' ? totalBudget : 0,
        executed_budget: typeof executedBudget === 'number' ? executedBudget : 0,
        physical_progress_pct:
          typeof physicalProgressPct === 'number' ? physicalProgressPct : 0,
        start_date: startDate || null,
        estimated_completion_date: estCompletionDate || null,
        actual_completion_date: actCompletionDate || null,
        status,
        cover_photo_url: coverPhotoUrl.trim() || null,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 my-8 overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
          {project
            ? t('projects.modals.projectEditTitle', 'Editar Obra')
            : t('projects.modals.projectCreateTitle', 'Cadastrar Nova Obra')}
        </h3>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
        <div>
          <Label htmlFor="project-title">
            {t('projects.modals.projectTitleLabel', 'Título da Obra')} *
          </Label>
          <Input
            id="project-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t(
              'projects.modals.projectTitlePlaceholder',
              'Ex: Reforma da Piscina Principal'
            )}
            required
          />
        </div>

        <div>
          <Label htmlFor="project-contractor">
            {t(
              'projects.modals.contractorLabel',
              'Nome da Empreiteira / Responsável'
            )}
          </Label>
          <Input
            id="project-contractor"
            value={contractorName}
            onChange={(e) => setContractorName(e.target.value)}
            placeholder="Ex: Construtora Alfa"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <Label htmlFor="total-budget">
              {t('projects.modals.totalBudgetLabel', 'Orçamento Previsto (R$)')}
            </Label>
            <Input
              id="total-budget"
              type="number"
              min="0"
              step="0.01"
              value={totalBudget}
              onChange={(e) =>
                setTotalBudget(
                  e.target.value === '' ? '' : Number(e.target.value)
                )
              }
            />
          </div>

          <div>
            <Label htmlFor="executed-budget">
              {t(
                'projects.modals.executedBudgetLabel',
                'Orçamento Executado (R$)'
              )}
            </Label>
            <Input
              id="executed-budget"
              type="number"
              min="0"
              step="0.01"
              value={executedBudget}
              onChange={(e) =>
                setExecutedBudget(
                  e.target.value === '' ? '' : Number(e.target.value)
                )
              }
            />
          </div>

          <div>
            <Label htmlFor="progress-pct">
              {t('projects.modals.progressPctLabel', 'Progresso Físico (%)')}
            </Label>
            <Input
              id="progress-pct"
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={physicalProgressPct}
              onChange={(e) =>
                setPhysicalProgressPct(
                  e.target.value === '' ? '' : Number(e.target.value)
                )
              }
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <Label htmlFor="start-date">
              {t('projects.modals.startDateLabel', 'Data de Início')}
            </Label>
            <Input
              id="start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div>
            <Label htmlFor="est-comp-date">
              {t(
                'projects.modals.estCompletionDateLabel',
                'Previsão de Término'
              )}
            </Label>
            <Input
              id="est-comp-date"
              type="date"
              value={estCompletionDate}
              onChange={(e) => setEstCompletionDate(e.target.value)}
            />
          </div>

          <div>
            <Label htmlFor="act-comp-date">
              {t(
                'projects.modals.actCompletionDateLabel',
                'Conclusão Efetiva'
              )}
            </Label>
            <Input
              id="act-comp-date"
              type="date"
              value={actCompletionDate}
              onChange={(e) => setActCompletionDate(e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <Label htmlFor="project-status">
              {t('projects.modals.statusLabel', 'Status Atual')}
            </Label>
            <Select
              id="project-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as ProjectStatus)}
            >
              <option value="PLANNED">
                {t('projects.status.PLANNED', 'Planejada')}
              </option>
              <option value="IN_PROGRESS">
                {t('projects.status.IN_PROGRESS', 'Em Andamento')}
              </option>
              <option value="PAUSED">
                {t('projects.status.PAUSED', 'Pausada')}
              </option>
              <option value="COMPLETED">
                {t('projects.status.COMPLETED', 'Concluída')}
              </option>
            </Select>
          </div>

          <div>
            <Label htmlFor="cover-photo">
              {t('projects.modals.coverPhotoLabel', 'URL da Foto de Capa')}
            </Label>
            <Input
              id="cover-photo"
              value={coverPhotoUrl}
              onChange={(e) => setCoverPhotoUrl(e.target.value)}
              placeholder="https://exemplo.com/foto.jpg"
            />
          </div>
        </div>

        <div>
          <Label htmlFor="project-desc">
            {t('projects.modals.descriptionLabel', 'Descrição')}
          </Label>
          <Textarea
            id="project-desc"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t(
              'projects.modals.descriptionPlaceholder',
              'Detalhes sobre o escopo...'
            )}
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {project
              ? t('projects.modals.saveProject', 'Salvar Obra')
              : t('projects.modals.saveProject', 'Cadastrar Obra')}
          </Button>
        </div>
      </form>
    </div>
  );
};

export const ProjectFormModal: React.FC<ProjectFormModalProps> = ({
  open,
  onClose,
  onSubmit,
  project,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
      <ProjectFormInner
        key={project?.id || 'new'}
        onClose={onClose}
        onSubmit={onSubmit}
        project={project}
      />
    </div>
  );
};
