import React from "react";
import { useTranslation } from "react-i18next";
import { Download, FileText, X } from "lucide-react";

interface InvoicePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  invoiceUrl: string | null;
}

/**
 * PDF invoice viewer. Structurally parallel to the Document Center's
 * `PDFViewerModal` (T009), but standalone within this feature folder.
 * Renders the iframe immediately from the already-loaded `invoice_file_url`
 * — no extra confirmation step or fetch — satisfying the "1-click"
 * drill-down requirement.
 */
export const InvoicePreviewModal: React.FC<InvoicePreviewModalProps> = ({
  isOpen,
  onClose,
  invoiceUrl,
}) => {
  const { t } = useTranslation();

  if (!isOpen || !invoiceUrl) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative flex flex-col h-[90vh] w-full max-w-4xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-500" />
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              {t("finance.invoice.previewTitle", "Nota Fiscal")}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={invoiceUrl}
              download
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
            >
              <Download className="h-4 w-4" />
              <span>{t("finance.invoice.download", "Baixar")}</span>
            </a>
            <button
              type="button"
              onClick={onClose}
              aria-label={t("common.close", "Fechar")}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 bg-slate-100 dark:bg-slate-950 p-2 overflow-hidden">
          <iframe
            src={invoiceUrl}
            title={t("finance.invoice.previewTitle", "Nota Fiscal")}
            className="w-full h-full rounded-lg border-0 shadow-inner"
          />
        </div>
      </div>
    </div>
  );
};
