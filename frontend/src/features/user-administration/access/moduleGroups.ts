/**
 * The clusters the module checklists are headed by (APRAS-39 §2.3).
 *
 * **Presentation only.** Coupling is not encoded here: since APRAS-128 the
 * backend declares module bundles (`MODULE_BUNDLES`) and sends each module's
 * `bundle` key; the pages render one checkbox per bundle (see `unitsOf`).
 * What these headings do not cover is one-way dependencies (`lots` ->
 * residents, ...), which stay ordinary independent modules.
 *
 * One constant, two screens: `/admin/modules` (the raw operator switch) and
 * `/subscription` (the tenant's commercial surface) render the same modules
 * in the same order. Extracted in APRAS-40 round 1 (review S-1).
 *
 * Every consumer must still handle a module **no cluster names**: the backend
 * derives `MODULES` from the permission catalogue precisely so a module a
 * future task adds is toggleable the day its first permission exists, while
 * this list is hand-written. Both pages append an `"other"` group for the
 * remainder, so a new module is visible rather than silently dropped.
 */
export interface ModuleGroup {
  key: string;
  modules: readonly string[];
}

export const MODULE_GROUPS: readonly ModuleGroup[] = [
  // `billing` joined the core cluster with APRAS-40 §2.1: it is the surface a
  // condominium contracts modules from, so it can never be one of them.
  { key: "core", modules: ["tenants", "users", "roles", "billing"] },
  { key: "tasks", modules: ["tasks", "categories"] },
  { key: "property", modules: ["lots", "residents", "packages"] },
  { key: "communication", modules: ["announcements", "documents", "feedback"] },
  // `infractions` sits beside `occurrences`: an occurrence is its promotion
  // source (APRAS-44 §3.3, ER-6), so an operator turning one off wants the
  // other in front of them.
  { key: "operations", modules: ["occurrences", "infractions", "projects"] },
  { key: "finance", modules: ["finance", "purchases", "assets", "inventory"] },
  { key: "spaces", modules: ["reservations", "spaces"] },
  {
    key: "access",
    modules: [
      "visitors",
      "authorizations",
      "gate",
      "access_control",
    ],
  },
  { key: "governance", modules: ["assemblies", "votes"] },
  { key: "infrastructure", modules: ["uploads"] },
];

/**
 * `MODULE_GROUPS`, plus an `"other"` group for any module the clusters do not
 * name. Returns the constant unchanged when there is no remainder, so the
 * common case allocates nothing new and the group list stays referentially
 * stable across renders.
 */
export const groupsCovering = (
  modules: readonly string[],
): readonly ModuleGroup[] => {
  const grouped = new Set(MODULE_GROUPS.flatMap((group) => group.modules));
  // Deduplicated: both callers map over a unique module list today, but a
  // repeated module would otherwise render twice in the `"other"` group
  // instead of being collapsed (round-2 review N-4).
  const ungrouped = [...new Set(modules)].filter(
    (module) => !grouped.has(module),
  );
  return ungrouped.length > 0
    ? [...MODULE_GROUPS, { key: "other", modules: ungrouped }]
    : MODULE_GROUPS;
};

/**
 * The checkbox units of one group: a bundle collapses to a single unit holding
 * all its members, any other module is a unit of one. A bundle is emitted by
 * the first group to reach one of its members (`emitted` is shared across the
 * groups of one render), so it never renders twice even if the presentation
 * headings split its members. A module whose `bundle` is null or absent is
 * an ordinary unit of one.
 */
export const unitsOf = (
  group: ModuleGroup,
  bundleOf: (module: string) => string | null | undefined,
  allModules: readonly string[],
  emitted: Set<string>,
): string[][] => {
  const units: string[][] = [];
  for (const module of group.modules) {
    if (!allModules.includes(module)) continue;
    const bundle = bundleOf(module);
    if (!bundle) {
      units.push([module]);
    } else if (!emitted.has(bundle)) {
      emitted.add(bundle);
      units.push(allModules.filter((m) => bundleOf(m) === bundle));
    }
  }
  return units;
};
