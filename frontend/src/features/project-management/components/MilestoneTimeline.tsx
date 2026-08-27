import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircle2,
  Clock,
  Calendar,
  Plus,
  Edit2,
  Trash2,
  ListOrdered,
} from 'lucide-react';
import type { MilestoneStatus, ProjectMilestone } from '../../../types/project';
import { Button } from '../../../components/ui/button';

interface MilestoneTimelineProps {
  milestones: ProjectMilestone[];
  onAddMilestone?: () => void;
  onEditMilestone?: (milestone: ProjectMilestone) => void;
  onDeleteMilestone?: (milestone: ProjectMilestone) => void;
  canManage?: boolean;
}

interface ColumnConfig {
  status: MilestoneStatus;
  labelKey: string;
  defaultLabel: string;
  badgeClass: string;
  icon: React.FC<{ className?: string }>;
}

const COLUMNS: ColumnConfig[] = [
  {
    status: 'DONE',
    labelKey: 'projects.milestones.done',
    defaultLabel: 'Feito',
    badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
    icon: CheckCircle2,
  },
  {
    status: 'IN_PROGRESS',
    labelKey: 'projects.milestones.inProgress',
    defaultLabel: 'Em Andamento',
    badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-800',
    icon: Clock,
  },
  {
    status: 'NEXT_STEPS',
    labelKey: 'projects.milestones.nextSteps',
    defaultLabel: 'Próximos Passos',
    badgeClass: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700',
    icon: Calendar,
  },
];

export const MilestoneTimeline: React.FC<MilestoneTimelineProps> = ({
  milestones,
  onAddMilestone,
  onEditMilestone,
  onDeleteMilestone,
  canManage = false,
}) => {
  const { t } = useTranslation();

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ListOrdered className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">
            {t('projects.milestones.title', 'Marcos e Etapas da Obra')}
          </h3>
        </div>
        {canManage && onAddMilestone && (
          <Button
            size="sm"
            onClick={onAddMilestone}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <Plus className="w-4 h-4" />
            {t('projects.milestones.add', 'Novo Marco')}
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {COLUMNS.map(({ status, labelKey, defaultLabel, badgeClass, icon: Icon }) => {
          const columnMilestones = milestones
            .filter((m) => m.status === status)
            .sort((a, b) => (a.display_order || 0) - (b.display_order || 0));

          return (
            <div
              key={status}
              className="bg-slate-50 dark:bg-slate-800/40 rounded-lg p-3.5 border border-slate-200/80 dark:border-slate-800 flex flex-col space-y-3"
            >
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2">
                <div className="flex items-center gap-1.5">
                  <Icon className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                    {t(labelKey, defaultLabel)}
                  </span>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium border ${badgeClass}`}
                >
                  {columnMilestones.length}
                </span>
              </div>

              {columnMilestones.length === 0 ? (
                <div className="text-xs text-slate-400 dark:text-slate-500 italic py-4 text-center">
                  {t(
                    'projects.milestones.empty',
                    'Nenhum marco cadastrado nesta etapa.'
                  )}
                </div>
              ) : (
                <div className="space-y-2.5">
                  {columnMilestones.map((m) => (
                    <div
                      key={m.id}
                      data-testid={`milestone-card-${m.id}`}
                      className="bg-white dark:bg-slate-900 rounded-lg p-3 border border-slate-200 dark:border-slate-800 shadow-xs space-y-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2">
                          {m.title}
                        </h4>
                        {canManage && (
                          <div className="flex items-center gap-1 shrink-0">
                            {onEditMilestone && (
                              <button
                                aria-label="edit-milestone"
                                onClick={() => onEditMilestone(m)}
                                className="p-1 text-slate-400 hover:text-indigo-600 transition-colors"
                              >
                                <Edit2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                            {onDeleteMilestone && (
                              <button
                                aria-label="delete-milestone"
                                onClick={() => onDeleteMilestone(m)}
                                className="p-1 text-slate-400 hover:text-red-600 transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        )}
                      </div>

                      {m.description && (
                        <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-3">
                          {m.description}
                        </p>
                      )}

                      <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 pt-1 border-t border-slate-100 dark:border-slate-800">
                        {status === 'DONE' && m.completion_date && (
                          <span>
                            {t('projects.milestones.completedOn', 'Concluído em')}:{' '}
                            <strong className="font-medium text-slate-700 dark:text-slate-300">
                              {new Date(m.completion_date).toLocaleDateString()}
                            </strong>
                          </span>
                        )}
                        {status !== 'DONE' && m.due_date && (
                          <span>
                            {t('projects.milestones.dueOn', 'Previsão')}:{' '}
                            <strong className="font-medium text-slate-700 dark:text-slate-300">
                              {new Date(m.due_date).toLocaleDateString()}
                            </strong>
                          </span>
                        )}
                        {!m.due_date && !m.completion_date && (
                          <span className="text-slate-400">
                            {t('projects.card.notSpecified', 'Data não informada')}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
