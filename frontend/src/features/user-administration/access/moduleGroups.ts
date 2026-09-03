/**
 * The companion clusters the module checklists are grouped by (APRAS-39 §2.3).
 *
 * **Presentation, not machinery.** The 27 modules toggle independently, and
 * turning one companion off without the other is legal and safe — every
 * endpoint of a disabled module refuses, and it is reversible in one click.
 * Modelling `requires` edges would be a second authorization concept for an
 * operator mistake that costs one checkbox to fix.
 *
 * One constant, two screens: `/admin/modules` (the raw operator switch) and
 * `/subscription` (the tenant's commercial surface) render the same 27 modules
 * in the same order, and a hand-written list copied into both would have to be
 * edited in both forever. Extracted in APRAS-40 round 1 (review S-1).
 *
 * Every consumer must still handle a module **no cluster names**: the backend
 * derives `MODULES` from the permission catalogue precisely so a module a
 * future task adds is toggleable the day its first permission exists, while
 * this list is hand-written. Both pages append an `"other"` group for the
 * remainder, so a 28th module is visible rather than silently dropped.
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
  { key: "operations", modules: ["occurrences", "projects"] },
  { key: "finance", modules: ["finance", "purchases", "assets", "inventory"] },
  { key: "spaces", modules: ["reservations", "spaces"] },
  {
    key: "access",
    modules: [
      "visitors",
      "authorizations",
      "gate",
      "access_control",
      "uploads",
    ],
  },
  { key: "governance", modules: ["assemblies", "votes"] },
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
