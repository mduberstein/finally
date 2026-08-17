"use client";

import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { WATCHLIST_ROW_GRID, WatchlistRow } from "@/components/WatchlistRow";
import { WatchlistAddForm } from "@/components/WatchlistAddForm";
import type { PricePoint } from "@/lib/priceHistory";
import type { PriceTick, WatchlistEntry } from "@/lib/types";
import { WATCHLIST_REQUEST_FAILED_MESSAGE } from "@/lib/watchlistForm";

const SKELETON_ROW_COUNT = 10;

interface WatchlistProps {
  /** `null` means the initial fetch hasn't resolved yet — renders skeleton rows. */
  entries: WatchlistEntry[] | null;
  prices: Record<string, PriceTick>;
  history: Record<string, PricePoint[]>;
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
  onAdded: (entry: WatchlistEntry) => void;
  onRemove: (ticker: string) => Promise<boolean>;
}

/**
 * Removal is NOT optimistic: the request goes out, and only on success does
 * the parent drop the row (via `onRemove`'s resolved watchlist state
 * update). On failure the row stays in place and a brief inline error
 * renders beneath that row, matching the add form's convention (UI-SPEC
 * "watchlist add/remove: request failure").
 */
export function Watchlist({
  entries,
  prices,
  history,
  selectedTicker,
  onSelectTicker,
  onAdded,
  onRemove,
}: WatchlistProps) {
  const existingTickers = entries?.map((entry) => entry.ticker) ?? [];
  const [removingTicker, setRemovingTicker] = useState<string | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});

  async function handleRemove(ticker: string) {
    setRemovingTicker(ticker);
    setRowErrors((current) => {
      if (!(ticker in current)) return current;
      const next = { ...current };
      delete next[ticker];
      return next;
    });
    try {
      const removed = await onRemove(ticker);
      if (!removed) {
        setRowErrors((current) => ({ ...current, [ticker]: WATCHLIST_REQUEST_FAILED_MESSAGE }));
      }
    } finally {
      setRemovingTicker(null);
    }
  }

  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h2 className="text-heading mb-4 text-foreground">Watchlist</h2>

      <WatchlistAddForm existing={existingTickers} onAdded={onAdded} />

      <div className={`${WATCHLIST_ROW_GRID} px-4 pb-2 text-label text-muted-foreground`}>
        <span>TICKER</span>
        <span className="text-right">PRICE</span>
        <span className="text-right">CHG %</span>
        <span />
        <span />
      </div>

      {entries === null ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: SKELETON_ROW_COUNT }).map((_, index) => (
            <div key={index} className={`${WATCHLIST_ROW_GRID} px-4 py-3`}>
              <Skeleton className="h-4 w-12" />
              <Skeleton className="h-6 w-20 justify-self-end" />
              <Skeleton className="h-4 w-14 justify-self-end" />
              <Skeleton className="h-4 w-full" />
              <span />
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
            const rowError = rowErrors[entry.ticker];
            return (
              <div key={entry.ticker}>
                <WatchlistRow
                  ticker={entry.ticker}
                  price={price}
                  changePercent={changePercent}
                  direction={direction}
                  points={history[entry.ticker] ?? []}
                  selected={entry.ticker === selectedTicker}
                  onSelect={() => onSelectTicker(entry.ticker)}
                  onRemove={() => void handleRemove(entry.ticker)}
                  removing={removingTicker === entry.ticker}
                />
                {rowError && (
                  <p className="text-body px-4 text-down" role="alert">
                    {rowError}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
