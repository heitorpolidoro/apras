import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Select } from "../../../components/ui/select";
import { useUsers } from "../../../hooks/useUsers";
import { useSetUserRoles } from "../hooks/useRoleMutations";
import { friendlyPermissionError } from "../utils/permissionErrors";
import type { User } from "../../../types/auth";

interface RoleMembersPanelProps {
  roleId: string;
}

/**
 * Membership, edited **from the role side** (APRAS-48 §6.4).
 *
 * Members are a **client-side join** over `GET /users/` — already
 * tenant-scoped, already returning `roles[]` on every row, already
 * fetched by the admin area. A `GET /roles/{id}/members` endpoint would
 * be a second source of truth for the same join, plus a new route to guard,
 * classify in the parity matrix and test.
 *
 * Adding and removing are both `PATCH /users/{id}` with the recomputed
 * `role_ids`, through `useSetUserRoles` — the very mutation the
 * user-side modal uses, so both directions are one code path.
 *
 * Scale caveat, recorded rather than solved: `GET /users/` is unpaginated
 * today. A server-side `?role_id=` filter is a later slice.
 */
const RoleMembersPanel: React.FC<RoleMembersPanelProps> = ({ roleId }) => {
  const { t } = useTranslation();
  const { data: users, isPending } = useUsers();
  const setUserRoles = useSetUserRoles();
  const [error, setError] = useState<string | null>(null);
  const [candidateId, setCandidateId] = useState("");

  const { members, candidates } = useMemo(() => {
    const isMember = (user: User) =>
      user.roles?.some((role) => role.id === roleId) ?? false;
    return {
      members: (users ?? []).filter(isMember),
      candidates: (users ?? []).filter((user) => !isMember(user)),
    };
  }, [users, roleId]);

  const currentIds = (user: User) =>
    user.roles?.map((role) => role.id) ?? [];

  const mutate = (userId: string, roleIds: string[]) => {
    setError(null);
    setUserRoles.mutate(
      { userId, roleIds },
      // `assert_can_assign_roles` can answer 403 on this side exactly as
      // on the user side; both render it the same way (§6.5).
      { onError: (err) => setError(friendlyPermissionError(err, t)) },
    );
  };

  const add = () => {
    const user = candidates.find((candidate) => candidate.id === candidateId);
    if (!user) return;
    mutate(user.id, [...currentIds(user), roleId]);
    setCandidateId("");
  };

  const remove = (user: User) => {
    mutate(
      user.id,
      currentIds(user).filter((id) => id !== roleId),
    );
  };

  return (
    <section className="rounded-xl border bg-card p-4">
      <h2 className="text-sm font-semibold text-foreground mb-3">
        {t("roles.members")}
      </h2>

      {error && (
        <p role="alert" className="text-sm text-destructive mb-3">
          {error}
        </p>
      )}

      {isPending && (
        <p className="text-sm text-muted-foreground">
          {t("roles.membersLoading")}
        </p>
      )}

      {!isPending && members.length === 0 && (
        <p className="text-sm text-muted-foreground">
          {t("roles.membersEmpty")}
        </p>
      )}

      <ul className="divide-y">
        {members.map((member) => (
          <li
            key={member.id}
            className="flex items-center justify-between py-2 gap-3"
          >
            <span className="text-sm text-foreground">{member.full_name}</span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => remove(member)}
              disabled={setUserRoles.isPending}
              aria-label={`${t("roles.membersRemove")} ${member.full_name}`}
            >
              {t("roles.membersRemove")}
            </Button>
          </li>
        ))}
      </ul>

      <div className="flex items-center gap-2 mt-4">
        <Select
          aria-label={t("roles.membersAdd")}
          value={candidateId}
          onChange={(event) => setCandidateId(event.target.value)}
          className="h-8 text-sm w-56"
        >
          <option value="">{t("roles.membersSelect")}</option>
          {candidates.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.full_name}
            </option>
          ))}
        </Select>
        <Button
          size="sm"
          onClick={add}
          disabled={!candidateId || setUserRoles.isPending}
        >
          {t("roles.membersAdd")}
        </Button>
      </div>
    </section>
  );
};

export default RoleMembersPanel;
