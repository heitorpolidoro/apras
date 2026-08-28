export type AssemblyType = "AGO" | "AGE";
export type AssemblyStatus = "DRAFT" | "OPEN" | "CLOSED";
export type VoteKind = "ASSEMBLEIA" | "ENQUETE";
export type VoteType = "SINGLE_CHOICE" | "MULTIPLE_CHOICE";
export type VoteStatus = "OPEN" | "CLOSED";

export interface AssemblyRead {
  id: string;
  title: string;
  type: AssemblyType;
  held_on: string;
  agenda?: string | null;
  status: AssemblyStatus;
  created_by_id: string;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
}

export interface AssemblyCreatePayload {
  title: string;
  type: AssemblyType;
  held_on: string;
  agenda?: string | null;
}

export interface AssemblyUpdatePayload {
  title?: string;
  type?: AssemblyType;
  held_on?: string;
  agenda?: string | null;
  /**
   * CLOSED is not reachable through PATCH: closing cascades into every open
   * vote and freezes each tally snapshot, so it only happens through
   * `POST /assemblies/{id}/close`. The API rejects it with 400.
   */
  status?: Exclude<AssemblyStatus, "CLOSED">;
}

export interface VoteOptionRead {
  id: string;
  vote_id: string;
  label: string;
  order_index: number;
}

export interface VoteOptionCreatePayload {
  label: string;
  order_index?: number;
}

export interface VoteRead {
  id: string;
  assembly_id?: string | null;
  kind: VoteKind;
  title: string;
  description?: string | null;
  vote_type: VoteType;
  status: VoteStatus;
  is_anonymous: boolean;
  opens_at: string;
  closes_at: string;
  created_by_id: string;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
  options: VoteOptionRead[];
}

export interface VoteCreatePayload {
  assembly_id?: string | null;
  kind: VoteKind;
  title: string;
  description?: string | null;
  vote_type: VoteType;
  is_anonymous?: boolean;
  opens_at?: string | null;
  closes_at: string;
  options: VoteOptionCreatePayload[];
}

export interface VoteListParams {
  kind?: VoteKind;
  status?: VoteStatus;
  assembly_id?: string;
}

export interface BallotRead {
  id: string;
  vote_id: string;
  lot_id?: string | null;
  lot_label?: string | null;
  voter_user_id?: string | null;
  voter_name?: string | null;
  is_retraction: boolean;
  selected_option_ids: string[];
  cast_at: string;
}

/**
 * A ballot the caller is entitled to see. `can_edit` is true only for the
 * person who actually cast it — only that person may change or retract it.
 */
export interface MyBallotRead extends BallotRead {
  can_edit: boolean;
}

export interface BallotCreatePayload {
  lot_id?: string | null;
  selected_option_ids: string[];
}

export interface BallotRetractPayload {
  lot_id?: string | null;
}

export interface TallyResultRead {
  option_id: string;
  label: string;
  count: number;
}

export interface TallyAttributionRead {
  lot_id?: string | null;
  lot_label?: string | null;
  voter_user_id?: string | null;
  voter_name?: string | null;
  selected_labels: string[];
  cast_at: string;
}

/**
 * Two-mode payload: while the vote is open the API sends only
 * `voters_count` (plus `total_lots` in an assembly) and omits `results`
 * and `attributions` entirely.
 */
export interface TallyRead {
  vote_id: string;
  kind: VoteKind;
  status: VoteStatus;
  is_anonymous: boolean;
  voters_count: number;
  total_lots?: number;
  results?: TallyResultRead[];
  attributions?: TallyAttributionRead[];
}

export interface EligibleLotRead {
  id: string;
  label: string;
}

export interface LotVoterEligibilityRead {
  id: string;
  lot_id: string;
  user_id: string;
  user_name?: string | null;
  added_by_id?: string | null;
  added_at: string;
}

export interface LotVoterEligibilityCreatePayload {
  user_id: string;
}
