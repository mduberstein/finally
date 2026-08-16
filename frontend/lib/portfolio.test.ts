import { describe, expect, it } from "vitest";

import { derivePortfolioValue } from "./portfolio";
import type { PortfolioSnapshot, PriceTick } from "./types";

function tick(ticker: string, price: number): PriceTick {
  return {
    ticker,
    price,
    previous_price: price,
    change: 0,
    change_percent: 0,
    direction: "flat",
    timestamp: "2026-01-01T00:00:00Z",
  };
}

function snapshot(
  cash: number,
  positions: PortfolioSnapshot["positions"] = [],
): PortfolioSnapshot {
  const positionsValue = positions.reduce(
    (sum, position) => sum + (position.price == null ? 0 : position.quantity * position.price),
    0,
  );
  return {
    cash_balance: cash,
    positions_value: positionsValue,
    total_value: cash + positionsValue,
    positions,
  };
}

describe("derivePortfolioValue", () => {
  it("returns cash, positionsValue, and totalValue all null for a null snapshot", () => {
    expect(derivePortfolioValue(null, {})).toEqual({
      cash: null,
      positionsValue: null,
      totalValue: null,
    });
  });

  it("returns cash 10000, positionsValue 0, totalValue 10000 for cash with no positions", () => {
    expect(derivePortfolioValue(snapshot(10000), {})).toEqual({
      cash: 10000,
      positionsValue: 0,
      totalValue: 10000,
    });
  });

  it("uses the snapshot price when no live tick exists", () => {
    const snap = snapshot(5000, [
      { ticker: "AAPL", quantity: 10, avg_cost: 190, price: 190, unrealized_pnl: 0, change_percent: 0 },
    ]);
    expect(derivePortfolioValue(snap, {}).totalValue).toBe(6900);
  });

  it("uses the live tick price over the snapshot price", () => {
    const snap = snapshot(5000, [
      { ticker: "AAPL", quantity: 10, avg_cost: 190, price: 190, unrealized_pnl: 0, change_percent: 0 },
    ]);
    expect(derivePortfolioValue(snap, { AAPL: tick("AAPL", 200) }).totalValue).toBe(7000);
  });

  it("excludes a position whose price is null rather than treating it as zero-valued", () => {
    const snap = snapshot(1000, [
      { ticker: "ZZZZ", quantity: 5, avg_cost: 10, price: null, unrealized_pnl: null, change_percent: null },
    ]);
    const result = derivePortfolioValue(snap, {});
    expect(result.positionsValue).toBe(0);
    expect(result.totalValue).toBe(1000);
  });

  it("blends the live price for one position and the snapshot price for another", () => {
    const snap = snapshot(1000, [
      { ticker: "AAPL", quantity: 10, avg_cost: 190, price: 190, unrealized_pnl: 0, change_percent: 0 },
      { ticker: "GOOGL", quantity: 5, avg_cost: 175, price: 175, unrealized_pnl: 0, change_percent: 0 },
    ]);
    const result = derivePortfolioValue(snap, { AAPL: tick("AAPL", 200) });
    // AAPL: 10 * 200 (live) + GOOGL: 5 * 175 (snapshot) = 2000 + 875 = 2875
    expect(result.positionsValue).toBe(2875);
    expect(result.totalValue).toBe(3875);
  });

  it("ignores a live tick for a ticker not held", () => {
    const snap = snapshot(1000, [
      { ticker: "AAPL", quantity: 10, avg_cost: 190, price: 190, unrealized_pnl: 0, change_percent: 0 },
    ]);
    const result = derivePortfolioValue(snap, { ZZZZ: tick("ZZZZ", 50) });
    expect(result.positionsValue).toBe(1900);
    expect(result.totalValue).toBe(2900);
  });
});
