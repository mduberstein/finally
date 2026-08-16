"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MALFORMED_INPUT_MESSAGE, tradeErrorMessage, validateTradeInput } from "@/lib/trade";

interface TradeBarProps {
  onTraded: () => void;
}

const TICKER_MAX_LENGTH = 5;

/**
 * Ticker and quantity inputs with Buy and Sell submit actions. Fills
 * instantly at the server's cached price with no confirmation dialog
 * (PORT-02, PORT-03, UI-03). Each domain rejection renders inline beneath
 * the inputs in the exact 02-UI-SPEC.md copy and clears on the next input
 * change (D-04).
 */
export function TradeBar({ onTraded }: TradeBarProps) {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validation = validateTradeInput(ticker, quantity);
  const canSubmit = validation.ok && !submitting;

  function handleTickerChange(value: string) {
    setTicker(value);
    setError(null);
  }

  function handleQuantityChange(value: string) {
    setQuantity(value);
    setError(null);
  }

  async function submitTrade(side: "buy" | "sell") {
    if (!validation.ok) {
      setError(MALFORMED_INPUT_MESSAGE);
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/portfolio/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: validation.ticker,
          side,
          quantity: validation.quantity,
        }),
      });

      if (response.status === 400) {
        const body = await response.json();
        setError(tradeErrorMessage(body.detail));
        return;
      }
      if (!response.ok) {
        setError(tradeErrorMessage(null));
        return;
      }

      setTicker("");
      setQuantity("");
      onTraded();
    } catch {
      setError(tradeErrorMessage(null));
    } finally {
      setSubmitting(false);
    }
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
            onChange={(event) => handleTickerChange(event.target.value)}
            placeholder="AAPL"
            maxLength={TICKER_MAX_LENGTH}
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
            onChange={(event) => handleQuantityChange(event.target.value)}
            placeholder="10"
            inputMode="numeric"
            className="w-24"
          />
        </div>
        <Button
          onClick={() => submitTrade("buy")}
          disabled={!canSubmit}
          className="bg-submit text-submit-foreground hover:bg-submit/80"
        >
          Buy
        </Button>
        {/* "Sell" is the outline treatment (UI-SPEC) — not the shadcn destructive
            variant, since a sale is a reversible market order, not destructive. */}
        <Button
          onClick={() => submitTrade("sell")}
          disabled={!canSubmit}
          variant="outline"
          className="border-down text-down hover:bg-down/10"
        >
          Sell
        </Button>
      </div>
      {error && (
        <p className="text-body mt-2 text-down" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
