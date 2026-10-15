import type React from "react";

interface ModuleCardProps {
  /** The checkbox `id`; the whole card is its label. */
  id: string;
  /** The package name: a bundle's title, or the module's own name. */
  title: string;
  /** The features the package switches on; listed only for a bundle. */
  features: readonly string[];
  checked: boolean;
  disabled: boolean;
  onChange: () => void;
  /** Trailing details beside the title (core badge, price). */
  children?: React.ReactNode;
}

/**
 * One contractable package on `/admin/modules` and `/subscription`
 * (APRAS-128): a card with a checkbox, the package title and, for a bundle,
 * the list of features it toggles together.
 */
const ModuleCard = ({
  id,
  title,
  features,
  checked,
  disabled,
  onChange,
  children,
}: ModuleCardProps) => (
  <label
    htmlFor={id}
    className="flex items-start gap-3 rounded-lg border border-border bg-card p-3 text-sm shadow-sm"
  >
    <input
      id={id}
      type="checkbox"
      className="mt-0.5"
      // The visible label also carries the badge and the price, so the
      // accessible name is stated explicitly as the package title.
      aria-label={title}
      checked={checked}
      disabled={disabled}
      onChange={onChange}
    />
    <span className="flex flex-col gap-1">
      <span className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-foreground">{title}</span>
        {children}
      </span>
      {features.length > 1 && (
        <ul className="list-disc pl-4 text-xs text-muted-foreground">
          {features.map((feature) => (
            <li key={feature}>{feature}</li>
          ))}
        </ul>
      )}
    </span>
  </label>
);

export default ModuleCard;
