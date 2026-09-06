import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addContestation,
  addInfractionStage,
  closeCycle,
  createInfraction,
  getCycleCloses,
  getInfraction,
  getInfractions,
  getMyInfractions,
  getNextStep,
  promoteOccurrence,
} from "../../../api/infractions";
import { OCCURRENCES_QUERY_KEY } from "../../occurrence-management/hooks/useOccurrences";
import type {
  ContestationCreate,
  CycleCloseCreate,
  InfractionCreate,
  InfractionListFilters,
  InfractionPromote,
  InfractionStageCreate,
} from "../../../types/infraction";

/**
 * The process side. Every mutation invalidates both the list and the single
 * infraction, because appending a stage changes the *derived* current stage
 * the list filters on — there is no column to patch, so there is nothing to
 * patch surgically either.
 */

export const INFRACTIONS_KEY = "infractions";
export const MY_INFRACTIONS_KEY = ["my-infractions"] as const;
export const CYCLE_CLOSES_KEY = ["infraction-cycles"] as const;

const invalidateAll = (queryClient: ReturnType<typeof useQueryClient>) => {
  queryClient.invalidateQueries({ queryKey: [INFRACTIONS_KEY] });
  queryClient.invalidateQueries({ queryKey: MY_INFRACTIONS_KEY });
};

export const useInfractions = (filters: InfractionListFilters = {}) =>
  useQuery({
    queryKey: [INFRACTIONS_KEY, "list", filters],
    queryFn: () => getInfractions(filters),
  });

export const useInfraction = (id: string | null) =>
  useQuery({
    queryKey: [INFRACTIONS_KEY, "detail", id],
    queryFn: () => getInfraction(id as string),
    enabled: !!id,
  });

export const useNextStep = (id: string | null) =>
  useQuery({
    queryKey: [INFRACTIONS_KEY, "next-step", id],
    queryFn: () => getNextStep(id as string),
    enabled: !!id,
  });

export const useMyInfractions = () =>
  useQuery({
    queryKey: MY_INFRACTIONS_KEY,
    queryFn: getMyInfractions,
  });

export const useCycleCloses = () =>
  useQuery({
    queryKey: CYCLE_CLOSES_KEY,
    queryFn: getCycleCloses,
  });

export const useCreateInfraction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InfractionCreate) => createInfraction(data),
    onSuccess: () => invalidateAll(queryClient),
  });
};

export const usePromoteOccurrence = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      occurrenceId,
      data,
    }: {
      occurrenceId: string;
      data: InfractionPromote;
    }) => promoteOccurrence(occurrenceId, data),
    onSuccess: (_result, variables) => {
      invalidateAll(queryClient);
      // The occurrence detail carries `infraction_ids`, so the "already
      // promoted" link on the other side of the bridge is stale until this
      // runs -- and with `staleTime: 5 min` (main.tsx) "stale" means "wrong
      // for five minutes", not "refetched on the next render".
      //
      // Built from the occurrence feature's **own exported key**, never
      // retyped: round 2 shipped `["occurrence", id]` against a query
      // registered as `["occurrences", "detail", id]`, so the invalidation
      // matched nothing and the unit test asserted the typo rather than the
      // key the consuming query uses.
      queryClient.invalidateQueries({
        queryKey: [...OCCURRENCES_QUERY_KEY, "detail", variables.occurrenceId],
      });
    },
  });
};

export const useAddInfractionStage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: InfractionStageCreate }) =>
      addInfractionStage(id, data),
    onSuccess: () => invalidateAll(queryClient),
  });
};

export const useAddContestation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ContestationCreate }) =>
      addContestation(id, data),
    onSuccess: () => invalidateAll(queryClient),
  });
};

export const useCloseCycle = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CycleCloseCreate) => closeCycle(data),
    onSuccess: () => {
      invalidateAll(queryClient);
      queryClient.invalidateQueries({ queryKey: CYCLE_CLOSES_KEY });
    },
  });
};
