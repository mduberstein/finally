from __future__ import annotations

import os
from pathlib import Path

APP_USER_ID = "default"
DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]

DEFAULT_DB_PATH = Path(os.environ.get("FINALLY_DB_PATH", "/app/db/finally.db"))
DB_PATH = Path(os.environ.get("DB_PATH", str(DEFAULT_DB_PATH)))
STATIC_DIR = Path(os.environ.get("FINALLY_STATIC_DIR", "/app/static")).resolve()
PORT = int(os.environ.get("PORT", "8003"))

LLM_MOCK = os.environ.get("LLM_MOCK", "false").strip().lower() == "true"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/openai/gpt-oss-120b")

HISTORY_POLL_INTERVAL_SECONDS = float(os.environ.get("PORTFOLIO_SNAPSHOT_INTERVAL", "30"))
