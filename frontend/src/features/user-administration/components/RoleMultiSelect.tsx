import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Badge } from "../../../components/ui/badge";
import type { Role } from "../../../types/auth";

interface RoleMultiSelectProps {
  roles: Role[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

/**
 * Lightweight multi-select checkbox list for Roles, built on the
 * existing Button/Badge primitives. There is no multi-select primitive in
 * `components/ui` yet, so this is scoped to the admin role simulation
 * feature rather than added as a shared primitive.
 */
const RoleMultiSelect: React.FC<RoleMultiSelectProps> = ({
  roles,
  selectedIds,
  onChange,
}) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const toggleId = (id: string) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((existingId) => existingId !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const selectedRoles = roles.filter((role) =>
    selectedIds.includes(role.id),
  );

  return (
    <div className="relative" ref={containerRef}>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className="w-full justify-between font-normal"
      >
        <span className="flex flex-wrap gap-1 items-center overflow-hidden">
          {selectedRoles.length === 0 ? (
            <span className="text-muted-foreground">
              {t("simulation.rolesPlaceholder")}
            </span>
          ) : (
            selectedRoles.map((role) => (
              <Badge key={role.id} variant="secondary">
                {role.name}
              </Badge>
            ))
          )}
        </span>
        <ChevronDown className="size-4 shrink-0 opacity-60" />
      </Button>

      {isOpen && (
        <ul
          role="listbox"
          aria-multiselectable="true"
          className="absolute left-0 z-50 mt-1 w-full min-w-[14rem] max-h-64 overflow-y-auto rounded-md border border-input bg-popover p-1 shadow-md"
        >
          {roles.length === 0 ? (
            <li className="px-2 py-1.5 text-xs text-muted-foreground">
              {t("simulation.noRolesAvailable")}
            </li>
          ) : (
            roles.map((role) => {
              const checked = selectedIds.includes(role.id);
              return (
                <li key={role.id}>
                  <label className="flex items-center gap-2 px-2 py-1.5 rounded-sm text-sm cursor-pointer hover:bg-accent">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleId(role.id)}
                      className="size-3.5 accent-primary"
                    />
                    {role.name}
                  </label>
                </li>
              );
            })
          )}
        </ul>
      )}
    </div>
  );
};

export default RoleMultiSelect;
