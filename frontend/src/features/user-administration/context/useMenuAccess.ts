import { useEffectiveIdentity } from "./useEffectiveIdentity";
import { useUserTypes } from "../../../hooks/useUserTypes";
import { UserRole } from "../../../types/auth";

export type MenuKey = "tasks" | "categories";

/**
 * Returns whether the effective (possibly simulated, see
 * `useEffectiveIdentity`) identity can access the given menu/feature.
 *
 * ADMINISTRATOR always has access. Every other role needs at least one of
 * its assigned UserTypes to include `menuKey` in `allowed_menus` — a user
 * with no UserTypes assigned (or only non-matching ones) is denied.
 *
 * TRANSITIONAL (IAM F4 -> F5). IAM F4 moved every other menu onto permissions
 * (`useCanShowMenu`), but this hook survives for exactly two of the 26
 * modules, `tasks` and `categories`, because `deps.assert_menu_access` is
 * still enforced on 12 backend handlers (8 in `endpoints/tasks.py`, 4 in
 * `endpoints/categories.py`). A purely permission-derived menu there would
 * show a door the backend answers 403 to — `categories:read` is ALL_ROLES in
 * `LEGACY_ROLE_PERMISSIONS`. It is reached through `AccessRule.legacyMenu`,
 * set on the `/dashboard` and `/categories` entries of `ROUTE_ACCESS` and
 * nowhere else. When F5 deletes `assert_menu_access`, this file and its two
 * test files go with it.
 */
export const useMenuAccess = (menuKey: MenuKey): boolean => {
  const { role, userTypeIds } = useEffectiveIdentity();
  const { data: userTypes } = useUserTypes();

  if (role === UserRole.ADMINISTRATOR) return true;

  if (!userTypes) return false;

  return userTypes.some(
    (userType) =>
      userTypeIds.includes(userType.id) &&
      userType.allowed_menus.includes(menuKey),
  );
};
