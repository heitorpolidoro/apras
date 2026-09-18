import React from "react";
import { normalizeText } from "../utils/taskUtils";

interface HighlightedTextProps {
  /** The text to render, verbatim. */
  text: string | null | undefined;
  /** The free-text search whose matches are wrapped in `<mark>`. */
  search?: string | null;
}

/**
 * Builds the normalised (lower-cased, diacritic-free) form of `text` together
 * with a map from each normalised character back to its index in the original,
 * so a match found on the normalised text can be sliced out of the original.
 */
function normalizedWithIndexMap(text: string): {
  normalized: string;
  map: number[];
} {
  let normalized = "";
  const map: number[] = [];
  for (let i = 0; i < text.length; i += 1) {
    const chunk = normalizeText(text[i]);
    normalized += chunk;
    for (let k = 0; k < chunk.length; k += 1) map.push(i);
  }
  return { normalized, map };
}

/** The [start, end) ranges of the original text that the search matches. */
function matchRanges(text: string, needle: string): [number, number][] {
  const { normalized, map } = normalizedWithIndexMap(text);
  const ranges: [number, number][] = [];
  let from = 0;
  let at = normalized.indexOf(needle, from);
  while (at !== -1) {
    ranges.push([map[at], map[at + needle.length - 1] + 1]);
    from = at + needle.length;
    at = normalized.indexOf(needle, from);
  }
  return ranges;
}

/**
 * Renders `text`, wrapping every fragment matching `search` in a `<mark>`.
 * Matching is case- and accent-insensitive, and the rendered characters are
 * always the original ones — only the *matching* is normalised.
 */
const HighlightedText: React.FC<HighlightedTextProps> = ({ text, search }) => {
  const value = text ?? "";
  const needle = normalizeText(search).trim();
  if (!needle || !value) return <>{value}</>;

  const ranges = matchRanges(value, needle);
  if (ranges.length === 0) return <>{value}</>;

  const parts: React.ReactNode[] = [];
  let cursor = 0;
  ranges.forEach(([start, end], index) => {
    if (start > cursor) parts.push(value.slice(cursor, start));
    parts.push(
      <mark key={`${start}-${end}`} className="rounded bg-yellow-200 px-0.5 text-foreground dark:bg-yellow-500/40">
        {value.slice(start, end)}
      </mark>,
    );
    cursor = end;
    if (index === ranges.length - 1 && cursor < value.length) {
      parts.push(value.slice(cursor));
    }
  });

  return <>{parts}</>;
};

export default HighlightedText;
