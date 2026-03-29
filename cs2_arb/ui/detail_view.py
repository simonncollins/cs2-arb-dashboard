"""Match detail view widget.

Renders a detailed breakdown of a single arbitrage opportunity using
st.expander, showing all bookmaker odds, EV calculation details,
Kelly fraction, and a direct Polymarket market link.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Polymarket market URL prefix
# Polymarket market slugs are constructed from event_name; the canonical
# search URL always works as a fallback.
# ---------------------------------------------------------------------------
_POLY_SEARCH_URL = "https://polymarket.com/markets?q={query}"
_POLY_MARKET_URL = "https://polymarket.com/event/{slug}"

_KELLY_DISCLAIMER = (
    "⚠️ Kelly fraction is displayed for informational purposes only and "
    "does not constitute financial advice. Never risk money you cannot afford to lose."
)


def _poly_url(event_name: str, slug: str | None = None) -> str:
    """Return a Polymarket URL for the given event."""
    if slug:
        return _POLY_MARKET_URL.format(slug=slug)
    # Fallback: build a search URL from the event name
    query = event_name.replace(" ", "+").lower()
    return _POLY_SEARCH_URL.format(query=query)


def render_detail(
    opportunity: Any,
    *,
    poly_slug: str | None = None,
    all_books: list[dict[str, Any]] | None = None,
    expanded: bool = False,
) -> None:
    """Render a match detail view inside an expander.

    Shows:
    - Event information and outcome
    - Polymarket link (direct slug or fallback search)
    - EV and Kelly fraction breakdown
    - All bookmaker odds (if provided via ``all_books``)

    Args:
        opportunity: ArbitrageOpportunity (or protocol-compatible) object.
        poly_slug: Optional Polymarket market slug for a direct link.
        all_books: Optional list of ``{"name": str, "prob": float, "odds": float}``
            dicts for showing all bookmakers side-by-side.
        expanded: Whether the expander starts open.
    """
    opp = opportunity
    label = (
        f"📋 Detail: {opp.event_name} — "
        f"{opp.team_a if opp.outcome == 'team_a' else opp.team_b} wins "
        f"(Edge: {opp.edge_pct:.2f}%)"
    )

    with st.expander(label, expanded=expanded):
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### 📊 Probability Comparison")
            st.metric("Polymarket Prob", f"{opp.poly_prob:.1%}")
            st.metric(
                f"{getattr(opp, 'book_name', 'Book')} Implied Prob",
                f"{opp.book_prob:.1%}",
                delta=f"+{opp.edge_pct:.2f}% edge",
            )
            st.markdown("#### 💰 EV Breakdown")
            ev = getattr(opp, "ev_adjusted", 0.0)
            kf = getattr(opp, "kelly_fraction", 0.0)
            st.metric("EV (adjusted)", f"{ev:+.4f}", help="Positive = favourable")
            st.metric("Kelly Fraction", f"{kf:.2%}", help=_KELLY_DISCLAIMER)
            st.caption(_KELLY_DISCLAIMER)

        with col_right:
            st.markdown("#### 🌐 Polymarket Link")
            url = _poly_url(opp.event_name, poly_slug)
            st.markdown(f"[Open on Polymarket ↗]({url})")

            if all_books:
                st.markdown("#### 📚 All Bookmaker Odds")
                for book in sorted(all_books, key=lambda b: b.get("prob", 0), reverse=True):
                    prob = book.get("prob", 0.0)
                    odds = book.get("odds", 0.0)
                    name = book.get("name", "Unknown")
                    best = name == getattr(opp, "book_name", "")
                    prefix = "✅ " if best else ""
                    st.markdown(
                        f"{prefix}**{name}**: {prob:.1%} implied "
                        f"({odds:.2f} decimal)"
                    )
            else:
                st.markdown("#### 📚 Best Book")
                st.markdown(
                    f"**{getattr(opp, 'book_name', 'N/A')}**: "
                    f"{opp.book_prob:.1%} implied"
                )
