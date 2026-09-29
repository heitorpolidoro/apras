import React, { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { limitDecimals, MONEY_DECIMALS } from '../../../lib/money';
import { AlertTriangle, ImageOff, Trash2, Upload, X } from 'lucide-react';
import {
  UPLOAD_ACCEPT,
  UPLOAD_ALLOWED_MIME_TYPES,
  UPLOAD_MAX_FILE_SIZE_BYTES,
} from '../../../api/uploads';
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

/**
 * What the form asks to happen to the cover photo, alongside the obra's fields.
 *
 * Carried as intent rather than performed here: the upload has to run **after**
 * the obra exists, and a create does not know its own id until the caller's
 * `POST /projects` has answered (APRAS-104 §B).
 */
export interface CoverPhotoIntent {
  /** A file the operator picked, already checked for type and size. */
  file: File | null;
  /** Whether "Remover" was pressed, meaning `DELETE /{id}/cover-photo`. */
  remove: boolean;
}

interface ProjectFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (
    payload: ProjectCreatePayload | ProjectUpdatePayload,
    cover: CoverPhotoIntent
  ) => Promise<void>;
  project?: ConstructionProject | null;
}

interface ProjectFormInnerProps {
  onClose: () => void;
  onSubmit: (
    payload: ProjectCreatePayload | ProjectUpdatePayload,
    cover: CoverPhotoIntent
  ) => Promise<void>;
  project?: ConstructionProject | null;
  /** The cover-photo control's state, held by the **outer** component. */
  cover: CoverControl;
}

/**
 * The cover control's state and its setters, lifted out of the inner form.
 *
 * It lives in `ProjectFormModal` rather than in `ProjectFormInner` because the
 * inner form is keyed by `project?.id`, and §B's create sequence deliberately
 * changes that id mid-save: a successful `POST /projects` makes the caller
 * adopt the new obra and switch the modal to editing it, which remounts the
 * inner form. A picked file and a cover error held *inside* would be discarded
 * at exactly the moment they matter most -- the failed-upload state the
 * operator has to see and retry.
 */
interface CoverControl {
  file: File | null;
  setFile: (file: File | null) => void;
  error: string | null;
  setError: (message: string | null) => void;
  removed: boolean;
  setRemoved: (removed: boolean) => void;
}

/**
 * A preview URL for a picked file, or `null` where the environment has no
 * `createObjectURL` (jsdom does not implement it).
 *
 * The preview is a nicety; a missing one must not throw and take the whole form
 * with it.
 */
const objectUrlFor = (file: File): string | null => {
  try {
    return URL.createObjectURL(file);
  } catch {
    return null;
  }
};

/** The server's own refusal message, when the failure carried one. */
const coverErrorMessage = (error: unknown): string | null => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  return typeof detail === 'string' && detail.trim() ? detail : null;
};

