import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Select } from "../../../components/ui/select";
import { useUsers } from "../../../hooks/useUsers";
import { useSetUserGroups } from "../hooks/useUserTypeMutations";
import { friendlyPermissionError } from "../utils/permissionErrors";
import type { User } from "../../../types/auth";

interface GroupMembersPanelProps {
  groupId: string;
}

/**
 * Membership, edited **from the group side** (APRAS-48 §6.4).
 *
 * Members are a **client-side join** over `GET /users/` — already
 * tenant-scoped, already returning `user_types[]` on every row, already
 * fetched by the admin area. A `GET /user-types/{id}/members` endpoint would
 * be a second source of truth for the same join, plus a new route to guard,
 * classify in the parity matrix and test.
 *
 * Adding and removing are both `PATCH /users/{id}` with the recomputed
 * `user_type_ids`, through `useSetUserGroups` — the very mutation the
 * user-side modal uses, so both directions are one code path.
 *
 * Scale caveat, recorded rather than solved: `GET /users/` is unpaginated
 * today. A server-side `?user_type_id=` filter is a later slice.
 */
const GroupMembersPanel: React.FC<GroupMembersPanelProps> = ({ groupId }) => {
  const { t } = useTranslation();
  const { data: users, isPending } = useUsers();
  const setUserGroups = useSetUserGroups();
  const [error, setError] = useState<string | null>(null);
  const [candidateId, setCandidateId] = useState("");

  const { members, candidates } = useMemo(() => {
    const isMember = (user: User) =>
      user.user_types?.some((userType) => userType.id === groupId) ?? false;
    return {
      members: (users ?? []).filter(isMember),
      candidates: (users ?? []).filter((user) => !isMember(user)),
    };
  }, [users, groupId]);

  const currentIds = (user: User) =>
    user.user_types?.map((userType) => userType.id) ?? [];

  const mutate = (userId: string, userTypeIds: string[]) => {
    setError(null);
    setUserGroups.mutate(
      { userId, userTypeIds },
      // `assert_can_assign_user_types` can answer 403 on this side exactly as
      // on the user side; both render it the same way (§6.5).
      { onError: (err) => setError(friendlyPermissionError(err, t)) },
    );
  };

  const add = () => {
    const user = candidates.find((candidate) => candidate.id === candidateId);
    if (!user) return;
    mutate(user.id, [...currentIds(user), groupId]);
    setCandidateId("");
  };

  const remove = (user: User) => {
    mutate(
      user.id,
      currentIds(user).filter((id) => id !== groupId),
    );
  };

  return (
    <section className="rounded-xl border bg-card p-4">
      <h2 className="text-sm font-semibold text-foreground mb-3">
        {t("groups.members")}
      </h2>

      {error && (
        <p role="alert" className="text-sm text-destructive mb-3">
          {error}
        </p>
      )}

      {isPending && (
        <p className="text-sm text-muted-foreground">
          {t("groups.membersLoading")}
        </p>
      )}

      {!isPending && members.length === 0 && (
        <p className="text-sm text-muted-foreground">
          {t("groups.membersEmpty")}
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
              disabled={setUserGroups.isPending}
              aria-label={`${t("groups.membersRemove")} ${member.full_name}`}
            >
              {t("groups.membersRemove")}
            </Button>
          </li>
        ))}
      </ul>

      <div className="flex items-center gap-2 mt-4">
        <Select
          aria-label={t("groups.membersAdd")}
          value={candidateId}
          onChange={(event) => setCandidateId(event.target.value)}
          className="h-8 text-sm w-56"
        >
          <option value="">{t("groups.membersSelect")}</option>
          {candidates.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.full_name}
            </option>
          ))}
        </Select>
        <Button
          size="sm"
          onClick={add}
          disabled={!candidateId || setUserGroups.isPending}
        >
          {t("groups.membersAdd")}
        </Button>
      </div>
    </section>
  );
};

export default GroupMembersPanel;
