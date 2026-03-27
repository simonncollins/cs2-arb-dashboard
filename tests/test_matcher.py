"""Unit tests for app.data.matcher."""
from __future__ import annotations

from datetime import datetime, timezone

from app.data.matcher import match_events, normalize_team_name
from app.models import BookmakerOdds, PolymarketMarket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_poly(team_a: str, team_b: str) -> PolymarketMarket:
    return PolymarketMarket(
        market_id=f"pm-{team_a}-{team_b}",
        question=f"Will {team_a} win vs {team_b}?",
        outcomes=[team_a, team_b],
        implied_probs={team_a: 0.6, team_b: 0.4},
        volume_usd=5000.0,
        event_name=f"{team_a} vs {team_b}",
        team_a=team_a,
        team_b=team_b,
    )


def _make_book(team_a: str, team_b: str) -> BookmakerOdds:
    return BookmakerOdds(
        bookmaker="Pinnacle",
        event_name=f"{team_a} vs {team_b}",
        team_a=team_a,
        team_b=team_b,
        decimal_odds={team_a: 1.8, team_b: 2.2},
        implied_probs={team_a: 0.556, team_b: 0.455},
        fetched_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# normalize_team_name tests
# ---------------------------------------------------------------------------


class TestNormalizeTeamName:
    def test_navi_alias(self) -> None:
        "'NaVi' should normalize to 'natus vincere'."
        assert normalize_team_name("NaVi") == "natus vincere"

    def test_faze_alias(self) -> None:
        "'FaZe Clan' should normalize to 'faze clan'."
        assert normalize_team_name("FaZe Clan") == "faze clan"

    def test_unknown_returns_lowercased(self) -> None:
        "Unknown team names return lowercased."
        assert normalize_team_name("Unknown Team") == "unknown team"

    def test_strips_diacritics(self) -> None:
        "Diacritics removed before lookup."
        # 'naví' -> 'navi' -> 'natus vincere'
        assert normalize_team_name("naví") == "natus vincere"

    def test_case_insensitive(self) -> None:
        "Lookup is case-insensitive."
        assert normalize_team_name("NAVI") == "natus vincere"

    def test_g2_alias(self) -> None:
        "'G2' normalizes to 'g2 esports'."
        assert normalize_team_name("G2") == "g2 esports"


# ---------------------------------------------------------------------------
# match_events tests
# ---------------------------------------------------------------------------


class TestMatchEvents:
    def test_empty_returns_empty(self) -> None:
        matched, unmatched = match_events([], [])
        assert matched == []
        assert unmatched == []

    def test_no_bookmaker_events_all_unmatched(self) -> None:
        poly = [_make_poly("NaVi", "FaZe")]
        matched, unmatched = match_events(poly, [])
        assert matched == []
        assert len(unmatched) == 1

    def test_exact_match(self) -> None:
        "Identical team names produce a match."
        poly = [_make_poly("NaVi", "FaZe")]
        book = [_make_book("NaVi", "FaZe")]
        matched, unmatched = match_events(poly, book)
        assert len(matched) == 1
        assert unmatched == []
        assert matched[0][0].team_a == "NaVi"
        assert matched[0][1].bookmaker == "Pinnacle"

    def test_alias_match_navi(self) -> None:
        "'Natus Vincere' in Odds API matches 'NaVi' on Polymarket."
        poly = [_make_poly("NaVi", "FaZe")]
        book = [_make_book("Natus Vincere", "FaZe Clan")]
        matched, unmatched = match_events(poly, book)
        assert len(matched) == 1
        assert unmatched == []

    def test_swapped_team_order_matches(self) -> None:
        "Teams in reversed order should still match."
        poly = [_make_poly("NaVi", "FaZe")]
        book = [_make_book("FaZe", "NaVi")]
        matched, unmatched = match_events(poly, book)
        assert len(matched) == 1
        assert unmatched == []

    def test_no_match_below_threshold(self) -> None:
        "Completely unrelated team names produce no match."
        poly = [_make_poly("NaVi", "FaZe")]
        book = [_make_book("Team Liquid", "G2 Esports")]
        matched, unmatched = match_events(poly, book)
        assert matched == []
        assert len(unmatched) == 1

    def test_each_book_event_used_once(self) -> None:
        "A bookmaker event cannot be matched to two Polymarket markets."
        poly = [_make_poly("NaVi", "FaZe"), _make_poly("NaVi", "FaZe")]
        book = [_make_book("NaVi", "FaZe")]
        matched, unmatched = match_events(poly, book)
        # Only one match; the second poly market is unmatched
        assert len(matched) == 1
        assert len(unmatched) == 1

    def test_multiple_matches(self) -> None:
        "Two distinct pairs both match correctly."
        poly = [_make_poly("NaVi", "FaZe"), _make_poly("G2", "Team Liquid")]
        book = [
            _make_book("Natus Vincere", "FaZe Clan"),
            _make_book("G2 Esports", "Team Liquid"),
        ]
        matched, unmatched = match_events(poly, book)
        assert len(matched) == 2
        assert unmatched == []
