import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createInfractionRule,
  deactivateInfractionRule,
  getInfractionRules,
  getInfractionSettings,
  updateInfractionRule,
  writeInfractionPolicy,
  writeInfractionSettings,
} from "../../../api/infractions";
import type {
  InfractionPolicyStep,
  InfractionRuleCreate,
  InfractionRuleUpdate,
} from "../../../types/infraction";

/**
 * The catalogue, its ladder and the module settings.
 *
 * Every mutation invalidates `["infraction-rules"]` rather than patching the
 * cache: the ladder write returns the whole rule and a deactivation changes a
 * row the list is sorted by, so a surgical update would be three places to
 * keep right instead of one.
 */

export const INFRACTION_RULES_KEY = ["infraction-rules"] as const;
export const INFRACTION_SETTINGS_KEY = ["infraction-settings"] as const;

export const useInfractionRules = () =>
  useQuery({
    queryKey: INFRACTION_RULES_KEY,
    queryFn: getInfractionRules,
  });

export const useInfractionSettings = () =>
  useQuery({
    queryKey: INFRACTION_SETTINGS_KEY,
    queryFn: getInfractionSettings,
  });

export const useCreateInfractionRule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InfractionRuleCreate) => createInfractionRule(data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: INFRACTION_RULES_KEY }),
  });
};

export const useUpdateInfractionRule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: InfractionRuleUpdate }) =>
      updateInfractionRule(id, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: INFRACTION_RULES_KEY }),
  });
};

export const useDeactivateInfractionRule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deactivateInfractionRule(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: INFRACTION_RULES_KEY }),
  });
};

export const useWriteInfractionPolicy = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, steps }: { id: string; steps: InfractionPolicyStep[] }) =>
      writeInfractionPolicy(id, steps),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: INFRACTION_RULES_KEY }),
  });
};

export const useWriteInfractionSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (condoFeeAmount: number | null) =>
      writeInfractionSettings(condoFeeAmount),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: INFRACTION_SETTINGS_KEY }),
  });
};
