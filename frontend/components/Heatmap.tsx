import { HeatmapCell } from "@/components/HeatmapCell";
import { Skeleton } from "@/components/ui/skeleton";
import { HEATMAP_LABEL_MIN_WEIGHT, squarify, type HeatmapItem } from "@/lib/heatmap";

interface HeatmapProps {
  /** `null` means the first `/api/portfolio` fetch hasn't resolved yet. */
  items: HeatmapItem[] | null;
}

/**
 * Portfolio treemap: one rectangle per position, sized by real portfolio
 * weight (flexbox `flex-grow`, no pixel math) and coloured by that
 * position's P&L sign. Loading, empty, and populated states mirror
 * `PositionsTable`'s three-state contract, reusing its exact empty-state
 * copy — this panel and that table render the same zero-position condition.
 */
export function Heatmap({ items }: HeatmapProps) {
  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h2 className="text-heading mb-4 text-foreground">Heatmap</h2>

      {items === null ? (
        <Skeleton className="h-64 min-h-64 w-full" />
      ) : items.length === 0 ? (
        <div className="flex h-64 min-h-64 flex-col items-center justify-center gap-2 text-center">
          <p className="text-heading text-foreground">No open positions</p>
          <p className="text-body text-muted-foreground">
            Buy shares from the trade bar above to open your first position.
          </p>
        </div>
      ) : (
        <div className="flex h-64 min-h-64 w-full flex-col gap-1">
          {squarify(items).map((row, rowIndex) => (
            <div key={rowIndex} className="flex flex-1 gap-1" style={{ flexGrow: row.weight }}>
              {row.items.map((item) => (
                <HeatmapCell
                  key={item.ticker}
                  ticker={item.ticker}
                  weight={item.weight}
                  pnlPercent={item.pnlPercent}
                  showLabel={item.weight >= HEATMAP_LABEL_MIN_WEIGHT}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
