/**
 * The balance cylinder (APRAS-102), where the clamp lives.
 *
 * `budgetFigures` never clamps, because `_budget_html` never clamps. The
 * component clamps **geometry only** — `_cylinder_svg @ 869` does exactly that —
 * and prints the helper's own, unclamped percentage, so an over-budget obra
 * reads `-20%` here just as it does on the public report.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProjectBudgetCylinder } from "../components/ProjectBudgetCylinder";

/** The tank's own coordinate space, mirroring `_cylinder_svg`. */
const TOP = 20;
const BOTTOM = 140;

/**
 * The fill path's two y readings: the move-to's `y` (`yStart`) and the first
 * vertical operand (`h`, the fill height).
 *
 * `h` is a **relative** operand and not a coordinate, which is why only
 * `yStart` is range-checked against the tank below. The `d` the component emits
 * is `M10 <yStart> v<h> a50 12 0 0 0 100 0 v-<h>`.
 */
const fillGeometry = (d: string): { yStart: number; h: number } => {
  const match = /^M\s*[\d.]+\s+([\d.]+)\s*v\s*(-?[\d.]+)/.exec(d);
  if (!match) {
    throw new Error(`The fill path is not the expected shape: ${d}`);
  }
  return { yStart: Number(match[1]), h: Number(match[2]) };
};

/** Every node carrying a test id, so "exactly one" is asserted, not assumed. */
const allById = (container: HTMLElement, id: string): Element[] =>
  Array.from(container.querySelectorAll(`[data-testid="${id}"]`));

describe("ProjectBudgetCylinder", () => {
  it("shows the four labelled money lines, with saldo and one decimal", () => {
    render(<ProjectBudgetCylinder totalBudget={480000} executedBudget={204000} />);

    for (const label of ["orçamento previsto", "executado", "saldo", "% executado"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    // `saldo = total - executed`: a swapped operand order reads -276.000,00.
    expect(screen.getByText(/276\.000,00/)).toBeInTheDocument();
    expect(screen.getByText("42.5%")).toBeInTheDocument();
  });

  it("empties the tank over budget while printing the negative percentage", () => {
    // `executed > total`: the geometry clamps to an empty tank, the text does
    // not. An implementation that forgot the clamp yields `yStart = 164` and
    // `h = -24` here, so all three geometry assertions fail.
    const { container } = render(
      <ProjectBudgetCylinder totalBudget={100000} executedBudget={120000} />,
    );

    // Preconditions: neither node is unique by tag -- the figure renders two
    // `path` nodes (outline and fill) and two `ellipse` nodes (liquid surface
    // and rim) -- so a missing id must fail as a stated assertion rather than
    // by throwing inside the `d` parse below.
    const fills = allById(container, "cylinder-fill");
    const surfaces = allById(container, "cylinder-surface");
    expect(fills).toHaveLength(1);
    expect(surfaces).toHaveLength(1);

    const { yStart, h } = fillGeometry(fills[0].getAttribute("d") ?? "");
    const surfaceCy = Number(surfaces[0].getAttribute("cy"));

    expect(yStart).toBe(BOTTOM);
    expect(h).toBe(0);
    expect(surfaceCy).toBe(BOTTOM);
    // The two absolute y coordinates this test reads, and no other number in
    // the markup: the move-to's `x` is 10 and the arc's `rx 50 ry 12` are
    // absolute lengths outside this range by design.
    for (const y of [yStart, surfaceCy]) {
      expect(y).toBeGreaterThanOrEqual(TOP);
      expect(y).toBeLessThanOrEqual(BOTTOM);
    }

    // The printed number is the helper's own, unclamped: `-20%`, as
    // `_budget_html` prints it, and marked as the bad news it is.
    // `getAttribute("class")` and not `.className`: on an SVG element the
    // latter is an `SVGAnimatedString`, so a `toContain` over it passes for
    // every input and asserts nothing.
    const printed = screen.getByText("-20%");
    expect(printed).toBeInTheDocument();
    expect(printed.getAttribute("class")).toContain("text-destructive");
  });

  it("fills the tank completely for a zero budget", () => {
    // `total = 0` is 0 % executed by definition, hence 100 % remaining.
    const { container } = render(
      <ProjectBudgetCylinder totalBudget={0} executedBudget={0} />,
    );

    const fills = allById(container, "cylinder-fill");
    const surfaces = allById(container, "cylinder-surface");
    expect(fills).toHaveLength(1);
    expect(surfaces).toHaveLength(1);

    const { yStart, h } = fillGeometry(fills[0].getAttribute("d") ?? "");
    const surfaceCy = Number(surfaces[0].getAttribute("cy"));

    expect(yStart).toBe(TOP);
    expect(h).toBe(BOTTOM - TOP);
    for (const y of [yStart, surfaceCy]) {
      expect(y).toBeGreaterThanOrEqual(TOP);
      expect(y).toBeLessThanOrEqual(BOTTOM);
    }
    expect(screen.getByText("0.0%")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("prints 56% and not 57% at a real obra's half-way tie", () => {
    // `total = 400000, executed = 174000` -> `remaining_pct = 56.5`, which the
    // public report prints as `56%`. A `toFixed(0)` frontend prints `57%`: the
    // same obra, the same day, two numbers.
    render(<ProjectBudgetCylinder totalBudget={400000} executedBudget={174000} />);

    expect(screen.getByText("56%")).toBeInTheDocument();
    expect(screen.queryByText("57%")).not.toBeInTheDocument();
  });
});
