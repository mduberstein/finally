import { Skeleton } from "@/components/ui/skeleton";
import { WATCHLIST_ROW_GRID, WatchlistRow } from "@/components/WatchlistRow";
import type { PriceTick, WatchlistEntry } from "@/lib/types";

const SKELETON_ROW_COUNT = 10;

interface WatchlistProps {
  /** `null` means the initial fetch hasn't resolved yet — renders skeleton rows. */
  entries: WatchlistEntry[] | null;
  prices: Record<string, PriceTick>;
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
}

export function Watchlist({ entries, prices, selectedTicker, onSelectTicker }: WatchlistProps) {
  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h2 className="text-heading mb-4 text-foreground">Watchlist</h2>

      <div className={`${WATCHLIST_ROW_GRID} px-4 pb-2 text-label text-muted-foreground`}>
        <span>TICKER</span>
        <span className="text-right">PRICE</span>
        <span className="text-right">CHG %</span>
      </div>

      {entries === null ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: SKELETON_ROW_COUNT }).map((_, index) => (
            <div key={index} className={`${WATCHLIST_ROW_GRID} px-4 py-3`}>
              <Skeleton className="h-4 w-12" />
              <Skeleton className="h-6 w-20 justify-self-end" />
              <Skeleton className="h-4 w-14 justify-self-end" />
            </div>
          ))}
        </div>
      ) : entries.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-16 text-center">
          <p className="text-heading text-foreground">No tickers being tracked</p>
          <p className="text-body text-muted-foreground">
            Your watchlist will populate automatically when the app starts.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-1">
          {entries.map((entry) => {
            const live = prices[entry.ticker];
            const price = live?.price ?? entry.price;
            const changePercent = live?.change_percent ?? entry.change_percent;
            const direction = live?.direction ?? entry.direction;
            return (
              <WatchlistRow
                key={entry.ticker}
                ticker={entry.ticker}
                price={price}
                changePercent={changePercent}
                direction={direction}
                selected={entry.ticker === selectedTicker}
                onSelect={() => onSelectTicker(entry.ticker)}
              />
            );
          })}
        </div>
      )}
    </section>
  );
}
