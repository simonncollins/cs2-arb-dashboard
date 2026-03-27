"""Odds normalization utilities: convert bookmaker odds to implied probabilities.

Handles decimal and American formats, vig removal, and ArbitrageOpportunity
construction from matched Polymarket/bookmaker event pairs.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models import ArbitrageOpportunity, BookmakerOdds, PolymarketMarket

# Polymarket taker fee applied to all implied probability calculations.
_POLY_TAKER_FEE = 0.02


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def decimal_to_implied(odds: float) -> float:
    """Convert decimal odds to implied probability.

    Args:
        odds: Decimal odds (e.g. 2.0 for even money).

    Returns:
        Implied probability in [0.0, 1.0].
    """
    return 1.0 / odds


def american_to_implied(odds: int) -> float:
    """Convert American (moneyline) odds to implied probability.

    Args:
        odds: American odds (e.g. -110 or +200).

    Returns:
        Implied probability in [0.0, 1.0].
    """
    if odds >= 0:
        return 100.0 / (odds + 100.0)
    abs_odds = abs(odds)
    return abs_odds / (abs_odds + 100.0)


# ---------------------------------------------------------------------------
# Vig removal
# ---------------------------------------------------------------------------


def remove_vig(implied_probs: dict[str, float]) -> dict[str, float]:
    """Normalise implied probabilities so they sum to exactly 1.0.

    Args:
        implied_probs: Dict of outcome -> raw implied probability (may sum > 1
            due to bookmaker vig/overround).

    Returns:
        Dict of outcome -> fair probability summing to 1.0.
    """
    total = sum(implied_probs.values())
    if total == 0.0:
        return dict(implied_probs)
    return {k: v / total for k, v in implied_probs.items()}


# ---------------------------------------------------------------------------
# Bookmaker event normalization
# ---------------------------------------------------------------------------


def normalize_bookmaker_event(event: dict[str, Any]) -> BookmakerOdds:
    """Convert a raw Odds API event dict to a ``BookmakerOdds`` model.

    Picks the bookmaker with the lowest vig (sum of implied probabilities
    closest to 1.0) from the ``h2h`` market.

    Args:
        event: Raw event dict from the Odds API, containing keys:
            - ``home_team`` (str)
            - ``away_team`` (str)
            - ``commence_time`` (ISO 8601 str)
            - ``bookmakers`` (list of bookmaker dicts with ``title`` and
              ``markets`` fields)

    Returns:
        ``BookmakerOdds`` instance populated from the best bookmaker.
    """
    home = event["home_team"]
    away = event["away_team"]
    event_name = f"{home} vs {away}"

    best_bookmaker: str = ""
    best_decimal: dict[str, float] = {}
    best_implied: dict[str, float] = {}
    best_vig = float("inf")

    for bm in event.get("bookmakers", []):
        for market in bm.get("markets", []):
            if market.get("key") != "h2h":
                continue
            dec: dict[str, float] = {o["name"]: float(o["price"]) for o in market["outcomes"]}
            implied_raw = {name: decimal_to_implied(price) for name, price in dec.items()}
            vig = sum(implied_raw.values()) - 1.0
            if vig < best_vig:
                best_vig = vig
                best_bookmaker = bm["title"]
                best_decimal = dec
                best_implied = implied_raw

    return BookmakerOdds(
        bookmaker=best_bookmaker,
        event_name=event_name,
        team_a=home,
        team_b=away,
        decimal_odds=best_decimal,
        implied_probs=remove_vig(best_implied),
        fetched_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Opportunity builder
# ---------------------------------------------------------------------------


def build_opportunities(
    matches: list[tuple[PolymarketMarket, BookmakerOdds]],
) -> list[ArbitrageOpportunity]:
    """Build ``ArbitrageOpportunity`` objects from matched market pairs.

    For each pair applies the Polymarket 2% taker fee to implied probabilities
    and removes bookmaker vig, then computes per-outcome edge values.

    Args:
        matches: List of ``(PolymarketMarket, BookmakerOdds)`` pairs returned
            by the fuzzy matcher.

    Returns:
        List of ``ArbitrageOpportunity`` objects where ``edge_pct > 0``.
    """
    opportunities: list[ArbitrageOpportunity] = []

    for poly_market, book_odds in matches:
        fair_book_probs = remove_vig(book_odds.implied_probs)

        best_edge = 0.0
        best_outcome = ""
        best_poly_prob = 0.0
        best_book_prob = 0.0

        for outcome, poly_prob in poly_market.implied_probs.items():
            book_prob = fair_book_probs.get(outcome)
            if book_prob is None:
                continue
            # Apply Polymarket 2% taker fee
            poly_prob_adj = poly_prob * (1.0 - _POLY_TAKER_FEE)
            edge = poly_prob_adj - book_prob
            if edge > best_edge:
                best_edge = edge
                best_outcome = outcome
                best_poly_prob = poly_prob_adj
                best_book_prob = book_prob

        if best_edge > 0.0:
            opportunities.append(
                ArbitrageOpportunity(
                    polymarket_market=poly_market,
                    bookmaker_odds=book_odds,
                    edge_pct=best_edge * 100.0,
                    best_outcome=best_outcome,
                    polymarket_prob=best_poly_prob,
                    bookmaker_prob=best_book_prob,
                    ev_adjusted=best_edge * 100.0,
                )
            )

    return opportunities
