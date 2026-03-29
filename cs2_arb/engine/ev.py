"""Expected Value (EV) and Kelly fraction calculator.

Computes EV of a Polymarket bet accounting for the 2% taker fee,
and the fractional Kelly criterion for position sizing (display only).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cs2_arb.config import MIN_EDGE_DEFAULT, POLY_FEE


@dataclass
class ArbitrageOpportunity:
    """A single arbitrage opportunity between Polymarket and a bookmaker."""

    event_name: str
    team_a: str
    team_b: str
    outcome: str  # "team_a" or "team_b"
    poly_prob: float  # Polymarket implied probability (0-1)
    book_prob: float  # Bookmaker implied probability after vig removal (0-1)
    edge_pct: float  # (poly_prob_adj - book_prob) * 100
    ev_adjusted: float = field(default=0.0)
    kelly_fraction: float = field(default=0.0)
    is_significant: bool = field(default=False)
    book_name: str = field(default="")


def compute_ev(
    poly_prob: float,
    book_implied_prob: float,
    poly_fee: float = POLY_FEE,
) -> float:
    """Compute expected value of a Polymarket bet.

    EV = (book_implied_prob - poly_prob) - poly_fee * poly_prob

    A positive EV means the Polymarket price underestimates the true
    probability implied by the bookmaker (after accounting for the fee).

    Args:
        poly_prob: Polymarket YES price as implied probability (0-1).
        book_implied_prob: Bookmaker implied probability after vig removal (0-1).
        poly_fee: Polymarket taker fee (default 2%).

    Returns:
        EV as a float; positive = favourable bet.
    """
    return (book_implied_prob - poly_prob) - poly_fee * poly_prob


def compute_kelly(edge: float, odds: float) -> float:
    """Compute the fractional Kelly criterion for position sizing.

    Kelly fraction = edge / (odds - 1)

    This is display-only — not intended for automated execution.

    Args:
        edge: Edge as a fraction (e.g. 0.05 for 5%).
        odds: Decimal odds (e.g. 2.0 for evens).

    Returns:
        Kelly fraction (0-1); returns 0.0 when odds <= 1.
    """
    if odds <= 1.0:
        return 0.0
    return edge / (odds - 1.0)


def annotate_opportunities(
    opportunities: list[ArbitrageOpportunity],
    min_edge: float = MIN_EDGE_DEFAULT,
) -> list[ArbitrageOpportunity]:
    """Annotate a list of ArbitrageOpportunity with EV and significance flags.

    For each opportunity:
    - Computes ev_adjusted using compute_ev
    - Sets is_significant = ev_adjusted > min_edge
    - Computes kelly_fraction using compute_kelly (book_prob as proxy for odds)

    Args:
        opportunities: List of ArbitrageOpportunity to annotate.
        min_edge: Minimum EV threshold for significance (default MIN_EDGE_DEFAULT).

    Returns:
        The same list with ev_adjusted, kelly_fraction, is_significant populated.
    """
    for opp in opportunities:
        opp.ev_adjusted = compute_ev(opp.poly_prob, opp.book_prob)
        # Convert book implied prob to approximate decimal odds
        book_odds = 1.0 / opp.book_prob if opp.book_prob > 0 else 1.0
        opp.kelly_fraction = compute_kelly(opp.ev_adjusted, book_odds)
        opp.is_significant = opp.ev_adjusted > min_edge
    return opportunities
