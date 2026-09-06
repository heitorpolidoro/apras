import { describe, it, expect } from "vitest";
import {
  NAV_ITEMS,
  ROUTE_ACCESS,
} from "../../user-administration/access/routeAccess";
import type { AccessRule } from "../../../types/permissions";

/**
 * APRAS-44 §10.2: the three rules, evaluated against four permission sets.
 *
 * The one that matters is the **resident**: a `{ module: "infractions" }` rule
 * would offer them `/infractions`, the management list the API answers 403
 * for, because a module rule means "holds any `infractions:*`". `anyOf` is
 * what keeps the menu and the API agreeing.
 */

const evaluate = (rule: AccessRule, held: readonly string[]): boolean => {
  if ("anyOf" in rule) {
    return rule.anyOf.some((permission) => held.includes(permission));
  }
  if ("module" in rule) {
    return held.some((permission) => permission.startsWith(`${rule.module}:`));
  }
  // `{ superuser: true }`: never expressible as a permission, and none of the
  // three rules below is one.
  return false;
};

const FULL_STAFF = [
  "infractions:read",
  "infractions:create",
  "infractions:advance",
  "infractions:promote",
  "infractions:contest",
  "infractions:cycle_close",
  "infractions:my_lots_read",
  "infractions:rule_read",
  "infractions:rule_create",
  "infractions:rule_update",
  "infractions:rule_deactivate",
  "infractions:policy_update",
  "infractions:settings_update",
];
const RULES_ONLY = [
  "infractions:rule_read",
  "infractions:rule_create",
  "infractions:rule_update",
  "infractions:rule_deactivate",
  "infractions:policy_update",
];
const RESIDENT = ["infractions:my_lots_read", "infractions:contest"];
const NONE: string[] = [];

describe("infraction route access", () => {
  it("declares a rule for each of the three routes", () => {
    expect(ROUTE_ACCESS["/infractions"]).toEqual({
      anyOf: ["infractions:read"],
    });
    expect(ROUTE_ACCESS["/infraction-rules"]).toEqual({
      anyOf: [
        "infractions:rule_create",
        "infractions:rule_update",
        "infractions:rule_deactivate",
      ],
    });
    expect(ROUTE_ACCESS["/my-infractions"]).toEqual({
      anyOf: ["infractions:my_lots_read"],
    });
  });

  it("full staff reach all three", () => {
    for (const path of ["/infractions", "/infraction-rules", "/my-infractions"]) {
      expect(evaluate(ROUTE_ACCESS[path], FULL_STAFF)).toBe(true);
    }
  });

  it("a rules-only holder reaches the catalogue and not the management list", () => {
    expect(evaluate(ROUTE_ACCESS["/infraction-rules"], RULES_ONLY)).toBe(true);
    expect(evaluate(ROUTE_ACCESS["/infractions"], RULES_ONLY)).toBe(false);
    expect(evaluate(ROUTE_ACCESS["/my-infractions"], RULES_ONLY)).toBe(false);
  });

  it("a resident reaches only their own view -- never the management list", () => {
    expect(evaluate(ROUTE_ACCESS["/my-infractions"], RESIDENT)).toBe(true);
    expect(evaluate(ROUTE_ACCESS["/infractions"], RESIDENT)).toBe(false);
    expect(evaluate(ROUTE_ACCESS["/infraction-rules"], RESIDENT)).toBe(false);
    // The regression a `{ module }` rule would introduce, stated explicitly.
    expect(evaluate({ module: "infractions" }, RESIDENT)).toBe(true);
  });

  it("a holder of nothing reaches none of the three", () => {
    for (const path of ["/infractions", "/infraction-rules", "/my-infractions"]) {
      expect(evaluate(ROUTE_ACCESS[path], NONE)).toBe(false);
    }
  });

  it("every nav entry's access IS its route's rule", () => {
    const entries = NAV_ITEMS.filter((item) =>
      ["/infractions", "/infraction-rules", "/my-infractions"].includes(
        item.path,
      ),
    );
    expect(entries).toHaveLength(3);
    for (const entry of entries) {
      expect(entry.access).toBe(ROUTE_ACCESS[entry.path]);
    }
    expect(entries.map((entry) => entry.labelKey)).toEqual([
      "nav.infractions",
      "nav.infractionRules",
      "nav.myInfractions",
    ]);
  });
});
