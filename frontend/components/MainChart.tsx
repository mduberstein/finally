"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPercent, formatPrice } from "@/lib/format";
import type { PricePoint } from "@/lib/priceHistory";

interface MainChartProps {
  ticker: string | null;
  points: PricePoint[];
  price: number | null;
  changePercent: number | null;
}

const SELECT_TICKER_PROMPT = "Select a ticker from the watchlist to view its price chart.";

/** Local `HH:MM:SS` tick label — matches `PnlChart`'s per-panel time
 * formatting convention, at second resolution since this chart's data
 * arrives roughly every 500ms rather than every 30s. */
function formatTimeTick(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Recharts line chart of the selected watchlist ticker's accumulated price
 * history. Draws instantly from history already accumulated on the page
 * from the one open SSE stream — no fetch, no loading state. Stroked with
 * the Accent Blue selected-ticker colour (D-01), never the up/down P&L
 * tokens: this line is a selection indicator, not a gain/loss signal.
 */
export function MainChart({ ticker, points, price, changePercent }: MainChartProps) {
  const showPrompt = ticker == null || points.length === 0;

  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h2 className="text-heading mb-4 text-foreground">Chart</h2>

      {ticker != null && (
        <div className="mb-4 flex items-baseline gap-3">
          <span className="text-heading text-foreground">{ticker}</span>
          <span className="numeric text-display text-foreground">{formatPrice(price)}</span>
          <span className="numeric text-body text-muted-foreground">
            {formatPercent(changePercent)}
          </span>
        </div>
      )}

      <div className="h-96">
        {showPrompt ? (
          <div className="flex h-full items-center justify-center text-center">
            <p className="text-body text-muted-foreground">{SELECT_TICKER_PROMPT}</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimeTick}
                tick={{ fontSize: 12 }}
                stroke="var(--muted-foreground)"
              />
              <YAxis
                dataKey="price"
                domain={["auto", "auto"]}
                tick={{ fontSize: 12 }}
                stroke="var(--muted-foreground)"
                tickFormatter={formatPrice}
              />
              <Tooltip
                contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)" }}
                labelStyle={{ color: "var(--popover-foreground)" }}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="var(--primary)"
                dot={points.length < 2}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
