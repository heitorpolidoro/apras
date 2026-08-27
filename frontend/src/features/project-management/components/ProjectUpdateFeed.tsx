import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Camera,
  MessageSquare,
  Plus,
  Trash2,
  DollarSign,
  User as UserIcon,
  X,
} from 'lucide-react';
import type { ProjectUpdate } from '../../../types/project';
import { Badge } from '../../../components/ui/badge';
import { Button } from '../../../components/ui/button';
import { formatCurrency } from '../utils/currency';

interface ProjectUpdateFeedProps {
  updates: ProjectUpdate[];
  onAddUpdate?: () => void;
  onDeleteUpdate?: (update: ProjectUpdate) => void;
  canPostUpdate?: boolean;
  canDeleteUpdate?: boolean;
}

export const ProjectUpdateFeed: React.FC<ProjectUpdateFeedProps> = ({
  updates,
  onAddUpdate,
  onDeleteUpdate,
  canPostUpdate = false,
  canDeleteUpdate = false,
}) => {
  const { t } = useTranslation();
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Camera className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">
            {t('projects.updates.title', 'Diário de Bordo e Fotos da Obra')}
          </h3>
        </div>
        {canPostUpdate && onAddUpdate && (
          <Button
            size="sm"
            onClick={onAddUpdate}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <Plus className="w-4 h-4" />
            {t('projects.updates.add', 'Publicar Atualização')}
          </Button>
        )}
      </div>

      {updates.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-8 text-center bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-800">
          <MessageSquare className="w-8 h-8 text-slate-400 mb-2" />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
            {t('projects.updates.empty', 'Nenhuma atualização registrada ainda.')}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {updates.map((update) => (
            <div
              key={update.id}
              data-testid={`update-card-${update.id}`}
              className="bg-slate-50 dark:bg-slate-800/40 rounded-xl p-4 border border-slate-200 dark:border-slate-800 space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                    {update.title}
                  </h4>
                  <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    <span className="flex items-center gap-1">
                      <UserIcon className="w-3.5 h-3.5" />
                      {update.author?.full_name || update.author?.email || 'Autor desconhecido'}
                    </span>
                    <span>•</span>
                    <span>
                      {new Date(update.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {update.cost_impact && update.cost_impact > 0 ? (
                    <Badge variant="warning" className="flex items-center gap-1">
                      <DollarSign className="w-3 h-3" />
                      {t('projects.updates.costImpact', 'Impacto')}: {formatCurrency(update.cost_impact)}
                    </Badge>
                  ) : null}

                  {canDeleteUpdate && onDeleteUpdate && (
                    <button
                      aria-label="delete-update"
                      onClick={() => onDeleteUpdate(update)}
                      className="p-1.5 text-slate-400 hover:text-red-600 transition-colors rounded-md"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">
                {update.content}
              </p>

              {/* Photo thumbnails gallery */}
              {update.photos && update.photos.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 pt-2">
                  {update.photos.map((photoUrl, idx) => (
                    <div
                      key={idx}
                      onClick={() => setSelectedPhoto(photoUrl)}
                      className="group relative aspect-video bg-slate-200 dark:bg-slate-800 rounded-lg overflow-hidden border border-slate-300 dark:border-slate-700 cursor-pointer"
                    >
                      <img
                        src={photoUrl}
                        alt={`Photo ${idx + 1}`}
                        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Photo Lightbox Modal */}
      {selectedPhoto && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="relative max-w-4xl max-h-[90vh] bg-slate-900 rounded-xl overflow-hidden shadow-2xl">
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute top-3 right-3 p-2 bg-black/60 hover:bg-black text-white rounded-full transition-colors z-10"
            >
              <X className="w-5 h-5" />
            </button>
            <img
              src={selectedPhoto}
              alt="Enlarged site log"
              className="w-auto h-auto max-h-[85vh] max-w-full object-contain"
            />
          </div>
        </div>
      )}
    </div>
  );
};
