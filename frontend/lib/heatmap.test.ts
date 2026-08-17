import { describe, expect, it } from "vitest";

import { deriveHeatmapItems, squarify, type HeatmapItem } from "./heatmap";
import type { PositionRowData } from "./portfolio";

function row(overrides: Partial<PositionRowData> & { ticker: string }): PositionRowData {
  return {
    quantity: 0,
    avgCost: 0,
    price: null,
    unrealizedPnl: null,
    changePercent: null,
    ...overrides,
  };
}

describe("deriveHeatmapItems", () => {
  it("returns null for a null rows argument (loading case)", () => {
    expect(deriveHeatmapItems(null)).toBeNull();
  });

  it("returns an empty array for zero positions, distinct from loading", () => {
    expect(deriveHeatmapItems([])).toEqual([]);
  });

  it("returns one item with value 1000 and weight 1 for a single 10-share position at price 100", () => {
    const rows = [row({ ticker: "AAPL", quantity: 10, price: 100, changePercent: 5 })];
    const items = deriveHeatmapItems(rows);
    expect(items).toHaveLength(1);
    expect(items![0]).toEqual({ ticker: "AAPL", value: 1000, weight: 1, pnlPercent: 5 });
  });

  it("splits weights 0.75/0.25 across two positions worth 3000 and 1000, summing to 1", () => {
    const rows = [
      row({ ticker: "AAPL", quantity: 30, price: 100, changePercent: 1 }),
      row({ ticker: "GOOGL", quantity: 10, price: 100, changePercent: -2 }),
    ];
    const items = deriveHeatmapItems(rows)!;
    expect(items.find((i) => i.ticker === "AAPL")!.weight).toBeCloseTo(0.75, 6);
    expect(items.find((i) => i.ticker === "GOOGL")!.weight).toBeCloseTo(0.25, 6);
    expect(items.reduce((sum, i) => sum + i.weight, 0)).toBeCloseTo(1, 6);
  });

  it("sums to 1 within floating-point tolerance for ten positions", () => {
    const rows = Array.from({ length: 10 }, (_, i) =>
      row({ ticker: `T${i}`, quantity: i + 1, price: 37.5 }),
    );
    const items = deriveHeatmapItems(rows)!;
    expect(items).toHaveLength(10);
    expect(items.reduce((sum, i) => sum + i.weight, 0)).toBeCloseTo(1, 9);
  });

  it("excludes a position whose price is null, and the remaining weights still sum to 1", () => {
    const rows = [
      row({ ticker: "AAPL", quantity: 10, price: 100 }),
      row({ ticker: "ZZZZ", quantity: 5, price: null }),
    ];
    const items = deriveHeatmapItems(rows)!;
    expect(items).toHaveLength(1);
    expect(items[0].ticker).toBe("AAPL");
    expect(items[0].weight).toBeCloseTo(1, 6);
  });

  it("returns an empty array, not NaN weights, when every position has a null price", () => {
    const rows = [row({ ticker: "ZZZZ", quantity: 5, price: null })];
    expect(deriveHeatmapItems(rows)).toEqual([]);
  });

  it("carries changePercent through unchanged as pnlPercent, including a negative value", () => {
    const rows = [row({ ticker: "TSLA", quantity: 2, price: 200, changePercent: -12.34 })];
    const items = deriveHeatmapItems(rows)!;
    expect(items[0].pnlPercent).toBe(-12.34);
  });

  it("returns items sorted descending by weight", () => {
    const rows = [
      row({ ticker: "SMALL", quantity: 1, price: 100 }),
      row({ ticker: "BIG", quantity: 10, price: 100 }),
      row({ ticker: "MID", quantity: 5, price: 100 }),
    ];
    const items = deriveHeatmapItems(rows)!;
    expect(items.map((i) => i.ticker)).toEqual(["BIG", "MID", "SMALL"]);
  });
});

describe("squarify", () => {
  it("returns an empty array of rows for zero items", () => {
    expect(squarify([])).toEqual([]);
  });

  it("returns one row holding that item, with row weight 1, for a single item", () => {
    const items: HeatmapItem[] = [{ ticker: "AAPL", value: 1000, weight: 1, pnlPercent: 0 }];
    const rows = squarify(items);
    expect(rows).toHaveLength(1);
    expect(rows[0].items).toEqual(items);
    expect(rows[0].weight).toBeCloseTo(1, 6);
  });

  it("partitions ten items exactly once each, with no duplicates and no drops", () => {
    const items: HeatmapItem[] = Array.from({ length: 10 }, (_, i) => ({
      ticker: `T${i}`,
      value: 10 - i,
      weight: (10 - i) / 55,
      pnlPercent: 0,
    }));
    const rows = squarify(items);
    const flattened = rows.flatMap((r) => r.items);
    expect(flattened).toHaveLength(10);
    expect(new Set(flattened.map((i) => i.ticker)).size).toBe(10);
    for (const item of items) {
      expect(flattened).toContainEqual(item);
    }
  });

  it("row weights sum to the total input weight", () => {
    const items: HeatmapItem[] = Array.from({ length: 10 }, (_, i) => ({
      ticker: `T${i}`,
      value: 10 - i,
      weight: (10 - i) / 55,
      pnlPercent: 0,
    }));
    const rows = squarify(items);
    const totalWeight = items.reduce((sum, i) => sum + i.weight, 0);
    const rowsWeightSum = rows.reduce((sum, r) => sum + r.weight, 0);
    expect(rowsWeightSum).toBeCloseTo(totalWeight, 6);
  });

  it("preserves descending weight order across the concatenated rows", () => {
    const items: HeatmapItem[] = Array.from({ length: 10 }, (_, i) => ({
      ticker: `T${i}`,
      value: 10 - i,
      weight: (10 - i) / 55,
      pnlPercent: 0,
    }));
    const rows = squarify(items);
    const flattened = rows.flatMap((r) => r.items);
    expect(flattened.map((i) => i.ticker)).toEqual(items.map((i) => i.ticker));
  });

  it("does not mutate the array it was given", () => {
    const items: HeatmapItem[] = Array.from({ length: 5 }, (_, i) => ({
      ticker: `T${i}`,
      value: 5 - i,
      weight: (5 - i) / 15,
      pnlPercent: 0,
    }));
    const copy = [...items];
    squarify(items);
    expect(items).toEqual(copy);
  });
});