const ProjectFormInner: React.FC<ProjectFormInnerProps> = ({
  onClose,
  onSubmit,
  project,
  cover,
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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /** The URL the preview renders: the picked file, else what the obra has. */
  const previewUrl = cover.file
    ? objectUrlFor(cover.file)
    : cover.removed
      ? null
      : project?.cover_photo_display_url || null;

  /**
   * Type and size, checked in the browser first, against the **same constants**
   * the server enforces (`api/uploads.ts`'s pin on `media_service`). A refused
   * file never reaches the network and never becomes part of the intent.
   */
  const handlePick = (event: React.ChangeEvent<HTMLInputElement>) => {
    const picked = event.target.files?.[0];
    if (!picked) return;
    if (
      !(UPLOAD_ALLOWED_MIME_TYPES as readonly string[]).includes(picked.type)
    ) {
      cover.setFile(null);
      cover.setError(
        t(
          'projects.modals.coverPhotoInvalidFormat',
          'Formato de imagem inválido. Formatos aceitos: JPEG, PNG, WebP.'
        )
      );
      return;
    }
    if (picked.size > UPLOAD_MAX_FILE_SIZE_BYTES) {
      cover.setFile(null);
      cover.setError(
        t(
          'projects.modals.coverPhotoTooLarge',
          'Arquivo excede o limite máximo permitido de 5MB.'
        )
      );
      return;
    }
    cover.setError(null);
    cover.setRemoved(false);
    cover.setFile(picked);
  };

  const handleRemove = () => {
    cover.setError(null);
    cover.setFile(null);
    cover.setRemoved(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsSubmitting(true);
    try {
      // `cover_photo_url` is deliberately **absent**, not `null`: the column is
      // storage truth written only by the cover routes now (APRAS-104 §B), and
      // the service skips `null` values anyway, so sending one would be a key
      // that silently does nothing.
      await onSubmit(
        {
          title: title.trim(),
          description: description.trim() || null,
          contractor_name: contractorName.trim() || null,
          total_budget: typeof totalBudget === 'number' ? totalBudget : 0,
          executed_budget:
            typeof executedBudget === 'number' ? executedBudget : 0,
          physical_progress_pct:
            typeof physicalProgressPct === 'number' ? physicalProgressPct : 0,
          start_date: startDate || null,
          estimated_completion_date: estCompletionDate || null,
          actual_completion_date: actCompletionDate || null,
          status,
        },
        { file: cover.file, remove: cover.removed }
      );
      onClose();
    } catch (error) {
      // The cover step failed after the obra was saved. The modal stays open
      // on that obra reporting it -- never silently swallowed, and never closed,
      // because closing would leave the operator with no sign the photo is
      // missing (§B).
      cover.setError(
        coverErrorMessage(error) ??
          t(
            'projects.modals.coverPhotoUploadFailed',
            'A obra foi salva, mas a foto de capa não foi enviada.'
          )
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative w-full max-w-2xl bg-card rounded-2xl shadow-xl border border-border my-8 overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <h3 className="text-lg font-bold text-foreground">
          {project
            ? t('projects.modals.projectEditTitle', 'Editar Obra')
            : t('projects.modals.projectCreateTitle', 'Cadastrar Nova Obra')}
        </h3>
        <button
          onClick={onClose}
          className="p-1.5 text-muted-foreground hover:text-muted-foreground rounded-lg"
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
              inputMode="decimal"
              value={totalBudget}
              onChange={(e) => {
                const limited = limitDecimals(e.target.value, MONEY_DECIMALS);
                setTotalBudget(limited === '' ? '' : Number(limited));
              }}
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
              inputMode="decimal"
              value={executedBudget}
              onChange={(e) => {
                const limited = limitDecimals(e.target.value, MONEY_DECIMALS);
                setExecutedBudget(limited === '' ? '' : Number(limited));
              }}
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

        </div>

        <div>
          <Label htmlFor="cover-photo">
            {t('projects.modals.coverPhotoSectionLabel', 'Foto de capa')}
          </Label>
          <div
            className={`flex items-center gap-4 rounded-xl border p-4 ${
              previewUrl
                ? 'border-border bg-card'
                : 'border-dashed border-border bg-muted/40'
            }`}
          >
            {previewUrl ? (
              <img
                src={previewUrl}
                alt={t('projects.modals.coverPhotoSectionLabel', 'Foto de capa')}
                className="h-20 w-32 shrink-0 rounded-lg object-cover"
              />
            ) : (
              <div className="flex h-20 w-32 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <ImageOff className="h-6 w-6" />
              </div>
            )}
            <div className="min-w-0 space-y-2">
              <p className="truncate text-sm text-muted-foreground">
                {cover.file
                  ? cover.file.name
                  : cover.removed
                    ? t(
                        'projects.modals.coverPhotoPendingRemoval',
                        'A foto será removida quando a obra for salva.'
                      )
                    : t('projects.modals.coverPhotoEmpty', 'Nenhuma foto escolhida.')}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {previewUrl
                    ? t('projects.modals.coverPhotoReplace', 'Trocar foto')
                    : t('projects.modals.coverPhotoChoose', 'Escolher foto')}
                </Button>
                {(previewUrl || cover.file) && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleRemove}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    {t('projects.modals.coverPhotoRemove', 'Remover')}
                  </Button>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {project?.cover_photo_display_url
                  ? t(
                      'projects.modals.coverPhotoReplaceHint',
                      'A foto anterior é apagada do armazenamento depois que a troca é gravada.'
                    )
                  : t('projects.modals.coverPhotoHint', 'JPEG, PNG ou WebP, até 5 MB.')}
              </p>
            </div>
            {/* `accept` is derived from the shared constant, never retyped: it
                is the same set `media_service.ALLOWED_MIME_TYPES` enforces. */}
            <input
              id="cover-photo"
              ref={fileInputRef}
              type="file"
              accept={UPLOAD_ACCEPT}
              onChange={handlePick}
              className="hidden"
            />
          </div>
          {cover.error && (
            <p
              role="alert"
              className="mt-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{cover.error}</span>
            </p>
          )}
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
  // Held here, outside the keyed inner form, and reset on close rather than by
  // an effect on `project?.id`: §B's create sequence changes that id mid-save on
  // purpose, and an effect watching it would clear the picked file and the cover
  // error at exactly the wrong moment.
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [coverError, setCoverError] = useState<string | null>(null);
  const [coverRemoved, setCoverRemoved] = useState(false);

  const handleClose = () => {
    setCoverFile(null);
    setCoverError(null);
    setCoverRemoved(false);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
      <ProjectFormInner
        key={project?.id || 'new'}
        onClose={handleClose}
        onSubmit={onSubmit}
        project={project}
        cover={{
          file: coverFile,
          setFile: setCoverFile,
          error: coverError,
          setError: setCoverError,
          removed: coverRemoved,
          setRemoved: setCoverRemoved,
        }}
      />
    </div>
  );
};
