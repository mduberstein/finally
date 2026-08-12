"use client";

import { useEffect, useRef } from "react";
import type { IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts";
import { Panel } from "./Panel";
import { money, signedPercent, toneClass } from "@/lib/format";
import { priceStore, useTick } from "@/lib/priceStore";
import { CHART_THEME } from "@/lib/chartTheme";

/**
 * Price action for the selected symbol, accumulated from the stream. Ticks are
 * pushed into the series imperatively so a chart update costs no React render.
 */
export function MainChart({ ticker }: { ticker: string | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const tick = useTick(ticker ?? "");
  const session = ticker ? priceStore.getSessionChange(ticker) : null;

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !ticker) return;

    let chart: IChartApi | undefined;
    let series: ISeriesApi<"Area"> | undefined;
    let unsubscribe: (() => void) | undefined;
    let disposed = false;

    void (async () => {
      const { createChart, AreaSeries } = await import("lightweight-charts");
      if (disposed) return;

      chart = createChart(container, { ...CHART_THEME, autoSize: true });
      series = chart.addSeries(AreaSeries, {
        lineColor: "#209dd7",
        topColor: "rgba(32, 157, 215, 0.28)",
        bottomColor: "rgba(32, 157, 215, 0.01)",
        lineWidth: 2,
        priceLineColor: "#ecad0a",
        priceLineStyle: 2,
      });

      series.setData(
        priceStore.getSeries(ticker).map((point) => ({
          time: point.time as UTCTimestamp,
          value: point.value,
        })),
      );
      chart.timeScale().fitContent();

      unsubscribe = priceStore.subscribeTicker(ticker, () => {
        const points = priceStore.getSeries(ticker);
        const latest = points[points.length - 1];
        if (!latest) return;
        series?.update({ time: latest.time as UTCTimestamp, value: latest.value });
        // Until the series is long enough to fill the pane, keep refitting so a
        // fresh session does not render as a sliver at the right edge.
        if (points.length < 60) chart?.timeScale().fitContent();
      });
    })();

    return () => {
      disposed = true;
      unsubscribe?.();
      chart?.remove();
    };
  }, [ticker]);

  return (
    <Panel
      title={ticker ? `${ticker} — session` : "Price"}
      testId="main-chart"
      aside={
        ticker && tick ? (
          <span className="flex items-baseline gap-2">
            <span data-testid="main-chart-price" className="text-figure text-ink">
              {money(tick.price)}
            </span>
            <span className={toneClass(session?.percent ?? null)}>
              {session ? signedPercent(session.percent) : "—"}
            </span>
          </span>
        ) : null
      }
    >
      <div className="relative min-h-0 flex-1">
        <div ref={containerRef} data-testid="main-chart-canvas" className="absolute inset-0" />
        {!ticker ? (
          <EmptyOverlay>Select a symbol from the watchlist.</EmptyOverlay>
        ) : !tick ? (
          <EmptyOverlay>Waiting for {ticker} on the stream…</EmptyOverlay>
        ) : null}
      </div>
    </Panel>
  );
}

function EmptyOverlay({ children }: { children: React.ReactNode }) {
  return (
    <p className="absolute inset-0 flex items-center justify-center text-ink-faint">{children}</p>
  );
}
