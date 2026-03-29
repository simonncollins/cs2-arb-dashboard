"""Tests for config.py env-var defaults."""
from __future__ import annotations

import importlib
import os
import pathlib


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


def test_env_example_keys_documented() -> None:
    """Verify that .env.example documents the required environment variable keys."""
    env_example = pathlib.Path(__file__).parent.parent / ".env.example"
    assert env_example.exists(), ".env.example must exist at the project root"
    content = env_example.read_text()
    required_keys = [
        "ODDS_API_KEY",
        "POLYMARKET_GAMMA_URL",
        "POLYMARKET_CLOB_URL",
        "MIN_EDGE_PCT",
        "REFRESH_INTERVAL_SECS",
    ]
    for key in required_keys:
        assert key in content, f"Expected env var '{key}' to be documented in .env.example"
