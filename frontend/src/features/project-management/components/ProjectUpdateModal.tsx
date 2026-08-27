import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import type { ProjectUpdateCreatePayload } from '../../../types/project';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';

interface ProjectUpdateModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: ProjectUpdateCreatePayload) => Promise<void>;
}

export const ProjectUpdateModal: React.FC<ProjectUpdateModalProps> = ({
  open,
  onClose,
  onSubmit,
}) => {
  const { t } = useTranslation();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [costImpact, setCostImpact] = useState<number | ''>(0);
  const [photosText, setPhotosText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;

    const photos = photosText
      .split('\n')
      .map((url) => url.trim())
      .filter((url) => url.length > 0);

    setIsSubmitting(true);
    try {
      await onSubmit({
        title: title.trim(),
        content: content.trim(),
        cost_impact: typeof costImpact === 'number' ? costImpact : 0,
        photos,
      });
      setTitle('');
      setContent('');
      setCostImpact(0);
      setPhotosText('');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            {t('projects.modals.updateCreateTitle', 'Publicar Atualização da Obra')}
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
            <Label htmlFor="update-title">
              {t('projects.modals.updateTitleLabel', 'Título da Atualização')} *
            </Label>
            <Input
              id="update-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t(
                'projects.modals.updateTitlePlaceholder',
                'Ex: Início da concretagem'
              )}
              required
            />
          </div>

          <div>
            <Label htmlFor="update-content">
              {t('projects.modals.updateContentLabel', 'Relato das Atividades')} *
            </Label>
            <Textarea
              id="update-content"
              rows={4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={t(
                'projects.modals.updateContentPlaceholder',
                'Descreva as atividades realizadas...'
              )}
              required
            />
          </div>

          <div>
            <Label htmlFor="update-cost">
              {t(
                'projects.modals.updateCostImpactLabel',
                'Impacto Financeiro Adicional (R$ - opcional)'
              )}
            </Label>
            <Input
              id="update-cost"
              type="number"
              min="0"
              step="0.01"
              value={costImpact}
              onChange={(e) =>
                setCostImpact(e.target.value === '' ? '' : Number(e.target.value))
              }
            />
          </div>

          <div>
            <Label htmlFor="update-photos">
              {t(
                'projects.modals.updatePhotosLabel',
                'URLs das Fotos (uma por linha)'
              )}
            </Label>
            <Textarea
              id="update-photos"
              rows={3}
              value={photosText}
              onChange={(e) => setPhotosText(e.target.value)}
              placeholder="https://exemplo.com/foto1.jpg&#10;https://exemplo.com/foto2.jpg"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {t('projects.modals.saveUpdate', 'Publicar Atualização')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
