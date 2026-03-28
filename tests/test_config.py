"""Tests for config.py — verifies env-var defaults and all required constants."""
from __future__ import annotations

import importlib
import os
import pathlib


def test_polymarket_urls_are_set() -> None:
    import config

    assert config.POLYMARKET_GAMMA_URL.startswith("https://")
    assert config.POLYMARKET_CLOB_URL.startswith("https://")


def test_odds_api_config() -> None:
    import config

    assert config.ODDS_API_BASE_URL.startswith("https://")
    assert isinstance(config.ODDS_API_SPORT_KEY, str)
    assert len(config.ODDS_API_SPORT_KEY) > 0


def test_thresholds_are_positive_floats() -> None:
    import config

    assert 0.0 < config.MIN_EDGE_DEFAULT < 1.0
    assert 0.0 < config.POLY_FEE < 1.0


def test_cache_ttls_are_positive_integers() -> None:
    import config

    assert isinstance(config.CACHE_TTL_PRICES, int)
    assert config.CACHE_TTL_PRICES > 0
    assert isinstance(config.CACHE_TTL_MARKETS, int)
    assert config.CACHE_TTL_MARKETS > 0


def test_fuzzy_match_threshold_in_range() -> None:
    import config

    assert 0 < config.FUZZY_MATCH_THRESHOLD <= 100


def test_odds_api_key_default() -> None:
    """ODDS_API_KEY defaults to empty string when not set."""
    os.environ.pop("ODDS_API_KEY", None)
    import config

    importlib.reload(config)
    assert config.ODDS_API_KEY == ""


def test_refresh_interval_default() -> None:
    """REFRESH_INTERVAL_SECONDS defaults to 60."""
    os.environ.pop("REFRESH_INTERVAL_SECONDS", None)
    import config

    importlib.reload(config)
    assert config.REFRESH_INTERVAL_SECONDS == 60


def test_min_arbitrage_edge_default() -> None:
    """MIN_ARBITRAGE_EDGE_PCT defaults to 2.0."""
    os.environ.pop("MIN_ARBITRAGE_EDGE_PCT", None)
    import config

    importlib.reload(config)
    assert config.MIN_ARBITRAGE_EDGE_PCT == 2.0


def test_polymarket_urls_hardcoded() -> None:
    """Polymarket URLs are hardcoded constants."""
    import config

    assert config.POLYMARKET_GAMMA_URL == "https://gamma-api.polymarket.com"
    assert config.POLYMARKET_CLOB_URL == "https://clob.polymarket.com"
