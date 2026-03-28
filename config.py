"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ---- Environment-driven settings -------------------------------------------

ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")
REFRESH_INTERVAL_SECONDS: int = int(os.getenv("REFRESH_INTERVAL_SECONDS", "60"))
MIN_ARBITRAGE_EDGE_PCT: float = float(os.getenv("MIN_ARBITRAGE_EDGE_PCT", "2.0"))

# ---- Polymarket API endpoints -----------------------------------------------

POLYMARKET_GAMMA_URL: str = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL: str = "https://clob.polymarket.com"

# ---- The Odds API -----------------------------------------------------------

ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"
ODDS_API_SPORT_KEY: str = "esports_cs2"

# ---- Arbitrage / EV thresholds ---------------------------------------------

MIN_EDGE_DEFAULT: float = 0.005  # 0.5% minimum edge
POLY_FEE: float = 0.02  # 2% Polymarket taker fee

# ---- Cache TTLs (seconds) --------------------------------------------------

CACHE_TTL_PRICES: int = 60  # Price/odds data
CACHE_TTL_MARKETS: int = 300  # Market/event listings

# ---- Fuzzy matching --------------------------------------------------------

FUZZY_MATCH_THRESHOLD: int = 80  # Minimum rapidfuzz score (0-100)
