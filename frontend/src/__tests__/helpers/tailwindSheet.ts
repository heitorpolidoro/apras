/// <reference types="node" />
//
// Tailwind's own `compile()`, plus the stylesheet readers two suites share.
//
// `themeTokenCompile.test.ts` (APRAS-78) owns the ΔL/ΔE mapping table and
// uses `rules` / `declarations`; `darkVariantCompile.test.ts` (APRAS-125) owns
// the `dark:`-gated paint guard and uses `rulesDeep` / `declarationsDeep` /
// `escape`. The deep readers are **new functions placed beside the old ones**,
// never modifications of them: that is what makes
// "`themeTokenCompile.test.ts` is still green" a proof about code this task
// did not touch.
//
// This file carries no `dark:bg-*` / `dark:text-*` literal, deliberately. It
// sits under `__tests__`, so APRAS-125's scanner excludes it from the scanned
// file set, and a literal here would be a candidate nobody could see.
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "tailwindcss";

const HERE = path.dirname(fileURLToPath(import.meta.url));

/** `frontend/src`. Note the two levels: this helper sits one directory deeper
 *  than the suites that used to derive these constants, so a literal copy of
 *  their `path.resolve(HERE, "..")` would be wrong by one. */
export const SRC = path.resolve(HERE, "..", "..");

/** `frontend`, where `node_modules` lives. */
export const FRONTEND_ROOT = path.resolve(SRC, "..");

/**
 * `src/index.css` compiled over exactly `candidates`, as a CSS string.
 *
 * **Contract: a fresh `compile()` on every call, and nothing is cached.** The
 * compile is the slow part of both suites and memoising this function is an
 * obvious optimisation, which is why the prohibition is written down here. One
 * `compile()` instance **accumulates** candidates across `build()` calls —
 * measured on both Tailwind 4.2.4 and 4.3.3 — so a shared compiler would let
 * one caller's candidate list prop up another's rules. That is precisely the
 * leak APRAS-110's self-defeating guard had, and APRAS-125's sentinel case
 * asserts it is absent.
 *
 * `build(candidates)` takes its candidates as an argument and reads no
 * filesystem candidates, so the caller's array is the entire scanned set.
 */
export const compileIndexCss = async (
  candidates: readonly string[],
): Promise<string> => {
  const loadStylesheet = async (id: string, base: string) => {
    const file =
      id === "tailwindcss"
        ? path.join(FRONTEND_ROOT, "node_modules", "tailwindcss", "index.css")
        : id.startsWith("tailwindcss/")
          ? path.join(FRONTEND_ROOT, "node_modules", id)
          : path.resolve(base, id);
    return {
      path: file,
      base: path.dirname(file),
      content: readFileSync(file, "utf8"),
    };
  };
  const compiler = await compile(
    readFileSync(path.join(SRC, "index.css"), "utf8"),
    { base: SRC, loadStylesheet },
  );
  return compiler.build([...candidates]);
};

// --- the stylesheet reader -------------------------------------------------

export interface Rule {
  selector: string;
  body: string;
}

/**
 * Every rule in `css`, with `@layer` wrappers flattened away.
 *
 * A brace scanner rather than a regular expression: `bg-primary/90` nests an
 * `@supports` block inside its own rule, and the theme layer nests hundreds
 * of declarations inside an at-rule.
 */
