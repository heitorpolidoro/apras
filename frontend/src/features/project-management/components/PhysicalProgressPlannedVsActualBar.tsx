import React from "react";
import { useTranslation } from "react-i18next";

import { formatPercent } from "../lib/budgetFigures";
import { plannedProgress } from "../lib/plannedProgress";

/**
 * The report's planned-vs-actual physical-progress bar (APRAS-102).
 *
 * Mirrors `_one_bar` in `backend/app/services/project_report_service.py` and
 * the four parts the pinned stylesheet gives it (`.one .seg.a`, `.one .seg.b`,
 * `.one .seg.b.behind`, `.one .mark`):
 *
 * 1. the realized segment, from `0` to `min(planned, realized)`;
 * 2. the gap, from `min` to `max` — the distance between plan and reality, and
 *    the part that carries the status;
 * 3. the planned marker, a rule at `planned`;
 * 4. the `previsto` / `realizado` labels, both through `formatPercent(v, 0)`,
 *    because the report prints `42%` for a `42.5` measurement.
 *
 * **Behind plan is never signalled by colour alone** (WCAG 1.4.1): besides the
 * gap's tint, the plan label carries a short text state and the track's
 * `aria-label` names both numbers and the state.
 *
 * With no usable curve (`plannedProgress` returns `null`) the realized segment
 * is drawn **alone** — no gap, no marker, the plan label reads an em dash —
 * which is `_one_bar`'s own documented branch. The segment is still rendered:
 * "throws nothing" is not satisfied by rendering nothing.
 *
 * Two sanctioned divergences from the report's pixels, named so neither is
 * mistaken for a defect: the report's `.one .mark` is a `--card`-coloured
 * hairline, near-invisible on a light card, so the marker here is
 * `bg-foreground`; and the ahead gap is a `bg-primary/30` tint rather than the
 * report's gold `--brand-alt`, which this theme simply has no token for. It is
 * expected to look faint — it is an "ahead of plan" grace band, not a value
 * read off the pixels, and both numbers are printed as text either way.
 */

/** What the plan label reads with no usable curve. */
const NO_CURVE_LABEL = "—";

interface PhysicalProgressPlannedVsActualBarProps {
  physicalProgressPct: number;
  /** The raw `planned_progress_json`, judged by `plannedProgress` alone. */
  plannedProgressJson?: unknown;
  /**
   * An instant, injected only by tests. Read in **UTC** by `plannedProgress`,
   * which is where the reason is written down.
   */
  today?: Date;
}

export const PhysicalProgressPlannedVsActualBar: React.FC<
  PhysicalProgressPlannedVsActualBarProps
> = ({ physicalProgressPct, plannedProgressJson, today }) => {
  const { t } = useTranslation();

  const realized = physicalProgressPct || 0;
  const planned = plannedProgress(plannedProgressJson, today ?? new Date());
  const hasCurve = planned !== null;
  const low = hasCurve ? Math.min(planned, realized) : realized;
  const high = hasCurve ? Math.max(planned, realized) : realized;
  const behind = hasCurve && realized < planned;

  const plannedLabel = hasCurve
    ? `${formatPercent(planned, 0)}%`
    : NO_CURVE_LABEL;
  const realizedLabel = `${formatPercent(realized, 0)}%`;

  let ariaLabel: string;
  if (!hasCurve) {
    ariaLabel = t(
      "projects.plannedBar.ariaLabelNoCurve",
      "Avanço físico: sem curva prevista, realizado {{realized}}",
      { realized: realizedLabel },
    );
  } else if (behind) {
    ariaLabel = t(
      "projects.plannedBar.ariaLabelBehind",
      "Avanço físico: previsto {{planned}}, realizado {{realized}}, abaixo do previsto",
      { planned: plannedLabel, realized: realizedLabel },
    );
  } else {
    ariaLabel = t(
      "projects.plannedBar.ariaLabel",
      "Avanço físico: previsto {{planned}}, realizado {{realized}}",
      { planned: plannedLabel, realized: realizedLabel },
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
      <h3 className="font-semibold text-foreground">
        {t(
          "projects.plannedBar.title",
          "Avanço físico · previsto até hoje × realizado",
        )}
      </h3>

      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 text-xs">
        <span className="text-muted-foreground">
          {t("projects.plannedBar.planned", "previsto")}{" "}
          <strong
            data-testid="progress-planned-value"
            className="text-sm font-bold text-foreground"
          >
            {plannedLabel}
          </strong>
        </span>
        <span className="text-muted-foreground">
          {t("projects.plannedBar.realized", "realizado")}{" "}
          <strong
            data-testid="progress-realized-value"
            className="text-sm font-bold text-foreground"
          >
            {realizedLabel}
          </strong>
        </span>
        {behind && (
          <span className="text-destructive font-semibold">
            {t("projects.plannedBar.behind", "abaixo do previsto")}
          </span>
        )}
      </div>

      {/* The track. Positions are the **unrounded** percentages; only the two
          labels above go through `formatPercent`. */}
      <div
        role="img"
        aria-label={ariaLabel}
        className="relative w-full h-3 bg-muted rounded-full overflow-hidden"
      >
        <div
          data-testid="progress-realized"
          className="absolute inset-y-0 left-0 bg-primary"
          style={{ width: `${low}%` }}
        />
        {hasCurve && (
          <div
            data-testid="progress-gap"
            className={`absolute inset-y-0 ${behind ? "bg-destructive/70" : "bg-primary/30"}`}
            style={{ left: `${low}%`, width: `${high - low}%` }}
          />
        )}
        {hasCurve && (
          <div
            data-testid="progress-marker"
            className="absolute inset-y-0 w-0.5 bg-foreground"
            style={{ left: `${planned}%` }}
          />
        )}
      </div>

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{t("projects.plannedBar.start", "Início")}</span>
        <span>{t("projects.plannedBar.finish", "Conclusão")}</span>
      </div>
    </div>
  );
};
