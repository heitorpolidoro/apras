import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { useUsers } from "../../../hooks/useUsers";
import {
  deriveAllowedMenus,
  useCreateUserType,
  useDeleteUserType,
} from "../hooks/useUserTypeMutations";
import { friendlyPermissionError } from "../utils/permissionErrors";
import type { UserType } from "../../../types/auth";

/**
 * `/admin/groups` — the group list (APRAS-48 §6.1, ER-1).
 *
 * Role-linked groups ("grupos de sistema") are shown, badged and **not**
 * deletable, mirroring the backend's 403; their permissions stay editable,
 * which is how an operator restores baseline-by-role access under the new
 * model, and is the main reason the rows are listed at all (§6.2).
 *
 * Clone is `POST /user-types/` with the source's bundle and an editable
 * pre-filled name — no new endpoint, and `assert_can_grant` applies to it
 * exactly as to a hand-built group.
 */
const GroupsAdminPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: groups, isPending } = useUserTypes();
  const { data: users } = useUsers();
  const createGroup = useCreateUserType();
  const deleteGroup = useDeleteUserType();

  const [name, setName] = useState("");
  const [draftPermissions, setDraftPermissions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const memberCount = (groupId: string) =>
    (users ?? []).filter((user) =>
      user.user_types?.some((userType) => userType.id === groupId),
    ).length;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setError(null);
    createGroup.mutate(
      {
        name: trimmed,
        permissions: draftPermissions,
        allowed_menus: deriveAllowedMenus(draftPermissions),
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

  const startClone = (group: UserType) => {
    setName(`${group.name}${t("groups.cloneSuffix")}`);
    // The clone carries no `role` (the field is read-only in every write
    // schema), so it is an ordinary group.
    setDraftPermissions(group.permissions ?? []);
    setError(null);
  };

  const remove = (group: UserType) => {
    // Deleting a group revokes, from every member at once, every permission it
    // grants — so it is confirmed, exactly as the inline user-type card this
    // screen replaces confirmed `admin.confirmDeleteType`.
    if (!window.confirm(t("groups.confirmDelete"))) return;
    setError(null);
    deleteGroup.mutate(group.id, {
      onError: (err) => setError(friendlyPermissionError(err, t)),
    });
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-foreground">
          {t("groups.title")}
        </h1>
        <Button variant="outline" asChild>
          <Link to="/admin/users">{t("admin.title")}</Link>
        </Button>
      </div>
      <p className="text-sm text-muted-foreground mb-6">
        {t("groups.subtitle")}
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
          aria-label={t("groups.namePlaceholder")}
          placeholder={t("groups.namePlaceholder")}
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="h-9 text-sm w-64"
        />
        {draftPermissions.length > 0 && (
          <span className="text-xs text-muted-foreground">
            {t("permissions.selectedCount", { count: draftPermissions.length })}
          </span>
        )}
        <Button type="submit" disabled={!name.trim() || createGroup.isPending}>
          {t("groups.create")}
        </Button>
      </form>

      {isPending && (
        <p className="text-sm text-muted-foreground">{t("groups.loading")}</p>
      )}
      {!isPending && groups?.length === 0 && (
        <p className="text-sm text-muted-foreground">{t("groups.empty")}</p>
      )}

      {!!groups?.length && (
        <div className="rounded-xl border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40">
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("groups.colName")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("groups.colPermissions")}
                </th>
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">
                  {t("groups.colMembers")}
                </th>
                <th className="text-right px-4 py-3 font-semibold text-muted-foreground">
                  {t("groups.colActions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-foreground">
                        {group.name}
                      </span>
                      {group.role && (
                        <Badge
                          variant="outline"
                          title={t("groups.roleLinkedHint")}
                        >
                          {t("groups.roleLinkedBadge")}
                        </Badge>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {group.permissions?.length ?? 0}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {memberCount(group.id)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 justify-end flex-wrap">
                      <Button size="sm" variant="outline" asChild>
                        <Link to={`/admin/groups/${group.id}`}>
                          {t("groups.edit")}
                        </Link>
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => startClone(group)}
                        aria-label={`${t("groups.clone")} ${group.name}`}
                      >
                        {t("groups.clone")}
                      </Button>
                      {/* No delete control for role-linked groups: the
                          backend answers 403 for them, and offering a button
                          that cannot work is not a gate, it is a trap. */}
                      {!group.role && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => remove(group)}
                          disabled={deleteGroup.isPending}
                          aria-label={`${t("groups.delete")} ${group.name}`}
                        >
                          {t("groups.delete")}
                        </Button>
                      )}
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

export default GroupsAdminPage;
