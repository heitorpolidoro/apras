import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Trash2, Plus, Check, X, AlertTriangle } from "lucide-react";
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from "../hooks/useCategories";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { AlertModal } from "../../../components/ui/alert-modal";
import type { CategoryRead } from "../types";
import { useAuth, UserRole } from "../../user-administration/context/AuthContext";

interface ApiError extends Error {
  response?: { data?: { detail?: string } };
}

const PRESET_COLORS = [
  "#6366f1", "#8b5cf6", "#ec4899", "#ef4444",
  "#f97316", "#eab308", "#22c55e", "#14b8a6",
  "#3b82f6", "#06b6d4", "#64748b", "#808080",
];

interface EditState {
  id: string;
  name: string;
  color: string;
}

const ColorPicker: React.FC<{
  value: string;
  onChange: (color: string) => void;
}> = ({ value, onChange }) => (
  <div className="flex flex-wrap gap-1.5">
    {PRESET_COLORS.map((c) => (
      <button
        key={c}
        type="button"
        className="size-6 rounded-full border-2 transition-transform hover:scale-110"
        style={{
          backgroundColor: c,
          borderColor: value === c ? "white" : "transparent",
          outline: value === c ? `2px solid ${c}` : "none",
          outlineOffset: "1px",
        }}
        onClick={() => onChange(c)}
        aria-label={c}
      />
    ))}
    <input
      type="color"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="size-6 rounded-full cursor-pointer border-0 p-0 bg-transparent"
      title="Custom color"
    />
  </div>
);

const CategoriesPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: categories, isLoading } = useCategories();
  const createMutation = useCreateCategory();
  const updateMutation = useUpdateCategory();
  const deleteMutation = useDeleteCategory();

  const { user } = useAuth();
  const canWrite = user?.role === UserRole.ADMINISTRATOR || user?.role === UserRole.DIRECTOR;

  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#6366f1");
  const [showForm, setShowForm] = useState(false);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setError(null);
    createMutation.mutate(
      { name: newName.trim(), color: newColor },
      {
        onSuccess: () => {
          setNewName("");
          setNewColor("#6366f1");
          setShowForm(false);
        },
        onError: (err: ApiError) => {
          setError(err.response?.data?.detail || t("categories.errorCreating"));
        },
      },
    );
  };

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editState?.name.trim()) return;
    setError(null);
    updateMutation.mutate(
      { id: editState.id, data: { name: editState.name.trim(), color: editState.color } },
      {
        onSuccess: () => setEditState(null),
        onError: (err: ApiError) => {
          setError(err.response?.data?.detail || t("categories.errorUpdating"));
        },
      },
    );
  };

  const handleDelete = (id: string) => {
    setError(null);
    deleteMutation.mutate(id, {
      onSuccess: () => setConfirmDeleteId(null),
      onError: (err: ApiError) => {
        setError(err.response?.data?.detail || t("categories.errorDeleting"));
        setConfirmDeleteId(null);
      },
    });
  };

  const startEdit = (cat: CategoryRead) => {
    setEditState({ id: cat.id, name: cat.name, color: cat.color });
    setConfirmDeleteId(null);
    setShowForm(false);
  };

  const renderList = () => {
    if (isLoading) {
      return <p className="text-sm text-muted-foreground">{t("categories.loading")}</p>;
    }
    if (!categories?.length) {
      return <p className="text-sm text-muted-foreground">{t("categories.empty")}</p>;
    }
    return (
      <ul className="flex flex-col gap-2">
        {categories.map((cat) => {
          if (editState?.id === cat.id && canWrite) {
            const edit = editState;
            return (
              <li key={cat.id} className="rounded-lg border bg-card p-4">
                <form onSubmit={handleUpdate} className="flex flex-col gap-3">
                  <Input
                    value={edit.name}
                    onChange={(e) =>
                      setEditState({ ...edit, name: e.target.value })
                    }
                    disabled={updateMutation.isPending}
                  />
                  <ColorPicker
                    value={edit.color}
                    onChange={(c) => setEditState({ ...edit, color: c })}
                  />
                  <div className="flex gap-2 justify-end">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditState(null)}
                    >
                      <X className="size-4" />
                    </Button>
                    <Button
                      type="submit"
                      size="sm"
                      disabled={!edit.name.trim() || updateMutation.isPending}
                    >
                      <Check className="size-4" />
                    </Button>
                  </div>
                </form>
              </li>
            );
          }

          if (confirmDeleteId === cat.id && canWrite) {
            return (
              <li
                key={cat.id}
                className="flex items-center justify-between rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3"
              >
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertTriangle className="size-4 shrink-0" />
                  <span>{t("categories.confirmDelete", { name: cat.name })}</span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmDeleteId(null)}
                  >
                    <X className="size-4" />
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDelete(cat.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Check className="size-4" />
                  </Button>
                </div>
              </li>
            );
          }

          return (
            <li
              key={cat.id}
              className="flex items-center justify-between rounded-lg border bg-card px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <span
                  className="size-4 rounded-full shrink-0"
                  style={{ backgroundColor: cat.color }}
                />
                <span className="text-sm font-medium">{cat.name}</span>
              </div>
              {canWrite && (
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => startEdit(cat)}
                    className="px-2"
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmDeleteId(cat.id)}
                    className="px-2 text-destructive hover:text-destructive"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">
          {t("categories.title")}
        </h1>
        {canWrite && !showForm && (
          <Button onClick={() => { setShowForm(true); setEditState(null); }}>
            <Plus className="size-4" />
            {t("categories.newCategory")}
          </Button>
        )}
      </div>

      <AlertModal
        open={!!error}
        onClose={() => setError(null)}
        variant="destructive"
        title="Erro"
        message={error ?? ""}
      />

      {canWrite && showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-6 p-4 rounded-lg border bg-card flex flex-col gap-3"
        >
          <p className="text-sm font-semibold text-foreground">
            {t("categories.newCategory")}
          </p>
          <Input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t("categories.namePlaceholder")}
            disabled={createMutation.isPending}
          />
          <ColorPicker value={newColor} onChange={setNewColor} />
          <div className="flex gap-2 justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowForm(false)}
            >
              {t("categories.cancel")}
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!newName.trim() || createMutation.isPending}
            >
              {t("categories.save")}
            </Button>
          </div>
        </form>
      )}

      {renderList()}
    </div>
  );
};

export default CategoriesPage;
