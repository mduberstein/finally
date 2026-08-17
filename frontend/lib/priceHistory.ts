import type { PriceTick } from "./types";

/** Pure per-ticker price-history accumulator and watchlist-driven prune.
 * No framework import and no side effect of any kind lives in this file —
 * it is the testable half of the split, exactly as `connection.ts` is to
 * `usePriceStream.ts`. */

export interface PricePoint {
  price: number;
  timestamp: string;
}

/** Cap per ticker, roughly two and a half minutes of simulator ticks at 500ms. */
export const MAX_HISTORY_POINTS = 300;

/**
 * Append every ticker in `prices` to its history array, using the tick's
 * `timestamp` (not its price) as the new-tick discriminator: two
 * consecutive ticks at the same price are two real observations and must
 * both be recorded, while the same tick object re-delivered on a re-render
 * must not be double-counted. Trims each array to `maxPoints`, oldest
 * dropped first. Returns a new object; never mutates the argument.
 */
export function appendTicks(
  history: Record<string, PricePoint[]>,
  prices: Record<string, PriceTick>,
  maxPoints: number,
): Record<string, PricePoint[]> {
  const next: Record<string, PricePoint[]> = { ...history };
  let changed = false;

  for (const ticker of Object.keys(prices)) {
    const tick = prices[ticker];
    const existing = history[ticker] ?? [];
    const lastPoint = existing[existing.length - 1];
    if (lastPoint != null && lastPoint.timestamp === tick.timestamp) continue;

    next[ticker] = [...existing, { price: tick.price, timestamp: tick.timestamp }].slice(
      -maxPoints,
    );
    changed = true;
  }

  return changed ? next : history;
}

/**
 * Keep only history entries whose ticker is in the supplied list. This is
 * the ONLY removal signal available: the backend price cache never drops a
 * ticker, so its last price streams forever. Drive pruning from the
 * watchlist entries the page already holds.
 */
export function pruneToWatchlist(
  history: Record<string, PricePoint[]>,
  tickers: readonly string[],
): Record<string, PricePoint[]> {
  const keep = new Set(tickers);
  const next: Record<string, PricePoint[]> = {};
  for (const ticker of Object.keys(history)) {
    if (keep.has(ticker)) next[ticker] = history[ticker];
  }
  return next;
}
