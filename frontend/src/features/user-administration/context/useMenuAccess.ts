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
