import apiClient from "./client";
import type {
  Invitation,
  InvitationAccept,
  InvitationCreate,
  InvitationPreview,
  InvitationToken,
} from "../types/invitations";

/**
 * The four invitation routes of APRAS-71, consumed by APRAS-72.
 *
 * The paths are written **exactly** as FastAPI mounts them — `/invitations`,
 * `/invitations/preview`, `/invitations/accept`, none with a trailing slash —
 * because a mismatch costs a 307 redirect that drops headers on some proxies.
 *
 * Both public calls are `POST`, the preview included, despite being a read:
 * a token in a path or a query string lands in access logs, in `Referer`
 * headers and in browser history (APRAS-71 D5).
 */

/** Invite one address to administer one condominium. Superuser only. */
export const issueInvitation = async (
  payload: InvitationCreate,
): Promise<Invitation> => {
  const response = await apiClient.post<Invitation>("/invitations", payload);
  return response.data;
};

/**
 * Invitations, newest first. Superuser only.
 *
 * `tenant_id` is **optional on the route**: `list_invitations` declares it
 * `UUID | None = None` and `InvitationService.list_invitations` applies the
 * `where` clause only when it is given, so an unfiltered call returns every
 * invitation in the installation — which is exactly the audience of
 * `/admin/tenants`. That screen fills its Administrator column from one such
 * call for the whole table; the open panel uses the filtered one.
 */
export const listInvitations = async (
  tenantId?: string,
): Promise<Invitation[]> => {
  const response = await apiClient.get<Invitation[]>(
    "/invitations",
    tenantId === undefined ? undefined : { params: { tenant_id: tenantId } },
  );
  return response.data;
};

/** What the invitee is shown before accepting. Unauthenticated. */
export const previewInvitation = async (
  token: string,
): Promise<InvitationPreview> => {
  const response = await apiClient.post<InvitationPreview>(
    "/invitations/preview",
    { token },
  );
  return response.data;
};

/**
 * The two accept branches, told apart by **status and nothing else**.
 *
 * `201` carries a `Token`; `200` carries an `InvitationPreview` and no
 * credential of any kind (APRAS-71 D8). The status is returned alongside the
 * body precisely so the caller cannot be tempted to guess the branch from the
 * preview's `account_exists`, which was computed at a different moment.
 */
export const acceptInvitation = async (
  payload: InvitationAccept,
): Promise<{ status: number; data: InvitationToken | InvitationPreview }> => {
  const response = await apiClient.post<InvitationToken | InvitationPreview>(
    "/invitations/accept",
    payload,
  );
  return { status: response.status, data: response.data };
};
