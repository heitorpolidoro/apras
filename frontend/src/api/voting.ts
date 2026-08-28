import apiClient from "./client";
import type { Lot } from "../types/lot";
import type {
  AssemblyCreatePayload,
  AssemblyRead,
  AssemblyUpdatePayload,
  BallotCreatePayload,
  BallotRead,
  BallotRetractPayload,
  EligibleLotRead,
  LotVoterEligibilityCreatePayload,
  LotVoterEligibilityRead,
  MyBallotRead,
  TallyRead,
  VoteCreatePayload,
  VoteListParams,
  VoteRead,
} from "../types/voting";

export const getAssemblies = async (): Promise<AssemblyRead[]> => {
  const response = await apiClient.get<AssemblyRead[]>("/assemblies/");
  return response.data;
};

export const getAssembly = async (id: string): Promise<AssemblyRead> => {
  const response = await apiClient.get<AssemblyRead>(`/assemblies/${id}`);
  return response.data;
};

export const createAssembly = async (
  data: AssemblyCreatePayload,
): Promise<AssemblyRead> => {
  const response = await apiClient.post<AssemblyRead>("/assemblies/", data);
  return response.data;
};

export const updateAssembly = async (
  id: string,
  data: AssemblyUpdatePayload,
): Promise<AssemblyRead> => {
  const response = await apiClient.patch<AssemblyRead>(`/assemblies/${id}`, data);
  return response.data;
};

export const closeAssembly = async (id: string): Promise<AssemblyRead> => {
  const response = await apiClient.post<AssemblyRead>(`/assemblies/${id}/close`);
  return response.data;
};

export const getAssemblyMinutes = async (id: string): Promise<string> => {
  const response = await apiClient.get<string>(`/assemblies/${id}/minutes`, {
    responseType: "text",
  });
  return response.data;
};

export const saveAssemblyMinutes = async (id: string): Promise<unknown> => {
  const response = await apiClient.post(`/assemblies/${id}/minutes/save`);
  return response.data;
};

export const getVotes = async (params?: VoteListParams): Promise<VoteRead[]> => {
  const response = await apiClient.get<VoteRead[]>("/votes/", { params });
  return response.data;
};

export const getVote = async (id: string): Promise<VoteRead> => {
  const response = await apiClient.get<VoteRead>(`/votes/${id}`);
  return response.data;
};

export const createVote = async (
  data: VoteCreatePayload,
): Promise<VoteRead> => {
  const response = await apiClient.post<VoteRead>("/votes/", data);
  return response.data;
};

export const closeVote = async (id: string): Promise<VoteRead> => {
  const response = await apiClient.post<VoteRead>(`/votes/${id}/close`);
  return response.data;
};

export const castBallot = async (
  voteId: string,
  data: BallotCreatePayload,
): Promise<BallotRead> => {
  const response = await apiClient.post<BallotRead>(
    `/votes/${voteId}/ballots`,
    data,
  );
  return response.data;
};

export const retractBallot = async (
  voteId: string,
  data: BallotRetractPayload,
): Promise<BallotRead> => {
  const response = await apiClient.post<BallotRead>(
    `/votes/${voteId}/ballots/retract`,
    data,
  );
  return response.data;
};

export const getMyBallot = async (voteId: string): Promise<MyBallotRead[]> => {
  const response = await apiClient.get<MyBallotRead[]>(
    `/votes/${voteId}/my-ballot`,
  );
  return response.data;
};

export const getEligibleLots = async (
  voteId: string,
): Promise<EligibleLotRead[]> => {
  const response = await apiClient.get<EligibleLotRead[]>(
    `/votes/${voteId}/eligible-lots`,
  );
  return response.data;
};

export const getTally = async (voteId: string): Promise<TallyRead> => {
  const response = await apiClient.get<TallyRead>(`/votes/${voteId}/tally`);
  return response.data;
};

/**
 * Flip the manual delinquency flag of a lot. Dedicated endpoint because
 * this is the flag that bars the unit from voting in an assembly.
 */
export const updateLotDelinquency = async (
  lotId: string,
  isDelinquent: boolean,
): Promise<Lot> => {
  const response = await apiClient.patch<Lot>(`/lots/${lotId}/delinquency`, {
    is_delinquent: isDelinquent,
  });
  return response.data;
};

export const getLotVoterEligibility = async (
  lotId: string,
): Promise<LotVoterEligibilityRead[]> => {
  const response = await apiClient.get<LotVoterEligibilityRead[]>(
    `/lots/${lotId}/voter-eligibility`,
  );
  return response.data;
};

export const addLotVoterEligibility = async (
  lotId: string,
  data: LotVoterEligibilityCreatePayload,
): Promise<LotVoterEligibilityRead> => {
  const response = await apiClient.post<LotVoterEligibilityRead>(
    `/lots/${lotId}/voter-eligibility`,
    data,
  );
  return response.data;
};

export const removeLotVoterEligibility = async (
  lotId: string,
  userId: string,
): Promise<void> => {
  await apiClient.delete(`/lots/${lotId}/voter-eligibility/${userId}`);
};
