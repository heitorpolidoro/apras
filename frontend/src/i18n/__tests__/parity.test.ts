import { describe, it, expect } from "vitest";
import en from "../locales/en.json";
import pt from "../locales/pt.json";

/**
 * pt/en structural parity, made mechanical by IAM F4 (APRAS-48 §9).
 *
 * A key present in one locale and missing from the other renders as its raw
 * dotted path for half the users; with 110 new permission keys added in this
 * slice alone, catching that by eye stopped being realistic.
 */
type Tree = Record<string, unknown>;

const flatten = (tree: Tree, prefix = ""): string[] =>
  Object.entries(tree).flatMap(([key, value]) =>
    value !== null && typeof value === "object" && !Array.isArray(value)
      ? flatten(value as Tree, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );

const EN_KEYS = flatten(en as Tree).sort();
const PT_KEYS = flatten(pt as Tree).sort();

describe("i18n locale parity", () => {
  it("en and pt have identical flattened key sets", () => {
    const onlyInEn = EN_KEYS.filter((key) => !PT_KEYS.includes(key));
    const onlyInPt = PT_KEYS.filter((key) => !EN_KEYS.includes(key));

    expect(onlyInEn).toEqual([]);
    expect(onlyInPt).toEqual([]);
    expect(EN_KEYS).toEqual(PT_KEYS);
  });

  it("every module and action key exists in both", () => {
    const modules = (keys: string[]) =>
      keys.filter((key) => key.startsWith("permissions.modules."));
    const actions = (keys: string[]) =>
      keys.filter((key) => key.startsWith("permissions.actions."));

    // The catalogue is 26 modules and 84 distinct actions (IAM F1/F2).
    expect(modules(PT_KEYS)).toHaveLength(26);
    expect(actions(PT_KEYS)).toHaveLength(84);
    expect(modules(EN_KEYS)).toEqual(modules(PT_KEYS));
    expect(actions(EN_KEYS)).toEqual(actions(PT_KEYS));
  });

  it("no locale value is an empty string", () => {
    const empty = (tree: Tree, prefix = ""): string[] =>
      Object.entries(tree).flatMap(([key, value]) =>
        value !== null && typeof value === "object" && !Array.isArray(value)
          ? empty(value as Tree, `${prefix}${key}.`)
          : value === ""
            ? [`${prefix}${key}`]
            : [],
      );

    expect(empty(pt as Tree)).toEqual([]);
    expect(empty(en as Tree)).toEqual([]);
  });
});