export const rules = (source: string): Rule[] => {
  // Comments and statement at-rules (`@layer theme, base, …;`) are dropped
  // first: left in, they end up glued to the front of the next selector and
  // `:root, :host` stops being findable by name.
  const css = source.replace(/\/\*[\s\S]*?\*\//g, "");
  const found: Rule[] = [];
  let selector = "";
  for (let index = 0; index < css.length; index += 1) {
    const character = css[index];
    if (character === ";") {
      selector = "";
      continue;
    }
    if (character !== "{") {
      selector += character;
      continue;
    }
    let depth = 1;
    let end = index + 1;
    for (; end < css.length && depth > 0; end += 1) {
      if (css[end] === "{") depth += 1;
      if (css[end] === "}") depth -= 1;
    }
    const body = css.slice(index + 1, end - 1);
    const name = selector.trim();
    if (name.startsWith("@layer")) {
      found.push(...rules(body));
    } else {
      found.push({ selector: name, body });
    }
    selector = "";
    index = end - 1;
  }
  return found;
};

/** The `name: value` pairs declared directly in a rule body, nested blocks
 *  excluded. */
export const declarations = (body: string): Map<string, string> => {
  const pairs = new Map<string, string>();
  let depth = 0;
  let buffer = "";
  const flush = () => {
    const colon = buffer.indexOf(":");
    if (colon > 0) {
      pairs.set(buffer.slice(0, colon).trim(), buffer.slice(colon + 1).trim());
    }
    buffer = "";
  };
  for (const character of body) {
    if (character === "{") depth += 1;
    if (character === "}") depth -= 1;
    if (character === ";" && depth === 0) {
      flush();
      continue;
    }
    if (depth === 0) buffer += character;
  }
  flush();
  return pairs;
};

// --- the deep readers, new beside the two above ----------------------------

/**
 * Every rule in `css`, at every nesting depth, carrying an **effective**
 * selector rather than the sheet's literal nesting.
 *
 * This exists because the installed Tailwinds disagree about where the `dark:`
 * variant goes:
 *
 *     4.2.4   .dark\:bg-foreground { &:is(.dark *) { background-color: … } }
 *     4.3.3   .dark\:bg-foreground:is(.dark *) { background-color: … }
 *
 * A reader that matched a rule whose selector *equalled* `"." + escape(token)`
 * would match every token on 4.2.4 and none on 4.3.3 — green on a developer
 * tree and red in CI. So no emission shape is encoded anywhere: at-rule
 * preludes (`@layer`, `@media`, `@supports`) contribute no selector and their
 * bodies are parsed with the **parent** selector carried through unchanged,
 * `&` is substituted with the parent, and a parentless nested selector is
 * joined with a descendant combinator.
 *
 * Comments are stripped before parsing, so a selector written in a comment can
 * never match.
 */
export const rulesDeep = (source: string): Rule[] => {
  const found: Rule[] = [];
  const walk = (text: string, parent: string): void => {
    let prelude = "";
    for (let index = 0; index < text.length; index += 1) {
      const character = text[index];
      if (character === ";") {
        prelude = "";
        continue;
      }
      if (character !== "{") {
        prelude += character;
        continue;
      }
      let depth = 1;
      let end = index + 1;
      for (; end < text.length && depth > 0; end += 1) {
        if (text[end] === "{") depth += 1;
        if (text[end] === "}") depth -= 1;
      }
      const body = text.slice(index + 1, end - 1);
      const name = prelude.trim();
      if (name.startsWith("@")) {
        walk(body, parent);
      } else {
        const selector = name.includes("&")
          ? name.replace(/&/g, parent)
          : parent.length === 0
            ? name
            : `${parent} ${name}`;
        found.push({ selector, body });
        walk(body, selector);
      }
      prelude = "";
      index = end - 1;
    }
  };
  walk(source.replace(/\/\*[\s\S]*?\*\//g, ""), "");
  return found;
};

/**
 * The `name: value` pairs declared **at any depth** below `body`, as a list
 * rather than a map so a property declared twice is not collapsed.
 *
 * The depth-blind harvest is required, not a convenience: on both installed
 * Tailwinds a stacked token (a `hover:` on top of the dark variant) keeps
 * its declaration below the gated rule inside `@media (hover: hover)`, and
 * the depth-0 {@link declarations} returns nothing for any of them. That the
 * same mechanism absorbs 4.2.4's `&:is(.dark *)` nesting for free is why the
 * dual-version contract needs no version check anywhere.
 *
 * Preludes are discarded at the `{` they introduce, which is what stops
 * `@supports (color: color-mix(in lab, …))` being harvested as a bogus
 * `color` declaration, and a selector such as `&:hover` being read as a
 * declaration of `&`.
 */
export const declarationsDeep = (body: string): Array<[string, string]> => {
  const pairs: Array<[string, string]> = [];
  const walk = (text: string): void => {
    let buffer = "";
    const flush = () => {
      const colon = buffer.indexOf(":");
      if (colon > 0) {
        pairs.push([
          buffer.slice(0, colon).trim(),
          buffer.slice(colon + 1).trim(),
        ]);
      }
      buffer = "";
    };
    for (let index = 0; index < text.length; index += 1) {
      const character = text[index];
      if (character === ";") {
        flush();
        continue;
      }
      if (character !== "{") {
        buffer += character;
        continue;
      }
      let depth = 1;
      let end = index + 1;
      for (; end < text.length && depth > 0; end += 1) {
        if (text[end] === "{") depth += 1;
        if (text[end] === "}") depth -= 1;
      }
      // Whatever accumulated since the last `;` or `}` is this block's
      // prelude — a selector or an at-rule — never a declaration.
      buffer = "";
      walk(text.slice(index + 1, end - 1));
      index = end - 1;
    }
    flush();
  };
  walk(body.replace(/\/\*[\s\S]*?\*\//g, ""));
  return pairs;
};

/**
 * `token` escaped for use inside a CSS class selector.
 *
 * Deliberately **not** `themeTokenCompile.test.ts`'s `escapeClass`, which
 * escapes only `/` and `.`: without `:` it would fail to find every single
 * `dark:` token. The bracket, parenthesis, quote and hash forms are here for
 * the arbitrary values the negative controls carry.
 */
export const escape = (token: string): string =>
  token.replace(/[:/.[\]()'#]/g, (character) => `\\${character}`);
