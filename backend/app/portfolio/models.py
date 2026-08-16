"""Domain models for portfolio state and trade execution."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """A single holding: one ticker's quantity and cost basis."""

    ticker: str
    quantity: float
    avg_cost: float


@dataclass(frozen=True, slots=True)
class TradeResult:
    """The outcome of a filled trade, including the caller's new cash balance."""

    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str
    cash_balance: float


class TradeRejected(Exception):  # noqa: N818 -- plan-specified name, not an Error suffix
    """Base class for every reason a trade can be refused before any write."""

    code: str

    def detail(self) -> dict:
        raise NotImplementedError


class UntradableTickerError(TradeRejected):
    """Raised when the ticker has no entry in `PriceCache` (D-02)."""

    code = "untradable_ticker"

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"{ticker} has no live price and cannot be traded")

    def detail(self) -> dict:
        return {"code": self.code, "ticker": self.ticker}


class InsufficientCashError(TradeRejected):
    """Raised when a buy's cost exceeds the available cash balance."""

    code = "insufficient_cash"

    def __init__(self, ticker: str, cost: float, cash_balance: float) -> None:
        self.ticker = ticker
        self.cost = cost
        self.cash_balance = cash_balance
        super().__init__(f"buying {ticker} costs {cost}, only {cash_balance} available")

    def detail(self) -> dict:
        return {
            "code": self.code,
            "ticker": self.ticker,
            "cost": self.cost,
            "cash_balance": self.cash_balance,
        }


class InsufficientSharesError(TradeRejected):
    """Raised when a sell's quantity exceeds the owned quantity.

    No path in this plan raises it yet — Plan 02 adds the sell side — but the
    exception family is one artifact rather than two.
    """

    code = "insufficient_shares"

    def __init__(self, ticker: str, owned: float) -> None:
        self.ticker = ticker
        self.owned = owned
        super().__init__(f"cannot sell {ticker}, only {owned} owned")

    def detail(self) -> dict:
        return {"code": self.code, "ticker": self.ticker, "owned": self.owned}
