import React, { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Search, UserX } from "lucide-react";
import type { User } from "../../../types/auth";
import { Input } from "../../../components/ui/input";
import { normalizeText } from "../utils/taskUtils";

interface AssigneePickerProps {
  /** The people a task may be assigned to (`useAssignableUsers`). */
  users: User[];
  /** The currently assigned user's id, or null/"" for no assignee. */
  value: string | null;
  /** Reports the chosen id, or `null` for the explicit no-assignee option. */
  onChange: (id: string | null) => void;
  disabled?: boolean;
  id?: string;
}

/** The two initials shown in an option's avatar. */
const initialsOf = (user: User): string =>
  (user.full_name || user.email)
    .split(" ")
    .map((part) => part[0])
    .join("")
    .substring(0, 2)
    .toUpperCase();

/**
 * A searchable assignee combobox over the assignable-user list: one option per
 * person with their initials, name and role, plus an explicit "leave
 * unassigned" option. It submits the very same `assigned_to_id: string | null`
 * the plain `<select>` it replaces did — no payload change.
 */
const AssigneePicker: React.FC<AssigneePickerProps> = ({
  users,
  value,
  onChange,
  disabled = false,
  id,
}) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const selected = users.find((user) => user.id === value) ?? null;
  const selectedLabel = selected
    ? selected.full_name || selected.email
    : "";

  const matches = useMemo(() => {
    const needle = normalizeText(query).trim();
    if (!needle) return users;
    return users.filter(
      (user) =>
        normalizeText(user.full_name).includes(needle) ||
        normalizeText(user.email).includes(needle),
    );
  }, [users, query]);

  /** The no-assignee option is always last, and is never filtered out. */
  const optionCount = matches.length + 1;

  const open = () => {
    if (disabled) return;
    setIsOpen(true);
  };

  const close = () => {
    setIsOpen(false);
    setQuery(null);
    setActiveIndex(-1);
  };

  const choose = (index: number) => {
    onChange(index < matches.length ? matches[index].id : null);
    close();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!isOpen) {
        open();
        setActiveIndex(0);
        return;
      }
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((current) => {
        const next = current + step;
        if (next < 0) return optionCount - 1;
        if (next >= optionCount) return 0;
        return next;
      });
      return;
    }
    if (e.key === "Enter" && isOpen) {
      e.preventDefault();
      choose(activeIndex < 0 ? 0 : activeIndex);
      return;
    }
    if (e.key === "Escape" && isOpen) {
      e.preventDefault();
      close();
    }
  };

  const listboxId = `${id ?? "assignee"}-listbox`;

  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
      <Input
        id={id}
        role="combobox"
        className="pl-9"
        autoComplete="off"
        disabled={disabled}
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-autocomplete="list"
        placeholder={t("tasks.form.assigneeSearchPlaceholder")}
        value={query ?? selectedLabel}
        onFocus={open}
        onClick={open}
        onBlur={() => {
          // Let a click on an option run before the listbox unmounts.
          blurTimer.current = setTimeout(close, 0);
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setActiveIndex(-1);
          open();
        }}
        onKeyDown={handleKeyDown}
      />

      {isOpen && (
        <ul
          id={listboxId}
          role="listbox"
          aria-label={t("tasks.form.assigneeLabel")}
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border border-border bg-card shadow-lg"
        >
          {matches.length === 0 && (
            <li className="px-3 py-2 text-xs italic text-muted-foreground">
              {t("tasks.form.assigneeNoResults")}
            </li>
          )}
          {matches.map((user, index) => (
            <li
              key={user.id}
              role="option"
              aria-selected={index === activeIndex}
              className={`flex items-center gap-3 px-3 py-2 cursor-pointer ${
                index === activeIndex ? "bg-muted" : "hover:bg-muted/60"
              }`}
              onMouseDown={(e) => e.preventDefault()}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => {
                if (blurTimer.current) clearTimeout(blurTimer.current);
                choose(index);
              }}
            >
              <span className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary-text">
                {initialsOf(user)}
              </span>
              <span className="leading-tight">
                <span className="block text-sm font-medium text-foreground">
                  {user.full_name || user.email}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {user.roles?.length
                    ? user.roles.map((role) => role.name).join(", ")
                    : t("tasks.form.assigneeNoRole")}
                </span>
              </span>
            </li>
          ))}
          <li
            role="option"
            aria-selected={activeIndex === matches.length}
            className={`flex items-center gap-3 border-t border-border/60 px-3 py-2 cursor-pointer ${
              activeIndex === matches.length ? "bg-muted" : "hover:bg-muted/60"
            }`}
            onMouseDown={(e) => e.preventDefault()}
            onMouseEnter={() => setActiveIndex(matches.length)}
            onClick={() => {
              if (blurTimer.current) clearTimeout(blurTimer.current);
              choose(matches.length);
            }}
          >
            <span className="flex size-8 items-center justify-center rounded-full border border-dashed border-border text-muted-foreground">
              <UserX className="size-4" />
            </span>
            <span className="text-sm text-muted-foreground">
              {t("tasks.form.assigneeNone")}
            </span>
          </li>
        </ul>
      )}
    </div>
  );
};

export default AssigneePicker;
