/** Pure watchlist ticker validation and rejection-to-copy mapping,
 * mirroring `lib/trade.ts`. Client-side validation is a courtesy for
 * instant feedback; the server remains the sole authority. */

export const MAX_WATCHLIST_TICKER_LENGTH = 10;

const TICKER_PATTERN = /^[A-Z]{1,10}$/;

export const INVALID_TICKER_MESSAGE =
  "Enter a valid ticker symbol (letters only, up to 10 characters).";

export const WATCHLIST_REQUEST_FAILED_MESSAGE = "Couldn't update your watchlist — try again.";

const WATCHLIST_FULL_MESSAGE = "Your watchlist is full — remove a ticker before adding another.";

export function duplicateTickerMessage(ticker: string): string {
  return `${ticker} is already on your watchlist.`;
}

export type WatchlistTickerResult =
  | { ok: true; ticker: string }
  | { ok: false; message: string };

/**
 * Trim, uppercase, require one to ten letters, then reject a symbol already
 * in `existing` with the duplicate sentence.
 */
export function validateWatchlistTicker(
  raw: string,
  existing: readonly string[],
): WatchlistTickerResult {
  const ticker = raw.trim().toUpperCase();
  if (!TICKER_PATTERN.test(ticker)) {
    return { ok: false, message: INVALID_TICKER_MESSAGE };
  }
  if (existing.includes(ticker)) {
    return { ok: false, message: duplicateTickerMessage(ticker) };
  }
  return { ok: true, ticker };
}

/**
 * Map the backend `code` values Plan 01 emits to copy. Anything
 * unrecognised or malformed maps to the request-failed sentence rather than
 * raw JSON.
 */
export function watchlistErrorMessage(detail: unknown, ticker: string): string {
  if (detail === null || typeof detail !== "object") {
    return WATCHLIST_REQUEST_FAILED_MESSAGE;
  }
  const payload = detail as Record<string, unknown>;

  switch (payload.code) {
    case "invalid_ticker":
      return INVALID_TICKER_MESSAGE;
    case "duplicate_ticker":
      return duplicateTickerMessage(ticker);
    case "watchlist_full":
      return WATCHLIST_FULL_MESSAGE;
    default:
      return WATCHLIST_REQUEST_FAILED_MESSAGE;
  }
}
