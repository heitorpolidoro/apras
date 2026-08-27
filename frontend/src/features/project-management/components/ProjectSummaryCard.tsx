import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Building2,
  Calendar,
  ChevronRight,
  Edit2,
  HardHat,
  Trash2,
} from 'lucide-react';
import type { ConstructionProject, ProjectStatus } from '../../../types/project';
import { Button } from '../../../components/ui/button';
import { formatCurrency } from '../utils/currency';

interface ProjectSummaryCardProps {
  project: ConstructionProject;
  onSelect: (project: ConstructionProject) => void;
  onEdit?: (project: ConstructionProject) => void;
  onDelete?: (project: ConstructionProject) => void;
  canManage?: boolean;
}

const STATUS_BADGES: Record<
  ProjectStatus,
  { labelKey: string; defaultLabel: string; badgeClass: string }
> = {
  PLANNED: {
    labelKey: 'projects.status.PLANNED',
    defaultLabel: 'Planejada',
    badgeClass: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700',
  },
  IN_PROGRESS: {
    labelKey: 'projects.status.IN_PROGRESS',
    defaultLabel: 'Em Andamento',
    badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-800',
  },
  PAUSED: {
    labelKey: 'projects.status.PAUSED',
    defaultLabel: 'Pausada',
    badgeClass: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-800',
  },
  COMPLETED: {
    labelKey: 'projects.status.COMPLETED',
    defaultLabel: 'Concluída',
    badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
  },
};

export const ProjectSummaryCard: React.FC<ProjectSummaryCardProps> = ({
  project,
  onSelect,
  onEdit,
  onDelete,
  canManage = false,
}) => {
  const { t } = useTranslation();

  const statusConfig = STATUS_BADGES[project.status] || STATUS_BADGES.PLANNED;
  const budgetPercentage =
    project.total_budget > 0
      ? Math.min(
          Math.round((project.executed_budget / project.total_budget) * 100),
          100
        )
      : 0;

  return (
    <div
      data-testid={`project-card-${project.id}`}
      className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
    >
      {/* Cover Image & Status Header */}
      <div className="relative aspect-video w-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center overflow-hidden">
        {project.cover_photo_url ? (
          <img
            src={project.cover_photo_url}
            alt={project.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-slate-400">
            <Building2 className="w-10 h-10 mb-1 opacity-50" />
            <span className="text-xs">Sem foto de capa</span>
          </div>
        )}

        <div className="absolute top-3 left-3">
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-semibold border backdrop-blur-xs ${statusConfig.badgeClass}`}
          >
            {t(statusConfig.labelKey, statusConfig.defaultLabel)}
          </span>
        </div>

        {canManage && (
          <div className="absolute top-3 right-3 flex items-center gap-1 bg-black/50 backdrop-blur-xs rounded-lg p-1">
            {onEdit && (
              <button
                aria-label="edit-project"
                onClick={() => onEdit(project)}
                className="p-1 text-white hover:text-indigo-300 transition-colors"
              >
                <Edit2 className="w-4 h-4" />
              </button>
            )}
            {onDelete && (
              <button
                aria-label="delete-project"
                onClick={() => onDelete(project)}
                className="p-1 text-white hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
        <div className="space-y-2">
          <h3 className="font-bold text-lg text-slate-900 dark:text-slate-100 line-clamp-1">
            {project.title}
          </h3>

          {project.contractor_name && (
            <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
              <HardHat className="w-3.5 h-3.5 text-slate-500" />
              <span>
                {t('projects.card.contractor', 'Empreiteira')}:{' '}
                <strong className="font-medium text-slate-800 dark:text-slate-200">
                  {project.contractor_name}
                </strong>
              </span>
            </div>
          )}

          {project.description && (
            <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
              {project.description}
            </p>
          )}
        </div>

        {/* Progress & Financial Bars */}
        <div className="space-y-2.5 pt-2 border-t border-slate-100 dark:border-slate-800">
          {/* Physical Progress */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-500 dark:text-slate-400">
                {t('projects.card.physicalProgress', 'Progresso Físico')}
              </span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {project.physical_progress_pct}%
              </span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-indigo-600 h-full transition-all duration-300"
                style={{ width: `${Math.min(project.physical_progress_pct, 100)}%` }}
              />
            </div>
          </div>

          {/* Financial Execution */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-500 dark:text-slate-400">
                {t('projects.card.budgetExecution', 'Orçamento Executado')}
              </span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {formatCurrency(project.executed_budget)} / {formatCurrency(project.total_budget)}
              </span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  project.executed_budget > project.total_budget
                    ? 'bg-red-500'
                    : 'bg-emerald-500'
                }`}
                style={{ width: `${budgetPercentage}%` }}
              />
            </div>
          </div>

          {/* Dates */}
          {(project.start_date || project.estimated_completion_date) && (
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 pt-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>
                {project.start_date
                  ? new Date(project.start_date).toLocaleDateString()
                  : '-'}
                {' → '}
                {project.estimated_completion_date
                  ? new Date(project.estimated_completion_date).toLocaleDateString()
                  : '-'}
              </span>
            </div>
          )}
        </div>

        {/* View Details Button */}
        <div className="pt-2">
          <Button
            variant="outline"
            onClick={() => onSelect(project)}
            className="w-full flex items-center justify-center gap-1.5 text-xs font-semibold"
          >
            <span>{t('projects.card.viewDetails', 'Ver Detalhes')}</span>
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};
