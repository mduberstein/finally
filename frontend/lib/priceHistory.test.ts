import { describe, expect, it } from "vitest";

import { appendTicks, MAX_HISTORY_POINTS, pruneToWatchlist } from "./priceHistory";
import type { PriceTick } from "./types";

function tick(overrides: Partial<PriceTick> = {}): PriceTick {
  return {
    ticker: "AAPL",
    price: 190,
    previous_price: 189,
    change: 1,
    change_percent: 0.53,
    direction: "up",
    timestamp: "2026-08-17T00:00:00.000Z",
    ...overrides,
  };
}

describe("appendTicks", () => {
  it("yields one AAPL point carrying that tick's price and timestamp", () => {
    const t1 = tick({ price: 190, timestamp: "t1" });
    const result = appendTicks({}, { AAPL: t1 }, 300);
    expect(result.AAPL).toEqual([{ price: 190, timestamp: "t1" }]);
  });

  it("yields an unchanged AAPL array when the same tick object is delivered again", () => {
    const t1 = tick({ price: 190, timestamp: "t1" });
    const existing = appendTicks({}, { AAPL: t1 }, 300);
    const result = appendTicks(existing, { AAPL: t1 }, 300);
    expect(result.AAPL).toEqual(existing.AAPL);
    expect(result.AAPL).toHaveLength(1);
  });

  it("appends a second point for two ticks at the same price but different timestamps", () => {
    const t1 = tick({ price: 190, timestamp: "t1" });
    const t2 = tick({ price: 190, timestamp: "t2" });
    const existing = appendTicks({}, { AAPL: t1 }, 300);
    const result = appendTicks(existing, { AAPL: t2 }, 300);
    expect(result.AAPL).toEqual([
      { price: 190, timestamp: "t1" },
      { price: 190, timestamp: "t2" },
    ]);
  });

  it("caps the array at maxPoints, dropping the oldest and keeping the newest last", () => {
    let history: Record<string, { price: number; timestamp: string }[]> = {
      AAPL: Array.from({ length: 3 }, (_, i) => ({ price: i, timestamp: `t${i}` })),
    };
    history = appendTicks(history, { AAPL: tick({ price: 99, timestamp: "t-new" }) }, 3);
    expect(history.AAPL).toHaveLength(3);
    expect(history.AAPL[0]).toEqual({ price: 1, timestamp: "t1" });
    expect(history.AAPL[2]).toEqual({ price: 99, timestamp: "t-new" });
  });

  it("does not mutate the history object it was given", () => {
    const original = { AAPL: [{ price: 190, timestamp: "t1" }] };
    const frozen = JSON.parse(JSON.stringify(original));
    appendTicks(original, { AAPL: tick({ price: 191, timestamp: "t2" }) }, 300);
    expect(original).toEqual(frozen);
  });

  it("accumulates two tickers independently", () => {
    const result = appendTicks(
      {},
      {
        AAPL: tick({ ticker: "AAPL", price: 190, timestamp: "t1" }),
        GOOGL: tick({ ticker: "GOOGL", price: 175, timestamp: "t1" }),
      },
      300,
    );
    expect(result.AAPL).toEqual([{ price: 190, timestamp: "t1" }]);
    expect(result.GOOGL).toEqual([{ price: 175, timestamp: "t1" }]);
  });

  it("respects MAX_HISTORY_POINTS as 300", () => {
    expect(MAX_HISTORY_POINTS).toBe(300);
  });
});

describe("pruneToWatchlist", () => {
  it("drops the PYPL array entirely and leaves AAPL untouched", () => {
    const history = { AAPL: [{ price: 1, timestamp: "t1" }], PYPL: [{ price: 2, timestamp: "t1" }] };
    const result = pruneToWatchlist(history, ["AAPL"]);
    expect(result).toEqual({ AAPL: history.AAPL });
    expect(result.PYPL).toBeUndefined();
  });

  it("yields an empty object for an empty ticker list", () => {
    const history = { AAPL: [{ price: 1, timestamp: "t1" }] };
    expect(pruneToWatchlist(history, [])).toEqual({});
  });

  it("starts a re-added ticker's array from length 1, not from its old length", () => {
    let history = appendTicks(
      {},
      { PYPL: tick({ ticker: "PYPL", price: 10, timestamp: "t1" }) },
      300,
    );
    history = appendTicks(history, { PYPL: tick({ ticker: "PYPL", price: 11, timestamp: "t2" }) }, 300);
    expect(history.PYPL).toHaveLength(2);

    history = pruneToWatchlist(history, []);
    history = appendTicks(history, { PYPL: tick({ ticker: "PYPL", price: 12, timestamp: "t3" }) }, 300);
    expect(history.PYPL).toHaveLength(1);
  });
});
