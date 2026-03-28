"""Fuzzy event matcher: aligns Polymarket CS2 markets with bookmaker events.

Handles disparate naming conventions (e.g. "NaVi" vs "Natus Vincere") using
RapidFuzz token-sort-ratio scoring and a curated team alias table.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz
import structlog

from app.models import BookmakerOdds, PolymarketMarket

logger = structlog.get_logger(__name__)

# ---- Constants -------------------------------------------------------------

_MATCH_THRESHOLD = 80  # minimum token-sort-ratio score to accept a match
_TEAM_ALIASES_PATH = Path(__file__).parent / "team_aliases.json"

# Mapping from canonical lowercased form -> canonical lowercased form.
# Built from team_aliases.json: each alias variant maps to the canonical key.
_ALIAS_MAP: dict[str, str] = {}


def _load_aliases() -> dict[str, str]:
    """Load the alias table from disk and build variant->canonical mapping."""
    if not _TEAM_ALIASES_PATH.exists():
        return {}
    with _TEAM_ALIASES_PATH.open() as fh:
        raw: dict[str, list[str]] = json.load(fh)
    mapping: dict[str, str] = {}
    for canonical, variants in raw.items():
        mapping[canonical] = canonical  # canonical maps to itself
        for variant in variants:
            mapping[variant.lower()] = canonical
    return mapping


_ALIAS_MAP = _load_aliases()


# ---- Normalisation helpers -------------------------------------------------


def _strip_diacritics(text: str) -> str:
    """Remove diacritic marks from a Unicode string."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_team_name(name: str) -> str:
    """Produce a canonical, lowercased team name for comparison.

    Steps:
    1. Lowercase.
    2. Strip diacritics.
    3. Look up in alias table; replace with canonical form if found.

    Args:
        name: Raw team name string.

    Returns:
        Canonical lowercased team name suitable for fuzzy comparison.
    """
    cleaned = _strip_diacritics(name.lower().strip())
    return _ALIAS_MAP.get(cleaned, cleaned)


def _team_similarity(name_a: str, name_b: str) -> float:
    """Compute token-sort-ratio similarity between two team names [0, 100]."""
    norm_a = normalize_team_name(name_a)
    norm_b = normalize_team_name(name_b)
    score: float = fuzz.token_sort_ratio(norm_a, norm_b)
    return score


def _match_teams(
    poly_a: str,
    poly_b: str,
    book_a: str,
    book_b: str,
) -> float:
    """Return average similarity score for a candidate event pairing.

    Tries both orderings (A vs B and B vs A) and returns the best.
    """
    # Direct alignment
    score_direct = (
        _team_similarity(poly_a, book_a) + _team_similarity(poly_b, book_b)
    ) / 2.0
    # Swapped alignment
    score_swapped = (
        _team_similarity(poly_a, book_b) + _team_similarity(poly_b, book_a)
    ) / 2.0
    return max(score_direct, score_swapped)


# ---- Public API ------------------------------------------------------------


def match_events(
    poly_markets: list[PolymarketMarket],
    bookmaker_events: list[BookmakerOdds],
) -> tuple[list[tuple[PolymarketMarket, BookmakerOdds]], list[PolymarketMarket]]:
    """Match Polymarket CS2 markets to bookmaker events.

    Uses fuzzy team-name similarity to pair events across sources. Each
    Polymarket market is matched to at most one bookmaker event (the
    highest-scoring pair above the threshold).

    Args:
        poly_markets: Normalised Polymarket markets.
        bookmaker_events: Normalised bookmaker odds events.

    Returns:
        A 2-tuple of:
        - ``matched``: List of ``(PolymarketMarket, BookmakerOdds)`` pairs.
        - ``unmatched``: Polymarket markets that could not be matched.
    """
    matched: list[tuple[PolymarketMarket, BookmakerOdds]] = []
    unmatched: list[PolymarketMarket] = []
    used_book_indices: set[int] = set()

    for poly in poly_markets:
        best_score = 0.0
        best_idx: int | None = None

        for idx, book in enumerate(bookmaker_events):
            if idx in used_book_indices:
                continue
            score = _match_teams(poly.team_a, poly.team_b, book.team_a, book.team_b)
            logger.debug(
                "match_score",
                poly_event=poly.event_name,
                book_event=book.event_name,
                score=round(score, 1),
            )
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is not None and best_score >= _MATCH_THRESHOLD:
            matched.append((poly, bookmaker_events[best_idx]))
            used_book_indices.add(best_idx)
            logger.info(
                "event_matched",
                poly_event=poly.event_name,
                book_event=bookmaker_events[best_idx].event_name,
                score=round(best_score, 1),
            )
        else:
            unmatched.append(poly)
            logger.debug(
                "event_unmatched",
                poly_event=poly.event_name,
                best_score=round(best_score, 1),
            )

    return matched, unmatched
