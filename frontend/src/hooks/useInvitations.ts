import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { issueInvitation, listInvitations } from "../api/invitations";
import type { Invitation, InvitationCreate } from "../types/invitations";

/**
 * The superuser side of administrator invitations (APRAS-72 D2, D4).
 *
 * One key, `["invitations", tenantId]`, so the panel and the Administrator
 * column of `/admin/tenants` read the **same** cache entry and a resend
 * refreshes both.
 */

/**
 * Every invitation in the installation, newest first — one call for the whole
 * `/admin/tenants` table.
 *
 * The Administrator column needs each condominium's most recent invitation,
 * and the route's `tenant_id` filter is optional, so one unfiltered request
 * answers the whole column. It is issued **once by the page**, never by a
 * cell, which is what "not once per table row" asks for; each cell then
 * selects its own condominium's newest entry out of this single payload.
 *
 * This entry is the column's only authority. `useTenantInvitations` below
 * holds the same rows again under a different key for the open panel, so for
 * the moment between a resend and both queries settling the column and the
 * panel can differ; the invalidation covers both keys, so it closes on its
 * own, and the panel — the surface actually being read then — is the one
 * that refetches first.
 */
export const useAllInvitations = () =>
  useQuery<Invitation[]>({
    queryKey: ["invitations"],
    queryFn: () => listInvitations(),
  });

/**
 * One condominium's invitations, newest first — the open panel's query.
 *
 * A separate cache entry from `useAllInvitations`, so the panel stays
 * authoritative for the condominium being looked at while the column keeps
 * its whole-table answer. `["invitations"]` is a prefix of this key, so one
 * invalidation refreshes both.
 *
 * It takes no `enabled` flag: the panel is the only caller and the page
 * mounts it under `panelFor &&`, so the query exists exactly while the panel
 * is open. The gating is by mount, not by a flag.
 */
export const useTenantInvitations = (tenantId: string) =>
  useQuery<Invitation[]>({
    queryKey: ["invitations", tenantId],
    queryFn: () => listInvitations(tenantId),
  });

/**
 * Issue an invitation, and refresh every tenant's list.
 *
 * The invalidation is `["invitations"]` — the prefix, not one tenant's key —
 * because issuing supersedes (APRAS-71 D4): the previous row's `expires_at`
 * becomes now, so the cached copy of that row is stale too and not only the
 * absence of the new one.
 */
export const useIssueInvitation = () => {
  const queryClient = useQueryClient();
  return useMutation<Invitation, unknown, InvitationCreate>({
    mutationFn: (payload) => issueInvitation(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["invitations"] });
    },
  });
};
