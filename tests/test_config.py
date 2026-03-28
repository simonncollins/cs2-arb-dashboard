"""Tests for config module — verifies all required constants are present and have sensible values."""

import cs2_arb.config as config


def test_polymarket_urls_are_set():
    assert config.POLYMARKET_GAMMA_URL.startswith("https://")
    assert config.POLYMARKET_CLOB_URL.startswith("https://")


def test_odds_api_config():
    assert config.ODDS_API_BASE_URL.startswith("https://")
    assert isinstance(config.ODDS_API_SPORT_KEY, str)
    assert len(config.ODDS_API_SPORT_KEY) > 0


def test_thresholds_are_positive_floats():
    assert 0.0 < config.MIN_EDGE_DEFAULT < 1.0
    assert 0.0 < config.POLY_FEE < 1.0


def test_cache_ttls_are_positive_integers():
    assert isinstance(config.CACHE_TTL_PRICES, int)
    assert config.CACHE_TTL_PRICES > 0
    assert isinstance(config.CACHE_TTL_MARKETS, int)
    assert config.CACHE_TTL_MARKETS > 0


def test_fuzzy_match_threshold_in_range():
    assert 0 < config.FUZZY_MATCH_THRESHOLD <= 100
