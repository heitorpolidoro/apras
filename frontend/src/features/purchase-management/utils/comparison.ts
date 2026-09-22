/**
 * The pure rules behind the quote comparison and the decision context
 * (APRAS-63).
 *
 * They live beside the components rather than inside them so that
 * `react-refresh/only-export-components` stays satisfied — a component
 * module may export components and constants, not functions — and so each
 * rule can be exercised without rendering anything.
 */

import {
  QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES,
  QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES,
} from "../../../api/purchases";
import type {
  PurchaseQuote,
  PurchaseQuoteItem,
  PurchaseRequestItem,
} from "../../../types/purchase";

/**
 * The union of every `extra_fields` label, in first-seen order across the
 * quotes **as the backend sent them**.
 *
 * Deliberately not sorted and deliberately not re-derived from the ordered
 * columns: the row order of the table must not change when the reader sorts
 * the columns, or the comparison they were half-way through reading moves
 * under them.
 */
export const unionExtraFieldLabels = (quotes: PurchaseQuote[]): string[] => {
  const seen = new Set<string>();
  const labels: string[] = [];
  for (const quote of quotes) {
    for (const field of quote.extra_fields) {
      if (!seen.has(field.label)) {
        seen.add(field.label);
        labels.push(field.label);
      }
    }
  }
  return labels;
};

/**
 * The client-side refusal (D2), mirrored from the backend through the
 * two-sided pin in `api/purchases.ts`. Returns the i18n key of the reason,
 * or `null` when the file may be sent.
 */
export const attachmentRejectionKey = (file: File): string | null => {
  const accepted: readonly string[] = QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES;
  if (!accepted.includes(file.type)) return "purchases.attachment.invalidType";
  if (file.size > QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES) {
    return "purchases.attachment.tooLarge";
  }
  return null;
};

/**
 * The gap between the quote being decided and the lowest one (D8).
 *
 * Computed **client-side** from the quotes the detail already carries: no
 * endpoint changes and `is_lowest_price` is already on every quote. `null`
 * whenever there is nothing to warn about — no lowest quote known, the quote
 * being decided *is* a lowest one (ties included: both carry
 * `is_lowest_price`, so neither is warned about), or the lowest total is
 * zero, where a percentage would be a division by zero rather than a fact.
 */
export const computeGap = (
  quote: PurchaseQuote,
  lowestQuote: PurchaseQuote | null,
): { difference: number; percent: number } | null => {
  // APRAS-73 D10: a partial offer's distance from a full one is not a price
  // difference. The decision modal shows `decision-coverage-warning` there
  // instead, and the two panels are mutually exclusive.
  if (quote.is_complete === false) return null;
  if (!lowestQuote || quote.is_lowest_price || quote.id === lowestQuote.id) {
    return null;
  }
  const difference = quote.total_price - lowestQuote.total_price;
  if (difference <= 0 || lowestQuote.total_price <= 0) return null;
  return {
    difference,
    percent: (difference / lowestQuote.total_price) * 100,
  };
};

/** One row of the comparison grid, plus the cell each quote fills in it. */
export interface ComparisonGridRow {
  /**
   * The `request_item_id` for a request-line row and the quote item's own
   * `id` for a supplier extra row — the same key the cell testids carry.
   */
  key: string;
  description: string;
  quantity: number;
  /** A line only one supplier asked to sell; every other column is empty. */
  isExtra: boolean;
  /** `undefined` where that supplier did not price the line (D5). */
  cells: Record<string, PurchaseQuoteItem | undefined>;
}

/**
 * The grid, derived and nothing else (APRAS-73 D9).
 *
 * One row per request line in `position` order, then the supplier extra
 * lines beneath them, in the order the quotes arrive and in each quote's own
 * `position` order. Alignment is by **request line identity**, never by
 * matching free text: both suppliers point at the same
 * `purchase_request_item` row, so the rows are exact.
 *
 * Pure and exported so the grid can be asserted without rendering anything.
 */
export const buildComparisonGrid = (
  requestItems: PurchaseRequestItem[],
  quotes: PurchaseQuote[],
): ComparisonGridRow[] => {
  const ordered = [...requestItems].sort((a, b) => a.position - b.position);
  const rows: ComparisonGridRow[] = ordered.map((item) => ({
    key: item.id,
    description: item.description,
    quantity: item.quantity,
    isExtra: false,
    cells: Object.fromEntries(
      quotes
        .map(
          (quote) =>
            [
              quote.id,
              quote.items.find((line) => line.request_item_id === item.id),
            ] as const,
        )
        .filter(([, line]) => line !== undefined),
    ),
  }));

  for (const quote of quotes) {
    const extras = [...quote.items]
      .filter((line) => line.request_item_id === null)
      .sort((a, b) => a.position - b.position);
    for (const line of extras) {
      rows.push({
        key: line.id,
        description: line.description,
        quantity: line.quantity,
        isExtra: true,
        cells: { [quote.id]: line },
      });
    }
  }

  return rows;
};
