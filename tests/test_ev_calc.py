"""Tests for EV/edge calculator (issue #59)."""

from __future__ import annotations

import pytest

from cs2_arb.engine.ev import (
    ArbitrageOpportunity,
    annotate_opportunities,
    compute_ev,
    compute_kelly,
)


class TestComputeEV:
    def test_compute_ev_positive(self) -> None:
        """book > poly means the market underprices the outcome — positive EV."""
        ev = compute_ev(poly_prob=0.45, book_implied_prob=0.55, poly_fee=0.02)
        # EV = (0.55 - 0.45) - 0.02 * 0.45 = 0.10 - 0.009 = 0.091
        assert ev == pytest.approx(0.091, rel=1e-6)
        assert ev > 0

    def test_compute_ev_negative_after_fee(self) -> None:
        """Small book edge eaten by fee → negative EV."""
        # With poly=0.50, book=0.505: EV = 0.005 - 0.01 = -0.005
        ev2 = compute_ev(poly_prob=0.50, book_implied_prob=0.505, poly_fee=0.02)
        assert ev2 < 0

    def test_compute_ev_zero_edge_negative_due_to_fee(self) -> None:
        """When poly_prob == book_implied_prob, fee makes EV negative."""
        ev = compute_ev(poly_prob=0.50, book_implied_prob=0.50, poly_fee=0.02)
        # EV = 0 - 0.02 * 0.50 = -0.01
        assert ev == pytest.approx(-0.01, rel=1e-6)
        assert ev < 0

    def test_compute_ev_uses_default_fee(self) -> None:
        """Default fee should be 0.02 (POLY_FEE)."""
        from cs2_arb.config import POLY_FEE

        ev_default = compute_ev(poly_prob=0.4, book_implied_prob=0.5)
        ev_explicit = compute_ev(poly_prob=0.4, book_implied_prob=0.5, poly_fee=POLY_FEE)
        assert ev_default == pytest.approx(ev_explicit)

    def test_compute_ev_formula(self) -> None:
        """Verify the exact formula: EV = (book - poly) - fee * poly."""
        poly, book, fee = 0.35, 0.60, 0.02
        expected = (book - poly) - fee * poly
        assert compute_ev(poly, book, fee) == pytest.approx(expected)


class TestComputeKelly:
    def test_compute_kelly_basic(self) -> None:
        """edge=0.05, odds=2.0 → Kelly = 0.05 / 1.0 = 0.05."""
        k = compute_kelly(edge=0.05, odds=2.0)
        assert k == pytest.approx(0.05)

    def test_compute_kelly_invalid_odds_zero(self) -> None:
        """odds=0 should return 0.0."""
        assert compute_kelly(edge=0.10, odds=0.0) == 0.0

    def test_compute_kelly_invalid_odds_one(self) -> None:
        """odds=1 (no payout above stake) should return 0.0."""
        assert compute_kelly(edge=0.10, odds=1.0) == 0.0

    def test_compute_kelly_invalid_odds_less_than_one(self) -> None:
        """odds < 1 should return 0.0."""
        assert compute_kelly(edge=0.10, odds=0.5) == 0.0

    def test_compute_kelly_large_edge(self) -> None:
        """Higher edge → higher Kelly fraction."""
        k_small = compute_kelly(edge=0.01, odds=3.0)
        k_large = compute_kelly(edge=0.20, odds=3.0)
        assert k_large > k_small

    def test_compute_kelly_high_odds(self) -> None:
        """Higher odds → lower Kelly fraction for same edge."""
        k_low_odds = compute_kelly(edge=0.05, odds=2.0)
        k_high_odds = compute_kelly(edge=0.05, odds=5.0)
        assert k_high_odds < k_low_odds


class TestAnnotateOpportunities:
    def _make_opp(
        self, poly_prob: float, book_prob: float, event: str = "Team A vs Team B"
    ) -> ArbitrageOpportunity:
        return ArbitrageOpportunity(
            event_name=event,
            team_a="Team A",
            team_b="Team B",
            outcome="team_a",
            poly_prob=poly_prob,
            book_prob=book_prob,
            edge_pct=(poly_prob - book_prob) * 100,
        )

    def test_annotate_marks_significant(self) -> None:
        """Opportunity with EV above min_edge is marked significant."""
        opp = self._make_opp(poly_prob=0.40, book_prob=0.55)
        result = annotate_opportunities([opp], min_edge=0.005)
        assert result[0].is_significant is True
        assert result[0].ev_adjusted > 0

    def test_annotate_marks_insignificant(self) -> None:
        """Opportunity with EV below min_edge is not significant."""
        opp = self._make_opp(poly_prob=0.50, book_prob=0.50)
        result = annotate_opportunities([opp], min_edge=0.005)
        assert result[0].is_significant is False

    def test_annotate_empty_list(self) -> None:
        """Empty input returns empty list."""
        assert annotate_opportunities([]) == []

    def test_annotate_sets_kelly_fraction(self) -> None:
        """Kelly fraction is computed and set on each opportunity."""
        opp = self._make_opp(poly_prob=0.40, book_prob=0.60)
        result = annotate_opportunities([opp])
        assert result[0].kelly_fraction >= 0

    def test_annotate_returns_same_list(self) -> None:
        """annotate_opportunities mutates and returns the same list."""
        opps = [self._make_opp(0.4, 0.6), self._make_opp(0.5, 0.5)]
        result = annotate_opportunities(opps)
        assert result is opps
