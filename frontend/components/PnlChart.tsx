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
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice } from "@/lib/format";
import { STARTING_CASH_BALANCE } from "@/lib/portfolio";
import type { PortfolioSnapshotPoint } from "@/lib/types";

interface PnlChartProps {
  /** `null` means the first `/api/portfolio/history` fetch hasn't resolved yet. */
  points: PortfolioSnapshotPoint[] | null;
}

/** Local `HH:MM` tick label — the axis is a fixed-format timestamp, never
 * user-generated text. */
function formatTimeTick(recordedAt: string): string {
  return new Date(recordedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * Recharts line chart of total portfolio value over time. Plots only what
 * `GET /api/portfolio/history` returned — no synthesized starting point, no
 * interpolation, no extension to the current moment. The chart is a record
 * of recorded snapshots, not an estimate of simulated performance.
 */
export function PnlChart({ points }: PnlChartProps) {
  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h2 className="text-heading mb-4 text-foreground">Portfolio Value</h2>

      {points === null ? (
        <Skeleton className="h-64 w-full" />
      ) : points.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center gap-2 text-center">
          <p className="text-heading text-foreground">No portfolio history yet</p>
          <p className="text-body text-muted-foreground">
            Your first snapshot appears within 30 seconds, or immediately after your first trade.
          </p>
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis
                dataKey="recorded_at"
                tickFormatter={formatTimeTick}
                tick={{ fontSize: 12 }}
                stroke="var(--muted-foreground)"
              />
              <YAxis
                dataKey="total_value"
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
                dataKey="total_value"
                stroke={
                  points[points.length - 1].total_value >= STARTING_CASH_BALANCE
                    ? "var(--up)"
                    : "var(--down)"
                }
                dot={points.length === 1}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
