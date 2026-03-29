"""Tests for tournament winner arbitrage detector (issue #60)."""

from __future__ import annotations

import pytest

from cs2_arb.engine.tournament_detector import detect_tournament_arb

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

POLY_FEE = 0.02


def _poly(event: str, team: str, yes_price: float) -> dict:
    return {"event_name": event, "team_name": team, "yes_price": yes_price}


def _book(event: str, team: str, implied_prob: float) -> dict:
    return {"event_name": event, "team_name": team, "implied_prob": implied_prob}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDetectTournamentArb:
    def test_detects_mispriced_team(self) -> None:
        """Poly has team at 0.40, book at 0.30 — positive edge after fee."""
        poly = [_poly("IEM Cologne 2026", "NAVI", 0.40)]
        book = [_book("IEM Cologne 2026", "NAVI", 0.30)]
        result = detect_tournament_arb(poly, book)
        assert len(result) == 1
        opp = result[0]
        # poly_prob_adj = 0.40 * 0.98 = 0.392, edge = (0.392 - 0.30) * 100 = 9.2%
        assert opp.edge_pct == pytest.approx(9.2, rel=1e-4)
        assert opp.team_name == "NAVI"
        assert opp.event_name == "IEM Cologne 2026"

    def test_blast_event_flagged(self) -> None:
        """Event name containing 'BLAST' sets is_blast_event=True."""
        poly = [_poly("BLAST Premier 2026", "FaZe", 0.50)]
        book = [_book("BLAST Premier 2026", "FaZe", 0.40)]
        result = detect_tournament_arb(poly, book)
        assert result[0].is_blast_event is True

    def test_iem_event_flagged(self) -> None:
        """Event name containing 'IEM' sets is_blast_event=True."""
        poly = [_poly("IEM Katowice 2026", "G2", 0.35)]
        book = [_book("IEM Katowice 2026", "G2", 0.20)]
        result = detect_tournament_arb(poly, book)
        assert result[0].is_blast_event is True

    def test_regular_event_not_flagged(self) -> None:
        """Generic event name does not set is_blast_event."""
        poly = [_poly("Some Random Cup", "Team A", 0.60)]
        book = [_book("Some Random Cup", "Team A", 0.40)]
        result = detect_tournament_arb(poly, book)
        assert result[0].is_blast_event is False

    def test_partial_match_skipped(self) -> None:
        """Team only in poly (not in book) is not returned."""
        poly = [
            _poly("IEM Cologne 2026", "NAVI", 0.50),
            _poly("IEM Cologne 2026", "FaZe", 0.30),  # only in poly
        ]
        book = [_book("IEM Cologne 2026", "NAVI", 0.30)]
        result = detect_tournament_arb(poly, book)
        # Only NAVI should appear
        assert len(result) == 1
        assert result[0].team_name == "NAVI"

    def test_fee_applied_removes_opportunity(self) -> None:
        """After 2% fee, very small edge becomes negative and is excluded."""
        # poly=0.30, adj=0.294, book=0.295 → edge=(0.294-0.295)*100 = -0.1% — excluded
        poly = [_poly("IEM Cologne 2026", "Team X", 0.30)]
        book = [_book("IEM Cologne 2026", "Team X", 0.295)]
        result = detect_tournament_arb(poly, book)
        assert result == []

    def test_ranked_by_edge_desc(self) -> None:
        """Results are sorted with highest edge first."""
        poly = [
            _poly("IEM Cologne 2026", "Team A", 0.50),  # edge = (0.49 - 0.20)*100 = 29%
            _poly("IEM Cologne 2026", "Team B", 0.40),  # edge = (0.392 - 0.35)*100 = 4.2%
        ]
        book = [
            _book("IEM Cologne 2026", "Team A", 0.20),
            _book("IEM Cologne 2026", "Team B", 0.35),
        ]
        result = detect_tournament_arb(poly, book)
        assert len(result) == 2
        assert result[0].edge_pct > result[1].edge_pct
        assert result[0].team_name == "Team A"

    def test_empty_poly_returns_empty(self) -> None:
        """Empty poly_markets returns empty list."""
        book = [_book("IEM Cologne 2026", "NAVI", 0.30)]
        assert detect_tournament_arb([], book) == []

    def test_empty_book_returns_empty(self) -> None:
        """Empty book_markets returns empty list."""
        poly = [_poly("IEM Cologne 2026", "NAVI", 0.40)]
        assert detect_tournament_arb(poly, []) == []

    def test_both_empty_returns_empty(self) -> None:
        """Both empty returns empty list."""
        assert detect_tournament_arb([], []) == []

    def test_is_significant_above_threshold(self) -> None:
        """Opportunity above min_edge_pct is marked significant."""
        poly = [_poly("IEM Cologne 2026", "NAVI", 0.50)]
        book = [_book("IEM Cologne 2026", "NAVI", 0.30)]
        result = detect_tournament_arb(poly, book, min_edge_pct=1.0)
        assert result[0].is_significant is True

    def test_is_significant_below_threshold(self) -> None:
        """Opportunity below min_edge_pct is not marked significant."""
        # poly=0.31, adj=0.3038, book=0.30 → edge = 0.38%
        poly = [_poly("IEM Cologne 2026", "NAVI", 0.31)]
        book = [_book("IEM Cologne 2026", "NAVI", 0.30)]
        result = detect_tournament_arb(poly, book, min_edge_pct=1.0)
        # Should have positive edge but not significant
        assert len(result) == 1
        assert result[0].is_significant is False

    def test_case_insensitive_matching(self) -> None:
        """Team and event names matched case-insensitively."""
        poly = [_poly("IEM Cologne 2026", "navi", 0.40)]
        book = [_book("IEM Cologne 2026", "NAVI", 0.20)]
        result = detect_tournament_arb(poly, book)
        assert len(result) == 1
