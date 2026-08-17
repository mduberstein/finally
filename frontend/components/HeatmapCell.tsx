import { formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

interface HeatmapCellProps {
  ticker: string;
  weight: number;
  pnlPercent: number | null;
  showLabel: boolean;
}

/**
 * One weighted, P&L-coloured rectangle. `flexGrow: weight` is the only
 * inline style — the browser's flex engine does the proportional sizing,
 * so this component computes no pixels, reads no bounding rectangle, and
 * registers no resize observer.
 */
export function HeatmapCell({ ticker, weight, pnlPercent, showLabel }: HeatmapCellProps) {
  const profitable = pnlPercent != null && pnlPercent >= 0;
  const weightPercent = `${(weight * 100).toFixed(1)}%`;
  const pnlLabel = formatPercent(pnlPercent);

  return (
    <div
      style={{ flexGrow: weight }}
      title={`${ticker} — ${weightPercent} of portfolio, ${pnlLabel}`}
      className={cn(
        "min-w-0 overflow-hidden border border-border p-2",
        profitable ? "bg-up/70" : "bg-down/70",
      )}
    >
      {showLabel ? (
        <>
          <p className="text-label truncate text-foreground">{ticker}</p>
          <p className="numeric text-label text-foreground">{pnlLabel}</p>
        </>
      ) : null}
    </div>
  );
}
