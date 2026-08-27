import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import apiClient from "../../../api/client";
import { useAuth } from "../context/AuthContext";
import type { User } from "../../../types/auth";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { AlertModal } from "../../../components/ui/alert-modal";

const ContactInfoDashboard: React.FC = () => {
  const [actionError, setActionError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editPhone, setEditPhone] = useState("");
  const [editAddress, setEditAddress] = useState("");
  const queryClient = useQueryClient();
  const { logout } = useAuth();
  const { t } = useTranslation();

  const {
    data: users,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const response = await apiClient.get<User[]>("/users/");
      return response.data;
    },
  });

  const updateContactInfoMutation = useMutation({
    mutationFn: async ({
      userId,
      data,
    }: {
      userId: string;
      data: { phone?: string | null; address?: string | null };
    }) => {
      const response = await apiClient.patch<User>(
        `/users/${userId}/contact-info`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setActionError(null);
      setEditingUser(null);
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setActionError(err.response?.data?.detail || t("contactInfo.errorUpdating"));
    },
  });

  const openEditModal = (user: User) => {
    setEditingUser(user);
    setEditPhone(user.phone ?? "");
    setEditAddress(user.address ?? "");
  };

  const handleSaveEdit = () => {
    /* v8 ignore next */
    if (!editingUser) return;
    updateContactInfoMutation.mutate({
      userId: editingUser.id,
      data: { phone: editPhone, address: editAddress },
    });
  };

  if (isLoading)
    return (
      <div className="p-8 text-muted-foreground">
        {t("contactInfo.loadingUsers")}
      </div>
    );
  if (error)
    return (
      <div className="p-8 text-destructive">
        {t("contactInfo.errorLoadingUsers")}
      </div>
    );

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">
          {t("contactInfo.title")}
        </h1>
        <div className="flex gap-3">
          <Button variant="outline" asChild>
            <Link to="/dashboard">{t("contactInfo.backToDashboard")}</Link>
          </Button>
          <Button variant="ghost" onClick={logout}>
            {t("common.logout")}
          </Button>
        </div>
      </div>

      <AlertModal
        open={!!actionError}
        onClose={() => setActionError(null)}
        variant="destructive"
        title="Erro"
        message={actionError ?? ""}
      />

      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40">
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("contactInfo.colName")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground hidden md:table-cell">
                  {t("contactInfo.colEmail")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("contactInfo.colPhone")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("contactInfo.colAddress")}
                </th>
                <th className="text-right px-4 py-3 font-semibold text-muted-foreground">
                  {t("contactInfo.colActions")}
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
                  <td className="px-4 py-3 text-muted-foreground hidden md:table-cell">
                    {user.email}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {user.phone || "—"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {user.address || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 justify-end flex-wrap">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openEditModal(user)}
                      >
                        {t("contactInfo.edit")}
                      </Button>
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

      {/* Edit Contact Info Modal */}
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
              {t("contactInfo.editTitle")}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground block mb-1">
                  {t("contactInfo.editPhone")}
                </label>
                <Input
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground block mb-1">
                  {t("contactInfo.editAddress")}
                </label>
                <Input
                  value={editAddress}
                  onChange={(e) => setEditAddress(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <Button variant="outline" onClick={() => setEditingUser(null)}>
                {t("contactInfo.cancel")}
              </Button>
              <Button
                onClick={handleSaveEdit}
                disabled={updateContactInfoMutation.isPending}
              >
                {t("contactInfo.save")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContactInfoDashboard;
