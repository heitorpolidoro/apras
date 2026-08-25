import React, { useRef, useState, useEffect } from 'react';

interface AvatarCropEditorProps {
  imageSrc: string;
  onCropComplete: (croppedBlob: Blob) => void;
  onCancel: () => void;
}

export const AvatarCropEditor: React.FC<AvatarCropEditorProps> = ({
  imageSrc,
  onCropComplete,
  onCancel,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = imageSrc;
    img.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.rotate((rotation * Math.PI) / 180);
      ctx.scale(zoom, zoom);
      ctx.drawImage(img, -img.width / 2, -img.height / 2);
      ctx.restore();
    };
  }, [imageSrc, zoom, rotation]);

  const handleConfirmCrop = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const outputCanvas = document.createElement('canvas');
    outputCanvas.width = 300;
    outputCanvas.height = 300;
    const ctx = outputCanvas.getContext('2d');

    if (ctx && canvas) {
      ctx.drawImage(canvas, 0, 0, 300, 300);
      outputCanvas.toBlob(
        (blob) => {
          if (blob) {
            onCropComplete(blob);
          }
        },
        'image/jpeg',
        0.9
      );
    }
  };

  return (
    <div className="flex flex-col items-center space-y-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
      <h4 className="text-sm font-semibold text-slate-700">Ajustar Recorte da Foto</h4>

      <div className="relative w-64 h-64 border-2 border-dashed border-indigo-400 rounded-full overflow-hidden bg-slate-900 flex items-center justify-center">
        <canvas ref={canvasRef} width={256} height={256} className="w-full h-full object-cover" />
      </div>

      <div className="w-full max-w-xs space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-600">
          <span>Zoom</span>
          <span>{Math.round(zoom * 100)}%</span>
        </div>
        <input
          type="range"
          min="1"
          max="3"
          step="0.1"
          value={zoom}
          onChange={(e) => setZoom(parseFloat(e.target.value))}
          className="w-full h-1 bg-slate-300 rounded-lg appearance-none cursor-pointer accent-indigo-600"
        />
      </div>

      <div className="flex items-center space-x-2">
        <button
          type="button"
          onClick={() => setRotation((prev) => (prev + 90) % 360)}
          className="px-3 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-100"
        >
          Girar 90°
        </button>
      </div>

      <div className="flex items-center space-x-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-100"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={handleConfirmCrop}
          className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-700 shadow-sm"
        >
          Confirmar Recorte
        </button>
      </div>
    </div>
  );
};

export default AvatarCropEditor;
