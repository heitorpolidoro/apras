import { describe, expect, it } from "vitest";
import { BRAND_AUTHORED_KEYS, type BrandPalette } from "../../api/tenantProfile";
import { parseBrandPalettePaste, type PasteProblem } from "../brandPalettePaste";

/**
 * The two grammars of APRAS-95, case by case against the spec's tables.
 *
 * The module is pure: text in, either thirteen values out or a list of
 * problems. Nothing here renders, and no problem carries a sentence — only an
 * i18n key and its parameters, so every visible string stays in the locale
 * files.
 */

/** The palette the operator derived from the APRAS-60 obras mock. Its
 *  `muted-foreground` is `#5d625c` and not the mock's own grey, which fails
 *  AA — see the spec. */
const WORKED: BrandPalette = {
  background: "#f7f1e5",
  foreground: "#1d2925",
  card: "#ffffff",
  "card-foreground": "#1d2925",
  primary: "#174b40",
  "primary-foreground": "#f7f1e5",
  secondary: "#eee6d7",
  "secondary-foreground": "#082f2a",
  accent: "#ead6a4",
  "accent-foreground": "#082f2a",
  muted: "#eee6d7",
  "muted-foreground": "#5d625c",
  border: "#ddd1b6",
};

const cssOf = (palette: BrandPalette, prefix = "--"): string =>
  BRAND_AUTHORED_KEYS.map((key) => `${prefix}${key}: ${palette[key]};`).join("\n");

const keysOf = (problems: PasteProblem[]): string[] =>
  problems.map((problem) => problem.key);

const accepted = (text: string) => {
  const result = parseBrandPalettePaste(text);
  if (!result.ok) {
    throw new Error(`refused: ${JSON.stringify(result.problems)}`);
  }
  return result;
};

const refused = (text: string) => {
  const result = parseBrandPalettePaste(text);
  if (result.ok) {
    throw new Error("accepted, but the spec refuses this text");
  }
  return result.problems;
};

describe("the JSON grammar", () => {
  it("accepts the wrapped object with both palettes", () => {
    const result = accepted(
      JSON.stringify({ mode: "advanced", light: WORKED, dark: WORKED }),
    );

    expect(result.light).toEqual(WORKED);
    expect(result.dark).toEqual(WORKED);
  });

  it("reads an explicit null dark as 'derive the dark scheme'", () => {
    const result = accepted(
      JSON.stringify({ mode: "advanced", light: WORKED, dark: null }),
    );

    expect(result.light).toEqual(WORKED);
    expect(result.dark).toBeNull();
  });

  it("accepts the wrapper without a mode, saying nothing about dark", () => {
    const result = accepted(JSON.stringify({ light: WORKED }));

    expect(result.light).toEqual(WORKED);
    expect(result.dark).toBeUndefined();
  });

  it("reads a bare palette object as the light palette", () => {
    const result = accepted(JSON.stringify(WORKED));

    expect(result.light).toEqual(WORKED);
    expect(result.dark).toBeUndefined();
  });

  it("yields the same thirteen values in all four accepted shapes", () => {
    const shapes = [
      JSON.stringify({ mode: "advanced", light: WORKED, dark: WORKED }),
      JSON.stringify({ mode: "advanced", light: WORKED, dark: null }),
      JSON.stringify({ light: WORKED }),
      JSON.stringify(WORKED),
    ];

    for (const shape of shapes) {
      expect(accepted(shape).light).toEqual(WORKED);
    }
  });

  it("accepts arbitrary whitespace, any key order and uppercase hex", () => {
    const shuffled = Object.fromEntries(
      [...BRAND_AUTHORED_KEYS]
        .reverse()
        .map((key) => [key, WORKED[key].toUpperCase()]),
    );

    const result = accepted(`\n\n  ${JSON.stringify({ light: shuffled }, null, 4)}\n `);

    expect(result.light.primary).toBe("#174B40");
  });

  it("refuses a mode other than advanced, naming it", () => {
    const problems = refused(
      JSON.stringify({ mode: "simple", primary: "#174b40", accent: "#ead6a4" }),
    );

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.notAdvanced",
    ]);
    expect(problems[0].params).toEqual({ mode: "simple" });
  });

  it("refuses an unknown key at the top level of a wrapped object", () => {
    const problems = refused(JSON.stringify({ light: WORKED, extra: 1 }));

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.unknownTopLevel",
    ]);
    expect(problems[0].params).toEqual({ key: "extra" });
  });

  it("refuses a wrapper with no light palette", () => {
    const problems = refused(JSON.stringify({ mode: "advanced", dark: null }));

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.missingLight",
    ]);
  });

  it("refuses a dark value that is neither null nor a palette", () => {
    const problems = refused(JSON.stringify({ light: WORKED, dark: "auto" }));

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.darkNotPalette",
    ]);
  });

  it("refuses a dark palette of its own accord, naming its faults", () => {
    const problems = refused(
      JSON.stringify({ light: WORKED, dark: { ...WORKED, primary: "#fff" } }),
    );

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.badValue",
    ]);
    expect(problems[0].params).toEqual({
      key: "primary",
      value: "#fff",
      scheme: "dark",
    });
  });

  it("resolves a repeated JSON key last-wins, as JSON.parse does", () => {
    const body = JSON.stringify({ light: WORKED }).replace(
      '"background":"#f7f1e5"',
      '"background":"#000000","background":"#f7f1e5"',
    );

    expect(accepted(body).light.background).toBe("#f7f1e5");
  });
});

