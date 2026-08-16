"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface TradeBarProps {
  onTraded: () => void;
}

/**
 * Ticker and quantity inputs with a Buy submit action. Fills instantly at
 * the server's cached price with no confirmation dialog (PORT-02, UI-03).
 * Sell, the oversell guard, and inline error copy are Plan 02.
 */
export function TradeBar({ onTraded }: TradeBarProps) {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");

  async function handleBuy() {
    const parsedQuantity = Number.parseInt(quantity, 10);
    if (!ticker || !Number.isFinite(parsedQuantity) || parsedQuantity <= 0) return;

    await fetch("/api/portfolio/trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticker: ticker.toUpperCase(),
        side: "buy",
        quantity: parsedQuantity,
      }),
    });
    onTraded();
  }

  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h2 className="text-heading mb-4 text-foreground">Trade</h2>
      <div className="flex items-end gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="trade-ticker" className="text-label text-muted-foreground">
            Ticker
          </label>
          <Input
            id="trade-ticker"
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
            placeholder="AAPL"
            className="w-28"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="trade-quantity" className="text-label text-muted-foreground">
            Quantity
          </label>
          <Input
            id="trade-quantity"
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
            placeholder="10"
            inputMode="numeric"
            className="w-24"
          />
        </div>
        <Button
          onClick={handleBuy}
          className="bg-submit text-submit-foreground hover:bg-submit/80"
        >
          Buy
        </Button>
      </div>
    </section>
  );
}
