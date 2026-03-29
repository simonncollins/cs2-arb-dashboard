"""Configuration constants for the CS2 Arbitrage Dashboard."""

# Polymarket API endpoints
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"

# The Odds API
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
ODDS_API_SPORT_KEY = "esports_cs2_bo3"  # Discover correct key at runtime if needed

# Arbitrage / EV thresholds
MIN_EDGE_DEFAULT = 0.005  # 0.5% minimum edge
POLY_FEE = 0.02           # 2% Polymarket taker fee

# Cache TTLs (seconds)
CACHE_TTL_PRICES = 60     # Polymarket price/odds data (1 minute)
CACHE_TTL_MARKETS = 300   # Market/event listings (5 minutes)
ODDS_API_TTL_SECS = 300   # The Odds API response cache TTL (5 minutes)

# Fuzzy matching
FUZZY_MATCH_THRESHOLD = 80  # Minimum thefuzz score (0-100)
