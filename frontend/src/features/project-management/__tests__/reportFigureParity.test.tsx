/**
 * The parity pin (APRAS-102): the report's figures and the tracker's are
 * computed twice, in two languages, and the only thing that stops them
 * diverging is that the frontend's expectations are **bytes the backend
 * produced**.
 *
 * `backend/tests/data/report_page_null_detail_baseline.html` is the single real
 * `div.page` the backend renders for a declared fixture project; the backend
 * suite pins that file byte for byte
 * (`tests/test_project_stage_detail.py::test_the_all_null_page_renders_the_committed_baseline`).
 * This case takes the **inputs** out of it, feeds them to the new helper and
 * components, and compares the **derived** figures — which are not re-derivable
 * from the inputs without doing the arithmetic, so neither side's expectation is
 * hand-written and a hardcode-both-sides pass is impossible.
 *
 * `../backend/tests/data` is the one directory outside the frontend root that
 * `vitest.config.ts` allows, for exactly this reason (APRAS-118's precedent).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import baselinePage from "../../../../../backend/tests/data/report_page_null_detail_baseline.html?raw";
import { PhysicalProgressPlannedVsActualBar } from "../components/PhysicalProgressPlannedVsActualBar";
import { ProjectBudgetCylinder } from "../components/ProjectBudgetCylinder";
import { plannedProgress } from "../lib/plannedProgress";

/**
 * `_brl` builds `"R$ " + …` with an ordinary U+0020; `formatCurrency` is
 * `Intl.NumberFormat('pt-BR', { style: 'currency' })`, which emits U+00A0 —
 * verified: the rendered string's first three code points are `52 24 A0`. This
 * maps U+00A0 and U+202F to U+0020 **and changes nothing else**: digits, the
 * thousands separators, the decimal comma and the `R$` prefix are still compared
 * character for character. Writing a second currency formatter to dodge the NBSP
 * is explicitly not the way out — `utils/currency.ts` stays the one formatter.
 */
/** U+00A0, the no-break space `Intl` emits after `R$`. */
const NBSP = String.fromCharCode(0x00a0);
/** U+202F, the narrow no-break space some `Intl` builds emit instead. */
const NARROW_NBSP = String.fromCharCode(0x202f);
/** U+0020, the ordinary space `_brl` writes. */
const SPACE = String.fromCharCode(0x0020);

const normaliseSpaces = (value: string): string =>
  // Built from code points rather than from the characters themselves: a
  // literal NBSP in a source file is invisible, and `no-irregular-whitespace`
  // rejects it. Two replacements, so the mapping is legible one line at a time.
  value.split(NBSP).join(SPACE).split(NARROW_NBSP).join(SPACE);

/** pt-BR money back to a number: `R$ 480.000,00` -> `480000`. */
const parseBrl = (value: string): number =>
  Number(
    normaliseSpaces(value)
      .replace(/[^\d,.-]/g, "")
      .replace(/\./g, "")
      .replace(",", "."),
  );

/**
 * Exactly-one selection, named so a renamed backend class fails loudly instead
 * of yielding a vacuous fixture. A selector matching zero nodes is the defect
 * `docs/audits/APRAS-111-test-suite-audit.md` found 19 times in this tree: the
 * comparison then becomes trivially true and the test keeps passing while the
 * two implementations drift.
 */
const exactlyOne = (root: Document, selector: string): Element => {
  const found = root.querySelectorAll(selector);
  if (found.length !== 1) {
    throw new Error(
      `report_page_null_detail_baseline.html matched ${found.length} nodes for ` +
        `\`${selector}\`, expected exactly 1; the APRAS-102 parity pin cannot ` +
        `read the baseline's figures.`,
    );
  }
  return found[0];
};

const baseline = new DOMParser().parseFromString(baselinePage, "text/html");

/** The four money lines, in the order `_budget_html` prints them. */
const BUDGET_ROWS = baseline.querySelectorAll(".budget-col .budget-row");

/** The value a `.budget-row` prints, by its position in that section. */
const rowValue = (index: number): string => {
  const strong = BUDGET_ROWS[index]?.querySelector("strong");
  if (!strong) {
    throw new Error(
      `report_page_null_detail_baseline.html has no \`strong\` in budget row ` +
        `${index}; the APRAS-102 parity pin cannot read the baseline's figures.`,
    );
  }
  return strong.textContent ?? "";
};

/** The label beside a row's value, so the positional read is not blind. */
const rowLabel = (index: number): string =>
  BUDGET_ROWS[index]?.querySelector("small")?.textContent ?? "";

/** The value printed inside the cylinder's own caption — the `58%`. */
const CYLINDER_REMAINING = exactlyOne(baseline, ".cyl .txt strong").textContent ?? "";

/** The rendered `strong` beside a cylinder row's label. */
const renderedRowValue = (label: string): string => {
  const labelNode = screen.getByText(label);
  const value = labelNode.parentElement?.querySelector("strong");
  if (!value) {
    throw new Error(`The rendered cylinder has no value beside \`${label}\`.`);
  }
  return value.textContent ?? "";
};

