import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  FileText,
  FolderPlus,
  Plus,
  Search,
  Filter,
  RefreshCw,
} from "lucide-react";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";
import {
  useCreateDocumentVersion,
  useCreateFolder,
  useDeleteDocument,
  useDeleteFolder,
  useDocumentFolders,
  useDocuments,
  useDownloadDocument,
  useUpdateFolder,
  useUploadDocument,
} from "../hooks/useDocuments";
import type { AssociationDocument, DocumentFolderTree } from "../../../types/document";
import { FolderTreeSidebar } from "./FolderTreeSidebar";
import { DocumentGridTable } from "./DocumentGridTable";
import { PDFViewerModal } from "./PDFViewerModal";
import { DocumentUploadModal } from "./DocumentUploadModal";
import { FolderFormModal } from "./FolderFormModal";
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";

export const DocumentCenterPage: React.FC = () => {
  const { t } = useTranslation();
  const { role } = useEffectiveIdentity();
  const canManage = role === "ADMINISTRATOR" || role === "DIRECTOR";

  // State
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [yearFilter, setYearFilter] = useState<number | "">("");
  const [monthFilter, setMonthFilter] = useState<number | "">("");

  // Modals
  const [previewDoc, setPreviewDoc] = useState<AssociationDocument | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [versionParentDoc, setVersionParentDoc] = useState<AssociationDocument | null>(null);
  const [folderModalOpen, setFolderModalOpen] = useState(false);
  const [editingFolder, setEditingFolder] = useState<DocumentFolderTree | null>(null);
  const [parentFolderIdForNew, setParentFolderIdForNew] = useState<string | null>(null);

  // Queries & Mutations
  const { data: folders = [], isLoading: isLoadingFolders } = useDocumentFolders();
  const { data: documentsData, isLoading: isLoadingDocs, refetch: refetchDocs } = useDocuments({
    folder_id: selectedFolderId || undefined,
    search: searchQuery || undefined,
    tag: tagFilter || undefined,
    year: yearFilter ? Number(yearFilter) : undefined,
    month: monthFilter ? Number(monthFilter) : undefined,
  });

  const createFolderMutation = useCreateFolder();
  const updateFolderMutation = useUpdateFolder();
  const deleteFolderMutation = useDeleteFolder();
  const uploadDocMutation = useUploadDocument();
  const createVersionMutation = useCreateDocumentVersion();
  const downloadDocMutation = useDownloadDocument();
  const deleteDocMutation = useDeleteDocument();

  const handleDownload = async (doc: AssociationDocument) => {
    try {
      const res = await downloadDocMutation.mutateAsync(doc.id);
      window.open(res.file_url, "_blank");
    } catch {
      window.open(doc.file_url, "_blank");
    }
  };

  const handleCreateFolderSubmit = async (data: any) => {
    if (editingFolder) {
      await updateFolderMutation.mutateAsync({ id: editingFolder.id, data });
    } else {
      await createFolderMutation.mutateAsync(data);
    }
  };

  const handleUploadSubmit = async (data: any) => {
    if (versionParentDoc) {
      await createVersionMutation.mutateAsync({ id: versionParentDoc.id, data });
    } else {
      await uploadDocMutation.mutateAsync(data);
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    if (window.confirm(t("documents.confirmDeleteFolder", "Tem certeza que deseja excluir esta pasta e todo seu conteúdo?"))) {
      await deleteFolderMutation.mutateAsync(folderId);
      if (selectedFolderId === folderId) {
        setSelectedFolderId(null);
      }
    }
  };

  const handleDeleteDoc = async (doc: AssociationDocument) => {
    if (window.confirm(t("documents.confirmDeleteDocument", "Tem certeza que deseja excluir este documento?"))) {
      await deleteDocMutation.mutateAsync(doc.id);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-indigo-50 dark:bg-indigo-950/60 rounded-xl">
              <FileText className="h-7 w-7 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                {t("documents.pageTitle", "Central de Documentos")}
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t(
                  "documents.pageSubtitle",
                  "Repositório digital de arquivos legais, financeiros e administrativos da associação."
                )}
              </p>
            </div>
          </div>
        </div>

        {canManage && (
          <div className="flex items-center space-x-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setEditingFolder(null);
                setParentFolderIdForNew(null);
                setFolderModalOpen(true);
              }}
              className="border-slate-300 dark:border-slate-700"
            >
              <FolderPlus className="h-4 w-4 mr-2 text-indigo-600" />
              <span>{t("documents.newFolder", "Nova Pasta")}</span>
            </Button>

            <Button
              type="button"
              onClick={() => {
                setVersionParentDoc(null);
                setUploadModalOpen(true);
              }}
              className="bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              <Plus className="h-4 w-4 mr-2" />
              <span>{t("documents.uploadDocument", "Novo Documento")}</span>
            </Button>
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xs space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-5 relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("documents.searchPlaceholder", "Buscar por título ou descrição...")}
              className="pl-9"
            />
          </div>

          <div className="md:col-span-3">
            <Input
              type="text"
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              placeholder={t("documents.tagFilterPlaceholder", "Filtrar por tag (ex: ata)")}
            />
          </div>

          <div className="md:col-span-2">
            <Input
              type="number"
              value={yearFilter}
              onChange={(e) => setYearFilter(e.target.value ? Number(e.target.value) : "")}
              placeholder={t("documents.yearFilterPlaceholder", "Ano")}
            />
          </div>

          <div className="md:col-span-2 flex items-center space-x-2">
            <Input
              type="number"
              min={1}
              max={12}
              value={monthFilter}
              onChange={(e) => setMonthFilter(e.target.value ? Number(e.target.value) : "")}
              placeholder={t("documents.monthFilterPlaceholder", "Mês")}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => refetchDocs()}
              title="Atualizar"
            >
              <RefreshCw className="h-4 w-4 text-slate-500" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content Layout: Sidebar + Document List */}
      <div className="flex flex-col md:flex-row gap-6">
        <FolderTreeSidebar
          folders={folders}
          selectedFolderId={selectedFolderId}
          onSelectFolder={(id) => setSelectedFolderId(id)}
          onAddFolder={(pId) => {
            setEditingFolder(null);
            setParentFolderIdForNew(pId || null);
            setFolderModalOpen(true);
          }}
          onEditFolder={(folder) => {
            setEditingFolder(folder);
            setParentFolderIdForNew(null);
            setFolderModalOpen(true);
          }}
          onDeleteFolder={handleDeleteFolder}
          canManage={canManage}
        />

        <div className="flex-1 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              {selectedFolderId
                ? folders.find((f) => f.id === selectedFolderId)?.name || t("documents.documentsList", "Documentos")
                : t("documents.allDocumentsTitle", "Todos os Documentos")}
            </h2>
            <span className="text-xs text-slate-500 font-mono">
              {documentsData?.total || 0} {t("documents.itemsFound", "documento(s)")}
            </span>
          </div>

          {isLoadingDocs ? (
            <div className="p-12 text-center text-slate-400">
              {t("common.loading", "Carregando documentos...")}
            </div>
          ) : (
            <DocumentGridTable
              documents={documentsData?.items || []}
              onPreview={(doc) => setPreviewDoc(doc)}
              onDownload={handleDownload}
              onNewVersion={(doc) => {
                setVersionParentDoc(doc);
                setUploadModalOpen(true);
              }}
              onDelete={handleDeleteDoc}
              canManage={canManage}
            />
          )}
        </div>
      </div>

      {/* Modals */}
      <PDFViewerModal
        isOpen={Boolean(previewDoc)}
        onClose={() => setPreviewDoc(null)}
        document={previewDoc}
        onDownload={handleDownload}
      />

      <DocumentUploadModal
        isOpen={uploadModalOpen}
        onClose={() => {
          setUploadModalOpen(false);
          setVersionParentDoc(null);
        }}
        folders={folders}
        initialFolderId={selectedFolderId}
        parentDocument={versionParentDoc}
        onSubmit={handleUploadSubmit}
        isLoading={uploadDocMutation.isPending || createVersionMutation.isPending}
      />

      <FolderFormModal
        isOpen={folderModalOpen}
        onClose={() => {
          setFolderModalOpen(false);
          setEditingFolder(null);
          setParentFolderIdForNew(null);
        }}
        folders={folders}
        initialData={editingFolder}
        initialParentId={parentFolderIdForNew}
        onSubmit={handleCreateFolderSubmit}
        isLoading={createFolderMutation.isPending || updateFolderMutation.isPending}
      />
    </div>
  );
};
