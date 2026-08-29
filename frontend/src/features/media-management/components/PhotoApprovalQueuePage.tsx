import React, { useState } from 'react';
import {
  usePendingPhotos,
  useApprovePhoto,
  useRejectPhoto,
} from '../hooks/useMediaAssets';
import type { MediaAssetRead } from '../../../types/media_asset';

export const PhotoApprovalQueuePage: React.FC = () => {
  const [page] = useState(1);
  const [rejectingPhotoId, setRejectingPhotoId] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [previewAsset, setPreviewAsset] = useState<MediaAssetRead | null>(null);

  const { data, isLoading, error } = usePendingPhotos(page);
  const approveMutation = useApprovePhoto();
  const rejectMutation = useRejectPhoto();

  const handleApprove = async (photoId: string) => {
    await approveMutation.mutateAsync(photoId);
  };

  const handleOpenRejectModal = (photoId: string) => {
    setRejectingPhotoId(photoId);
    setRejectionReason('');
  };

  const handleConfirmReject = async () => {
    if (!rejectingPhotoId || !rejectionReason.trim()) return;
    await rejectMutation.mutateAsync({
      photoId: rejectingPhotoId,
      rejectionReason: rejectionReason.trim(),
    });
    setRejectingPhotoId(null);
    setRejectionReason('');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Fila de Aprovação de Fotos</h1>
          <p className="text-sm text-slate-500">
            Gerencie e valide fotos de moradores e visitantes antes de estarem ativas no sistema.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-semibold">
            Pendente ({data?.pending_count || 0})
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Carregando fila de aprovação...</div>
      ) : error ? (
        <div className="p-4 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">
          Erro ao carregar fotos pendentes.
        </div>
      ) : !data?.items || data.items.length === 0 ? (
        <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
          Nenhuma foto aguardando aprovação no momento.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.items.map((asset) => (
            <div
              key={asset.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col justify-between"
            >
              <div className="p-4 space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="font-semibold text-slate-700 uppercase tracking-wide">
                    {asset.entity_type}
                  </span>
                  <span>{new Date(asset.created_at).toLocaleDateString('pt-BR')}</span>
                </div>

                <div
                  className="relative w-full h-48 bg-slate-100 rounded-lg overflow-hidden cursor-pointer group"
                  onClick={() => setPreviewAsset(asset)}
                >
                  <img
                    src={asset.url}
                    alt={asset.uploaded_by_name || 'Uploaded photo'}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xs font-medium">
                    Clique para ampliar
                  </div>
                </div>

                <div className="text-xs space-y-1 text-slate-600">
                  <p>
                    <strong className="text-slate-700">Enviado por:</strong>{' '}
                    {asset.uploaded_by_name || 'Usuário'}
                  </p>
                  <p>
                    <strong className="text-slate-700">Dimensões:</strong>{' '}
                    {asset.width && asset.height ? `${asset.width}x${asset.height}px` : 'N/A'}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2 p-4 bg-slate-50 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => handleOpenRejectModal(asset.id)}
                  disabled={rejectMutation.isPending}
                  className="flex-1 py-2 px-3 text-xs font-semibold text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-lg transition-colors"
                >
                  Rejeitar
                </button>
                <button
                  type="button"
                  onClick={() => handleApprove(asset.id)}
                  disabled={approveMutation.isPending}
                  className="flex-1 py-2 px-3 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors shadow-sm"
                >
                  Aprovar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reject Reason Modal */}
      {rejectingPhotoId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-800">Motivo da Rejeição</h3>
            <p className="text-xs text-slate-500">
              Descreva o motivo da rejeição da foto (ex: desfocada, escura, rosto encoberto).
            </p>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Informe o motivo da rejeição..."
              className="w-full h-24 p-3 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setRejectingPhotoId(null)}
                className="px-4 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={!rejectionReason.trim() || rejectMutation.isPending}
                onClick={handleConfirmReject}
                className="px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg disabled:opacity-50"
              >
                Confirmar Rejeição
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Image Zoom Modal */}
      {previewAsset && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 cursor-pointer"
          onClick={() => setPreviewAsset(null)}
        >
          <div className="relative max-w-3xl max-h-[85vh] bg-white rounded-xl overflow-hidden shadow-2xl p-2">
            <img src={previewAsset.url} alt="Full resolution" className="max-h-[80vh] w-auto object-contain rounded-lg" />
          </div>
        </div>
      )}
    </div>
  );
};

export default PhotoApprovalQueuePage;