describe("the report baseline pins the tracker's budget figures", () => {
  it("is not degenerate: five nodes, each matched exactly once", () => {
    // Asserted **before** anything is compared. Four rows plus the one
    // `.cyl .txt strong` that supplies the remaining percentage: if any is
    // absent, the comparisons below are vacuous rather than wrong.
    expect(BUDGET_ROWS).toHaveLength(4);
    for (let index = 0; index < 4; index += 1) {
      expect(BUDGET_ROWS[index].querySelectorAll("strong")).toHaveLength(1);
    }
    expect(baseline.querySelectorAll(".cyl .txt strong")).toHaveLength(1);

    // The labels, so the positional read above is anchored to the backend's own
    // order rather than hoping it never changes.
    expect(rowLabel(0)).toBe("Orçamento previsto");
    expect(rowLabel(1)).toBe("Executado");
    expect(rowLabel(2)).toBe("Saldo");
    expect(rowLabel(3)).toBe("% executado");

    // The two parsed inputs, both finite and both > 0.
    expect(parseBrl(rowValue(0))).toBe(480000);
    expect(parseBrl(rowValue(1))).toBe(204000);

    // Each expected string is non-empty and carries a digit, so an emptied node
    // cannot be compared equal to an emptied render.
    for (const expected of [rowValue(2), rowValue(3), CYLINDER_REMAINING]) {
      expect(expected.length).toBeGreaterThan(0);
      expect(expected).toMatch(/\d/);
    }
  });

  it("fails loudly, not vacuously, when the backend renames a class", () => {
    // The non-degeneracy guard above is only worth having if it fires. Proved
    // on a tampered copy of the baseline rather than argued: a renamed `.cyl`
    // makes the selector match zero nodes, and `exactlyOne` must throw its
    // named error instead of handing back an empty string that compares equal
    // to another empty string.
    const tampered = new DOMParser().parseFromString(
      baselinePage.replace('class="cyl"', 'class="cylinder"'),
      "text/html",
    );

    expect(tampered.querySelectorAll(".cyl .txt strong")).toHaveLength(0);
    expect(() => exactlyOne(tampered, ".cyl .txt strong")).toThrow(
      /matched 0 nodes/,
    );
    expect(() => exactlyOne(tampered, ".cyl .txt strong")).toThrow(
      /APRAS-102 parity pin/,
    );
    // And it fires on a *duplicated* node too, not only a missing one: two
    // matches mean the positional reads below are ambiguous.
    const doubled = new DOMParser().parseFromString(
      `${baselinePage}${baselinePage}`,
      "text/html",
    );
    expect(() => exactlyOne(doubled, ".cyl .txt strong")).toThrow(
      /matched 2 nodes/,
    );
  });

  it("renders the baseline's own saldo, % executado and remaining percentage", () => {
    const total = parseBrl(rowValue(0));
    const executed = parseBrl(rowValue(1));

    render(
      <ProjectBudgetCylinder totalBudget={total} executedBudget={executed} />,
    );

    expect(normaliseSpaces(renderedRowValue("saldo"))).toBe(
      normaliseSpaces(rowValue(2)),
    );
    expect(normaliseSpaces(renderedRowValue("% executado"))).toBe(
      normaliseSpaces(rowValue(3)),
    );
    // `R$ 276.000,00`, `42.5%` and `58%`, as the backend printed them.
    expect(normaliseSpaces(rowValue(2))).toBe("R$ 276.000,00");
    expect(normaliseSpaces(rowValue(3))).toBe("42.5%");
    expect(normaliseSpaces(CYLINDER_REMAINING)).toBe("58%");
    expect(
      screen.getByText(normaliseSpaces(CYLINDER_REMAINING)),
    ).toBeInTheDocument();
  });
});

describe("the report baseline pins the tracker's planned-vs-actual bar", () => {
  /**
   * `tests/test_project_stage_detail.PLANNED_CURVE`, the curve that produced the
   * baseline's `previsto 64%`. All three points are in 2020, so the latest-past
   * selection has the same forward stability the backend claims for itself and
   * this pin cannot rot with the calendar.
   */
  const PLANNED_CURVE = [
    { month: "2020-01", pct: 8.0 },
    { month: "2020-02", pct: 31.5 },
    { month: "2020-03", pct: 64.0 },
  ];

  it("reads the baseline's planned-to-date figure out of that curve", () => {
    const planned = baseline.querySelector(".pv .tag.plan b")?.textContent;
    if (!planned) {
      throw new Error(
        "report_page_null_detail_baseline.html has no `.pv .tag.plan b`; the " +
          "APRAS-102 parity pin cannot read the baseline's planned figure.",
      );
    }

    expect(planned).toBe("64%");
    expect(`${plannedProgress(PLANNED_CURVE)}%`).toBe(planned);
  });

  it("renders the baseline's 42% for a 42.5 measurement", () => {
    const realized = baseline.querySelector(".pv .tag.real b")?.textContent;
    if (!realized) {
      throw new Error(
        "report_page_null_detail_baseline.html has no `.pv .tag.real b`; the " +
          "APRAS-102 parity pin cannot read the baseline's realized figure.",
      );
    }
    // `_one_bar` prints both percentages with `:.0f`, so 42.5 is 42 -- and
    // `toFixed(0)` would print 43.
    expect(realized).toBe("42%");

    render(
      <PhysicalProgressPlannedVsActualBar
        physicalProgressPct={42.5}
        plannedProgressJson={PLANNED_CURVE}
      />,
    );

    expect(screen.getByTestId("progress-realized-value").textContent).toBe(
      realized,
    );
  });
});
