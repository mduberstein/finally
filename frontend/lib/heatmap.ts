import type { PositionRowData } from "./portfolio";

/**
 * Pure position-weight derivation and squarified row layout for the
 * portfolio heatmap. No framework import, no side effect, no element
 * measurement — proportions are computed as flex-growth weights, never
 * pixels, and the browser's flexbox engine does the rest (D-02).
 */

export interface HeatmapItem {
  ticker: string;
  value: number;
  weight: number;
  pnlPercent: number | null;
}

export interface HeatmapRow {
  items: HeatmapItem[];
  weight: number;
}

/**
 * Below this share of the portfolio a cell is too small to hold its ticker
 * and percent label legibly, so the component hides the label and keeps
 * the fill. Named here rather than left as a magic value in JSX.
 */
export const HEATMAP_LABEL_MIN_WEIGHT = 0.06;

/**
 * Values each position as `quantity * price`, drops any position whose
 * price is null (an unpriced position has no honest area), and weights the
 * rest by their share of the remaining total. Null in, null out — the same
 * loading signal `derivePositionRows` already uses. No minimum-size floor
 * and no clamping: a cell's area is the position's real share of the
 * portfolio.
 */
export function deriveHeatmapItems(rows: PositionRowData[] | null): HeatmapItem[] | null {
  if (rows === null) return null;

  const priced = rows.filter((row) => row.price != null);
  const total = priced.reduce((sum, row) => sum + row.quantity * (row.price as number), 0);
  if (total === 0) return [];

  const items: HeatmapItem[] = priced.map((row) => {
    const value = row.quantity * (row.price as number);
    return {
      ticker: row.ticker,
      value,
      weight: value / total,
      pnlPercent: row.changePercent,
    };
  });

  return items.sort((a, b) => b.weight - a.weight);
}

/** Sum of a row's weights, used both as the worst-ratio input and the
 * returned row's own weight. */
function rowWeightSum(row: readonly HeatmapItem[]): number {
  return row.reduce((sum, item) => sum + item.weight, 0);
}

/**
 * The Bruls/Huizing/van Wijk worst-aspect-ratio formula for a candidate
 * row, given the fixed side length the row is being laid out against.
 * Lower is more square (better); this is what squarify minimizes.
 */
function worstRatio(row: readonly HeatmapItem[], side: number): number {
  const sum = rowWeightSum(row);
  const weights = row.map((item) => item.weight);
  const max = Math.max(...weights);
  const min = Math.min(...weights);
  const sideSq = side * side;
  const sumSq = sum * sum;
  return Math.max((sideSq * max) / sumSq, sumSq / (sideSq * min));
}

function toRow(items: HeatmapItem[]): HeatmapRow {
  return { items, weight: rowWeightSum(items) };
}

/**
 * The squarified treemap row-building heuristic: walk the descending-sorted
 * items, accumulating a current row while adding the next item improves
 * (lowers) that row's worst aspect ratio, closing the row and starting a
 * new one otherwise. Every input item appears in exactly one output row —
 * partition, not sample — and rows are returned in input order. Never
 * mutates the input array.
 */
export function squarify(
  items: readonly HeatmapItem[],
  containerAspect = 1,
): HeatmapRow[] {
  if (items.length === 0) return [];

  // Treat the container as unit area (weights already sum to ~1) with the
  // given width/height aspect ratio; the fixed side is the shorter of the
  // two, matching the paper's "w" parameter.
  const width = Math.sqrt(containerAspect);
  const height = 1 / width;
  const side = Math.min(width, height);

  const rows: HeatmapRow[] = [];
  let currentRow: HeatmapItem[] = [];
  let remaining = items.slice();

  while (remaining.length > 0) {
    const next = remaining[0];
    const candidateRow = [...currentRow, next];

    if (
      currentRow.length === 0 ||
      worstRatio(candidateRow, side) <= worstRatio(currentRow, side)
    ) {
      currentRow = candidateRow;
      remaining = remaining.slice(1);
    } else {
      rows.push(toRow(currentRow));
      currentRow = [];
    }
  }

  if (currentRow.length > 0) rows.push(toRow(currentRow));

  return rows;
}
