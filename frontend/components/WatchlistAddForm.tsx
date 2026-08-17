"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  MAX_WATCHLIST_TICKER_LENGTH,
  validateWatchlistTicker,
  watchlistErrorMessage,
  WATCHLIST_REQUEST_FAILED_MESSAGE,
} from "@/lib/watchlistForm";
import type { WatchlistEntry } from "@/lib/types";

interface WatchlistAddFormProps {
  existing: readonly string[];
  onAdded: (entry: WatchlistEntry) => void;
}

/**
 * Inline ticker input plus Add button (D-05) — no modal, no dialog. The Add
 * button disables unless the input validates and while a request is in
 * flight, preventing a double-submit — the same `submitting` pattern the
 * trade bar uses. The error renders inline beneath the form with
 * `role="alert"` and clears on the next input change.
 */
export function WatchlistAddForm({ existing, onAdded }: WatchlistAddFormProps) {
  const [ticker, setTicker] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validation = validateWatchlistTicker(ticker, existing);
  const canSubmit = validation.ok && !submitting;

  function handleTickerChange(value: string) {
    setTicker(value.toUpperCase());
    setError(null);
  }

  async function submitAdd() {
    if (!validation.ok) {
      setError(validation.message);
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: validation.ticker }),
      });

      if (response.status === 400) {
        const body = await response.json();
        setError(watchlistErrorMessage(body.detail, validation.ticker));
        return;
      }
      if (!response.ok) {
        setError(WATCHLIST_REQUEST_FAILED_MESSAGE);
        return;
      }

      const entry = (await response.json()) as WatchlistEntry;
      setTicker("");
      onAdded(entry);
    } catch {
      setError(WATCHLIST_REQUEST_FAILED_MESSAGE);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mb-4 flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <label htmlFor="watchlist-add-ticker" className="sr-only">
          Ticker
        </label>
        <Input
          id="watchlist-add-ticker"
          value={ticker}
          onChange={(event) => handleTickerChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void submitAdd();
            }
          }}
          placeholder="Ticker"
          maxLength={MAX_WATCHLIST_TICKER_LENGTH}
          className="flex-1"
        />
        <Button
          onClick={() => void submitAdd()}
          disabled={!canSubmit}
          className="bg-submit text-submit-foreground hover:bg-submit/80"
        >
          Add
        </Button>
      </div>
      {error && (
        <p className="text-body text-down" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
