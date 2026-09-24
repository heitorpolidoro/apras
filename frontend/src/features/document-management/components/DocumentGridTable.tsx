import React from "react";
import { useTranslation } from "react-i18next";
import { Eye, FileText, History, Download, Trash2, Calendar, Tag as TagIcon,  } from "lucide-react";
import type { AssociationDocument } from "../../../types/document";
import { Badge } from "../../../components/ui/badge";

interface DocumentGridTableProps {
  documents: AssociationDocument[];
  onPreview: (doc: AssociationDocument) => void;
  onDownload: (doc: AssociationDocument) => void;
  onNewVersion?: (doc: AssociationDocument) => void;
  onDelete?: (doc: AssociationDocument) => void;
  canManage?: boolean;
}

function formatBytes(bytes: number, decimals = 1) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export const DocumentGridTable: React.FC<DocumentGridTableProps> = ({
  documents,
  onPreview,
  onDownload,
  onNewVersion,
  onDelete,
  canManage = false,
}) => {
  const { t } = useTranslation();

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center bg-card border border-border rounded-xl">
        <FileText className="h-12 w-12 text-slate-300 dark:text-slate-600 mb-3" />
        <h4 className="text-base font-semibold text-slate-800 dark:text-slate-200">
          {t("documents.noDocumentsFound", "Nenhum documento encontrado")}
        </h4>
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">
          {t(
            "documents.noDocumentsDescription",
            "Não há arquivos correspondentes à pasta ou aos filtros selecionados."
          )}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted text-xs font-semibold text-muted-foreground border-b border-border uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3.5">{t("documents.titleHeader", "Documento")}</th>
              <th className="px-4 py-3.5">{t("documents.folderHeader", "Pasta")}</th>
              <th className="px-4 py-3.5">{t("documents.versionHeader", "Versão")}</th>
              <th className="px-4 py-3.5">{t("documents.sizeHeader", "Tamanho")}</th>
              <th className="px-4 py-3.5">{t("documents.dateHeader", "Data / Ano")}</th>
              <th className="px-4 py-3.5 text-right">{t("documents.actionsHeader", "Ações")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-slate-700 dark:text-slate-300">
            {documents.map((doc) => (
              <tr
                key={doc.id}
                className="hover:bg-accent/80 transition-colors"
              >
                <td className="px-4 py-3.5 max-w-xs">
                  <div className="flex items-start space-x-3">
                    <FileText className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-foreground block truncate">
                        {doc.title}
                      </span>
                      {doc.description && (
                        <p className="text-xs text-muted-foreground truncate max-w-xs">
                          {doc.description}
                        </p>
                      )}
                      {doc.tags && doc.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {doc.tags.map((tag) => (
                            <span
                              key={tag}
                              className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground"
                            >
                              <TagIcon className="h-2.5 w-2.5" />
                              <span>{tag}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </td>

                <td className="px-4 py-3.5 whitespace-nowrap text-xs text-muted-foreground">
                  {doc.folder_name || "-"}
                </td>

                <td className="px-4 py-3.5 whitespace-nowrap">
                  <Badge variant="outline" className="text-xs font-mono">
                    v{doc.version_number}
                  </Badge>
                </td>

                <td className="px-4 py-3.5 whitespace-nowrap text-xs font-mono text-muted-foreground">
                  {formatBytes(doc.file_size_bytes)}
                </td>

                <td className="px-4 py-3.5 whitespace-nowrap text-xs text-muted-foreground">
                  <div className="flex items-center space-x-1">
                    <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>
                      {doc.publication_year
                        ? `${doc.publication_month ? `${doc.publication_month}/` : ""}${doc.publication_year}`
                        : new Date(doc.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </td>

                <td className="px-4 py-3.5 whitespace-nowrap text-right">
                  <div className="flex items-center justify-end space-x-1">
                    <button
                      type="button"
                      title={t("documents.preview", "Visualizar Inline")}
                      aria-label="Visualizar Inline"
                      onClick={() => onPreview(doc)}
                      className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-accent transition-colors"
                    >
                      <Eye className="h-4 w-4" />
                    </button>

                    <button
                      type="button"
                      title={t("documents.download", "Baixar Arquivo")}
                      aria-label="Baixar Arquivo"
                      onClick={() => onDownload(doc)}
                      className="p-1.5 rounded-lg text-muted-foreground hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 dark:hover:text-emerald-400 transition-colors"
                    >
                      <Download className="h-4 w-4" />
                    </button>

                    {canManage && onNewVersion && (
                      <button
                        type="button"
                        title={t("documents.newVersion", "Nova Versão")}
                        aria-label="Nova Versão"
                        onClick={() => onNewVersion(doc)}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-accent transition-colors"
                      >
                        <History className="h-4 w-4" />
                      </button>
                    )}

                    {canManage && onDelete && (
                      <button
                        type="button"
                        title={t("documents.delete", "Excluir")}
                        aria-label="Excluir"
                        onClick={() => onDelete(doc)}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 dark:hover:text-rose-400 transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
