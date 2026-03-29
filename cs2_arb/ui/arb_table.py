"""Streamlit arbitrage table widget.

Renders a sortable, filterable table of arbitrage opportunities
from MatchArbitrageOpportunity objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    pass

# BLAST tournament keywords for visual flagging
_BLAST_KEYWORDS = ("blast", "iem", "esl", "major", "cologne", "rio", "paris")


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
    lower = event_name.lower()
    return any(kw in lower for kw in _BLAST_KEYWORDS)


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
        st.info(
            "🔍 No arbitrage opportunities found above the current edge threshold. "
            "Try lowering the Min Edge % slider in the sidebar."
        )
        return

    df = _opps_to_df(opportunities)
    df = df.sort_values("Edge %", ascending=False).reset_index(drop=True)

    # Sort controls
    sort_col = st.selectbox(
        "Sort by",
        options=["Edge %", "Volume ($)", "EV (adj)", "Poly Prob", "Book Prob"],
        index=0,
        key="arb_table_sort",
    )
    ascending = st.checkbox("Ascending", value=False, key="arb_table_asc")
    df = df.sort_values(sort_col, ascending=ascending).reset_index(drop=True)

    # Hide internal BLAST bool column in display
    display_df = df.drop(columns=["BLAST"])

    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "Poly Prob": st.column_config.ProgressColumn(
                "Poly Prob",
                format="%.1f%%",
                min_value=0.0,
                max_value=1.0,
            ),
            "Book Prob": st.column_config.ProgressColumn(
                "Book Prob",
                format="%.1f%%",
                min_value=0.0,
                max_value=1.0,
            ),
            "Edge %": st.column_config.NumberColumn(
                "Edge %",
                format="%.2f%%",
            ),
            "EV (adj)": st.column_config.NumberColumn(
                "EV (adj)",
                format="%.4f",
            ),
            "Volume ($)": st.column_config.NumberColumn(
                "Volume ($)",
                format="$%.0f",
            ),
            "Kelly %": st.column_config.NumberColumn(
                "Kelly %",
                format="%.2f%%",
                help="Kelly fraction (display only — not financial advice)",
            ),
        },
        hide_index=True,
    )

    blast_count = df["BLAST"].sum()
    total = len(df)
    st.caption(
        f"Showing {total} opportunit{'y' if total == 1 else 'ies'}"
        + (f" — {blast_count} from BLAST/major events ⚡" if blast_count else "")
    )
