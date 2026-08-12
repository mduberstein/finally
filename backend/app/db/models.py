"""Row shapes the repositories return, plus the values they generate.

Callers never see a sqlite3.Row. Timestamps are ISO 8601 UTC strings, which is
also the shape API_CONTRACT.md serialises, so no conversion happens in between.
`user_id` is deliberately absent: it is always "default" and invisible to the
client.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

DEFAULT_USER_ID = "default"


def new_id() -> str:
    """A fresh primary key."""
    return str(uuid.uuid4())


def utc_now() -> str:
    """The current time as an ISO 8601 UTC string."""
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class WatchlistEntry:
    ticker: str
    added_at: str


@dataclass(frozen=True, slots=True)
class Position:
    ticker: str
    quantity: float
    avg_cost: float
    updated_at: str


@dataclass(frozen=True, slots=True)
class Trade:
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


@dataclass(frozen=True, slots=True)
class Snapshot:
    total_value: float
    recorded_at: str


@dataclass(frozen=True, slots=True)
class ChatMessage:
    id: str
    role: str
    content: str
    actions: list[dict]
    created_at: str
