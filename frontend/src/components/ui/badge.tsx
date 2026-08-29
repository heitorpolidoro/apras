import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary/10 text-primary",
        secondary: "bg-secondary text-secondary-foreground",
        outline: "border border-input text-foreground",
        // Status
        pending:
          "bg-[var(--status-pending-bg)] text-[var(--status-pending-fg)]",
        in_progress:
          "bg-[var(--status-in-progress-bg)] text-[var(--status-in-progress-fg)]",
        blocked:
          "bg-[var(--status-blocked-bg)] text-[var(--status-blocked-fg)]",
        completed:
          "bg-[var(--status-completed-bg)] text-[var(--status-completed-fg)]",
        canceled:
          "bg-[var(--status-canceled-bg)] text-[var(--status-canceled-fg)]",
        // Priority
        low: "bg-[var(--priority-low-bg)] text-[var(--priority-low-fg)]",
        medium:
          "bg-[var(--priority-medium-bg)] text-[var(--priority-medium-fg)]",
        high: "bg-[var(--priority-high-bg)] text-[var(--priority-high-fg)]",
        urgent:
          "bg-[var(--priority-urgent-bg)] text-[var(--priority-urgent-fg)]",
        // User status
        active: "bg-emerald-100 text-emerald-800",
        inactive: "bg-red-100 text-red-800",
        // Semantic
        destructive: "bg-red-100 text-red-800",
        warning: "bg-amber-100 text-amber-800",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends
    React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
