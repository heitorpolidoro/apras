import apiClient from "./client";
import type {
  ContestationCreate,
  CycleClose,
  CycleCloseCreate,
  Infraction,
  InfractionCreate,
  InfractionListFilters,
  InfractionPolicyStep,
  InfractionPromote,
  InfractionRule,
  InfractionRuleCreate,
  InfractionRuleUpdate,
  InfractionSettings,
  InfractionStageCreate,
  NextStep,
  PaginatedInfractions,
} from "../types/infraction";

/**
 * The 18 routes of the infraction module (APRAS-44 §4.2).
 *
 * `skip`/`limit`, never `page`/`page_size`: the whole codebase paginates one
 * way and this endpoint is not going to be the exception.
 */

// --- the rule catalogue ----------------------------------------------------

export async function getInfractionRules(): Promise<InfractionRule[]> {
  const response = await apiClient.get<InfractionRule[]>("/infraction-rules");
  return response.data;
}

export async function getInfractionRule(id: string): Promise<InfractionRule> {
  const response = await apiClient.get<InfractionRule>(
    `/infraction-rules/${id}`,
  );
  return response.data;
}

export async function createInfractionRule(
  data: InfractionRuleCreate,
): Promise<InfractionRule> {
  const response = await apiClient.post<InfractionRule>(
    "/infraction-rules",
    data,
  );
  return response.data;
}

export async function updateInfractionRule(
  id: string,
  data: InfractionRuleUpdate,
): Promise<InfractionRule> {
  const response = await apiClient.put<InfractionRule>(
    `/infraction-rules/${id}`,
    data,
  );
  return response.data;
}

/** `DELETE` **soft-deactivates**: the rule stays readable and navigable. */
export async function deactivateInfractionRule(id: string): Promise<void> {
  await apiClient.delete(`/infraction-rules/${id}`);
}

/** Replaces the ladder whole. A patch would need a merge rule nobody wrote. */
export async function writeInfractionPolicy(
  id: string,
  steps: InfractionPolicyStep[],
): Promise<InfractionRule> {
  const response = await apiClient.put<InfractionRule>(
    `/infraction-rules/${id}/policy`,
    { steps },
  );
  return response.data;
}

// --- the module settings singleton ----------------------------------------

/** Never 404s: an absent row reads as all nulls (§5). */
export async function getInfractionSettings(): Promise<InfractionSettings> {
  const response = await apiClient.get<InfractionSettings>(
    "/infraction-settings",
  );
  return response.data;
}

export async function writeInfractionSettings(
  condoFeeAmount: number | null,
): Promise<InfractionSettings> {
  const response = await apiClient.put<InfractionSettings>(
    "/infraction-settings",
    { condo_fee_amount: condoFeeAmount },
  );
  return response.data;
}

// --- the process -----------------------------------------------------------

export async function getInfractions(
  filters: InfractionListFilters = {},
): Promise<PaginatedInfractions> {
  const response = await apiClient.get<PaginatedInfractions>("/infractions", {
    params: filters,
  });
  return response.data;
}

/** The resident's own short list. A filter: an unlinked caller gets `[]`. */
export async function getMyInfractions(): Promise<Infraction[]> {
  const response = await apiClient.get<Infraction[]>("/infractions/my-lots");
  return response.data;
}

export async function getInfraction(id: string): Promise<Infraction> {
  const response = await apiClient.get<Infraction>(`/infractions/${id}`);
  return response.data;
}

export async function getNextStep(id: string): Promise<NextStep> {
  const response = await apiClient.get<NextStep>(
    `/infractions/${id}/next-step`,
  );
  return response.data;
}

export async function createInfraction(
  data: InfractionCreate,
): Promise<Infraction> {
  const response = await apiClient.post<Infraction>("/infractions", data);
  return response.data;
}

export async function promoteOccurrence(
  occurrenceId: string,
  data: InfractionPromote,
): Promise<Infraction> {
  const response = await apiClient.post<Infraction>(
    `/infractions/from-occurrence/${occurrenceId}`,
    data,
  );
  return response.data;
}

export async function addInfractionStage(
  id: string,
  data: InfractionStageCreate,
): Promise<Infraction> {
  const response = await apiClient.post<Infraction>(
    `/infractions/${id}/stages`,
    data,
  );
  return response.data;
}

export async function addContestation(
  id: string,
  data: ContestationCreate,
): Promise<Infraction> {
  const response = await apiClient.post<Infraction>(
    `/infractions/${id}/contestation`,
    data,
  );
  return response.data;
}

// --- recidivism cycles -----------------------------------------------------

export async function getCycleCloses(): Promise<CycleClose[]> {
  const response = await apiClient.get<CycleClose[]>("/infractions/cycles");
  return response.data;
}

export async function closeCycle(
  data: CycleCloseCreate,
): Promise<CycleClose> {
  const response = await apiClient.post<CycleClose>(
    "/infractions/cycles/close",
    data,
  );
  return response.data;
}
