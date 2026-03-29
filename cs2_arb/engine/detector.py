"""Arbitrage opportunity detector.

Compares Polymarket implied probabilities against bookmaker implied
probabilities to identify arbitrage opportunities for CS2 esports matches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cs2_arb.config import MIN_EDGE_DEFAULT, POLY_FEE


@dataclass
class MatchArbitrageOpportunity:
    """A single match-level arbitrage opportunity between Polymarket and a bookmaker."""

    event_name: str
    team_a: str
    team_b: str
    outcome: str  # "team_a" or "team_b"
    poly_prob: float  # Polymarket YES price (0-1)
    book_prob: float  # Bookmaker implied probability, vig-removed (0-1)
    edge_pct: float  # edge as percentage
    ev_adjusted: float = field(default=0.0)
    kelly_fraction: float = field(default=0.0)
    is_significant: bool = field(default=False)
    book_name: str = field(default="")
    volume_usd: float = field(default=0.0)


def filter_by_min_edge(
    opportunities: list[MatchArbitrageOpportunity],
    min_edge_pct: float = MIN_EDGE_DEFAULT * 100,
) -> list[MatchArbitrageOpportunity]:
    """Filter opportunities below the minimum edge percentage threshold.

    Args:
        opportunities: List of MatchArbitrageOpportunity to filter.
        min_edge_pct: Minimum edge in percentage points (e.g. 5.0 = 5%).

    Returns:
        Filtered list containing only opportunities with edge_pct >= min_edge_pct.
    """
    return [o for o in opportunities if o.edge_pct >= min_edge_pct]


def detect_arbitrage(
    matched_events: list[dict[str, Any]],
    min_edge_pct: float = MIN_EDGE_DEFAULT * 100,
    poly_fee: float = POLY_FEE,
) -> list[MatchArbitrageOpportunity]:
    """Detect arbitrage opportunities from matched Polymarket/bookmaker events.

    An opportunity exists when the Polymarket price (after fee) implies a
    higher probability than the bookmaker's vig-removed probability. Results
    are filtered to those with edge_pct >= min_edge_pct.

    Args:
        matched_events: List of dicts representing matched events. Each dict has:
            - ``event_name`` (str)
            - ``team_a`` (str)
            - ``team_b`` (str)
            - ``outcome`` (str): "team_a" or "team_b"
            - ``poly_prob`` (float): Polymarket YES price (0-1)
            - ``book_prob`` (float): Bookmaker implied probability (0-1)
            - ``book_name`` (str, optional): Name of the bookmaker
            - ``volume_usd`` (float, optional): Polymarket volume in USD
        min_edge_pct: Minimum edge percentage to include (default 0.5%).
        poly_fee: Polymarket taker fee fraction (default 2%).

    Returns:
        List of MatchArbitrageOpportunity, filtered and sorted by edge_pct desc.
    """
    opportunities: list[MatchArbitrageOpportunity] = []

    for event in matched_events:
        poly_prob = float(event["poly_prob"])
        book_prob = float(event["book_prob"])

        # Apply Polymarket fee: the effective probability after fee
        poly_prob_adj = poly_prob * (1.0 - poly_fee)
        edge_pct = (poly_prob_adj - book_prob) * 100.0

        if edge_pct < min_edge_pct:
            continue

        opp = MatchArbitrageOpportunity(
            event_name=event["event_name"],
            team_a=event["team_a"],
            team_b=event["team_b"],
            outcome=event.get("outcome", "team_a"),
            poly_prob=poly_prob,
            book_prob=book_prob,
            edge_pct=edge_pct,
            book_name=event.get("book_name", ""),
            volume_usd=float(event.get("volume_usd", 0.0)),
        )
        opportunities.append(opp)

    opportunities.sort(key=lambda o: o.edge_pct, reverse=True)
    return opportunities
