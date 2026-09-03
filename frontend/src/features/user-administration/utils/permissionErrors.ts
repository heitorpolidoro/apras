import type { TFunction } from "i18next";
import { parseApiError } from "../../../api/errors";
import { permissionLabel } from "./permissionLabels";

/**
 * The friendly 403 (APRAS-48 §6.5, ER-4).
 *
 * The backend's two anti-escalation sentences are English, ungrammatical in
 * Portuguese, and carry raw `<module>:<action>` strings an operator has no
 * reason to read. They are recognised by their prefixes — copied verbatim from
 * `role_service.assert_can_grant` — and re-rendered through the **same**
 * label resolver as the checkboxes, so a permission reads the same word in the
 * matrix and in the error.
 *
 * A prefix that drifts on the backend makes this fall through to
 * `parseApiError`, i.e. the raw sentence: degraded, never wrong.
 */
export const CANNOT_GRANT_PREFIX = "You cannot grant permissions you do not hold: ";
export const SUPERUSER_ONLY_PREFIX =
  "These permissions are granted by is_superuser only: ";

const NAME_TAKEN_DETAIL = "A role with this name already exists";

const labelled = (list: string, t: TFunction): string =>
  list
    .split(",")
    .map((permission) => permissionLabel(permission.trim(), t))
    .join(", ");

export const friendlyPermissionError = (err: unknown, t: TFunction): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;

  if (typeof detail === "string") {
    if (detail.startsWith(CANNOT_GRANT_PREFIX)) {
      return t("permissions.errors.cannotGrant", {
        permissions: labelled(detail.slice(CANNOT_GRANT_PREFIX.length), t),
      });
    }
    if (detail.startsWith(SUPERUSER_ONLY_PREFIX)) {
      return t("permissions.errors.superuserOnly", {
        permissions: labelled(detail.slice(SUPERUSER_ONLY_PREFIX.length), t),
      });
    }
    if (detail === NAME_TAKEN_DETAIL) {
      return t("roles.errors.nameTaken");
    }
  }

  return parseApiError(err, t, {
    validationError: "permissions.errors.validation",
    genericError: "permissions.errors.generic",
  });
};
