"""Known BLAST/major CS2 tournament keywords for event detection.

Used to identify high-liquidity Polymarket markets associated with
BLAST-partnered or major tournament events.
"""

from __future__ import annotations

# Lowercase keywords covering BLAST Premier, IEM, ESL, and PGL majors.
BLAST_KEYWORDS: tuple[str, ...] = (
    "blast",
    "iem",
    "esl",
    "pgl",
    "major",
    "cologne",
    "rio",
    "paris",
    "katowice",
    "copenhagen",
    "premier",
)


def is_blast_event(event_name: str) -> bool:
    """Return True if *event_name* matches a known BLAST/major tournament.

    The check is case-insensitive and matches any BLAST_KEYWORDS substring.

    Args:
        event_name: Raw event or market name from Polymarket or bookmaker feed.

    Returns:
        True when at least one BLAST keyword is found in the event name.
    """
    lower = event_name.lower()
    return any(kw in lower for kw in BLAST_KEYWORDS)
