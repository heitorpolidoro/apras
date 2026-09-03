import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { useRoles } from "../../../hooks/useRoles";
import { useUsers } from "../../../hooks/useUsers";
import { useCreateRole, useDeleteRole } from "../hooks/useRoleMutations";
import { friendlyPermissionError } from "../utils/permissionErrors";
import type { Role } from "../../../types/auth";

/**
 * `/admin/roles` — the role list (APRAS-48 §6.1, ER-1).
 *
 * Role-linked roles ("papéis de sistema") are shown, badged and **not**
 * deletable, mirroring the backend's 403; their permissions stay editable,
 * which is how an operator restores baseline-by-role access under the new
 * model, and is the main reason the rows are listed at all (§6.2).
 *
 * Clone is `POST /roles/` with the source's bundle and an editable
 * pre-filled name — no new endpoint, and `assert_can_grant` applies to it
 * exactly as to a hand-built role.
 */
const RolesAdminPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: roles, isPending } = useRoles();
  const { data: users } = useUsers();
  const createRole = useCreateRole();
  const deleteRole = useDeleteRole();

  const [name, setName] = useState("");
  const [draftPermissions, setDraftPermissions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const memberCount = (roleId: string) =>
    (users ?? []).filter((user) =>
      user.roles?.some((role) => role.id === roleId),
    ).length;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setError(null);
    createRole.mutate(
      {
        name: trimmed,
        permissions: draftPermissions,
      },
      {
        onSuccess: () => {
          setName("");
          setDraftPermissions([]);
        },
        onError: (err) => setError(friendlyPermissionError(err, t)),
      },
    );
  };

  const startClone = (role: Role) => {
    setName(`${role.name}${t("roles.cloneSuffix")}`);
    // The clone carries no `role` (the field is read-only in every write
    // schema), so it is an ordinary role.
    setDraftPermissions(role.permissions ?? []);
    setError(null);
  };

  const remove = (role: Role) => {
    // Deleting a role revokes, from every member at once, every permission it
    // grants — so it is confirmed, exactly as the inline user-type card this
    // screen replaces confirmed `admin.confirmDeleteType`.
    if (!window.confirm(t("roles.confirmDelete"))) return;
    setError(null);
    deleteRole.mutate(role.id, {
      onError: (err) => setError(friendlyPermissionError(err, t)),
    });
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-foreground">
          {t("roles.title")}
        </h1>
        <Button variant="outline" asChild>
          <Link to="/admin/users">{t("admin.title")}</Link>
        </Button>
      </div>
      <p className="text-sm text-muted-foreground mb-6">
        {t("roles.subtitle")}
      </p>

      {error && (
        <p role="alert" className="text-sm text-destructive mb-4">
          {error}
        </p>
      )}

      <form
        onSubmit={submit}
        className="flex flex-wrap gap-2 items-center rounded-xl border bg-card p-4 mb-6"
      >
        <Input
          aria-label={t("roles.namePlaceholder")}
          placeholder={t("roles.namePlaceholder")}
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="h-9 text-sm w-64"
        />
        {draftPermissions.length > 0 && (
          <span className="text-xs text-muted-foreground">
            {t("permissions.selectedCount", { count: draftPermissions.length })}
          </span>
        )}
        <Button type="submit" disabled={!name.trim() || createRole.isPending}>
          {t("roles.create")}
        </Button>
      </form>

      {isPending && (
        <p className="text-sm text-muted-foreground">{t("roles.loading")}</p>
      )}
      {!isPending && roles?.length === 0 && (
        <p className="text-sm text-muted-foreground">{t("roles.empty")}</p>
      )}

      {!!roles?.length && (
        <div className="rounded-xl border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40">
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("roles.colName")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("roles.colPermissions")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("roles.colMembers")}
                </th>
                <th className="text-right px-4 py-3 font-semibold text-muted-foreground">
                  {t("roles.colActions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr key={role.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-foreground">
                        {role.name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {role.permissions?.length ?? 0}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {memberCount(role.id)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 justify-end flex-wrap">
                      <Button size="sm" variant="outline" asChild>
                        <Link to={`/admin/roles/${role.id}`}>
                          {t("roles.edit")}
                        </Link>
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => startClone(role)}
                        aria-label={`${t("roles.clone")} ${role.name}`}
                      >
                        {t("roles.clone")}
                      </Button>
                      {/* IAM F5 (APRAS-49 §13): every row is deletable now.
                          There are no system roles, and deleting
                          `Diretor (papel)` strips every director — the
                          operator's prerogative. */}
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => remove(role)}
                        disabled={deleteRole.isPending}
                        aria-label={`${t("roles.delete")} ${role.name}`}
                      >
                        {t("roles.delete")}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default RolesAdminPage;
