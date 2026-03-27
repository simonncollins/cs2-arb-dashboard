"""Unit tests for app.ingestion.normalizer."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.ingestion.normalizer import (
    american_to_implied,
    build_opportunities,
    decimal_to_implied,
    normalize_bookmaker_event,
    remove_vig,
)
from app.models import ArbitrageOpportunity, BookmakerOdds, PolymarketMarket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_poly_market(
    team_a: str = "NaVi",
    team_b: str = "FaZe",
    prob_a: float = 0.6,
) -> PolymarketMarket:
    prob_b = round(1.0 - prob_a, 6)
    return PolymarketMarket(
        market_id="test-market-id",
        question=f"Will {team_a} win?",
        outcomes=[team_a, team_b],
        implied_probs={team_a: prob_a, team_b: prob_b},
        volume_usd=10000.0,
        event_name=f"{team_a} vs {team_b}",
        team_a=team_a,
        team_b=team_b,
    )


def _make_book_odds(
    team_a: str = "NaVi",
    team_b: str = "FaZe",
    prob_a: float = 0.5,
) -> BookmakerOdds:
    prob_b = round(1.0 - prob_a, 6)
    return BookmakerOdds(
        bookmaker="Pinnacle",
        event_name=f"{team_a} vs {team_b}",
        team_a=team_a,
        team_b=team_b,
        decimal_odds={team_a: round(1.0 / prob_a, 4), team_b: round(1.0 / prob_b, 4)},
        implied_probs={team_a: prob_a, team_b: prob_b},
        fetched_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# decimal_to_implied
# ---------------------------------------------------------------------------


class TestDecimalToImplied:
    def test_even_money(self) -> None:
        assert decimal_to_implied(2.0) == pytest.approx(0.5)

    def test_one_point_five(self) -> None:
        assert decimal_to_implied(1.5) == pytest.approx(0.6667, rel=1e-3)

    def test_large_odds(self) -> None:
        assert decimal_to_implied(10.0) == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# american_to_implied
# ---------------------------------------------------------------------------


class TestAmericanToImplied:
    def test_negative_110(self) -> None:
        assert american_to_implied(-110) == pytest.approx(0.5238, rel=1e-3)

    def test_positive_200(self) -> None:
        assert american_to_implied(200) == pytest.approx(0.3333, rel=1e-3)

    def test_positive_100(self) -> None:
        assert american_to_implied(100) == pytest.approx(0.5)

    def test_negative_200(self) -> None:
        assert american_to_implied(-200) == pytest.approx(0.6667, rel=1e-3)


# ---------------------------------------------------------------------------
# remove_vig
# ---------------------------------------------------------------------------


class TestRemoveVig:
    def test_sums_to_one(self) -> None:
        result = remove_vig({"a": 0.55, "b": 0.55})
        assert sum(result.values()) == pytest.approx(1.0)

    def test_keys_preserved(self) -> None:
        result = remove_vig({"home": 0.6, "away": 0.5})
        assert set(result.keys()) == {"home", "away"}

    def test_already_fair(self) -> None:
        result = remove_vig({"a": 0.5, "b": 0.5})
        assert result["a"] == pytest.approx(0.5)
        assert result["b"] == pytest.approx(0.5)

    def test_zero_total_returns_unchanged(self) -> None:
        result = remove_vig({"a": 0.0, "b": 0.0})
        assert result == {"a": 0.0, "b": 0.0}


# ---------------------------------------------------------------------------
# normalize_bookmaker_event
# ---------------------------------------------------------------------------


class TestNormalizeBookmakerEvent:
    def _sample_event(self) -> dict:  # type: ignore[type-arg]
        return {
            "id": "event-123",
            "home_team": "NaVi",
            "away_team": "FaZe",
            "commence_time": "2024-06-01T15:00:00Z",
            "bookmakers": [
                {
                    "title": "Pinnacle",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "NaVi", "price": 1.8},
                                {"name": "FaZe", "price": 2.2},
                            ],
                        }
                    ],
                },
                {
                    "title": "Bet365",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "NaVi", "price": 1.7},
                                {"name": "FaZe", "price": 2.0},
                            ],
                        }
                    ],
                },
            ],
        }

    def test_returns_bookmaker_odds(self) -> None:
        result = normalize_bookmaker_event(self._sample_event())
        assert isinstance(result, BookmakerOdds)

    def test_correct_teams(self) -> None:
        result = normalize_bookmaker_event(self._sample_event())
        assert result.team_a == "NaVi"
        assert result.team_b == "FaZe"

    def test_implied_probs_sum_to_one(self) -> None:
        result = normalize_bookmaker_event(self._sample_event())
        assert sum(result.implied_probs.values()) == pytest.approx(1.0)

    def test_picks_lowest_vig_bookmaker(self) -> None:
        """Pinnacle (1.8 / 2.2) has lower vig than Bet365 (1.7 / 2.0)."""
        result = normalize_bookmaker_event(self._sample_event())
        assert result.bookmaker == "Pinnacle"


# ---------------------------------------------------------------------------
# build_opportunities
# ---------------------------------------------------------------------------


class TestBuildOpportunities:
    def test_empty_input_returns_empty(self) -> None:
        assert build_opportunities([]) == []

    def test_no_positive_edge_returns_empty(self) -> None:
        """Polymarket prob lower than book prob -> no opportunity."""
        poly = _make_poly_market(prob_a=0.4)  # NaVi at 0.4
        book = _make_book_odds(prob_a=0.6)    # Book has NaVi at 0.6 (poly*0.98=0.392 < 0.6)
        result = build_opportunities([(poly, book)])
        assert result == []

    def test_positive_edge_returns_opportunity(self) -> None:
        """Poly implied prob higher than book -> opportunity detected."""
        # poly: NaVi=0.8, FaZe=0.2; book: NaVi=0.5, FaZe=0.5
        # edge for NaVi = 0.8*0.98 - 0.5 = 0.784 - 0.5 = 0.284 > 0
        poly = _make_poly_market(prob_a=0.8)
        book = _make_book_odds(prob_a=0.5)
        result = build_opportunities([(poly, book)])
        assert len(result) == 1
        assert isinstance(result[0], ArbitrageOpportunity)
        assert result[0].edge_pct > 0.0
        assert result[0].best_outcome == "NaVi"

    def test_poly_fee_applied(self) -> None:
        """2% fee must reduce poly_prob before edge calculation."""
        poly = _make_poly_market(prob_a=0.8)
        book = _make_book_odds(prob_a=0.5)
        result = build_opportunities([(poly, book)])
        assert len(result) == 1
        assert result[0].polymarket_prob == pytest.approx(0.8 * 0.98, rel=1e-6)

    def test_ev_adjusted_equals_edge_pct(self) -> None:
        """ev_adjusted should equal edge_pct."""
        poly = _make_poly_market(prob_a=0.8)
        book = _make_book_odds(prob_a=0.5)
        result = build_opportunities([(poly, book)])
        assert result[0].ev_adjusted == pytest.approx(result[0].edge_pct, rel=1e-6)
