"""Arbitrage detection engine: filter and rank ArbitrageOpportunity candidates.

Takes pre-computed candidates from the normalizer and applies a configurable
minimum edge threshold, returning results sorted highest-edge first.
"""
from __future__ import annotations

import structlog

from app.models import ArbitrageOpportunity

log = structlog.get_logger(__name__)


def detect_arbitrage(
    candidates: list[ArbitrageOpportunity],
    min_edge_pct: float = 0.02,
) -> list[ArbitrageOpportunity]:
    """Filter and rank arbitrage opportunities by edge percentage.

    Args:
        candidates: Pre-computed ``ArbitrageOpportunity`` objects from the
            normalizer. Edge values are not re-calculated here.
        min_edge_pct: Minimum edge percentage threshold (exclusive).
            Only opportunities with ``edge_pct > min_edge_pct`` are returned.
            Defaults to 0.02 (i.e. 0.02%).

    Returns:
        Filtered list of ``ArbitrageOpportunity`` objects sorted descending
        by ``edge_pct``.
    """
    above = [c for c in candidates if c.edge_pct > min_edge_pct]
    log.debug(
        "arbitrage candidates filtered",
        raw_count=len(candidates),
        above_threshold=len(above),
        min_edge_pct=min_edge_pct,
    )
    return sorted(above, key=lambda c: c.edge_pct, reverse=True)
