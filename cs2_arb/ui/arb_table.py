"""Streamlit arbitrage table widget.

Renders a sortable, filterable table of arbitrage opportunities
from MatchArbitrageOpportunity objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

import pandas as pd
import streamlit as st

from cs2_arb.data.blast_events import is_blast_event

if TYPE_CHECKING:
    pass


class _OppProto(Protocol):
    """Structural protocol for arbitrage opportunity objects."""

    event_name: str
    team_a: str
    team_b: str
    outcome: str
    poly_prob: float
    book_prob: float
    edge_pct: float
    ev_adjusted: float
    kelly_fraction: float
    book_name: str
    volume_usd: float


def _is_blast(event_name: str) -> bool:
    """Return True if the event name matches a known BLAST/major tournament."""
    return is_blast_event(event_name)


def _opps_to_df(opportunities: list[Any]) -> pd.DataFrame:
    """Convert a list of opportunity objects to a display DataFrame.

    Columns:
        Event, Outcome, Poly Prob, Book Prob, Edge %, EV (adj), Volume ($),
        Kelly %, Book, BLAST
    """
    rows = []
    for opp in opportunities:
        blast = _is_blast(opp.event_name)
        event_display = f"⚡ {opp.event_name}" if blast else opp.event_name
        outcome_label = opp.team_a if opp.outcome == "team_a" else opp.team_b
        rows.append(
            {
                "Event": event_display,
                "Outcome": outcome_label,
                "Poly Prob": opp.poly_prob,
                "Book Prob": opp.book_prob,
                "Edge %": opp.edge_pct,
                "EV (adj)": getattr(opp, "ev_adjusted", 0.0),
                "Volume ($)": getattr(opp, "volume_usd", 0.0),
                "Kelly %": getattr(opp, "kelly_fraction", 0.0) * 100,
                "Book": getattr(opp, "book_name", ""),
                "BLAST": blast,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Event",
                "Outcome",
                "Poly Prob",
                "Book Prob",
                "Edge %",
                "EV (adj)",
                "Volume ($)",
                "Kelly %",
                "Book",
                "BLAST",
            ]
        )
    return pd.DataFrame(rows)


def render_arb_table(opportunities: list[Any]) -> None:
    """Render a sortable arbitrage opportunities table.

    Displays all detected arbitrage opportunities in a ``st.dataframe``
    with formatted columns. Sorts by Edge % descending by default.
    Shows an empty-state message when no opportunities are found.

    Color guide: Edge % >= 5% = green, 2–5% = yellow, <2% = grey.

    BLAST/major events are prefixed with a ⚡ lightning bolt.

    Args:
        opportunities: List of MatchArbitrageOpportunity (or protocol-compatible)
            objects to display.
    """
    if not opportunities:
        st.info("No arbitrage opportunities found. Check back after the next refresh.")
        return

    df = _opps_to_df(opportunities)

    # Sort controls
    sort_col = st.selectbox(
        "Sort by",
        options=["Edge %", "Volume ($)", "EV (adj)", "Event"],
        index=0,
        key="arb_sort_col",
    )
    sort_asc = st.checkbox("Ascending", value=False, key="arb_sort_asc")
    df = df.sort_values(sort_col, ascending=sort_asc)

    # Edge % color coding helper (via column config)
    def _edge_color(val: float) -> str:
        if val >= 5.0:
            return "green"
        if val >= 2.0:
            return "yellow"
        return "grey"

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Poly Prob": st.column_config.NumberColumn(
                "Poly Prob", format="%.1f%%", help="Polymarket implied probability"
            ),
            "Book Prob": st.column_config.NumberColumn(
                "Book Prob", format="%.1f%%", help="Bookmaker implied probability"
            ),
            "Edge %": st.column_config.NumberColumn(
                "Edge %", format="%.2f%%", help="Mispricing edge percentage"
            ),
            "EV (adj)": st.column_config.NumberColumn(
                "EV (adj)", format="$%.4f", help="Adjusted expected value per $1 stake"
            ),
            "Volume ($)": st.column_config.NumberColumn(
                "Volume ($)", format="$%.0f", help="Polymarket market liquidity"
            ),
            "Kelly %": st.column_config.NumberColumn(
                "Kelly %", format="%.2f%%", help="Kelly criterion fraction (informational)"
            ),
            "BLAST": st.column_config.CheckboxColumn(
                "BLAST", help="BLAST/major tournament event"
            ),
        },
        hide_index=True,
    )
