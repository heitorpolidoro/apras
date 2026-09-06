import { describe, it, expect } from "vitest";
import i18n from "../index";
import en from "../locales/en.json";
import pt from "../locales/pt.json";

describe("i18n configuration", () => {
  it("should be initialized", () => {
    expect(i18n.isInitialized).toBe(true);
  });

  it("should have resources for en and pt", () => {
    expect(i18n.options.resources).toHaveProperty("en");
    expect(i18n.options.resources).toHaveProperty("pt");
  });

  it("should use en as default language", () => {
    expect(i18n.language).toBe("en");
  });

  it("should translate correctly", () => {
    // Just a simple check to see if translation works
    expect(i18n.t("common.appName")).toBeDefined();
  });
});

/**
 * The 28 catalogue modules (APRAS-39 §2.2, APRAS-40 §2.1, APRAS-44 §3.3),
 * listed here from a
 * local constant
 * rather than derived: a derivation from the label files would compare them
 * with themselves and assert nothing.
 *
 * A local constant on its own only catches a *removed* label, so this list is
 * one half of a pair. The other half is
 * `backend/tests/test_module_vocabulary.py::test_the_catalogue_modules_are_the_ones_the_ui_labels`,
 * which asserts `permissions.MODULES` equals these same 28 names and whose
 * failure message names this file. Neither side can import the other across
 * the language boundary, so an *added* catalogue module turns the backend
 * case red and a *removed or unlabelled* one turns this case red.
 */
const MODULES = [
  "access_control",
  "announcements",
  "assemblies",
  "assets",
  "authorizations",
  "billing",
  "categories",
  "documents",
  "feedback",
  "finance",
  "gate",
  "infractions",
  "inventory",
  "lots",
  "occurrences",
  "packages",
  "projects",
  "purchases",
  "reservations",
  "residents",
  "roles",
  "spaces",
  "tasks",
  "tenants",
  "uploads",
  "users",
  "visitors",
  "votes",
] as const;

type Tree = { [key: string]: unknown };

/** Every leaf key path of a resource tree, e.g. `common.appName`. */
const keyPaths = (tree: Tree, prefix = ""): string[] =>
  Object.entries(tree).flatMap(([key, value]) =>
    value !== null && typeof value === "object" && !Array.isArray(value)
      ? keyPaths(value as Tree, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );

/**
 * The parity pin APRAS-39 §11 adds. It is a *pin*, not a fix: the two files
 * already had identical key sets when it was written, so its only cost is
 * that every future key must be added to both. An `arrayContaining` or an
 * allowlist of known-missing keys would defeat the point.
 */
describe("locale parity", () => {
  it("has identical key sets for en and pt", () => {
    const inEn = new Set(keyPaths(en as Tree));
    const inPt = new Set(keyPaths(pt as Tree));

    const onlyInEn = [...inEn].filter((key) => !inPt.has(key)).sort();
    const onlyInPt = [...inPt].filter((key) => !inEn.has(key)).sort();

    expect(onlyInEn).toEqual([]);
    expect(onlyInPt).toEqual([]);
  });

  it("labels every module in both languages", () => {
    for (const tree of [en, pt] as Tree[]) {
      const names = (tree.modules as Tree | undefined)?.names as
        | Tree
        | undefined;
      expect(names).toBeDefined();
      expect(Object.keys(names ?? {}).sort()).toEqual([...MODULES].sort());
      for (const label of Object.values(names ?? {})) {
        expect(typeof label).toBe("string");
        expect(label).not.toBe("");
      }
    }
  });
});
