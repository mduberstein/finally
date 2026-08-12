"use client";

import { useState } from "react";
import { money } from "@/lib/format";
import { priceStore, usePriceVersion } from "@/lib/priceStore";
import type { TradeSide } from "@/lib/types";

export interface TradeResult {
  ok: boolean;
  message: string;
}

interface TradeBarProps {
  selected: string | null;
  onTrade: (ticker: string, shares: number, side: TradeSide) => Promise<TradeResult>;
}

/**
 * The order ticket, docked across the base of the terminal. Market orders fill
 * instantly; the only feedback is the line to the right of the buttons.
 */
export function TradeBar({ selected, onTrade }: TradeBarProps) {
  usePriceVersion();
  const [ticker, setTicker] = useState(selected ?? "");
  const [shares, setShares] = useState("");
  const [result, setResult] = useState<TradeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastSelected, setLastSelected] = useState(selected);

  // Selecting a symbol anywhere in the terminal loads it into the ticket.
  if (selected !== lastSelected) {
    setLastSelected(selected);
    if (selected) setTicker(selected);
  }

  const symbol = ticker.trim().toUpperCase();
  const parsedShares = Number(shares);
  const valid = symbol.length > 0 && Number.isFinite(parsedShares) && parsedShares > 0;
  const price = priceStore.getPrice(symbol);
  const estimate = valid && price != null ? price * parsedShares : null;

  async function submit(side: TradeSide) {
    if (!valid || busy) return;
    setBusy(true);
    setResult(await onTrade(symbol, parsedShares, side));
    setBusy(false);
  }

  return (
    <section
      data-testid="trade-bar"
      className="sticky bottom-0 z-10 flex h-11 shrink-0 items-center gap-2 overflow-x-auto border-t border-line-soft bg-panel px-2 lg:static lg:border-t-0"
    >
      <span aria-hidden className="h-2.5 w-0.5 bg-accent" />
      <h2 className="label mr-1">Ticket</h2>

      <label className="label sr-only" htmlFor="trade-ticker">
        Symbol
      </label>
      <input
        id="trade-ticker"
        data-testid="trade-ticker-input"
        value={ticker}
        maxLength={5}
        placeholder="SYM"
        onChange={(event) => setTicker(event.target.value.toUpperCase().replace(/[^A-Z]/g, ""))}
        className="w-20 bg-raise px-2 py-1 text-ink placeholder:text-ink-faint focus:outline-none"
      />

      <label className="label sr-only" htmlFor="trade-quantity">
        Quantity
      </label>
      <input
        id="trade-quantity"
        data-testid="trade-quantity-input"
        value={shares}
        inputMode="decimal"
        placeholder="QTY"
        onChange={(event) => setShares(event.target.value.replace(/[^0-9.]/g, ""))}
        className="w-24 bg-raise px-2 py-1 text-right text-ink placeholder:text-ink-faint focus:outline-none"
      />

      <button
        data-testid="trade-buy"
        disabled={!valid || busy}
        onClick={() => submit("buy")}
        className="bg-purple px-4 py-1 text-ink transition-colors hover:bg-purple/80 disabled:opacity-35"
      >
        Buy
      </button>
      <button
        data-testid="trade-sell"
        disabled={!valid || busy}
        onClick={() => submit("sell")}
        className="border border-down/60 px-4 py-1 text-down transition-colors hover:bg-down/15 disabled:opacity-35"
      >
        Sell
      </button>

      <span className="label whitespace-nowrap">
        Est <span className="text-ink-dim">{money(estimate)}</span>
      </span>

      {result ? (
        <span
          data-testid="trade-status"
          role="status"
          className={`ml-auto truncate pl-2 ${result.ok ? "text-up" : "text-down"}`}
        >
          {result.message}
        </span>
      ) : null}
    </section>
  );
}
