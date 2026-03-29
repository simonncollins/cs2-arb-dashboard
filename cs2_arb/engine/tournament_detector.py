"""Tournament winner arbitrage detector.

Detects mispriced tournament winner markets where Polymarket odds
diverge from bookmaker outright prices for CS2 esports events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cs2_arb.config import POLY_FEE

# CS2 esports tournament organizers whose events should be flagged
BLAST_KEYWORDS = ("BLAST", "IEM", "ESL", "PGL", "FACEIT")


@dataclass
class TournamentArbitrageOpportunity:
    """A single team-level mispricing in a tournament winner market."""

    event_name: str  # e.g. "IEM Cologne 2026"
    team_name: str
    poly_prob: float  # Polymarket implied probability (pre-fee)
    book_prob: float  # Bookmaker implied probability (post-vig removal)
    edge_pct: float  # (poly_prob_adj - book_prob) * 100
    is_blast_event: bool = field(default=False)
    is_significant: bool = field(default=False)


def _normalize_name(name: str) -> str:
    """Lowercase and strip whitespace for comparison."""
    return name.lower().strip()


def _is_blast_event(event_name: str) -> bool:
    """Return True if the event name matches a known CS2 tournament series."""
    upper = event_name.upper()
    return any(kw in upper for kw in BLAST_KEYWORDS)


def detect_tournament_arb(
    poly_markets: list[dict[str, Any]],
    book_markets: list[dict[str, Any]],
    min_edge_pct: float = 1.0,
    poly_fee: float = POLY_FEE,
) -> list[TournamentArbitrageOpportunity]:
    """Detect team-level mispricing in tournament winner markets.

    Matches Polymarket tournament outcome markets against bookmaker outright
    prices. Returns ranked list of opportunities where Polymarket underprices
    a team relative to the bookmaker (after applying Polymarket's taker fee).

    Args:
        poly_markets: List of dicts with keys:
            - ``event_name`` (str)
            - ``team_name`` (str)
            - ``yes_price`` (float, Polymarket implied probability 0-1)
        book_markets: List of dicts with keys:
            - ``event_name`` (str)
            - ``team_name`` (str)
            - ``implied_prob`` (float, vig-removed bookmaker probability 0-1)
        min_edge_pct: Minimum edge percentage for is_significant flag (default 1.0%).
        poly_fee: Polymarket taker fee to deduct from poly_prob (default 2%).

    Returns:
        List of TournamentArbitrageOpportunity, sorted by edge_pct descending,
        containing only entries with edge_pct > 0 (positive edge after fee).
    """
    # Build lookup: (norm_event, norm_team) -> implied_prob
    book_index: dict[tuple[str, str], float] = {}
    for bm in book_markets:
        key = (_normalize_name(bm["event_name"]), _normalize_name(bm["team_name"]))
        book_index[key] = float(bm["implied_prob"])

    opportunities: list[TournamentArbitrageOpportunity] = []

    for pm in poly_markets:
        key = (_normalize_name(pm["event_name"]), _normalize_name(pm["team_name"]))
        if key not in book_index:
            # Team only available on Polymarket — skip
            continue

        poly_prob = float(pm["yes_price"])
        book_prob = book_index[key]

        # Apply Polymarket taker fee to the probability we pay
        poly_prob_adj = poly_prob * (1.0 - poly_fee)
        edge_pct = (poly_prob_adj - book_prob) * 100.0

        if edge_pct <= 0:
            continue

        opp = TournamentArbitrageOpportunity(
            event_name=pm["event_name"],
            team_name=pm["team_name"],
            poly_prob=poly_prob,
            book_prob=book_prob,
            edge_pct=edge_pct,
            is_blast_event=_is_blast_event(pm["event_name"]),
            is_significant=edge_pct > min_edge_pct,
        )
        opportunities.append(opp)

    # Sort by edge_pct descending
    opportunities.sort(key=lambda o: o.edge_pct, reverse=True)
    return opportunities
