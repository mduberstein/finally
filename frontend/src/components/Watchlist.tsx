"use client";

import { useState, type FormEvent } from "react";
import { Panel } from "./Panel";
import { Sparkline } from "./Sparkline";
import { money, signedPercent, toneClass, toneOf } from "@/lib/format";
import { priceStore, useTick } from "@/lib/priceStore";
import { useFlash } from "@/lib/useFlash";
import type { WatchlistEntry } from "@/lib/types";

interface WatchlistProps {
  entries: WatchlistEntry[];
  loading: boolean;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<string | null>;
  onRemove: (ticker: string) => void;
}

const ROW = "grid grid-cols-[3.1rem_1fr_3.4rem_3.5rem_0.9rem] items-center gap-1.5 px-2";

export function Watchlist({
  entries,
  loading,
  selected,
  onSelect,
  onAdd,
  onRemove,
}: WatchlistProps) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const ticker = draft.trim().toUpperCase();
    if (!ticker || busy) return;
    setBusy(true);
    const failure = await onAdd(ticker);
    setBusy(false);
    setError(failure);
    if (!failure) setDraft("");
  }

  return (
    <Panel
      title="Watchlist"
      testId="watchlist"
      aside={<span className="label">chg since open</span>}
    >
      <div className={`${ROW} label h-6 border-b border-line-soft`}>
        <span>Sym</span>
        <span className="text-right">Last</span>
        <span className="text-right">Chg</span>
        <span className="text-right">Trend</span>
        <span />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
        {loading && entries.length === 0 ? (
          <p className="px-2 py-3 text-ink-faint">Loading symbols…</p>
        ) : entries.length === 0 ? (
          <p data-testid="watchlist-empty" className="px-2 py-3 text-ink-faint">
            No symbols yet. Add one below to start streaming prices.
          </p>
        ) : (
          entries.map((entry) => (
            <WatchlistRow
              key={entry.ticker}
              entry={entry}
              selected={entry.ticker === selected}
              onSelect={onSelect}
              onRemove={onRemove}
            />
          ))
        )}
      </div>

      <form onSubmit={submit} className="shrink-0 border-t border-line-soft p-1.5">
        <div className="flex gap-1">
          <input
            data-testid="watchlist-add-input"
            aria-label="Add symbol"
            value={draft}
            maxLength={5}
            placeholder="ADD SYMBOL"
            onChange={(event) => {
              setDraft(event.target.value.toUpperCase().replace(/[^A-Z]/g, ""));
              setError(null);
            }}
            className="min-w-0 flex-1 bg-raise px-1.5 py-1 text-ink placeholder:text-ink-faint focus:outline-none"
          />
          <button
            data-testid="watchlist-add-submit"
            type="submit"
            disabled={busy}
            className="border border-blue/50 px-2 py-1 text-blue transition-colors hover:bg-blue/15 disabled:opacity-40"
          >
            Add
          </button>
        </div>
        {error ? (
          <p data-testid="watchlist-add-error" className="mt-1 text-down">
            {error}
          </p>
        ) : null}
      </form>
    </Panel>
  );
}

interface RowProps {
  entry: WatchlistEntry;
  selected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

function WatchlistRow({ entry, selected, onSelect, onRemove }: RowProps) {
  const tick = useTick(entry.ticker);
  const flashRef = useFlash<HTMLSpanElement>(entry.ticker);
  const price = tick?.price ?? entry.price;
  const session = priceStore.getSessionChange(entry.ticker);
  const tone = toneOf(session?.percent ?? null);

  return (
    <div
      data-testid={`watchlist-row-${entry.ticker}`}
      data-selected={selected}
      role="button"
      tabIndex={0}
      onClick={() => onSelect(entry.ticker)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(entry.ticker);
        }
      }}
      className={`${ROW} group h-7 cursor-pointer border-b border-line-soft/60 hover:bg-raise/60 ${
        selected ? "rail bg-raise" : ""
      }`}
    >
      <span className={selected ? "text-accent" : "text-ink"}>{entry.ticker}</span>
      <span className="text-right text-ink">
        <span
          ref={flashRef}
          data-testid={`watchlist-price-${entry.ticker}`}
          className="flashable inline-block rounded-xs px-1"
        >
          {money(price)}
        </span>
      </span>
      <span
        data-testid={`watchlist-change-${entry.ticker}`}
        className={`text-right ${toneClass(session?.percent ?? null)}`}
      >
        {session ? signedPercent(session.percent) : "—"}
      </span>
      <span className="flex justify-end">
        <Sparkline ticker={entry.ticker} tone={tone} price={price} />
      </span>
      <button
        data-testid={`watchlist-remove-${entry.ticker}`}
        aria-label={`Remove ${entry.ticker}`}
        onClick={(event) => {
          event.stopPropagation();
          onRemove(entry.ticker);
        }}
        className="text-ink-faint opacity-0 transition-opacity group-hover:opacity-100 hover:text-down focus-visible:opacity-100"
      >
        ×
      </button>
    </div>
  );
}
