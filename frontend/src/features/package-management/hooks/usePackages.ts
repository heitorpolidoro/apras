import { useQueries, useQuery } from "@tanstack/react-query";
import { getMyPackageLots, getPackagesForLot } from "../../../api/packages";
import type { LotSummary, Package } from "../../../types/package";

export const useMyLots = () => {
  return useQuery({
    queryKey: ["my-package-lots"],
    queryFn: () => getMyPackageLots(),
  });
};

export interface LotWithPackages {
  lot: LotSummary;
  packages: Package[];
  isLoading: boolean;
}

/**
 * Resolves the current (resident) user's own linked lot(s) via useMyLots(),
 * then fetches each lot's packages in parallel via useQueries. Mirrors
 * usePackagesForLot's query key shape (["packages", lotId]) so cache entries
 * are shared with the gatekeeper-side hooks.
 */
export const useMyPackages = () => {
  const { data: lots, isLoading: isLoadingLots } = useMyLots();

  const packageQueries = useQueries({
    queries: (lots || []).map((lot) => ({
      queryKey: ["packages", lot.id, undefined, undefined, undefined],
      queryFn: () => getPackagesForLot(lot.id),
      enabled: !!lots,
    })),
  });

  const lotsWithPackages: LotWithPackages[] = (lots || []).map((lot, index) => ({
    lot,
    packages: packageQueries[index]?.data?.items || [],
    isLoading: packageQueries[index]?.isLoading ?? false,
  }));

  return {
    lotsWithPackages,
    isLoading: isLoadingLots || packageQueries.some((q) => q.isLoading),
  };
};
