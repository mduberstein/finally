import { formatPrice } from "./format";

/** Client-side pre-check copy only — the backend re-validates independently
 * as the security boundary (D-01, D-03). */
export const MALFORMED_INPUT_MESSAGE = "Enter a ticker and a whole number of shares.";

const MAX_TICKER_LENGTH = 5;

export type TradeInputResult =
  | { ok: true; ticker: string; quantity: number }
  | { ok: false; message: string };

/**
 * Trim and uppercase the ticker, and require a whole number of shares of at
 * least 1 (D-03: the manual trade bar stays whole-share even though the
 * schema stores REAL). Pure validation, no network call.
 */
export function validateTradeInput(ticker: string, quantity: string): TradeInputResult {
  const normalizedTicker = ticker.trim().toUpperCase();
  if (!normalizedTicker || normalizedTicker.length > MAX_TICKER_LENGTH) {
    return { ok: false, message: MALFORMED_INPUT_MESSAGE };
  }

  const trimmedQuantity = quantity.trim();
  if (!/^\d+$/.test(trimmedQuantity)) {
    return { ok: false, message: MALFORMED_INPUT_MESSAGE };
  }

  const parsedQuantity = Number.parseInt(trimmedQuantity, 10);
  if (parsedQuantity < 1) {
    return { ok: false, message: MALFORMED_INPUT_MESSAGE };
  }

  return { ok: true, ticker: normalizedTicker, quantity: parsedQuantity };
}

/**
 * Map a backend rejection detail to the exact UI-SPEC sentence. Every
 * message states a fact and a limit — never a characterisation of the
 * user's decision, never urgency to trade again. An unrecognised or
 * malformed payload returns a neutral fallback rather than raw JSON.
 */
export function tradeErrorMessage(detail: unknown): string {
  if (detail === null || typeof detail !== "object") {
    return "Something went wrong with that trade — please try again.";
  }
  const payload = detail as Record<string, unknown>;

  switch (payload.code) {
    case "insufficient_cash": {
      const cashBalance = typeof payload.cash_balance === "number" ? payload.cash_balance : null;
      return `Not enough cash — this trade costs more than your $${formatPrice(cashBalance)} available.`;
    }
    case "insufficient_shares": {
      const owned = typeof payload.owned === "number" ? payload.owned : 0;
      const ticker = typeof payload.ticker === "string" ? payload.ticker : "that ticker";
      return `You only own ${owned} shares of ${ticker}.`;
    }
    case "untradable_ticker": {
      const ticker = typeof payload.ticker === "string" ? payload.ticker : "That ticker";
      return `${ticker} isn't on your watchlist — trade one of the tickers shown above.`;
    }
    default:
      return "Something went wrong with that trade — please try again.";
  }
}
