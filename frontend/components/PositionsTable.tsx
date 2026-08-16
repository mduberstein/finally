import { POSITION_ROW_GRID, PositionRow } from "@/components/PositionRow";
import { Skeleton } from "@/components/ui/skeleton";
import type { PositionRowData } from "@/lib/portfolio";

const SKELETON_ROW_COUNT = 3;

interface PositionsTableProps {
  /** `null` means the initial fetch hasn't resolved yet — renders skeleton rows. */
  rows: PositionRowData[] | null;
}

export function PositionsTable({ rows }: PositionsTableProps) {
  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h2 className="text-heading mb-4 text-foreground">Positions</h2>

      <div className={`${POSITION_ROW_GRID} px-4 pb-2 text-label text-muted-foreground`}>
        <span>TICKER</span>
        <span className="text-right">QTY</span>
        <span className="text-right">AVG COST</span>
        <span className="text-right">PRICE</span>
        <span className="text-right">UNREAL P&amp;L</span>
        <span className="text-right">CHG %</span>
      </div>

      {rows === null ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: SKELETON_ROW_COUNT }).map((_, index) => (
            <div key={index} className={`${POSITION_ROW_GRID} px-4 py-3`}>
              <Skeleton className="h-4 w-12" />
              <Skeleton className="h-4 w-10 justify-self-end" />
              <Skeleton className="h-4 w-14 justify-self-end" />
              <Skeleton className="h-6 w-16 justify-self-end" />
              <Skeleton className="h-6 w-16 justify-self-end" />
              <Skeleton className="h-4 w-12 justify-self-end" />
            </div>
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-16 text-center">
          <p className="text-heading text-foreground">No open positions</p>
          <p className="text-body text-muted-foreground">
            Buy shares from the trade bar above to open your first position.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-1">
          {rows.map((row) => (
            <PositionRow
              key={row.ticker}
              ticker={row.ticker}
              quantity={row.quantity}
              avgCost={row.avgCost}
              price={row.price}
              unrealizedPnl={row.unrealizedPnl}
              changePercent={row.changePercent}
            />
          ))}
        </div>
      )}
    </section>
  );
}
