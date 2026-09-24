import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronRight, Folder as FolderIcon, FolderOpen, FolderPlus, Pencil, Trash2,  } from "lucide-react";
import type { DocumentFolderTree } from "../../../types/document";

interface FolderTreeSidebarProps {
  folders: DocumentFolderTree[];
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onAddFolder?: (parentId?: string) => void;
  onEditFolder?: (folder: DocumentFolderTree) => void;
  onDeleteFolder?: (folderId: string) => void;
  canManage?: boolean;
}

interface TreeNodeProps {
  folder: DocumentFolderTree;
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onAddFolder?: (parentId?: string) => void;
  onEditFolder?: (folder: DocumentFolderTree) => void;
  onDeleteFolder?: (folderId: string) => void;
  canManage?: boolean;
  level?: number;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  folder,
  selectedFolderId,
  onSelectFolder,
  onAddFolder,
  onEditFolder,
  onDeleteFolder,
  canManage = false,
  level = 0,
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const isSelected = selectedFolderId === folder.id;
  const hasChildren = folder.children && folder.children.length > 0;

  return (
    <div className="space-y-1">
      <div
        className={`role flex items-center justify-between rounded-lg px-2 py-1.5 text-sm font-medium transition-colors cursor-pointer ${
          isSelected
            ? "bg-accent text-primary-text font-semibold"
            : "text-slate-700 hover:bg-accent dark:text-slate-300"
        }`}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={() => onSelectFolder(folder.id)}
      >
        <div className="flex items-center space-x-2 truncate">
          {hasChildren ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(!isOpen);
              }}
              className="p-0.5 text-muted-foreground hover:text-muted-foreground"
            >
              {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
          ) : (
            <span className="w-4" />
          )}

          {isSelected || isOpen ? (
            <FolderOpen className="h-4 w-4 text-primary shrink-0" />
          ) : (
            <FolderIcon className="h-4 w-4 text-muted-foreground shrink-0" />
          )}

          <span className="truncate">{folder.name}</span>
        </div>

        <div className="flex items-center space-x-1">
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {folder.document_count}
          </span>

          {canManage && (
            <div className="hidden group-hover:flex items-center space-x-0.5 ml-1">
              {onAddFolder && (
                <button
                  type="button"
                  title="Nova Subpasta"
                  aria-label="Nova Subpasta"
                  onClick={(e) => {
                    e.stopPropagation();
                    onAddFolder(folder.id);
                  }}
                  className="p-1 text-muted-foreground hover:text-primary"
                >
                  <FolderPlus className="h-3.5 w-3.5" />
                </button>
              )}
              {onEditFolder && (
                <button
                  type="button"
                  title="Editar Pasta"
                  aria-label="Editar Pasta"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditFolder(folder);
                  }}
                  className="p-1 text-muted-foreground hover:text-primary"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              )}
              {onDeleteFolder && (
                <button
                  type="button"
                  title="Excluir Pasta"
                  aria-label="Excluir Pasta"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteFolder(folder.id);
                  }}
                  className="p-1 text-muted-foreground hover:text-rose-600 dark:hover:text-rose-400"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {hasChildren && isOpen && (
        <div className="space-y-1">
          {folder.children.map((child) => (
            <TreeNode
              key={child.id}
              folder={child}
              selectedFolderId={selectedFolderId}
              onSelectFolder={onSelectFolder}
              onAddFolder={onAddFolder}
              onEditFolder={onEditFolder}
              onDeleteFolder={onDeleteFolder}
              canManage={canManage}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const FolderTreeSidebar: React.FC<FolderTreeSidebarProps> = ({
  folders,
  selectedFolderId,
  onSelectFolder,
  onAddFolder,
  onEditFolder,
  onDeleteFolder,
  canManage = false,
}) => {
  const { t } = useTranslation();

  return (
    <div className="w-full md:w-64 bg-card border border-border rounded-xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider">
          {t("documents.foldersTitle", "Pastas")}
        </h3>
        {canManage && onAddFolder && (
          <button
            type="button"
            onClick={() => onAddFolder(undefined)}
            aria-label="Nova Pasta"
            className="flex items-center space-x-1 text-xs font-medium text-primary-text hover:text-primary-text"
          >
            <FolderPlus className="h-4 w-4" />
            <span>{t("documents.newFolder", "Criar")}</span>
          </button>
        )}
      </div>

      <nav className="space-y-1">
        <div
          onClick={() => onSelectFolder(null)}
          className={`flex items-center justify-between rounded-lg px-2 py-2 text-sm font-medium transition-colors cursor-pointer ${
            selectedFolderId === null
              ? "bg-accent text-primary-text font-semibold"
              : "text-slate-700 hover:bg-accent dark:text-slate-300"
          }`}
        >
          <div className="flex items-center space-x-2">
            <FolderIcon className="h-4 w-4 text-primary" />
            <span>{t("documents.allFolders", "Todos os Documentos")}</span>
          </div>
        </div>

        {folders.map((folder) => (
          <TreeNode
            key={folder.id}
            folder={folder}
            selectedFolderId={selectedFolderId}
            onSelectFolder={onSelectFolder}
            onAddFolder={onAddFolder}
            onEditFolder={onEditFolder}
            onDeleteFolder={onDeleteFolder}
            canManage={canManage}
          />
        ))}
      </nav>
    </div>
  );
};
