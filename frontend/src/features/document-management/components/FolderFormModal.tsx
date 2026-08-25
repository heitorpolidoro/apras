import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { FolderPlus, X } from "lucide-react";
import type { DocumentFolderTree } from "../../../types/document";
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";

interface FolderFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  folders: DocumentFolderTree[];
  initialData?: DocumentFolderTree | null;
  initialParentId?: string | null;
  onSubmit: (data: any) => Promise<void>;
  isLoading?: boolean;
}

const ALL_ROLES = ["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"];

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
  const [allowedRoles, setAllowedRoles] = useState<string[]>(ALL_ROLES);

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
      setAllowedRoles(initialData.allowed_roles || ALL_ROLES);
    } else {
      setName("");
      setDescription("");
      setParentId(initialParentId || "");
      setAllowedRoles(ALL_ROLES);
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
      allowed_roles: allowedRoles,
    });
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center space-x-2">
            <FolderPlus className="h-5 w-5 text-indigo-500" />
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              {isEditMode
                ? t("documents.editFolderTitle", "Editar Pasta")
                : t("documents.newFolderTitle", "Criar Nova Pasta")}
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
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
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
              {ALL_ROLES.map((role) => (
                <label
                  key={role}
                  className="flex items-center space-x-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={allowedRoles.includes(role)}
                    onChange={() => handleRoleToggle(role)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>{role}</span>
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
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              placeholder={t("documents.folderDescriptionPlaceholder", "Finalidade da pasta...")}
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-800">
            <Button type="button" variant="outline" onClick={onClose}>
              {t("common.cancel", "Cancelar")}
            </Button>
            <Button type="submit" disabled={isLoading} className="bg-indigo-600 hover:bg-indigo-700 text-white">
              <span>{isEditMode ? t("common.save", "Salvar") : t("documents.createFolder", "Criar Pasta")}</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
