import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addLotVoterEligibility,
  castBallot,
  closeAssembly,
  closeVote,
  createAssembly,
  createVote,
  getAssemblies,
  getAssemblyMinutes,
  getEligibleLots,
  getLotVoterEligibility,
  getMyBallot,
  getTally,
  getVotes,
  removeLotVoterEligibility,
  retractBallot,
  saveAssemblyMinutes,
  updateAssembly,
  updateLotDelinquency,
} from "../../../api/voting";
import type {
  AssemblyCreatePayload,
  AssemblyUpdatePayload,
  BallotCreatePayload,
  BallotRetractPayload,
  VoteCreatePayload,
  VoteListParams,
} from "../../../types/voting";

export const ASSEMBLIES_QUERY_KEY = ["assemblies"];
export const VOTES_QUERY_KEY = ["votes"];
export const MY_BALLOT_QUERY_KEY = ["my-ballot"];
export const TALLY_QUERY_KEY = ["tally"];
export const LOT_VOTER_ELIGIBILITY_QUERY_KEY = ["lot-voter-eligibility"];

export function useAssemblies() {
  return useQuery({ queryKey: ASSEMBLIES_QUERY_KEY, queryFn: getAssemblies });
}

export function useCreateAssembly() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AssemblyCreatePayload) => createAssembly(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ASSEMBLIES_QUERY_KEY });
    },
  });
}

/**
 * Edit an assembly — in practice the release of a `DRAFT` agenda into
 * `OPEN`, which is what makes its votes start accepting ballots. The vote
 * list is invalidated too because ballot acceptance hangs off the
 * assembly status, not off the vote row itself.
 */
export function useUpdateAssembly() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AssemblyUpdatePayload }) =>
      updateAssembly(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ASSEMBLIES_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: VOTES_QUERY_KEY });
    },
  });
}

export function useCloseAssembly() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => closeAssembly(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ASSEMBLIES_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: VOTES_QUERY_KEY });
    },
  });
}

export function useAssemblyMinutes(assemblyId?: string) {
  return useQuery({
    queryKey: ["assembly-minutes", assemblyId],
    queryFn: () => getAssemblyMinutes(assemblyId as string),
    enabled: Boolean(assemblyId),
  });
}

export function useSaveAssemblyMinutes() {
  return useMutation({ mutationFn: (id: string) => saveAssemblyMinutes(id) });
}

export function useVotes(params?: VoteListParams) {
  return useQuery({
    queryKey: [...VOTES_QUERY_KEY, params ?? {}],
    queryFn: () => getVotes(params),
  });
}

export function useCreateVote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: VoteCreatePayload) => createVote(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: VOTES_QUERY_KEY });
    },
  });
}

export function useCloseVote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => closeVote(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: VOTES_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: TALLY_QUERY_KEY });
    },
  });
}

export function useMyBallot(voteId?: string) {
  return useQuery({
    queryKey: [...MY_BALLOT_QUERY_KEY, voteId],
    queryFn: () => getMyBallot(voteId as string),
    enabled: Boolean(voteId),
  });
}

export function useEligibleLots(voteId?: string) {
  return useQuery({
    queryKey: ["eligible-lots", voteId],
    queryFn: () => getEligibleLots(voteId as string),
    enabled: Boolean(voteId),
  });
}

export function useTally(voteId?: string) {
  return useQuery({
    queryKey: [...TALLY_QUERY_KEY, voteId],
    queryFn: () => getTally(voteId as string),
    enabled: Boolean(voteId),
  });
}

export function useCastBallot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      voteId,
      data,
    }: {
      voteId: string;
      data: BallotCreatePayload;
    }) => castBallot(voteId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MY_BALLOT_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: TALLY_QUERY_KEY });
    },
  });
}

export function useRetractBallot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      voteId,
      data,
    }: {
      voteId: string;
      data: BallotRetractPayload;
    }) => retractBallot(voteId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MY_BALLOT_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: TALLY_QUERY_KEY });
    },
  });
}

export const LOTS_QUERY_KEY = ["lots"];

export function useUpdateLotDelinquency() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      lotId,
      isDelinquent,
    }: {
      lotId: string;
      isDelinquent: boolean;
    }) => updateLotDelinquency(lotId, isDelinquent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOTS_QUERY_KEY });
    },
  });
}

export function useLotVoterEligibility(lotId?: string) {
  return useQuery({
    queryKey: [...LOT_VOTER_ELIGIBILITY_QUERY_KEY, lotId],
    queryFn: () => getLotVoterEligibility(lotId as string),
    enabled: Boolean(lotId),
  });
}

export function useAddLotVoterEligibility() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ lotId, userId }: { lotId: string; userId: string }) =>
      addLotVoterEligibility(lotId, { user_id: userId }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: LOT_VOTER_ELIGIBILITY_QUERY_KEY,
      });
    },
  });
}

export function useRemoveLotVoterEligibility() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ lotId, userId }: { lotId: string; userId: string }) =>
      removeLotVoterEligibility(lotId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: LOT_VOTER_ELIGIBILITY_QUERY_KEY,
      });
    },
  });
}
