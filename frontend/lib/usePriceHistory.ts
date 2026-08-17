"use client";

import { useEffect, useState } from "react";

import { appendTicks, MAX_HISTORY_POINTS, pruneToWatchlist, type PricePoint } from "./priceHistory";
import type { PriceTick } from "./types";

/**
 * Thin `"use client"` wrapper binding the pure accumulator to the existing
 * price stream. Holds the map in component state: on a change to `prices`
 * fold it through `appendTicks`, on a change to `tickers` fold it through
 * `pruneToWatchlist`. Memoize the ticker list at the call site so the prune
 * effect does not fire on every render.
 */
export function usePriceHistory(
  prices: Record<string, PriceTick>,
  tickers: readonly string[],
): Record<string, PricePoint[]> {
  const [history, setHistory] = useState<Record<string, PricePoint[]>>({});

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the accumulator synchronizes with an external event stream, it is not derived from props alone
    setHistory((current) => appendTicks(current, prices, MAX_HISTORY_POINTS));
  }, [prices]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the accumulator synchronizes with an external event stream, it is not derived from props alone
    setHistory((current) => pruneToWatchlist(current, tickers));
  }, [tickers]);

  return history;
}
