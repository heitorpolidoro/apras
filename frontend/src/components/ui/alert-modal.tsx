import * as React from "react";
import { cn } from "../../lib/utils";
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from "lucide-react";

type AlertModalVariant = "destructive" | "success" | "warning" | "info";

interface AlertModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  message: React.ReactNode;
  variant?: AlertModalVariant;
  confirmLabel?: string;
}

const variantConfig: Record<
  AlertModalVariant,
  { icon: React.FC<{ className?: string }>; iconClass: string; titleClass: string; borderClass: string }
> = {
  destructive: {
    icon: AlertCircle,
    iconClass: "text-destructive",
    titleClass: "text-destructive",
    borderClass: "border-destructive/20",
  },
  success: {
    icon: CheckCircle2,
    iconClass: "text-emerald-500",
    titleClass: "text-emerald-700",
    borderClass: "border-emerald-200",
  },
  warning: {
    icon: AlertTriangle,
    iconClass: "text-amber-500",
    titleClass: "text-amber-700",
    borderClass: "border-amber-200",
  },
  info: {
    icon: Info,
    iconClass: "text-primary",
    titleClass: "text-primary",
    borderClass: "border-primary/20",
  },
};

const AlertModal: React.FC<AlertModalProps> = ({
  open,
  onClose,
  title,
  message,
  variant = "destructive",
  confirmLabel = "OK",
}) => {
  const config = variantConfig[variant];
  const Icon = config.icon;

  // Close on Escape key
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="alert-modal"
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200" />

      {/* Modal panel */}
      <div
        className={cn(
          "relative z-10 w-full max-w-sm mx-4 bg-card rounded-xl border shadow-xl p-6",
          "animate-in fade-in zoom-in-95 duration-200",
          config.borderClass,
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          aria-label="close-alert-modal"
          className="absolute top-3 right-3 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="size-4" />
        </button>

        {/* Icon + Title */}
        <div className="flex items-start gap-3 mb-3">
          <Icon className={cn("size-5 shrink-0 mt-0.5", config.iconClass)} />
          {title && (
            <h3 className={cn("font-semibold text-base leading-snug", config.titleClass)}>
              {title}
            </h3>
          )}
        </div>

        {/* Message */}
        <p className="text-sm text-muted-foreground leading-relaxed pl-8">{message}</p>

        {/* Confirm button */}
        <div className="mt-5 flex justify-end">
          <button
            onClick={onClose}
            className={cn(
              "px-4 py-1.5 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              variant === "destructive"
                ? "bg-destructive text-white hover:bg-destructive/90"
                : variant === "success"
                  ? "bg-emerald-600 text-white hover:bg-emerald-700"
                  : variant === "warning"
                    ? "bg-amber-500 text-white hover:bg-amber-600"
                    : "bg-primary text-primary-foreground hover:bg-primary/90",
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

AlertModal.displayName = "AlertModal";

export { AlertModal, type AlertModalProps, type AlertModalVariant };