describe("text neither grammar reads", () => {
  it("refuses an empty textarea", () => {
    expect(keysOf(refused("   \n  "))).toEqual([
      "tenantProfile.brand.paste.problems.empty",
    ]);
  });

  it("refuses JSON with a trailing comma, quoting the parser's own message", () => {
    // Text that opens with `{` and is neither valid JSON nor a declaration
    // block is reported as malformed JSON, with `JSON.parse`'s own message —
    // that is the parser the person was writing for.
    const problems = refused('{"light": {"background": "#f7f1e5",},}');

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.malformed",
    ]);
    expect(String(problems[0].params?.detail)).not.toBe("");
  });

  it("refuses a comment inside JSON the same way", () => {
    expect(
      keysOf(refused('{"light": {} /* as cores */}')),
    ).toEqual(["tenantProfile.brand.paste.problems.malformed"]);
  });

  it("refuses a JSON object whose light value is not an object", () => {
    expect(keysOf(refused('{"light": 3}'))).toEqual([
      "tenantProfile.brand.paste.problems.missingLight",
    ]);
  });

  it("refuses prose", () => {
    const problems = refused("as cores do condomínio estão no PDF");

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.cssDeclaration",
    ]);
  });
});

describe("the CSS grammar", () => {
  it("accepts thirteen plain declarations", () => {
    expect(accepted(cssOf(WORKED)).light).toEqual(WORKED);
  });

  it("says nothing about the dark scheme", () => {
    expect(accepted(cssOf(WORKED)).dark).toBeUndefined();
  });

  it("accepts declarations whose leading -- is omitted", () => {
    expect(accepted(cssOf(WORKED, "")).light).toEqual(WORKED);
  });

  it("accepts a missing semicolon on the last declaration", () => {
    expect(accepted(cssOf(WORKED).replace(/;$/, "")).light).toEqual(WORKED);
  });

  it("accepts a wrapping selector block, comments and mixed indentation", () => {
    const text = `/* paleta das obras
   derivada do mock APRAS-60 */
:root {
${BRAND_AUTHORED_KEYS.map(
  (key, index) => `${" ".repeat(index % 5)}--${key}: ${WORKED[key]}; /* ${key} */`,
).join("\n")}

}`;

    expect(accepted(text).light).toEqual(WORKED);
  });

  it("accepts declarations separated by semicolons on one line", () => {
    expect(
      accepted(
        BRAND_AUTHORED_KEYS.map((key) => `--${key}:${WORKED[key]}`).join("; "),
      ).light,
    ).toEqual(WORKED);
  });

  it("refuses two blocks pasted at once", () => {
    const problems = refused(`:root { ${cssOf(WORKED)} }\n.dark { ${cssOf(WORKED)} }`);

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.multipleBlocks",
    ]);
  });

  it("refuses an oklch value, naming the key and pointing at #rrggbb", () => {
    const problems = refused(
      cssOf(WORKED).replace("#5d625c", "oklch(0.55 0.01 140)"),
    );

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.oklchValue",
    ]);
    expect(problems[0].params).toEqual({
      key: "muted-foreground",
      value: "oklch(0.55 0.01 140)",
      scheme: "light",
    });
  });

  it("refuses a named colour and a three-digit hex, naming key and value", () => {
    const problems = refused(
      cssOf(WORKED).replace("#ffffff", "white").replace("#174b40", "#fff"),
    );

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.badValue",
      "tenantProfile.brand.paste.problems.badValue",
    ]);
    expect(problems.map((problem) => problem.params)).toEqual([
      { key: "card", value: "white", scheme: "light" },
      { key: "primary", value: "#fff", scheme: "light" },
    ]);
  });

  it("refuses an rgb() value", () => {
    expect(
      keysOf(refused(cssOf(WORKED).replace("#f7f1e5", "rgb(247 241 229)"))),
    ).toContain("tenantProfile.brand.paste.problems.badValue");
  });

  it("refuses a line that is not a declaration, quoting it", () => {
    const problems = refused(`${cssOf(WORKED)}\ncor primária do condomínio`);

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.cssDeclaration",
    ]);
    expect(problems[0].params).toEqual({ line: "cor primária do condomínio" });
  });

  it("resolves a repeated declaration last-wins", () => {
    const text = `--background: #000000;\n${cssOf(WORKED)}`;

    expect(accepted(text).light.background).toBe("#f7f1e5");
  });
});

