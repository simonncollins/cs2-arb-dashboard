"""Tests for arbitrage detector and min-edge threshold filtering (issue #61)."""

from __future__ import annotations

import pytest

from cs2_arb.engine.detector import (
    MatchArbitrageOpportunity,
    detect_arbitrage,
    filter_by_min_edge,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event(
    team_a: str = "NAVI",
    team_b: str = "FaZe",
    poly_prob: float = 0.50,
    book_prob: float = 0.40,
    event_name: str = "IEM Cologne 2026",
    outcome: str = "team_a",
    book_name: str = "bet365",
    volume_usd: float = 10000.0,
) -> dict:
    return {
        "event_name": event_name,
        "team_a": team_a,
        "team_b": team_b,
        "outcome": outcome,
        "poly_prob": poly_prob,
        "book_prob": book_prob,
        "book_name": book_name,
        "volume_usd": volume_usd,
    }


def _opp(edge_pct: float) -> MatchArbitrageOpportunity:
    return MatchArbitrageOpportunity(
        event_name="Test Event",
        team_a="A",
        team_b="B",
        outcome="team_a",
        poly_prob=0.5,
        book_prob=0.4,
        edge_pct=edge_pct,
    )


# ---------------------------------------------------------------------------
# filter_by_min_edge
# ---------------------------------------------------------------------------


class TestFilterByMinEdge:
    def test_filters_below_threshold(self) -> None:
        """Opportunities below min_edge_pct are excluded."""
        opps = [_opp(1.0), _opp(3.0), _opp(5.0)]
        result = filter_by_min_edge(opps, min_edge_pct=3.0)
        assert len(result) == 2
        assert all(o.edge_pct >= 3.0 for o in result)

    def test_includes_exactly_at_threshold(self) -> None:
        """Opportunity exactly at the threshold is included."""
        opp = _opp(5.0)
        result = filter_by_min_edge([opp], min_edge_pct=5.0)
        assert len(result) == 1

    def test_empty_input_returns_empty(self) -> None:
        assert filter_by_min_edge([], min_edge_pct=1.0) == []

    def test_all_below_threshold_returns_empty(self) -> None:
        opps = [_opp(0.1), _opp(0.5), _opp(0.9)]
        result = filter_by_min_edge(opps, min_edge_pct=5.0)
        assert result == []

    def test_zero_threshold_includes_all_non_negative(self) -> None:
        opps = [_opp(0.0), _opp(1.0), _opp(10.0)]
        result = filter_by_min_edge(opps, min_edge_pct=0.0)
        assert len(result) == 3

    def test_setting_min_edge_pct_0_05(self) -> None:
        """min_edge_pct=5 removes opportunities with edge < 5%."""
        opps = [_opp(3.0), _opp(6.0), _opp(4.99)]
        result = filter_by_min_edge(opps, min_edge_pct=5.0)
        assert len(result) == 1
        assert result[0].edge_pct == 6.0


# ---------------------------------------------------------------------------
# detect_arbitrage
# ---------------------------------------------------------------------------


class TestDetectArbitrage:
    def test_detects_opportunity(self) -> None:
        """Poly 0.50, book 0.40 with 2% fee → edge = (0.49-0.40)*100 = 9%."""
        events = [_event(poly_prob=0.50, book_prob=0.40)]
        result = detect_arbitrage(events, min_edge_pct=0.0)
        assert len(result) == 1
        assert result[0].edge_pct == pytest.approx(9.0, rel=1e-4)

    def test_applies_fee(self) -> None:
        """Fee is applied: poly_prob_adj = poly * (1 - fee)."""
        # poly=0.30, book=0.295 → adj=0.294, edge=(0.294-0.295)*100 = -0.1% — excluded
        events = [_event(poly_prob=0.30, book_prob=0.295)]
        result = detect_arbitrage(events, min_edge_pct=0.0)
        assert result == []

    def test_min_edge_filters_results(self) -> None:
        """Only events above min_edge_pct are returned."""
        events = [
            _event(poly_prob=0.50, book_prob=0.40),  # ~9% edge
            _event(poly_prob=0.35, book_prob=0.34, team_a="G2"),  # small edge
        ]
        result = detect_arbitrage(events, min_edge_pct=5.0)
        assert len(result) == 1
        assert result[0].edge_pct > 5.0

    def test_empty_input_returns_empty(self) -> None:
        assert detect_arbitrage([], min_edge_pct=0.0) == []

    def test_ranked_by_edge_desc(self) -> None:
        """Results are sorted by edge_pct descending."""
        events = [
            _event(poly_prob=0.35, book_prob=0.30, team_a="G2"),   # smaller edge
            _event(poly_prob=0.50, book_prob=0.40, team_a="NAVI"),  # bigger edge
        ]
        result = detect_arbitrage(events, min_edge_pct=0.0)
        assert len(result) == 2
        assert result[0].edge_pct > result[1].edge_pct

    def test_event_fields_populated(self) -> None:
        """All fields from event dict are set on the opportunity."""
        events = [_event(
            team_a="NAVI", team_b="FaZe", poly_prob=0.50,
            book_prob=0.40, book_name="bet365", volume_usd=12345.0,
        )]
        result = detect_arbitrage(events, min_edge_pct=0.0)
        opp = result[0]
        assert opp.team_a == "NAVI"
        assert opp.team_b == "FaZe"
        assert opp.book_name == "bet365"
        assert opp.volume_usd == pytest.approx(12345.0)

    def test_uses_default_poly_fee(self) -> None:
        """Default poly_fee of 2% is used when not specified."""
        from cs2_arb.config import POLY_FEE

        events = [_event(poly_prob=0.50, book_prob=0.40)]
        result_default = detect_arbitrage(events, min_edge_pct=0.0)
        result_explicit = detect_arbitrage(events, min_edge_pct=0.0, poly_fee=POLY_FEE)
        assert result_default[0].edge_pct == pytest.approx(result_explicit[0].edge_pct)

    def test_works_for_both_outcomes(self) -> None:
        """Detector handles team_a and team_b outcome fields."""
        events = [
            _event(outcome="team_a", poly_prob=0.55, book_prob=0.40),
            _event(outcome="team_b", poly_prob=0.60, book_prob=0.45),
        ]
        result = detect_arbitrage(events, min_edge_pct=0.0)
        assert len(result) == 2
        outcomes = {o.outcome for o in result}
        assert outcomes == {"team_a", "team_b"}
