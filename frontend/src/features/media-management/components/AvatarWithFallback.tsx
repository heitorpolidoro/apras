import React from 'react';
import { PhotoApprovalStatus } from '../../../types/media_asset';

interface AvatarWithFallbackProps {
  name?: string;
  photoUrl?: string | null;
  status?: PhotoApprovalStatus;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const AvatarWithFallback: React.FC<AvatarWithFallbackProps> = ({
  name = 'U',
  photoUrl,
  status = 'APPROVED',
  size = 'md',
  className = '',
}) => {
  const getInitials = (n?: string) => {
    if (!n) return 'U';
    const parts = n.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-12 h-12 text-sm',
    lg: 'w-16 h-16 text-base',
    xl: 'w-24 h-24 text-xl',
  }[size];

  const showImage = photoUrl && status === 'APPROVED';

  return (
    <div className={`relative inline-flex items-center justify-center rounded-full overflow-hidden bg-slate-200 text-slate-700 font-semibold border border-slate-300 ${sizeClasses} ${className}`}>
      {showImage ? (
        <img
          src={photoUrl}
          alt={name}
          className="w-full h-full object-cover rounded-full"
        />
      ) : (
        <span>{getInitials(name)}</span>
      )}

      {status === 'PENDING_APPROVAL' && (
        <span className="absolute bottom-0 inset-x-0 bg-amber-500/90 text-white text-[9px] text-center font-medium py-0.5 leading-none">
          Em Aprovação
        </span>
      )}
    </div>
  );
};

export default AvatarWithFallback;
