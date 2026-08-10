import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { Badge } from "../../../components/ui/badge";
import type { UserType } from "../../../types/auth";

interface UserTypeMultiSelectProps {
  userTypes: UserType[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

/**
 * Lightweight multi-select checkbox list for UserTypes, built on the
 * existing Button/Badge primitives. There is no multi-select primitive in
 * `components/ui` yet, so this is scoped to the admin role simulation
 * feature rather than added as a shared primitive.
 */
const UserTypeMultiSelect: React.FC<UserTypeMultiSelectProps> = ({
  userTypes,
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

  const selectedUserTypes = userTypes.filter((userType) =>
    selectedIds.includes(userType.id),
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
          {selectedUserTypes.length === 0 ? (
            <span className="text-muted-foreground">
              {t("simulation.userTypesPlaceholder")}
            </span>
          ) : (
            selectedUserTypes.map((userType) => (
              <Badge key={userType.id} variant="secondary">
                {userType.name}
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
          {userTypes.length === 0 ? (
            <li className="px-2 py-1.5 text-xs text-muted-foreground">
              {t("simulation.noUserTypesAvailable")}
            </li>
          ) : (
            userTypes.map((userType) => {
              const checked = selectedIds.includes(userType.id);
              return (
                <li key={userType.id}>
                  <label className="flex items-center gap-2 px-2 py-1.5 rounded-sm text-sm cursor-pointer hover:bg-accent">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleId(userType.id)}
                      className="size-3.5 accent-primary"
                    />
                    {userType.name}
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

export default UserTypeMultiSelect;
