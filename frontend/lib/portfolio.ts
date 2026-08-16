import type { PortfolioSnapshot, PriceTick } from "./types";

interface DerivedPortfolioValue {
  cash: number | null;
  positionsValue: number | null;
  totalValue: number | null;
}

export interface PositionRowData {
  ticker: string;
  quantity: number;
  avgCost: number;
  price: number | null;
  unrealizedPnl: number | null;
  changePercent: number | null;
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

/**
 * Pure live-overlay derivation of position-table rows from a snapshot plus
 * the SSE prices map. Uses the same `live?.price ?? position.price` merge as
 * `derivePortfolioValue`, then recomputes unrealized P&L and percent change
 * from that price rather than passing through the snapshot's own figures —
 * so the number on screen always agrees with the price beside it.
 */
export function derivePositionRows(
  snapshot: PortfolioSnapshot | null,
  prices: Record<string, PriceTick>,
): PositionRowData[] | null {
  if (snapshot === null) {
    return null;
  }

  return snapshot.positions.map((position) => {
    const price = prices[position.ticker]?.price ?? position.price;

    let unrealizedPnl: number | null = null;
    let changePercent: number | null = null;
    if (price != null) {
      unrealizedPnl = position.quantity * (price - position.avg_cost);
      changePercent =
        position.avg_cost === 0 ? null : ((price - position.avg_cost) / position.avg_cost) * 100;
    }

    return {
      ticker: position.ticker,
      quantity: position.quantity,
      avgCost: position.avg_cost,
      price,
      unrealizedPnl,
      changePercent,
    };
  });
}
