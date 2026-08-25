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
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative flex flex-col h-[90vh] w-full max-w-5xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center space-x-3 truncate">
            <FileText className="h-6 w-6 text-indigo-500 shrink-0" />
            <div className="truncate">
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-900 dark:text-white truncate">
                  {document.title}
                </h3>
                <Badge variant="outline" className="text-xs font-mono">
                  v{document.version_number}
                </Badge>
              </div>
              {document.description && (
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                  {document.description}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => onDownload(document)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
            >
              <Download className="h-4 w-4" />
              <span>{t("documents.download", "Baixar")}</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content Viewer */}
        <div className="flex-1 bg-slate-100 dark:bg-slate-950 p-2 overflow-hidden">
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