describe("the thirteen-key rule, identical in both grammars", () => {
  it("refuses a partial JSON palette, naming the missing keys", () => {
    const partial = { ...WORKED } as Record<string, string>;
    delete partial.border;
    delete partial.muted;

    const problems = refused(JSON.stringify({ light: partial }));

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.missingKeys",
    ]);
    expect(problems[0].params).toEqual({ keys: "muted, border", scheme: "light" });
  });

  it("refuses a partial CSS block rather than merging it", () => {
    const problems = refused("--primary: #174b40;\n--accent: #ead6a4;");

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.missingKeys",
    ]);
  });

  it("refuses a single colour, which the thirteen pickers already are for", () => {
    expect(keysOf(refused("--primary: #174b40;"))).toEqual([
      "tenantProfile.brand.paste.problems.missingKeys",
    ]);
  });

  it("refuses an unknown palette key by name rather than dropping it", () => {
    const problems = refused(`${cssOf(WORKED)}\n--ring: #174b40;`);

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.unknownKey",
    ]);
    expect(problems[0].params).toEqual({ key: "ring", scheme: "light" });
  });

  it("lists a missing key, an unknown key and a bad value together", () => {
    const text = cssOf(WORKED)
      .replace("--border: #ddd1b6;", "--ring: #174b40;")
      .replace("#5d625c", "oklch(0.55 0.01 140)");

    expect(keysOf(refused(text))).toEqual([
      "tenantProfile.brand.paste.problems.missingKeys",
      "tenantProfile.brand.paste.problems.unknownKey",
      "tenantProfile.brand.paste.problems.oklchValue",
    ]);
  });

  it("refuses a value that is not a string at all", () => {
    const problems = refused(
      JSON.stringify({ light: { ...WORKED, primary: 16711680 } }),
    );

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.badValue",
    ]);
    expect(problems[0].params).toEqual({
      key: "primary",
      value: "16711680",
      scheme: "light",
    });
  });

  it("carries the values as typed, never lowercasing them", () => {
    const upper = Object.fromEntries(
      BRAND_AUTHORED_KEYS.map((key) => [key, WORKED[key].toUpperCase()]),
    ) as BrandPalette;

    expect(accepted(cssOf(upper)).light).toEqual(upper);
  });
});

describe("shapes the readers reach only rarely", () => {
  it("refuses a bare palette object with a fault in it", () => {
    const problems = refused(JSON.stringify({ ...WORKED, primary: "#fff" }));

    expect(keysOf(problems)).toEqual([
      "tenantProfile.brand.paste.problems.badValue",
    ]);
  });

  it("accepts a block whose closing brace was left behind", () => {
    expect(accepted(`:root {\n${cssOf(WORKED)}`).light).toEqual(WORKED);
  });
});

describe("a block with a selector and nothing in it", () => {
  it("asks for a palette rather than accepting an empty one", () => {
    expect(keysOf(refused(":root {\n\n}"))).toEqual([
      "tenantProfile.brand.paste.problems.empty",
    ]);
  });

  it("refuses a JSON null, which is neither an object nor a declaration", () => {
    expect(keysOf(refused("null"))).toEqual([
      "tenantProfile.brand.paste.problems.cssDeclaration",
    ]);
  });
});
