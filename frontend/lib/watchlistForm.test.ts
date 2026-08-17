import { describe, expect, it } from "vitest";

import {
  duplicateTickerMessage,
  INVALID_TICKER_MESSAGE,
  validateWatchlistTicker,
  watchlistErrorMessage,
  WATCHLIST_REQUEST_FAILED_MESSAGE,
} from "./watchlistForm";

describe("validateWatchlistTicker", () => {
  it("trims and uppercases a valid ticker", () => {
    const result = validateWatchlistTicker("  pypl ", []);
    expect(result).toEqual({ ok: true, ticker: "PYPL" });
  });

  it("is not ok for a ticker containing digits", () => {
    const result = validateWatchlistTicker("AA1", []);
    expect(result).toEqual({ ok: false, message: INVALID_TICKER_MESSAGE });
  });

  it("is not ok for an empty ticker", () => {
    const result = validateWatchlistTicker("", []);
    expect(result).toEqual({ ok: false, message: INVALID_TICKER_MESSAGE });
  });

  it("is not ok for a ticker over 10 characters", () => {
    const result = validateWatchlistTicker("ABCDEFGHIJK", []);
    expect(result).toEqual({ ok: false, message: INVALID_TICKER_MESSAGE });
  });

  it("is not ok for a ticker containing a hyphen", () => {
    const result = validateWatchlistTicker("AA-PL", []);
    expect(result).toEqual({ ok: false, message: INVALID_TICKER_MESSAGE });
  });

  it("is not ok with the duplicate sentence naming the ticker when already present", () => {
    const result = validateWatchlistTicker("aapl", ["AAPL"]);
    expect(result).toEqual({ ok: false, message: duplicateTickerMessage("AAPL") });
  });
});

describe("watchlistErrorMessage", () => {
  it("maps the duplicate code to the duplicate sentence", () => {
    const message = watchlistErrorMessage({ code: "duplicate_ticker" }, "AAPL");
    expect(message).toBe(duplicateTickerMessage("AAPL"));
  });

  it("maps the invalid code to the invalid sentence", () => {
    const message = watchlistErrorMessage({ code: "invalid_ticker" }, "AA1");
    expect(message).toBe(INVALID_TICKER_MESSAGE);
  });

  it("maps a null detail to the request-failed sentence", () => {
    expect(watchlistErrorMessage(null, "AAPL")).toBe(WATCHLIST_REQUEST_FAILED_MESSAGE);
  });

  it("maps an unrecognised code to the request-failed sentence", () => {
    expect(watchlistErrorMessage({ code: "something_else" }, "AAPL")).toBe(
      WATCHLIST_REQUEST_FAILED_MESSAGE,
    );
  });
});
