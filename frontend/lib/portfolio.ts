import type { PortfolioSnapshot, PriceTick } from "./types";

interface DerivedPortfolioValue {
  cash: number | null;
  positionsValue: number | null;
  totalValue: number | null;
}

/**
 * Pure live-overlay derivation of portfolio value from a snapshot plus the
 * SSE prices map. Mirrors `Watchlist.tsx`'s `live?.price ?? entry.price`
 * merge — the same idea applied to money. Contains no fetch and no timer:
 * the header moves on every SSE tick without a network round trip.
 */
export function derivePortfolioValue(
  snapshot: PortfolioSnapshot | null,
  prices: Record<string, PriceTick>,
): DerivedPortfolioValue {
  if (snapshot === null) {
    return { cash: null, positionsValue: null, totalValue: null };
  }

  let positionsValue = 0;
  for (const position of snapshot.positions) {
    const livePrice = prices[position.ticker]?.price ?? position.price;
    if (livePrice == null) continue;
    positionsValue += position.quantity * livePrice;
  }

  return {
    cash: snapshot.cash_balance,
    positionsValue,
    totalValue: snapshot.cash_balance + positionsValue,
  };
}
