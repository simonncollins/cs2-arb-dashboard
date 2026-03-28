"""Unit tests for app.models Pydantic v2 data models."""
from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError
import pytest

from app.models import ArbitrageOpportunity, BookmakerOdds, PolymarketMarket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_POLY = {
    "market_id": "mkt-001",
    "question": "Will NaVi win IEM Cologne 2026?",
    "outcomes": ["NaVi", "FaZe"],
    "implied_probs": {"NaVi": 0.55, "FaZe": 0.45},
    "volume_usd": 125000.0,
    "event_name": "navi vs faze iem cologne 2026",
    "team_a": "Natus Vincere",
    "team_b": "FaZe Clan",
    "raw_slug": "will-navi-win-iem-cologne-2026",
}

VALID_BOOK = {
    "bookmaker": "Pinnacle",
    "event_name": "navi vs faze iem cologne 2026",
    "team_a": "Natus Vincere",
    "team_b": "FaZe Clan",
    "decimal_odds": {"NaVi": 1.85, "FaZe": 2.10},
    "implied_probs": {"NaVi": 0.5405, "FaZe": 0.4762},
    "fetched_at": datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC),
}


# ---------------------------------------------------------------------------
# PolymarketMarket
# ---------------------------------------------------------------------------


class TestPolymarketMarket:
    def test_round_trip_serialization(self) -> None:
        """model_dump → model_validate round-trip preserves all fields."""
        market = PolymarketMarket(**VALID_POLY)
        dumped = market.model_dump()
        restored = PolymarketMarket.model_validate(dumped)
        assert restored == market

    def test_default_raw_slug_is_empty_string(self) -> None:
        data = {**VALID_POLY}
        del data["raw_slug"]
        market = PolymarketMarket(**data)
        assert market.raw_slug == ""

    def test_implied_prob_above_one_raises(self) -> None:
        data = {**VALID_POLY, "implied_probs": {"NaVi": 1.01, "FaZe": 0.45}}
        with pytest.raises(ValidationError, match="implied_prob"):
            PolymarketMarket(**data)

    def test_implied_prob_below_zero_raises(self) -> None:
        data = {**VALID_POLY, "implied_probs": {"NaVi": -0.01, "FaZe": 0.45}}
        with pytest.raises(ValidationError, match="implied_prob"):
            PolymarketMarket(**data)

    def test_implied_prob_boundary_values_valid(self) -> None:
        data = {**VALID_POLY, "implied_probs": {"NaVi": 0.0, "FaZe": 1.0}}
        market = PolymarketMarket(**data)
        assert market.implied_probs["NaVi"] == pytest.approx(0.0)
        assert market.implied_probs["FaZe"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# BookmakerOdds
# ---------------------------------------------------------------------------


class TestBookmakerOdds:
    def test_round_trip_serialization(self) -> None:
        """model_dump → model_validate round-trip preserves all fields."""
        odds = BookmakerOdds(**VALID_BOOK)
        dumped = odds.model_dump()
        restored = BookmakerOdds.model_validate(dumped)
        assert restored == odds

    def test_implied_prob_above_one_raises(self) -> None:
        data = {**VALID_BOOK, "implied_probs": {"NaVi": 1.1, "FaZe": 0.4}}
        with pytest.raises(ValidationError, match="implied_prob"):
            BookmakerOdds(**data)

    def test_implied_prob_below_zero_raises(self) -> None:
        data = {**VALID_BOOK, "implied_probs": {"NaVi": -0.1, "FaZe": 0.4}}
        with pytest.raises(ValidationError, match="implied_prob"):
            BookmakerOdds(**data)


# ---------------------------------------------------------------------------
# ArbitrageOpportunity
# ---------------------------------------------------------------------------


class TestArbitrageOpportunity:
    def _make_opportunity(self) -> ArbitrageOpportunity:
        poly = PolymarketMarket(**VALID_POLY)
        book = BookmakerOdds(**VALID_BOOK)
        return ArbitrageOpportunity(
            polymarket_market=poly,
            bookmaker_odds=book,
            edge_pct=3.5,
            best_outcome="NaVi",
            polymarket_prob=0.55,
            bookmaker_prob=0.5405,
            ev_adjusted=0.035,
        )

    def test_round_trip_serialization(self) -> None:
        """model_dump → model_validate round-trip preserves all fields."""
        opp = self._make_opportunity()
        dumped = opp.model_dump()
        restored = ArbitrageOpportunity.model_validate(dumped)
        assert restored == opp

    def test_default_is_blast_event_false(self) -> None:
        opp = self._make_opportunity()
        assert opp.is_blast_event is False

    def test_is_blast_event_can_be_set_true(self) -> None:
        poly = PolymarketMarket(**VALID_POLY)
        book = BookmakerOdds(**VALID_BOOK)
        opp = ArbitrageOpportunity(
            polymarket_market=poly,
            bookmaker_odds=book,
            edge_pct=2.0,
            best_outcome="FaZe",
            polymarket_prob=0.45,
            bookmaker_prob=0.4762,
            ev_adjusted=0.02,
            is_blast_event=True,
        )
        assert opp.is_blast_event is True
