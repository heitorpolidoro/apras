/**
 * Administrator invitations, as APRAS-71 puts them on the wire (APRAS-72).
 *
 * The invited person becomes the condominium's **administrator in the
 * system** — `user_tenant_link.is_tenant_admin`. That is a system role and
 * not one of the condominium's own elected offices, which this flow never
 * grants.
 */

/**
 * One invitation, mirroring `InvitationRead` field for field.
 *
 * There is deliberately **no `status`**: the backend stores none (APRAS-71
 * D1), so a field here would be a second source of truth for something the
 * two timestamps below already decide.
 */
export interface Invitation {
  id: string;
  tenant_id: string;
  email: string;
  expires_at: string;
  accepted_at: string | null;
  accepted_user_id: string | null;
  invited_by_user_id: string;
  created_at: string;
}

/**
 * What the public page is shown before accepting, mirroring
 * `InvitationPreview`.
 *
 * The inviter's field is `invited_by_name` — the name the backend actually
 * serialises. It carries no credential of any kind, which is why the same
 * shape doubles as the body of the `200` accept answer (APRAS-71 D8).
 */
export interface InvitationPreview {
  email: string;
  tenant_name: string;
  tenant_slug: string;
  invited_by_name: string;
  expires_at: string;
  account_exists: boolean;
}

/** What a superuser posts to invite an administrator (`InvitationCreate`). */
export interface InvitationCreate {
  tenant_id: string;
  email: string;
  full_name?: string;
}

/** The acceptance body (`InvitationAcceptRequest`). */
export interface InvitationAccept {
  token: string;
  full_name?: string;
  cpf?: string;
  password?: string;
}

/**
 * The `201` accept body, mirroring `schemas/token.Token`.
 *
 * Declared here rather than reused from `types/auth`, which has no token
 * shape: `LoginPage` reads `response.data.access_token` off an untyped axios
 * answer.
 */
export interface InvitationToken {
  access_token: string;
  token_type: string;
}

export type InvitationStatus = "pending" | "accepted" | "expired";

/**
 * D3: the browser applies the backend's own rule to the same two timestamps.
 *
 * `accepted_at` first — a consumed invitation stays *accepted* forever, even
 * once its deadline is behind it. Clock skew can only mislabel an invitation
 * in the minutes around its expiry, and the authoritative answer is the `410`
 * the accept call returns anyway.
 */
export const invitationStatus = (
  invitation: Invitation,
  now: Date = new Date(),
): InvitationStatus => {
  if (invitation.accepted_at !== null) return "accepted";
  return new Date(invitation.expires_at) <= now ? "expired" : "pending";
};
