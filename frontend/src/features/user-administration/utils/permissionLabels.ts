import type { TFunction } from "i18next";

/**
 * Permission labels by **composition**, not by 156 keys (APRAS-48 §2.8).
 *
 * A permission renders as a checkbox row inside its module's `<fieldset>`, so
 * the row's label is the *action* and the legend is the *module*. That is 26
 * module keys + 84 action keys = 110 per locale instead of 156, and it means a
 * verb translated once reads the same everywhere.
 *
 * Resolution ladder, for both halves:
 *   `permissions.overrides.<module>.<action>` → `permissions.actions.<action>`
 *   → humanized fallback.
 *
 * The fallback matters: a permission added by a future slice with no i18n key
 * yet renders as "Brand new thing" rather than leaking
 * `permissions.actions.brand_new_thing` into the UI.
 */

/** `snake_case` → `Snake case`. */
export const humanize = (value: string): string => {
  const words = value.replace(/_/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
};

/** A key resolves iff `t` returned something other than the key itself. */
const resolve = (key: string, t: TFunction): string | undefined => {
  const value = t(key);
  return typeof value === "string" && value !== key ? value : undefined;
};

export const moduleLabel = (module: string, t: TFunction): string =>
  resolve(`permissions.modules.${module}`, t) ?? humanize(module);

export const actionLabel = (action: string, t: TFunction): string =>
  resolve(`permissions.actions.${action}`, t) ?? humanize(action);

/** The label of one checkbox row: the action, unless a module overrides it. */
export const permissionLabel = (permission: string, t: TFunction): string => {
  const [module, action = ""] = permission.split(":", 2);
  return (
    resolve(`permissions.overrides.${module}.${action}`, t) ??
    actionLabel(action, t)
  );
};

/**
 * The display order of the `<fieldset>`s: the modules an operator configures
 * most often first, then the rest alphabetically, then anything the catalogue
 * grew that this constant does not know about (§2.8 — unknown modules sort
 * last with their raw name as the legend).
 */
export const PERMISSION_MODULE_ORDER: readonly string[] = [
  "tasks",
  "categories",
  "users",
  "user_types",
  "lots",
  "residents",
  "finance",
  "announcements",
  "documents",
  "occurrences",
  "projects",
  "votes",
  "assemblies",
  "reservations",
  "spaces",
  "packages",
  "visitors",
  "authorizations",
  "gate",
  "access_control",
  "assets",
  "inventory",
  "purchases",
  "feedback",
  "uploads",
  "tenants",
];

const rank = (module: string): number => {
  const index = PERMISSION_MODULE_ORDER.indexOf(module);
  return index === -1 ? PERMISSION_MODULE_ORDER.length : index;
};

export const sortModules = (modules: readonly string[]): string[] =>
  [...modules].sort(
    (a, b) => rank(a) - rank(b) || a.localeCompare(b),
  );
