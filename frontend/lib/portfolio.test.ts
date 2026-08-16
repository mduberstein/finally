import { describe, expect, it } from "vitest";

import { derivePortfolioValue, derivePositionRows } from "./portfolio";
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

describe("derivePositionRows", () => {
  it("returns null for a null snapshot, distinguishing not-loaded-yet from empty", () => {
    expect(derivePositionRows(null, {})).toBeNull();
  });

  it("returns an empty array for a snapshot with no positions", () => {
    expect(derivePositionRows(snapshot(10000), {})).toEqual([]);
  });

  it("derives price, unrealizedPnl, and changePercent from the snapshot price when no live tick exists", () => {
    const snap = snapshot(5000, [
      { ticker: "AAPL", quantity: 10, avg_cost: 190, price: 195, unrealized_pnl: 0, change_percent: 0 },
    ]);
    const rows = derivePositionRows(snap, {});
    expect(rows).toHaveLength(1);
    expect(rows![0].ticker).toBe("AAPL");
    expect(rows![0].quantity).toBe(10);
    expect(rows![0].avgCost).toBe(190);
    expect(rows![0].price).toBe(195);
    expect(rows![0].unrealizedPnl).toBeCloseTo(50, 6);
    expect(rows![0].changePercent).toBeCloseTo(2.6316, 4);
  });

  it("overrides the snapshot price with a live tick and recomputes derived figures from it", () => {
    const snap = snapshot(5000, [
      { ticker: "AAPL", quantity: 10, avg_cost: 190, price: 195, unrealized_pnl: 0, change_percent: 0 },
    ]);
    const rows = derivePositionRows(snap, { AAPL: tick("AAPL", 200) });
    expect(rows![0].price).toBe(200);
    expect(rows![0].unrealizedPnl).toBeCloseTo(100, 6);
    expect(rows![0].changePercent).toBeCloseTo(5.2632, 4);
  });

  it("returns null price, unrealizedPnl, and changePercent when no price is available from either source", () => {
    const snap = snapshot(1000, [
      { ticker: "ZZZZ", quantity: 5, avg_cost: 10, price: null, unrealized_pnl: null, change_percent: null },
    ]);
    const rows = derivePositionRows(snap, {});
    expect(rows![0].price).toBeNull();
    expect(rows![0].unrealizedPnl).toBeNull();
    expect(rows![0].changePercent).toBeNull();
  });

  it("derives values from a live tick when the snapshot price is null", () => {
    const snap = snapshot(1000, [
      { ticker: "ZZZZ", quantity: 5, avg_cost: 10, price: null, unrealized_pnl: null, change_percent: null },
    ]);
    const rows = derivePositionRows(snap, { ZZZZ: tick("ZZZZ", 20) });
    expect(rows![0].price).toBe(20);
    expect(rows![0].unrealizedPnl).toBeCloseTo(50, 6);
    expect(rows![0].changePercent).toBeCloseTo(100, 6);
  });

  it("returns a null changePercent for a zero average cost rather than infinity or NaN", () => {
    const snap = snapshot(1000, [
      { ticker: "FREE", quantity: 3, avg_cost: 0, price: 10, unrealized_pnl: 0, change_percent: 0 },
    ]);
    const rows = derivePositionRows(snap, {});
    expect(rows![0].changePercent).toBeNull();
    expect(rows![0].unrealizedPnl).toBeCloseTo(30, 6);
  });

  it("returns rows in the same order as snapshot.positions, ignoring a live tick for a ticker not held", () => {
    const snap = snapshot(1000, [
      { ticker: "AAPL", quantity: 10, avg_cost: 190, price: 195, unrealized_pnl: 0, change_percent: 0 },
      { ticker: "GOOGL", quantity: 5, avg_cost: 175, price: 180, unrealized_pnl: 0, change_percent: 0 },
    ]);
    const rows = derivePositionRows(snap, { ZZZZ: tick("ZZZZ", 50) });
    expect(rows).toHaveLength(2);
    expect(rows![0].ticker).toBe("AAPL");
    expect(rows![1].ticker).toBe("GOOGL");
  });
});
