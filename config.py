"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")
REFRESH_INTERVAL_SECONDS: int = int(os.getenv("REFRESH_INTERVAL_SECONDS", "60"))
MIN_ARBITRAGE_EDGE_PCT: float = float(os.getenv("MIN_ARBITRAGE_EDGE_PCT", "2.0"))
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "60"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
POLYMARKET_GAMMA_URL: str = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL: str = "https://clob.polymarket.com"
ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"
