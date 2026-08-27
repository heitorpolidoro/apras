import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import type {
  MilestoneCreatePayload,
  MilestoneStatus,
  MilestoneUpdatePayload,
  ProjectMilestone,
} from '../../../types/project';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select } from '../../../components/ui/select';

interface MilestoneFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: MilestoneCreatePayload | MilestoneUpdatePayload) => Promise<void>;
  milestone?: ProjectMilestone | null;
}

interface MilestoneFormInnerProps {
  onClose: () => void;
  onSubmit: (payload: MilestoneCreatePayload | MilestoneUpdatePayload) => Promise<void>;
  milestone?: ProjectMilestone | null;
}

const MilestoneFormInner: React.FC<MilestoneFormInnerProps> = ({
  onClose,
  onSubmit,
  milestone,
}) => {
  const { t } = useTranslation();
  const [title, setTitle] = useState(milestone?.title || '');
  const [description, setDescription] = useState(milestone?.description || '');
  const [status, setStatus] = useState<MilestoneStatus>(
    milestone?.status || 'NEXT_STEPS'
  );
  const [dueDate, setDueDate] = useState(
    milestone?.due_date ? milestone.due_date.split('T')[0] : ''
  );
  const [completionDate, setCompletionDate] = useState(
    milestone?.completion_date ? milestone.completion_date.split('T')[0] : ''
  );
  const [displayOrder, setDisplayOrder] = useState<number | ''>(
    milestone?.display_order ?? 0
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
        status,
        due_date: dueDate || null,
        completion_date: completionDate || null,
        display_order: typeof displayOrder === 'number' ? displayOrder : 0,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
          {milestone
            ? t('projects.modals.milestoneEditTitle', 'Editar Marco')
            : t('projects.modals.milestoneCreateTitle', 'Novo Marco da Obra')}
        </h3>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-4">
        <div>
          <Label htmlFor="milestone-title">
            {t('projects.modals.milestoneTitleLabel', 'Título do Marco')} *
          </Label>
          <Input
            id="milestone-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t(
              'projects.modals.milestoneTitlePlaceholder',
              'Ex: Fundação'
            )}
            required
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <Label htmlFor="milestone-status">
              {t('projects.modals.statusLabel', 'Status')}
            </Label>
            <Select
              id="milestone-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as MilestoneStatus)}
            >
              <option value="NEXT_STEPS">
                {t('projects.milestoneStatus.NEXT_STEPS', 'Próximos Passos')}
              </option>
              <option value="IN_PROGRESS">
                {t('projects.milestoneStatus.IN_PROGRESS', 'Em Andamento')}
              </option>
              <option value="DONE">
                {t('projects.milestoneStatus.DONE', 'Feito')}
              </option>
            </Select>
          </div>

          <div>
            <Label htmlFor="milestone-order">
              {t('projects.modals.milestoneOrderLabel', 'Ordem de Exibição')}
            </Label>
            <Input
              id="milestone-order"
              type="number"
              value={displayOrder}
              onChange={(e) =>
                setDisplayOrder(
                  e.target.value === '' ? '' : Number(e.target.value)
                )
              }
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <Label htmlFor="milestone-due-date">
              {t('projects.modals.milestoneDueDateLabel', 'Data Prevista')}
            </Label>
            <Input
              id="milestone-due-date"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>

          <div>
            <Label htmlFor="milestone-comp-date">
              {t('projects.modals.milestoneCompDateLabel', 'Data de Conclusão')}
            </Label>
            <Input
              id="milestone-comp-date"
              type="date"
              value={completionDate}
              onChange={(e) => setCompletionDate(e.target.value)}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="milestone-desc">
            {t('projects.modals.milestoneDescLabel', 'Descrição')}
          </Label>
          <Textarea
            id="milestone-desc"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Detalhes ou requisitos da etapa..."
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
            {t('projects.modals.saveMilestone', 'Salvar Marco')}
          </Button>
        </div>
      </form>
    </div>
  );
};

export const MilestoneFormModal: React.FC<MilestoneFormModalProps> = ({
  open,
  onClose,
  onSubmit,
  milestone,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <MilestoneFormInner
        key={milestone?.id || 'new'}
        onClose={onClose}
        onSubmit={onSubmit}
        milestone={milestone}
      />
    </div>
  );
};
