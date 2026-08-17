"""Watchlist rejection exception family with machine-checkable detail payloads."""


class WatchlistRejected(Exception):  # noqa: N818 -- plan-specified name, not an Error suffix
    """Base class for every reason a watchlist write can be refused before any write."""

    code: str

    def detail(self) -> dict:
        raise NotImplementedError


class InvalidTickerError(WatchlistRejected):
    """Raised when a ticker fails the `^[A-Z]{1,10}$` shape check after normalization."""

    code = "invalid_ticker"

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"{ticker!r} is not a valid ticker symbol")

    def detail(self) -> dict:
        return {"code": self.code, "ticker": self.ticker}


class DuplicateTickerError(WatchlistRejected):
    """Raised when the `UNIQUE (user_id, ticker)` constraint rejects an insert."""

    code = "duplicate_ticker"

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"{ticker} is already on the watchlist")

    def detail(self) -> dict:
        return {"code": self.code, "ticker": self.ticker}


class WatchlistFullError(WatchlistRejected):
    """Raised when adding a ticker would exceed `MAX_WATCHLIST_TICKERS`."""

    code = "watchlist_full"

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"watchlist is at its {limit}-ticker limit")

    def detail(self) -> dict:
        return {"code": self.code, "limit": self.limit}
