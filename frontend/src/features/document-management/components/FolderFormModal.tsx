import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { FolderPlus, X } from "lucide-react";
import type { DocumentFolderTree } from "../../../types/document";
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";
import { useRoles } from "../../../hooks/useRoles";

interface FolderFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  folders: DocumentFolderTree[];
  initialData?: DocumentFolderTree | null;
  initialParentId?: string | null;
  onSubmit: (data: any) => Promise<void>;
  isLoading?: boolean;
}

export const FolderFormModal: React.FC<FolderFormModalProps> = ({
  isOpen,
  onClose,
  folders,
  initialData = null,
  initialParentId = null,
  onSubmit,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const isEditMode = Boolean(initialData);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parentId, setParentId] = useState<string | "">("");
  // IAM F5 (APRAS-49 §6): the list is every role of the tenant, not the six
  // hard-coded legacy names — a folder can now be scoped to any role. The
  // default is empty because the backend's default is `[]` and
  // `DocumentFolderCreate.allowed_role_ids` is required: a folder created
  // without an explicit ACL would be invisible to everyone, so the caller
  // is made to say.
  const { data: roles } = useRoles();
  const [allowedRoles, setAllowedRoles] = useState<string[]>([]);

  const flattenFolders = (
    items: DocumentFolderTree[],
    depth = 0
  ): { id: string; name: string; depth: number }[] => {
    let result: { id: string; name: string; depth: number }[] = [];
    for (const item of items) {
      if (initialData && item.id === initialData.id) continue;
      result.push({ id: item.id, name: item.name, depth });
      if (item.children && item.children.length > 0) {
        result = result.concat(flattenFolders(item.children, depth + 1));
      }
    }
    return result;
  };

  const folderOptions = flattenFolders(folders);

  useEffect(() => {
    if (initialData) {
      setName(initialData.name);
      setDescription(initialData.description || "");
      setParentId(initialData.parent_id || "");
      setAllowedRoles(initialData.allowed_role_ids || []);
    } else {
      setName("");
      setDescription("");
      setParentId(initialParentId || "");
      setAllowedRoles([]);
    }
  }, [initialData, initialParentId, isOpen]);

  if (!isOpen) return null;

  const handleRoleToggle = (role: string) => {
    if (allowedRoles.includes(role)) {
      setAllowedRoles(allowedRoles.filter((r) => r !== role));
    } else {
      setAllowedRoles([...allowedRoles, role]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({
      name,
      description: description || undefined,
      parent_id: parentId || null,
      allowed_role_ids: allowedRoles,
    });
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/70 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md bg-card rounded-2xl shadow-2xl overflow-hidden border border-border"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center space-x-2">
            <FolderPlus className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold text-foreground">
              {isEditMode
                ? t("documents.editFolderTitle", "Editar Pasta")
                : t("documents.newFolderTitle", "Criar Nova Pasta")}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-muted-foreground hover:bg-accent transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              {t("documents.folderNameLabel", "Nome da Pasta")} *
            </label>
            <Input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("documents.folderNamePlaceholder", "Ex: Legislação e Atas")}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              {t("documents.parentFolderLabel", "Pasta Pai (Opcional)")}
            </label>
            <select
              value={parentId}
              onChange={(e) => setParentId(e.target.value)}
              className="w-full rounded-lg border border-input bg-card px-3 py-2 text-sm text-foreground focus:outline-hidden focus:ring-2 focus:ring-ring"
            >
              <option value="">{t("documents.noParent", "(Nenhuma - Pasta Raiz)")}</option>
              {folderOptions.map((f) => (
                <option key={f.id} value={f.id}>
                  {"\u00A0\u00A0".repeat(f.depth)}📁 {f.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              {t("documents.allowedRolesLabel", "Perfis com Acesso")}
            </label>
            <div className="grid grid-cols-2 gap-2 mt-2">
              {(roles ?? []).map((role) => (
                <label
                  key={role.id}
                  className="flex items-center space-x-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={allowedRoles.includes(role.id)}
                    onChange={() => handleRoleToggle(role.id)}
                    className="rounded border-input text-primary focus:ring-ring"
                  />
                  <span>{role.name}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              {t("documents.folderDescriptionLabel", "Descrição")}
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-lg border border-input bg-card px-3 py-2 text-sm text-foreground focus:outline-hidden focus:ring-2 focus:ring-ring"
              placeholder={t("documents.folderDescriptionPlaceholder", "Finalidade da pasta...")}
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-border">
            <Button type="button" variant="outline" onClick={onClose}>
              {t("common.cancel", "Cancelar")}
            </Button>
            <Button type="submit" disabled={isLoading} className="bg-primary hover:bg-primary/90 text-primary-foreground">
              <span>{isEditMode ? t("common.save", "Salvar") : t("documents.createFolder", "Criar Pasta")}</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
