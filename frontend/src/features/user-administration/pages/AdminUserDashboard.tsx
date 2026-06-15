import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "../../../api/client";
import { UserRole, useAuth } from "../context/AuthContext";
import type { User, UserType } from "../../../types/auth";
import { Link } from "react-router-dom";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Select } from "../../../components/ui/select";
import { Alert, AlertDescription } from "../../../components/ui/alert";

const AdminUserDashboard: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<
    "all" | "active" | "inactive"
  >("all");
  const [actionError, setActionError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editFullName, setEditFullName] = useState("");
  const [editTypeId, setEditTypeId] = useState<string>("");
  const [newTypeName, setNewTypeName] = useState("");
  const queryClient = useQueryClient();
  const { user: currentUser, logout } = useAuth();
  const { t } = useTranslation();

  const {
    data: users,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["users", statusFilter],
    queryFn: async () => {
      const params: Record<string, boolean> = {};
      if (statusFilter === "active") params.is_active = true;
      if (statusFilter === "inactive") params.is_active = false;
      const response = await apiClient.get<User[]>("/users/", { params });
      return response.data;
    },
  });

  const { data: userTypes } = useQuery({
    queryKey: ["user-types"],
    queryFn: async () => {
      const response = await apiClient.get<UserType[]>("/user-types/");
      return response.data;
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: async ({
      userId,
      data,
    }: {
      userId: string;
      data: Partial<User> & { type_id?: string | null };
    }) => {
      const response = await apiClient.patch<User>(`/users/${userId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setActionError(null);
      setEditingUser(null);
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setActionError(
        err.response?.data?.detail || t("admin.errorUpdatingUser"),
      );
    },
  });

  const createTypeMutation = useMutation({
    mutationFn: async (name: string) => {
      const response = await apiClient.post<UserType>("/user-types/", { name });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-types"] });
      setNewTypeName("");
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setActionError(
        err.response?.data?.detail || t("admin.errorCreatingType"),
      );
    },
  });

  const deleteTypeMutation = useMutation({
    mutationFn: async (typeId: string) => {
      await apiClient.delete(`/user-types/${typeId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-types"] });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setActionError(
        err.response?.data?.detail || t("admin.errorDeletingType"),
      );
    },
  });

  const handleToggleActive = (user: User) => {
    if (user.id === currentUser?.id) {
      setActionError(t("admin.cannotDeactivateSelf"));
      return;
    }
    updateUserMutation.mutate({
      userId: user.id,
      data: { is_active: !user.is_active },
    });
  };

  const handleRoleSelect = (user: User, newRole: UserRole) => {
    if (user.id === currentUser?.id) {
      setActionError(t("admin.cannotChangeOwnRole"));
      return;
    }
    updateUserMutation.mutate({ userId: user.id, data: { role: newRole } });
  };

  const openEditModal = (user: User) => {
    setEditingUser(user);
    setEditFullName(user.full_name);
    setEditTypeId(user.type?.id ?? "");
  };

  const handleSaveEdit = () => {
    /* v8 ignore next */
    if (!editingUser) return;
    updateUserMutation.mutate({
      userId: editingUser.id,
      data: {
        full_name: editFullName || undefined,
        type_id: editTypeId || null,
      },
    });
  };

  const handleAddType = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTypeName.trim()) return;
    createTypeMutation.mutate(newTypeName.trim());
  };

  if (isLoading)
    return (
      <div className="p-8 text-muted-foreground">{t("admin.loadingUsers")}</div>
    );
  if (error)
    return (
      <div className="p-8 text-destructive">{t("admin.errorLoadingUsers")}</div>
    );

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">
          {t("admin.title")}
        </h1>
        <div className="flex gap-3">
          <Button variant="outline" asChild>
            <Link to="/dashboard">{t("admin.backToDashboard")}</Link>
          </Button>
          <Button variant="ghost" onClick={logout}>
            {t("common.logout")}
          </Button>
        </div>
      </div>

      {actionError && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription className="flex items-center justify-between">
            {actionError}
            <button
              onClick={() => setActionError(null)}
              className="ml-4 text-xs hover:underline"
              aria-label={t("common.close")}
            >
              {t("common.close").toLowerCase()}
            </button>
          </AlertDescription>
        </Alert>
      )}

      {/* User Types Section */}
      <div className="rounded-xl border bg-card p-4 mb-6">
        <h2 className="text-sm font-semibold text-foreground mb-3">
          {t("admin.userTypes")}
        </h2>
        <div className="flex flex-wrap gap-2 mb-3">
          {userTypes?.length === 0 && (
            <span className="text-sm text-muted-foreground">
              {t("admin.noTypesYet")}
            </span>
          )}
          {userTypes?.map((ut) => (
            <div key={ut.id} className="flex items-center gap-1">
              <Badge variant="secondary">{ut.name}</Badge>
              <button
                onClick={() => {
                  if (window.confirm(t("admin.confirmDeleteType"))) {
                    deleteTypeMutation.mutate(ut.id);
                  }
                }}
                className="text-xs text-muted-foreground hover:text-destructive transition-colors ml-1"
                aria-label={`delete ${ut.name}`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <form onSubmit={handleAddType} className="flex gap-2 items-center">
          <Input
            value={newTypeName}
            onChange={(e) => setNewTypeName(e.target.value)}
            placeholder={t("admin.newTypeName")}
            className="h-8 text-sm w-48"
          />
          <Button
            type="submit"
            size="sm"
            disabled={!newTypeName.trim() || createTypeMutation.isPending}
          >
            {t("admin.addType")}
          </Button>
        </form>
      </div>

      <div className="flex items-center gap-3 mb-5">
        <label
          htmlFor="status-filter"
          className="text-sm font-medium text-muted-foreground"
        >
          {t("admin.filterByStatus")}
        </label>
        <Select
          id="status-filter"
          value={statusFilter}
          onChange={(e) =>
            setStatusFilter(e.target.value as "all" | "active" | "inactive")
          }
          className="w-44"
        >
          <option value="all">{t("admin.filterAll")}</option>
          <option value="active">{t("admin.filterActive")}</option>
          <option value="inactive">{t("admin.filterPending")}</option>
        </Select>
      </div>

      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40">
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("admin.colName")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("admin.colUsername")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground hidden md:table-cell">
                  {t("admin.colEmail")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("admin.colRole")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("admin.colType")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("admin.colStatus")}
                </th>
                <th className="text-right px-4 py-3 font-semibold text-muted-foreground">
                  {t("admin.colActions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {users?.map((user) => (
                <tr
                  key={user.id}
                  className="border-b last:border-0 hover:bg-muted/20 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-foreground">
                    {user.full_name}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {user.username}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground hidden md:table-cell">
                    {user.email}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="secondary">{user.role}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    {user.type ? (
                      <Badge variant="secondary">{user.type.name}</Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={user.is_active ? "active" : "inactive"}>
                      {user.is_active
                        ? t("admin.statusActive")
                        : t("admin.statusInactive")}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 justify-end flex-wrap">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openEditModal(user)}
                      >
                        {t("admin.edit")}
                      </Button>
                      <Button
                        size="sm"
                        variant={user.is_active ? "destructive" : "success"}
                        onClick={() => handleToggleActive(user)}
                      >
                        {user.is_active
                          ? t("admin.deactivate")
                          : t("admin.approve")}
                      </Button>
                      <Select
                        aria-label={t("admin.colRole")}
                        value={user.role}
                        onChange={(e) => handleRoleSelect(user, e.target.value as UserRole)}
                        className="h-8 text-sm w-36"
                        disabled={user.id === currentUser?.id || updateUserMutation.isPending}
                      >
                        <option value={UserRole.ADMINISTRATOR}>{t("roles.ADMINISTRATOR")}</option>
                        <option value={UserRole.DIRECTOR}>{t("roles.DIRECTOR")}</option>
                        <option value={UserRole.MANAGER}>{t("roles.MANAGER")}</option>
                        <option value={UserRole.GUEST}>{t("roles.GUEST")}</option>
                      </Select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Version footer */}
      <p className="mt-6 text-xs text-muted-foreground text-right">
        {import.meta.env.VITE_APP_VERSION ?? "dev"}
      </p>

      {/* Edit User Modal */}
      {editingUser && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) setEditingUser(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") setEditingUser(null);
          }}
        >
          <div className="bg-card border rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h2 className="text-lg font-semibold text-foreground mb-4">
              {t("admin.editUser")}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground block mb-1">
                  {t("admin.editFullName")}
                </label>
                <Input
                  value={editFullName}
                  onChange={(e) => setEditFullName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground block mb-1">
                  {t("admin.editType")}
                </label>
                <Select
                  value={editTypeId}
                  onChange={(e) => setEditTypeId(e.target.value)}
                  className="w-full"
                >
                  <option value="">{t("admin.noType")}</option>
                  {userTypes?.map((ut) => (
                    <option key={ut.id} value={ut.id}>
                      {ut.name}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <Button variant="outline" onClick={() => setEditingUser(null)}>
                {t("admin.cancel")}
              </Button>
              <Button
                onClick={handleSaveEdit}
                disabled={updateUserMutation.isPending}
              >
                {t("admin.save")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUserDashboard;
