import React, { useRef, useState, useEffect } from 'react';

interface WebcamCaptureDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCapture: (blob: Blob) => void;
}

export const WebcamCaptureDialog: React.FC<WebcamCaptureDialogProps> = ({
  isOpen,
  onClose,
  onCapture,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setCapturedUrl(null);
      setCameraError(null);
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices
          .getUserMedia({ video: { width: 640, height: 480 } })
          .then((mediaStream) => {
            setStream(mediaStream);
            if (videoRef.current) {
              videoRef.current.srcObject = mediaStream;
            }
          })
          .catch((err) => {
            console.error('Camera access error:', err);
            setCameraError('Não foi possível acessar a câmera. Verifique as permissões do navegador.');
          });
      } else {
        setCameraError('Câmera não suportada neste dispositivo.');
      }
    } else {
      stopStream();
    }

    return () => {
      stopStream();
    };
  }, [isOpen]);

  const stopStream = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
  };

  const handleTakeSnapshot = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          setCapturedUrl(url);
        }
      },
      'image/jpeg',
      0.9
    );
  };

  const handleRetake = () => {
    setCapturedUrl(null);
  };

  const handleConfirm = () => {
    if (!canvasRef.current) return;
    canvasRef.current.toBlob(
      (blob) => {
        if (blob) {
          onCapture(blob);
          stopStream();
          onClose();
        }
      },
      'image/jpeg',
      0.9
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden border border-slate-200">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 bg-slate-50">
          <h3 className="font-semibold text-slate-800 text-base">Capturar Foto da Câmera</h3>
          <button
            onClick={() => {
              stopStream();
              onClose();
            }}
            className="text-slate-400 hover:text-slate-600 font-bold text-lg"
          >
            &times;
          </button>
        </div>

        <div className="p-5 flex flex-col items-center justify-center space-y-4 min-h-[320px]">
          {cameraError ? (
            <div className="p-4 bg-red-50 text-red-700 text-sm rounded-lg text-center border border-red-200">
              {cameraError}
            </div>
          ) : capturedUrl ? (
            <div className="relative w-full max-w-sm aspect-video rounded-lg overflow-hidden border border-slate-300">
              <img src={capturedUrl} alt="Captured" className="w-full h-full object-cover" />
            </div>
          ) : (
            <div className="relative w-full max-w-sm aspect-video bg-slate-900 rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
            </div>
          )}

          <canvas ref={canvasRef} className="hidden" />
        </div>

        <div className="flex items-center justify-end space-x-3 px-5 py-4 bg-slate-50 border-t border-slate-100">
          <button
            type="button"
            onClick={() => {
              stopStream();
              onClose();
            }}
            className="px-4 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100"
          >
            Cancelar
          </button>

          {capturedUrl ? (
            <>
              <button
                type="button"
                onClick={handleRetake}
                className="px-4 py-2 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-300 rounded-lg hover:bg-amber-100"
              >
                Tirar Outra
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
              >
                Usar Esta Foto
              </button>
            </>
          ) : (
            <button
              type="button"
              disabled={!!cameraError}
              onClick={handleTakeSnapshot}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              Capturar Foto
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default WebcamCaptureDialog;
