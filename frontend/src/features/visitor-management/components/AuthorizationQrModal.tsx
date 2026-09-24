import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { X, QrCode } from "lucide-react";
import apiClient from "../../../api/client";
import type { VisitorAuthorization } from "../../../types/visitor";

interface AuthorizationQrModalProps {
  authorization: VisitorAuthorization | null;
  onClose: () => void;
}

export const AuthorizationQrModal: React.FC<AuthorizationQrModalProps> = ({
  authorization,
  onClose,
}) => {
  const { t } = useTranslation();
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authorization) {
      return undefined;
    }

    let objectUrl: string | null = null;
    let cancelled = false;

    // Bare <img src="..."> cannot carry the Bearer auth header this endpoint
    // requires, so the image bytes are fetched as a blob through apiClient
    // (which attaches the token) and rendered via an object URL instead.
    apiClient
      .get(`/authorizations/${authorization.id}/qr-code`, { responseType: "blob" })
      .then((response) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(response.data);
        setImageUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) {
          setError(t("authorizations.qrLoadError"));
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [authorization, t]);

  if (!authorization) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
            <QrCode className="size-5 text-primary" />
            {t("authorizations.qrCodeTitle")}
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent"
          >
            <X className="size-5" />
          </button>
        </div>

        <div className="mt-4 flex min-h-[220px] flex-col items-center justify-center gap-3">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {!error && !imageUrl && (
            <p className="text-sm text-muted-foreground">
              {t("authorizations.loading")}
            </p>
          )}
          {imageUrl && (
            <img
              src={imageUrl}
              alt={t("authorizations.qrCodeTitle")}
              className="size-56 rounded-lg border border-border"
            />
          )}
        </div>
      </div>
    </div>
  );
};
