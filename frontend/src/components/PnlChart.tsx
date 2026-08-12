"use client";

import { useEffect, useRef } from "react";
import type { IChartApi, UTCTimestamp } from "lightweight-charts";
import { Panel } from "./Panel";
import { signedMoney, toneClass } from "@/lib/format";
import { CHART_THEME } from "@/lib/chartTheme";
import type { Snapshot } from "@/lib/types";

/**
 * Snapshots as chart points, at one-second resolution.
 *
 * The backend records every 30 seconds and again immediately after each trade,
 * so two snapshots can share a second. The chart library requires strictly
 * increasing times, so the later value wins for that second.
 */
export function snapshotSeries(snapshots: Snapshot[]): { time: number; value: number }[] {
  const points: { time: number; value: number }[] = [];

  for (const snapshot of snapshots) {
    const time = Math.floor(new Date(snapshot.recorded_at).getTime() / 1000);
    if (!Number.isFinite(time)) continue;

    const last = points[points.length - 1];
    if (last && last.time >= time) last.value = snapshot.total_value;
    else points.push({ time, value: snapshot.total_value });
  }

  return points;
}

/** Total portfolio value over time, from the server's snapshot log. */
export function PnlChart({ snapshots }: { snapshots: Snapshot[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const first = snapshots[0]?.total_value;
  const last = snapshots[snapshots.length - 1]?.total_value;
  const drift = first != null && last != null ? last - first : null;

  useEffect(() => {
    const container = containerRef.current;
    if (!container || snapshots.length === 0) return;

    let chart: IChartApi | undefined;
    let disposed = false;

    void (async () => {
      const { createChart, LineSeries } = await import("lightweight-charts");
      if (disposed) return;

      chart = createChart(container, { ...CHART_THEME, autoSize: true });
      const rising = (last ?? 0) >= (first ?? 0);
      const series = chart.addSeries(LineSeries, {
        color: rising ? "#21c07a" : "#f0576b",
        lineWidth: 2,
        priceLineVisible: false,
      });

      series.setData(
        snapshotSeries(snapshots).map((point) => ({
          time: point.time as UTCTimestamp,
          value: point.value,
        })),
      );

      if (first != null) {
        series.createPriceLine({
          price: first,
          color: "#59616f",
          lineWidth: 1,
          lineStyle: 1,
          axisLabelVisible: false,
          title: "start",
        });
      }
      chart.timeScale().fitContent();
    })();

    return () => {
      disposed = true;
      chart?.remove();
    };
  }, [snapshots, first, last]);

  return (
    <Panel
      title="Portfolio value"
      testId="pnl-chart"
      aside={
        drift != null ? (
          <span className={toneClass(drift)}>{signedMoney(drift)}</span>
        ) : null
      }
    >
      <div className="relative min-h-0 flex-1">
        <div ref={containerRef} data-testid="pnl-chart-canvas" className="absolute inset-0" />
        {snapshots.length === 0 ? (
          <p
            data-testid="pnl-chart-empty"
            className="absolute inset-0 flex items-center justify-center text-ink-faint"
          >
            No snapshots yet. The first lands within 30 seconds.
          </p>
        ) : null}
      </div>
    </Panel>
  );
}
