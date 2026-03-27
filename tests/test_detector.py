"""Unit tests for app.engine.detector.detect_arbitrage."""
from __future__ import annotations

from datetime import datetime

from app.engine.detector import detect_arbitrage
from app.models import ArbitrageOpportunity, BookmakerOdds, PolymarketMarket


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_opportunity(edge_pct: float) -> ArbitrageOpportunity:
    """Build a minimal ArbitrageOpportunity with a given edge_pct."""
    poly = PolymarketMarket(
        market_id="test-market",
        question="Team A vs Team B",
        outcomes=["Team A", "Team B"],
        implied_probs={"Team A": 0.55, "Team B": 0.45},
        volume_usd=10_000.0,
        event_name="team-a-vs-team-b",
        team_a="Team A",
        team_b="Team B",
    )
    book = BookmakerOdds(
        bookmaker="Pinnacle",
        event_name="team-a-vs-team-b",
        team_a="Team A",
        team_b="Team B",
        decimal_odds={"Team A": 1.9, "Team B": 2.1},
        implied_probs={"Team A": 0.5, "Team B": 0.5},
        fetched_at=datetime(2024, 1, 1, 12, 0, 0),
    )
    return ArbitrageOpportunity(
        polymarket_market=poly,
        bookmaker_odds=book,
        edge_pct=edge_pct,
        best_outcome="Team A",
        polymarket_prob=0.539,
        bookmaker_prob=0.5,
        ev_adjusted=edge_pct,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty() -> None:
    assert detect_arbitrage([]) == []


def test_filters_negative_edge() -> None:
    candidates = [_make_opportunity(-1.0)]
    assert detect_arbitrage(candidates) == []


def test_filters_zero_edge() -> None:
    """edge_pct=0.0 is NOT strictly greater than min_edge_pct=0.02."""
    candidates = [_make_opportunity(0.0)]
    assert detect_arbitrage(candidates) == []


def test_returns_positive_edge() -> None:
    opp = _make_opportunity(3.5)
    result = detect_arbitrage([opp])
    assert result == [opp]


def test_sorted_descending() -> None:
    low = _make_opportunity(1.0)
    mid = _make_opportunity(2.5)
    high = _make_opportunity(5.0)
    result = detect_arbitrage([low, high, mid])
    assert result == [high, mid, low]


def test_min_edge_pct_filter() -> None:
    below = _make_opportunity(3.0)
    above = _make_opportunity(6.0)
    result = detect_arbitrage([below, above], min_edge_pct=5.0)
    assert result == [above]
    assert below not in result


def test_all_negative_returns_empty() -> None:
    candidates = [_make_opportunity(-5.0), _make_opportunity(-1.0), _make_opportunity(-0.01)]
    assert detect_arbitrage(candidates) == []
