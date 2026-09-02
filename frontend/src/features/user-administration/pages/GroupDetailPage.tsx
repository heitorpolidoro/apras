import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { usePermissionCatalogue } from "../../../hooks/usePermissionQueries";
import { usePermissionSet } from "../access/useCanAccess";
import PermissionMatrix from "../components/PermissionMatrix";
import GroupMembersPanel from "../components/GroupMembersPanel";
import {
  deriveAllowedMenus,
  useUpdateUserType,
} from "../hooks/useUserTypeMutations";
import { friendlyPermissionError } from "../utils/permissionErrors";
import type { UserType } from "../../../types/auth";

/**
 * The editor proper, mounted under `key={group.id}`.
 *
 * Splitting it out is what lets the draft state be *initialised* from the
 * stored group instead of synchronised into it by an effect: React remounts
 * this component when the id changes, and a refetch after a save (same id,
 * new object) deliberately does **not** clobber what the operator is editing.
 */
const GroupEditor: React.FC<{ group: UserType }> = ({ group }) => {
  const { t } = useTranslation();
  const { data: catalogue, isPending: cataloguePending } =
    usePermissionCatalogue();
  const mySet = usePermissionSet();
  const updateGroup = useUpdateUserType();

  const [name, setName] = useState(group.name);
  const [selected, setSelected] = useState<string[]>(group.permissions ?? []);
  const [error, setError] = useState<string | null>(null);

  const isRoleLinked = Boolean(group.role);

  const save = () => {
    setError(null);
    updateGroup.mutate(
      {
        groupId: group.id,
        payload: {
          // A role-linked group saves its stored name unchanged.
          name: isRoleLinked ? group.name : name,
          // The disabled-but-checked boxes are in `selected` and are resent
          // verbatim, so editing a name never strips a permission the author
          // cannot grant (§6.3).
          permissions: selected,
          // Derived **and unioned with the stored value**, never replaced.
          allowed_menus: deriveAllowedMenus(selected, group.allowed_menus),
        },
      },
      { onError: (err) => setError(friendlyPermissionError(err, t)) },
    );
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-2xl font-bold text-foreground">{group.name}</h1>
          {isRoleLinked && (
            <Badge variant="outline" title={t("groups.roleLinkedHint")}>
              {t("groups.roleLinkedBadge")}
            </Badge>
          )}
        </div>
        <Button variant="outline" asChild>
          <Link to="/admin/groups">{t("groups.back")}</Link>
        </Button>
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <div>
        <label
          htmlFor="group-name"
          className="text-sm font-medium text-muted-foreground block mb-1"
        >
          {t("groups.name")}
        </label>
        <Input
          id="group-name"
          value={name}
          readOnly={isRoleLinked}
          title={isRoleLinked ? t("groups.roleLinkedHint") : undefined}
          onChange={(event) => setName(event.target.value)}
          className="w-72"
        />
      </div>

      {cataloguePending && (
        <p className="text-sm text-muted-foreground">
          {t("permissions.loading")}
        </p>
      )}
      {!!catalogue && (
        <PermissionMatrix
          descriptors={catalogue}
          selected={selected}
          onChange={setSelected}
          mySet={mySet}
        />
      )}

      <div className="flex gap-3 justify-end">
        <Button variant="outline" asChild>
          <Link to="/admin/groups">{t("groups.cancel")}</Link>
        </Button>
        <Button onClick={save} disabled={updateGroup.isPending}>
          {t("groups.save")}
        </Button>
      </div>

      <GroupMembersPanel groupId={group.id} />
    </div>
  );
};

/**
 * `/admin/groups/:groupId` — name, permission matrix, members (§6.1, ER-1).
 *
 * A role-linked group's name input is `readOnly` and the save sends the
 * unchanged name: the API *does* permit renaming those rows, but the name is
 * the only human trace of which legacy role the row serves, and
 * `get_effective_user_type_ids` matches on `role`, not on name — a rename
 * would confuse without enabling anything (§6.2).
 */
const GroupDetailPage: React.FC = () => {
  const { groupId = "" } = useParams();
  const { t } = useTranslation();
  const { data: groups, isPending } = useUserTypes();

  const group = groups?.find((candidate) => candidate.id === groupId);

  if (isPending) {
    return (
      <div className="p-8 text-muted-foreground">{t("groups.loading")}</div>
    );
  }
  if (!group) {
    return (
      <div className="p-8 text-muted-foreground">{t("groups.notFound")}</div>
    );
  }

  return <GroupEditor key={group.id} group={group} />;
};

export default GroupDetailPage;
