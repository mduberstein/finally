"""The one domain error the portfolio service raises."""


class TradeError(Exception):
    """A trade that failed a business rule.

    `detail` carries the exact text API_CONTRACT.md documents for the failure.
    The API returns it as a 400 body and the LLM reads it back to the user, so
    it names the amounts involved rather than saying "invalid trade".
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
