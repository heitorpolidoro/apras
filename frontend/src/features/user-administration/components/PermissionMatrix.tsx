import React, { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import {
  moduleLabel,
  permissionLabel,
  sortModules,
} from "../utils/permissionLabels";
import type { PermissionDescriptor } from "../../../types/permissions";
import type { PermissionSet } from "../access/useCanAccess";

interface PermissionMatrixProps {
  /** The whole catalogue, from `GET /permissions/`. */
  descriptors: readonly PermissionDescriptor[];
  /** The permissions currently checked. */
  selected: readonly string[];
  onChange: (permissions: string[]) => void;
  /** The author's own effective set — the mirror of `assert_can_grant`. */
  mySet: PermissionSet;
}

/**
 * One `<fieldset>` per module, one checkbox per permission (APRAS-48 §6.3).
 *
 * A box is **disabled** iff the permission is `superuser_only` or the author
 * does not hold it — the exact mirror of the backend's `assert_can_grant`,
 * in the same order, so the UI can only ever be a preview of the 403 rather
 * than a second policy.
 *
 * A disabled box that is **already checked** in the stored bundle stays
 * checked and disabled and is resent unchanged on save: otherwise renaming a
 * group would silently strip the permissions its author cannot grant.
 *
 * There are deliberately **no menu checkboxes** — `allowed_menus` is derived
 * from the selection on save (`deriveAllowedMenus`).
 */
const PermissionMatrix: React.FC<PermissionMatrixProps> = ({
  descriptors,
  selected,
  onChange,
  mySet,
}) => {
  const { t } = useTranslation();
  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const byModule = useMemo(() => {
    const groups = new Map<string, PermissionDescriptor[]>();
    for (const descriptor of descriptors) {
      const bucket = groups.get(descriptor.module);
      if (bucket) bucket.push(descriptor);
      else groups.set(descriptor.module, [descriptor]);
    }
    return groups;
  }, [descriptors]);

  const modules = useMemo(
    () => sortModules([...byModule.keys()]),
    [byModule],
  );

  const isLocked = (descriptor: PermissionDescriptor) =>
    descriptor.superuser_only || !mySet.has(descriptor.permission);

  const toggle = (permission: string, checked: boolean) => {
    onChange(
      checked
        ? [...selected, permission]
        : selected.filter((value) => value !== permission),
    );
  };

  /** Affects only the module's **enabled** boxes; locked ones keep their state. */
  const setModule = (module: string, checked: boolean) => {
    const targets = (byModule.get(module) ?? []).filter(
      (descriptor) => !isLocked(descriptor),
    );
    const keys = targets.map((descriptor) => descriptor.permission);
    onChange(
      checked
        ? [...new Set([...selected, ...keys])]
        : selected.filter((value) => !keys.includes(value)),
    );
  };

  return (
    <div className="space-y-4">
      {modules.map((module) => {
        const rows = byModule.get(module) ?? [];
        const checkedCount = rows.filter((descriptor) =>
          selectedSet.has(descriptor.permission),
        ).length;
        return (
          <fieldset
            key={module}
            className="rounded-xl border bg-card p-4"
            data-module={module}
          >
            <legend className="px-2 text-sm font-semibold text-foreground">
              {moduleLabel(module, t)}
            </legend>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-muted-foreground">
                {t("permissions.selectedCount", { count: checkedCount })}
              </span>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setModule(module, true)}
              >
                {t("permissions.selectAll")}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setModule(module, false)}
              >
                {t("permissions.clearAll")}
              </Button>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {rows.map((descriptor) => {
                const locked = isLocked(descriptor);
                return (
                  <label
                    key={descriptor.permission}
                    className="flex items-center gap-2 text-sm cursor-pointer select-none"
                    title={descriptor.permission}
                  >
                    <input
                      type="checkbox"
                      data-permission={descriptor.permission}
                      checked={selectedSet.has(descriptor.permission)}
                      disabled={locked}
                      title={
                        locked
                          ? t(
                              descriptor.superuser_only
                                ? "permissions.disabledSuperuserOnly"
                                : "permissions.disabledNotHeld",
                            )
                          : descriptor.permission
                      }
                      onChange={(event) =>
                        toggle(descriptor.permission, event.target.checked)
                      }
                      className="rounded border-gray-300 text-primary focus:ring-primary h-4 w-4"
                    />
                    <span className={locked ? "text-muted-foreground" : ""}>
                      {permissionLabel(descriptor.permission, t)}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        );
      })}
    </div>
  );
};

export default PermissionMatrix;
