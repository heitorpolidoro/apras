import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { useRoles } from "../../../hooks/useRoles";
import { usePermissionCatalogue } from "../../../hooks/usePermissionQueries";
import { usePermissionSet } from "../access/useCanAccess";
import PermissionMatrix from "../components/PermissionMatrix";
import RoleMembersPanel from "../components/RoleMembersPanel";
import { useUpdateRole } from "../hooks/useRoleMutations";
import { friendlyPermissionError } from "../utils/permissionErrors";
import type { Role } from "../../../types/auth";

/**
 * The editor proper, mounted under `key={role.id}`.
 *
 * Splitting it out is what lets the draft state be *initialised* from the
 * stored role instead of synchronised into it by an effect: React remounts
 * this component when the id changes, and a refetch after a save (same id,
 * new object) deliberately does **not** clobber what the operator is editing.
 */
const RoleEditor: React.FC<{ role: Role }> = ({ role }) => {
  const { t } = useTranslation();
  const { data: catalogue, isPending: cataloguePending } =
    usePermissionCatalogue();
  const mySet = usePermissionSet();
  const updateRole = useUpdateRole();

  const [name, setName] = useState(role.name);
  const [selected, setSelected] = useState<string[]>(role.permissions ?? []);
  const [error, setError] = useState<string | null>(null);

  const save = () => {
    setError(null);
    updateRole.mutate(
      {
        roleId: role.id,
        payload: {
          name,
          // The disabled-but-checked boxes are in `selected` and are resent
          // verbatim, so editing a name never strips a permission the author
          // cannot grant (§6.3).
          permissions: selected,
        },
      },
      { onError: (err) => setError(friendlyPermissionError(err, t)) },
    );
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-foreground">{role.name}</h1>
        <Button variant="outline" asChild>
          <Link to="/admin/roles">{t("roles.back")}</Link>
        </Button>
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <div>
        <label
          htmlFor="role-name"
          className="text-sm font-medium text-muted-foreground block mb-1"
        >
          {t("roles.name")}
        </label>
        <Input
          id="role-name"
          value={name}
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
          <Link to="/admin/roles">{t("roles.cancel")}</Link>
        </Button>
        <Button onClick={save} disabled={updateRole.isPending}>
          {t("roles.save")}
        </Button>
      </div>

      <RoleMembersPanel roleId={role.id} />
    </div>
  );
};

/**
 * `/admin/roles/:roleId` — name, permission matrix, members (§6.1, ER-1).
 *
 * A role-linked role's name input is `readOnly` and the save sends the
 * unchanged name: the API *does* permit renaming those rows, but the name is
 * the only human trace of which legacy role the row serves, and
 * `get_effective_role_ids` matches on `role`, not on name — a rename
 * would confuse without enabling anything (§6.2).
 */
const RoleDetailPage: React.FC = () => {
  const { roleId = "" } = useParams();
  const { t } = useTranslation();
  const { data: roles, isPending } = useRoles();

  const role = roles?.find((candidate) => candidate.id === roleId);

  if (isPending) {
    return (
      <div className="p-8 text-muted-foreground">{t("roles.loading")}</div>
    );
  }
  if (!role) {
    return (
      <div className="p-8 text-muted-foreground">{t("roles.notFound")}</div>
    );
  }

  return <RoleEditor key={role.id} role={role} />;
};

export default RoleDetailPage;
