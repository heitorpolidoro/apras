import React from "react";
import { useTranslation } from "react-i18next";
import { Download, X, FileText } from "lucide-react";
import type { AssociationDocument } from "../../../types/document";
import { Badge } from "../../../components/ui/badge";

interface PDFViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: AssociationDocument | null;
  onDownload: (doc: AssociationDocument) => void;
}

export const PDFViewerModal: React.FC<PDFViewerModalProps> = ({
  isOpen,
  onClose,
  document,
  onDownload,
}) => {
  const { t } = useTranslation();

  if (!isOpen || !document) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/70 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative flex flex-col h-[90vh] w-full max-w-5xl bg-card rounded-2xl shadow-2xl overflow-hidden border border-border"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center space-x-3 truncate">
            <FileText className="h-6 w-6 text-primary shrink-0" />
            <div className="truncate">
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-foreground truncate">
                  {document.title}
                </h3>
                <Badge variant="outline" className="text-xs font-mono">
                  v{document.version_number}
                </Badge>
              </div>
              {document.description && (
                <p className="text-xs text-muted-foreground truncate">
                  {document.description}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => onDownload(document)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground transition-colors"
            >
              <Download className="h-4 w-4" />
              <span>{t("documents.download", "Baixar")}</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-muted-foreground hover:bg-accent transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content Viewer */}
        <div className="flex-1 bg-muted p-2 overflow-hidden">
          <iframe
            src={document.file_url}
            title={document.title}
            className="w-full h-full rounded-lg border-0 shadow-inner"
          />
        </div>
      </div>
    </div>
  );
};
