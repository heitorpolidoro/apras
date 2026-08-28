import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Trash2, Plus, Check, X, AlertTriangle } from "lucide-react";
import {
  useReservableSpaces,
  useCreateReservableSpace,
  useUpdateReservableSpace,
  useDeactivateReservableSpace,
} from "../hooks/useReservations";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { AlertModal } from "../../../components/ui/alert-modal";
import type { ReservableSpaceRead } from "../../../types/reservation";
import { UserRole } from "../../../types/auth";
import { useEffectiveIdentity } from "../../user-administration/context/useEffectiveIdentity";

interface ApiError extends Error {
  response?: { data?: { detail?: string } };
}

interface EditState {
  id: string;
  name: string;
  description: string;
  capacity: string;
  requires_approval: boolean;
}

const ReservableSpacesPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: spaces, isLoading } = useReservableSpaces();
  const createMutation = useCreateReservableSpace();
  const updateMutation = useUpdateReservableSpace();
  const deactivateMutation = useDeactivateReservableSpace();

  const { role } = useEffectiveIdentity();
  const canWrite = role === UserRole.ADMINISTRATOR || role === UserRole.DIRECTOR;

  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newCapacity, setNewCapacity] = useState("");
  const [newRequiresApproval, setNewRequiresApproval] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resetCreateForm = () => {
    setNewName("");
    setNewDescription("");
    setNewCapacity("");
    setNewRequiresApproval(false);
    setShowForm(false);
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setError(null);
    createMutation.mutate(
      {
        name: newName.trim(),
        description: newDescription.trim() || null,
        capacity: newCapacity ? Number(newCapacity) : null,
        requires_approval: newRequiresApproval,
      },
      {
        onSuccess: () => resetCreateForm(),
        onError: (err: ApiError) => {
          setError(err.response?.data?.detail || t("reservations.spaces.errorCreating"));
        },
      },
    );
  };

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editState?.name.trim()) return;
    setError(null);
    updateMutation.mutate(
      {
        id: editState.id,
        data: {
          name: editState.name.trim(),
          description: editState.description.trim() || null,
          capacity: editState.capacity ? Number(editState.capacity) : null,
          requires_approval: editState.requires_approval,
        },
      },
      {
        onSuccess: () => setEditState(null),
        onError: (err: ApiError) => {
          setError(err.response?.data?.detail || t("reservations.spaces.errorUpdating"));
        },
      },
    );
  };

  const handleDelete = (id: string) => {
    setError(null);
    deactivateMutation.mutate(id, {
      onSuccess: () => setConfirmDeleteId(null),
      onError: (err: ApiError) => {
        setError(err.response?.data?.detail || t("reservations.spaces.errorDeleting"));
        setConfirmDeleteId(null);
      },
    });
  };

  const startEdit = (space: ReservableSpaceRead) => {
    setEditState({
      id: space.id,
      name: space.name,
      description: space.description ?? "",
      capacity: space.capacity != null ? String(space.capacity) : "",
      requires_approval: space.requires_approval,
    });
    setConfirmDeleteId(null);
    setShowForm(false);
  };

  const renderList = () => {
    if (isLoading) {
      return (
        <p className="text-sm text-muted-foreground">
          {t("reservations.spaces.loading")}
        </p>
      );
    }
    if (!spaces?.length) {
      return (
        <p className="text-sm text-muted-foreground">
          {t("reservations.spaces.empty")}
        </p>
      );
    }
    return (
      <ul className="flex flex-col gap-2">
        {spaces.map((space) => {
          if (editState?.id === space.id && canWrite) {
            const edit = editState;
            return (
              <li key={space.id} className="rounded-lg border bg-card p-4">
                <form onSubmit={handleUpdate} className="flex flex-col gap-3">
                  <Input
                    value={edit.name}
                    onChange={(e) => setEditState({ ...edit, name: e.target.value })}
                    disabled={updateMutation.isPending}
                  />
                  <textarea
                    value={edit.description}
                    onChange={(e) =>
                      setEditState({ ...edit, description: e.target.value })
                    }
                    placeholder={t("reservations.spaces.descriptionPlaceholder")}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    rows={2}
                  />
                  <Input
                    type="number"
                    min={1}
                    value={edit.capacity}
                    onChange={(e) =>
                      setEditState({ ...edit, capacity: e.target.value })
                    }
                    placeholder={t("reservations.spaces.capacityPlaceholder")}
                  />
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={edit.requires_approval}
                      onChange={(e) =>
                        setEditState({
                          ...edit,
                          requires_approval: e.target.checked,
                        })
                      }
                    />
                    {t("reservations.spaces.requiresApproval")}
                  </label>
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

          if (confirmDeleteId === space.id && canWrite) {
            return (
              <li
                key={space.id}
                className="flex items-center justify-between rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3"
              >
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertTriangle className="size-4 shrink-0" />
                  <span>
                    {t("reservations.spaces.confirmDelete", { name: space.name })}
                  </span>
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
                    onClick={() => handleDelete(space.id)}
                    disabled={deactivateMutation.isPending}
                  >
                    <Check className="size-4" />
                  </Button>
                </div>
              </li>
            );
          }

          return (
            <li
              key={space.id}
              className="flex items-center justify-between rounded-lg border bg-card px-4 py-3"
            >
              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-medium">{space.name}</span>
                {space.description && (
                  <span className="text-xs text-muted-foreground">
                    {space.description}
                  </span>
                )}
                {space.requires_approval && (
                  <span className="text-xs text-amber-600">
                    {t("reservations.spaces.requiresApproval")}
                  </span>
                )}
              </div>
              {canWrite && (
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => startEdit(space)}
                    className="px-2"
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmDeleteId(space.id)}
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
          {t("reservations.spaces.title")}
        </h1>
        {canWrite && !showForm && (
          <Button
            onClick={() => {
              setShowForm(true);
              setEditState(null);
            }}
          >
            <Plus className="size-4" />
            {t("reservations.spaces.newSpace")}
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
            {t("reservations.spaces.newSpace")}
          </p>
          <Input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t("reservations.spaces.namePlaceholder")}
            disabled={createMutation.isPending}
          />
          <textarea
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            placeholder={t("reservations.spaces.descriptionPlaceholder")}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            rows={2}
          />
          <Input
            type="number"
            min={1}
            value={newCapacity}
            onChange={(e) => setNewCapacity(e.target.value)}
            placeholder={t("reservations.spaces.capacityPlaceholder")}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={newRequiresApproval}
              onChange={(e) => setNewRequiresApproval(e.target.checked)}
            />
            {t("reservations.spaces.requiresApproval")}
          </label>
          <div className="flex gap-2 justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => resetCreateForm()}
            >
              {t("reservations.spaces.cancel")}
            </Button>
            <Button type="submit" size="sm" disabled={!newName.trim() || createMutation.isPending}>
              {t("reservations.spaces.save")}
            </Button>
          </div>
        </form>
      )}

      {renderList()}
    </div>
  );
};

export default ReservableSpacesPage;
