import { describe, expect, it } from "vitest";
import { snapshotSeries } from "./PnlChart";
import type { Snapshot } from "@/lib/types";

function snapshot(recorded_at: string, total_value: number): Snapshot {
  return { recorded_at, total_value };
}

describe("snapshotSeries", () => {
  it("converts snapshots to unix-second points", () => {
    const points = snapshotSeries([
      snapshot("2026-08-11T21:07:12.181031+00:00", 10000),
      snapshot("2026-08-11T21:07:42.184921+00:00", 10010),
    ]);

    expect(points).toEqual([
      { time: 1786482432, value: 10000 },
      { time: 1786482462, value: 10010 },
    ]);
  });

  it("collapses a background snapshot and a trade snapshot in the same second", () => {
    // The chart library rejects duplicate times; the later value wins.
    const points = snapshotSeries([
      snapshot("2026-08-11T21:09:42.203726+00:00", 9998.5),
      snapshot("2026-08-11T21:09:42.540590+00:00", 9990.25),
      snapshot("2026-08-11T21:10:12.206263+00:00", 10002.75),
    ]);

    expect(points).toHaveLength(2);
    expect(points[0].value).toBe(9990.25);
    expect(points.map((point) => point.time)).toEqual([...points].map((p) => p.time).sort());
  });

  it("drops unparseable timestamps and returns [] for no snapshots", () => {
    expect(snapshotSeries([snapshot("not a date", 10)])).toEqual([]);
    expect(snapshotSeries([])).toEqual([]);
  });
});
