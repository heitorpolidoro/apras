import React, { useState } from 'react';
import type { EntityType } from '../../../types/media_asset';
import { useUploadPhoto } from '../hooks/useMediaAssets';
import AvatarCropEditor from './AvatarCropEditor';
import WebcamCaptureDialog from './WebcamCaptureDialog';

interface PhotoUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  entityType: EntityType;
  entityId?: string;
}

export const PhotoUploadModal: React.FC<PhotoUploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  entityType,
  entityId,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | Blob | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [isCropping, setIsCropping] = useState(false);
  const [isWebcamOpen, setIsWebcamOpen] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const uploadMutation = useUploadPhoto();

  if (!isOpen) return null;

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 5 * 1024 * 1024) {
        setErrorMsg('O arquivo excede o tamanho máximo permitido de 5MB.');
        return;
      }
      setSelectedFile(file);
      setPreviewSrc(URL.createObjectURL(file));
      setIsCropping(true);
    }
  };

  const handleWebcamCapture = (capturedBlob: Blob) => {
    setErrorMsg(null);
    setSelectedFile(capturedBlob);
    setPreviewSrc(URL.createObjectURL(capturedBlob));
    setIsCropping(true);
  };

  const handleCropComplete = (croppedBlob: Blob) => {
    setSelectedFile(croppedBlob);
    setPreviewSrc(URL.createObjectURL(croppedBlob));
    setIsCropping(false);
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) return;
    try {
      await uploadMutation.mutateAsync({
        file: selectedFile,
        entityType,
        entityId,
      });
      onSuccess?.();
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Erro ao enviar foto. Tente novamente.';
      setErrorMsg(msg);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-card rounded-xl shadow-2xl w-full max-w-lg overflow-hidden border border-border">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-muted">
          <h3 className="font-semibold text-slate-800 text-base">Enviar Foto de Cadastro</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-muted-foreground font-bold text-lg">
            &times;
          </button>
        </div>

        <div className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
              {errorMsg}
            </div>
          )}

          {isCropping && previewSrc ? (
            <AvatarCropEditor
              imageSrc={previewSrc}
              onCropComplete={handleCropComplete}
              onCancel={() => setIsCropping(false)}
            />
          ) : previewSrc ? (
            <div className="flex flex-col items-center space-y-3">
              <div className="w-40 h-40 rounded-full overflow-hidden border-2 border-primary shadow-inner">
                <img src={previewSrc} alt="Preview" className="w-full h-full object-cover" />
              </div>
              <button
                type="button"
                onClick={() => setIsCropping(true)}
                className="text-xs text-primary-text hover:text-primary-text font-medium underline"
              >
                Ajustar Recorte
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center border-2 border-dashed border-input rounded-xl p-8 bg-muted hover:bg-accent transition-colors">
              <svg className="w-12 h-12 text-muted-foreground mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <p className="text-sm font-medium text-slate-700 mb-1">Arraste uma foto ou clique para escolher</p>
              <p className="text-xs text-muted-foreground mb-4">Formatos suportados: JPEG, PNG, WebP (máx. 5MB)</p>

              <label className="cursor-pointer inline-flex items-center px-4 py-2 text-xs font-semibold text-primary-foreground bg-primary rounded-lg hover:bg-primary/90 shadow-sm">
                <span>Selecionar Arquivo</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileSelect}
                  className="hidden"
                  data-testid="file-input"
                />
              </label>

              <div className="relative w-full flex items-center justify-center my-4">
                <div className="border-t border-border w-full" />
                <span className="bg-muted px-2 text-xs text-muted-foreground absolute">ou</span>
              </div>

              <button
                type="button"
                onClick={() => setIsWebcamOpen(true)}
                className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-slate-700 bg-card border border-input rounded-lg hover:bg-accent shadow-sm"
              >
                <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>Usar Câmera / Webcam</span>
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end space-x-3 px-6 py-4 bg-muted border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-700 bg-card border border-input rounded-lg hover:bg-accent"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={!selectedFile || uploadMutation.isPending}
            onClick={handleUploadSubmit}
            className="px-4 py-2 text-xs font-semibold text-primary-foreground bg-primary rounded-lg hover:bg-primary/90 disabled:opacity-50 shadow-sm"
          >
            {uploadMutation.isPending ? 'Enviando...' : 'Enviar Foto'}
          </button>
        </div>
      </div>

      <WebcamCaptureDialog
        isOpen={isWebcamOpen}
        onClose={() => setIsWebcamOpen(false)}
        onCapture={handleWebcamCapture}
      />
    </div>
  );
};

export default PhotoUploadModal;
