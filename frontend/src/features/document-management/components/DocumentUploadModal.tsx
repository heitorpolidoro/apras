import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { X, Upload, FileUp } from "lucide-react";
import type {
  AssociationDocument,
  DocumentFolderTree,
} from "../../../types/document";
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  folders: DocumentFolderTree[];
  initialFolderId?: string | null;
  parentDocument?: AssociationDocument | null;
  onSubmit: (data: any) => Promise<void>;
  isLoading?: boolean;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  folders,
  initialFolderId,
  parentDocument = null,
  onSubmit,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const isVersionMode = Boolean(parentDocument);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [folderId, setFolderId] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [fileSizeBytes, setFileSizeBytes] = useState<number>(1048576);
  const [publicationYear, setPublicationYear] = useState<number | "">(new Date().getFullYear());
  const [publicationMonth, setPublicationMonth] = useState<number | "">(new Date().getMonth() + 1);
  const [tagsInput, setTagsInput] = useState("");

  const flattenFolders = (
    items: DocumentFolderTree[],
    depth = 0
  ): { id: string; name: string; depth: number }[] => {
    let result: { id: string; name: string; depth: number }[] = [];
    for (const item of items) {
      result.push({ id: item.id, name: item.name, depth });
      if (item.children && item.children.length > 0) {
        result = result.concat(flattenFolders(item.children, depth + 1));
      }
    }
    return result;
  };

  const folderOptions = flattenFolders(folders);

  useEffect(() => {
    if (parentDocument) {
      setTitle(parentDocument.title);
      setDescription(parentDocument.description || "");
      setFolderId(parentDocument.folder_id);
      setTagsInput(parentDocument.tags ? parentDocument.tags.join(", ") : "");
      setPublicationYear(parentDocument.publication_year || new Date().getFullYear());
      setPublicationMonth(parentDocument.publication_month || new Date().getMonth() + 1);
    } else {
      setTitle("");
      setDescription("");
      setFolderId(initialFolderId || (folderOptions[0]?.id || ""));
      setFileUrl("");
      setFileSizeBytes(1048576);
      setTagsInput("");
      setPublicationYear(new Date().getFullYear());
      setPublicationMonth(new Date().getMonth() + 1);
    }
  }, [parentDocument, initialFolderId, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const tags = tagsInput
      ? tagsInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : undefined;

    if (isVersionMode && parentDocument) {
      await onSubmit({
        title: title || undefined,
        description: description || undefined,
        file_url: fileUrl,
        file_size_bytes: fileSizeBytes,
        tags,
      });
    } else {
      await onSubmit({
        folder_id: folderId,
        title,
        description: description || undefined,
        file_url: fileUrl,
        file_size_bytes: fileSizeBytes,
        publication_year: publicationYear ? Number(publicationYear) : undefined,
        publication_month: publicationMonth ? Number(publicationMonth) : undefined,
        tags,
      });
    }
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center space-x-2">
            <FileUp className="h-5 w-5 text-indigo-500" />
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              {isVersionMode
                ? t("documents.uploadNewVersionTitle", "Nova Versão do Documento")
                : t("documents.uploadDocumentTitle", "Novo Documento")}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {!isVersionMode && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                {t("documents.folderLabel", "Pasta Destino")} *
              </label>
              <select
                value={folderId}
                onChange={(e) => setFolderId(e.target.value)}
                required
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              >
                <option value="" disabled>
                  {t("documents.selectFolder", "Selecione uma pasta")}
                </option>
                {folderOptions.map((f) => (
                  <option key={f.id} value={f.id}>
                    {"\u00A0\u00A0".repeat(f.depth)}📁 {f.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              {t("documents.titleLabel", "Título")} *
            </label>
            <Input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("documents.titlePlaceholder", "Ex: Balancete Financeiro Jan/2026")}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              {t("documents.fileUrlLabel", "URL do Arquivo")} *
            </label>
            <Input
              type="url"
              required
              value={fileUrl}
              onChange={(e) => setFileUrl(e.target.value)}
              placeholder="https://storage.example.com/arquivo.pdf"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                {t("documents.yearLabel", "Ano Publicação")}
              </label>
              <Input
                type="number"
                value={publicationYear}
                onChange={(e) =>
                  setPublicationYear(e.target.value ? Number(e.target.value) : "")
                }
                placeholder="2026"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                {t("documents.monthLabel", "Mês Publicação")}
              </label>
              <Input
                type="number"
                min={1}
                max={12}
                value={publicationMonth}
                onChange={(e) =>
                  setPublicationMonth(e.target.value ? Number(e.target.value) : "")
                }
                placeholder="1"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              {t("documents.tagsLabel", "Tags (separadas por vírgula)")}
            </label>
            <Input
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="balancete, 2026, financeiro"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              {t("documents.descriptionLabel", "Descrição")}
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              placeholder={t("documents.descriptionPlaceholder", "Resumo das informações do documento...")}
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-800">
            <Button type="button" variant="outline" onClick={onClose}>
              {t("common.cancel", "Cancelar")}
            </Button>
            <Button type="submit" disabled={isLoading} className="bg-indigo-600 hover:bg-indigo-700 text-white">
              <Upload className="h-4 w-4 mr-1.5" />
              <span>{isVersionMode ? t("documents.saveVersion", "Enviar Nova Versão") : t("documents.saveDocument", "Salvar Documento")}</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
