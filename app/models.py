"""Core Pydantic v2 data models for the CS2 Arbitrage Dashboard pipeline."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class PolymarketMarket(BaseModel):
    """Represents a single Polymarket prediction market for a CS2 event.

    Attributes:
        market_id: Unique market identifier (conditionId from Gamma API).
        question: Human-readable market question string.
        outcomes: List of possible outcome labels (e.g. ["Team A", "Team B"]).
        implied_probs: Dict mapping each outcome label to its implied probability [0.0, 1.0].
        volume_usd: Total USD volume traded on this market.
        event_name: Normalized event/match name for fuzzy matching.
        team_a: First team name (home/favourite).
        team_b: Second team name (away/underdog).
        raw_slug: Raw Polymarket slug, used for BLAST event detection.
    """

    market_id: str
    question: str
    outcomes: list[str]
    implied_probs: dict[str, float]
    volume_usd: float
    event_name: str
    team_a: str
    team_b: str
    raw_slug: str = ""

    @field_validator("implied_probs")
    @classmethod
    def validate_implied_probs(cls, v: dict[str, float]) -> dict[str, float]:
        """Each implied probability must be in [0.0, 1.0]."""
        for outcome, prob in v.items():
            if not (0.0 <= prob <= 1.0):
                msg = f"implied_prob for '{outcome}' must be in [0.0, 1.0], got {prob}"
                raise ValueError(msg)
        return v


class BookmakerOdds(BaseModel):
    """Represents bookmaker odds for a CS2 match event.

    Attributes:
        bookmaker: Bookmaker name (e.g. "Pinnacle", "Bet365").
        event_name: Normalized event/match name for fuzzy matching.
        team_a: First team name.
        team_b: Second team name.
        decimal_odds: Dict mapping each outcome label to its decimal odds.
        implied_probs: Dict mapping each outcome label to implied probability [0.0, 1.0].
        fetched_at: Timestamp when the odds were fetched.
    """

    bookmaker: str
    event_name: str
    team_a: str
    team_b: str
    decimal_odds: dict[str, float]
    implied_probs: dict[str, float]
    fetched_at: datetime

    @field_validator("implied_probs")
    @classmethod
    def validate_implied_probs(cls, v: dict[str, float]) -> dict[str, float]:
        """Each implied probability must be in [0.0, 1.0]."""
        for outcome, prob in v.items():
            if not (0.0 <= prob <= 1.0):
                msg = f"implied_prob for '{outcome}' must be in [0.0, 1.0], got {prob}"
                raise ValueError(msg)
        return v


class ArbitrageOpportunity(BaseModel):
    """Represents a detected arbitrage opportunity between Polymarket and a bookmaker.

    Attributes:
        polymarket_market: The Polymarket market involved.
        bookmaker_odds: The bookmaker odds being compared.
        edge_pct: Arbitrage edge as a percentage (e.g. 3.5 = 3.5% edge).
        best_outcome: The outcome label where the edge is largest.
        polymarket_prob: Polymarket implied probability for the best_outcome (after fee).
        bookmaker_prob: Bookmaker implied probability for the best_outcome (after vig removal).
        ev_adjusted: Expected value of the arbitrage, fee-adjusted.
        is_blast_event: True if this event is a BLAST tournament (high liquidity).
    """

    polymarket_market: PolymarketMarket
    bookmaker_odds: BookmakerOdds
    edge_pct: float
    best_outcome: str
    polymarket_prob: float
    bookmaker_prob: float
    ev_adjusted: float
    is_blast_event: bool = False
