/**
 * The TS mirrors of `app/schemas/infraction.py` (APRAS-44 §4.4).
 *
 * Three shapes carry the whole design and are worth reading first:
 *
 * - `Infraction.current_stage` / `current_stage_at` / `defense_due_on` are
 *   **derived** server-side from the append-only stage history. There is no
 *   `status` column and no `current_stage` column, so the UI must never write
 *   them back — the only way to move a process is to append a stage.
 * - `InfractionTimelineEntry` is flat and discriminated by `kind`, so the
 *   timeline renders one ordered list with no client-side merge.
 * - `NextStep.reason` and `NextStep.is_saturated` are **not** the same
 *   predicate: they disagree at exactly the last rung, where the step *is* the
 *   suggestion (saturated) but nothing was truncated (not clamped).
 */

export type InfractionRuleOrigin =
  | "ESTATUTO"
  | "REGIMENTO_INTERNO"
  | "CONVENCAO";

export type InfractionStepAction = "AVISO" | "NOTIFICACAO" | "MULTA";

export type InfractionFineMode = "FIXED" | "MULTIPLE";

/** Why the suggestion is what it is (§6.5). Total: exactly one always holds. */
export type NextStepReason = "SUGGESTED" | "NO_POLICY" | "CLAMPED";

/** `?stage=` on the management list. `NONE` means "no stage applied yet". */
export type InfractionStageFilter = InfractionStepAction | "NONE";

export interface InfractionPolicyStep {
  id?: string;
  step_order: number;
  action: InfractionStepAction;
  /** Required iff `action === "NOTIFICACAO"`. */
  defense_deadline_days?: number | null;
  /** Required iff `action === "MULTA"`. */
  fine_mode?: InfractionFineMode | null;
  fine_fixed_amount?: number | null;
  fine_fee_multiplier?: number | null;
  note?: string | null;
}

export interface InfractionRule {
  id: string;
  article: string;
  origin: InfractionRuleOrigin;
  description: string;
  recidivism_window_days: number;
  is_active: boolean;
  /** Ordered by `step_order`; **empty is a legitimate state** (§6.5). */
  steps: InfractionPolicyStep[];
  created_at: string;
  updated_at: string;
}

export interface InfractionRuleCreate {
  article: string;
  origin: InfractionRuleOrigin;
  description: string;
  recidivism_window_days: number;
  is_active?: boolean;
}

export type InfractionRuleUpdate = Partial<InfractionRuleCreate>;

export interface InfractionRuleSummary {
  id: string;
  article: string;
  origin: InfractionRuleOrigin;
  description: string;
}

export interface InfractionActor {
  id: string;
  full_name: string;
}

export interface ResidentSummary {
  id: string;
  full_name: string;
  lot_id: string;
}

export interface LotSummary {
  id: string;
  block: string;
  lot_number: string;
}

export interface InfractionSettings {
  condo_fee_amount: number | null;
  updated_at: string | null;
  updated_by: InfractionActor | null;
}

export interface InfractionTimelineEntry {
  kind: "STAGE" | "CONTESTATION";
  id: string;
  at: string;
  actor: InfractionActor | null;
  action: InfractionStepAction | null;
  note: string | null;
  fine_amount: number | null;
  fine_amount_overridden: boolean | null;
  defense_due_on: string | null;
  policy_step_order: number | null;
  suggestion_followed: boolean | null;
  attachment_urls: string[];
}

export interface Infraction {
  id: string;
  rule: InfractionRuleSummary;
  lot: LotSummary;
  responsible: ResidentSummary;
  occurred_on: string;
  description: string;
  evidence_urls: string[];
  source_occurrence_id: string | null;
  source_occurrence_protocol: string | null;
  /** DERIVED from the last stage. Never a column, never written by the UI. */
  current_stage: InfractionStepAction | null;
  current_stage_at: string | null;
  defense_due_on: string | null;
  timeline: InfractionTimelineEntry[];
  created_at: string;
}

export interface PaginatedInfractions {
  items: Infraction[];
  total: number;
  skip: number;
  limit: number;
}

export interface InfractionCreate {
  rule_id: string;
  lot_id: string;
  responsible_resident_id: string;
  occurred_on: string;
  description: string;
  evidence_urls?: string[];
}

export interface InfractionPromote {
  rule_id: string;
  responsible_resident_id: string;
  /** Optional: the effective-lot rule of §7.4 resolves it. */
  lot_id?: string | null;
  description?: string | null;
  occurred_on?: string | null;
}

export interface InfractionStageCreate {
  /** `null` (or absent) means "apply the suggestion". */
  action?: InfractionStepAction | null;
  note: string;
  fine_amount?: number | null;
  defense_deadline_days?: number | null;
  evidence_urls?: string[];
}

export interface ContestationCreate {
  body: string;
  attachment_urls?: string[];
}

export interface CycleCloseCreate {
  rule_id: string;
  responsible_resident_id: string;
  /** Audit context only; never part of the recidivism predicate (§6.2). */
  lot_id?: string | null;
  justification: string;
}

export interface CycleClose {
  id: string;
  rule: InfractionRuleSummary;
  responsible: ResidentSummary;
  lot_id: string | null;
  justification: string;
  closed_by: InfractionActor;
  closed_at: string;
}

export interface NextStep {
  recidivism_count: number;
  window_start: string;
  cycle_closed_at: string | null;
  stages_applied: number;
  ladder_index: number;
  suggested_step_order: number | null;
  suggested_action: InfractionStepAction | null;
  reason: NextStepReason;
  defense_deadline_days: number | null;
  fine_amount: number | null;
  /** `"CONDO_FEE_NOT_SET"` or null (§6.3). */
  fine_amount_unavailable_reason: string | null;
  is_saturated: boolean;
}

export interface InfractionListFilters {
  rule_id?: string;
  lot_id?: string;
  responsible_id?: string;
  stage?: InfractionStageFilter;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
}
