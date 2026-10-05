import React from "react";
import { useTranslation } from "react-i18next";

import { budgetFigures, formatPercent } from "../lib/budgetFigures";
import { formatCurrency } from "../utils/currency";

/**
 * The public report's balance cylinder, in the internal tracker (APRAS-102).
 *
 * Mirrors `_budget_html` and `_cylinder_svg` in
 * `backend/app/services/project_report_service.py`: a tank filled to the
 * remaining-budget percentage beside four labelled money lines.
 *
 * **The division of labour over the clamp.** `budgetFigures` never clamps,
 * because `_budget_html` never clamps; this component clamps the *geometry*
 * only, exactly where `_cylinder_svg` has its own clamp, so no SVG coordinate
 * is ever negative or past the rim. The *printed* percentage is the helper's
 * own number, so an over-budget obra reads `-20%` here just as it does on the
 * report — a card reading `0%` would hide the one fact the síndico needs.
 *
 * The percentage is printed as text, so the figure is readable with no colour
 * and no SVG at all (WCAG 1.4.1), which is the same reason `_budget_html`
 * prints the balance beside its gauge.
 */

/** The tank's coordinate space, as `_cylinder_svg` defines it. */
const TOP = 20;
const BOTTOM = 140;
const RX = 50;
const RY = 12;

interface ProjectBudgetCylinderProps {
  totalBudget: number;
  executedBudget: number;
}

export const ProjectBudgetCylinder: React.FC<ProjectBudgetCylinderProps> = ({
  totalBudget,
  executedBudget,
}) => {
  const { t } = useTranslation();
  const figures = budgetFigures(totalBudget, executedBudget);

  // Geometry only. The text below reads `figures.remainingPct` untouched.
  const filled = Math.max(0, Math.min(100, figures.remainingPct));
  const surfaceY = BOTTOM - ((BOTTOM - TOP) * filled) / 100;
  const height = BOTTOM - surfaceY;
  const printed = `${formatPercent(figures.remainingPct, 0)}%`;
  const overBudget = figures.remainingPct < 0;
  // The number rides the liquid level (operator decision: inside the tank), but
  // never climbs above a readable line near the rim.
  const labelY = Math.max(surfaceY + 22, TOP + 30);

  const row = (label: string, value: string, strong: boolean) => (
    <div
      key={label}
      className="flex items-baseline justify-between gap-4 border-b border-border py-1.5"
    >
      <span className="text-xs text-muted-foreground">{label}</span>
      <strong
        className={`font-semibold text-foreground ${strong ? "text-base" : "text-sm"}`}
      >
        {value}
      </strong>
    </div>
  );

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
      <h3 className="font-semibold text-foreground">
        {t("projects.cylinder.title", "Orçamento da obra")}
      </h3>

      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          {row(
            t("projects.cylinder.total", "orçamento previsto"),
            formatCurrency(figures.total),
            true,
          )}
          {row(
            t("projects.cylinder.executed", "executado"),
            formatCurrency(figures.executed),
            false,
          )}
          {row(
            t("projects.cylinder.balance", "saldo"),
            formatCurrency(figures.balance),
            false,
          )}
          {row(
            t("projects.cylinder.executedPct", "% executado"),
            `${formatPercent(figures.executedPct, 1)}%`,
            false,
          )}
        </div>

        <div className="flex items-center gap-4">
          <svg
            viewBox="0 0 120 165"
            className="w-28 shrink-0"
            role="img"
            aria-label={t("projects.cylinder.ariaLabel", "Saldo restante {{percent}}", {
              percent: printed,
            })}
          >
            {/* The tank body. Its closing stroke is a *relative* upward
                vertical, so this `d` legitimately carries `v-120`. */}
            <path
              d={`M10 ${TOP} v${BOTTOM - TOP} a${RX} ${RY} 0 0 0 100 0 v-${BOTTOM - TOP}`}
              className="fill-muted stroke-border"
            />
            <path
              data-testid="cylinder-fill"
              d={`M10 ${surfaceY.toFixed(1)} v${height.toFixed(1)} a${RX} ${RY} 0 0 0 100 0 v-${height.toFixed(1)}`}
              className="fill-primary"
            />
            <ellipse
              data-testid="cylinder-surface"
              cx="60"
              cy={surfaceY.toFixed(1)}
              rx={RX}
              ry={RY}
              strokeWidth="1.2"
              className="fill-primary stroke-primary-foreground"
            />
            <ellipse
              cx="60"
              cy={TOP}
              rx={RX}
              ry={RY}
              fill="none"
              className="stroke-border"
            />
            {/* Operator decision: the balance number goes inside the tank,
                printed large over the green. `fill="currentColor"` is what lets
                the colour come from a semantic text token rather than a literal:
                `--primary-foreground` is the only AA-clean fill on `--primary`
                (5.7588:1), and an over-budget reading goes `--destructive`,
                where the empty tank has already dropped it onto the card. */}
            <text
              x="60"
              y={labelY.toFixed(1)}
              fontSize="16"
              fontWeight="700"
              textAnchor="middle"
              fill="currentColor"
              className={overBudget ? "text-destructive" : "text-primary-foreground"}
            >
              {printed}
            </text>
          </svg>

          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">
              {t("projects.cylinder.remaining", "Saldo restante")}
            </div>
            <p className="text-xs text-muted-foreground max-w-[16ch]">
              {t(
                "projects.cylinder.remainingNote",
                "{{amount}} ainda disponíveis do orçamento previsto.",
                { amount: formatCurrency(figures.balance) },
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
