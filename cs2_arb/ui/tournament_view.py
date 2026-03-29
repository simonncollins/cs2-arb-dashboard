"""Tournament winner arbitrage view widget.

Renders a grouped view of tournament winner mispricing opportunities,
highlighting BLAST/major events (IEM Cologne, PGL Major, etc.).
"""

from __future__ import annotations

from typing import Any, Protocol

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# BLAST / major tournament detection
# ---------------------------------------------------------------------------

_BLAST_KEYWORDS = ("blast", "iem", "esl", "pgl", "faceit", "major")

_BLAST_BADGE = "⚡ BLAST"
_MAJOR_BADGE = "🏆 Major"


class _TournOppProto(Protocol):
    """Structural protocol for TournamentArbitrageOpportunity objects."""

    event_name: str
    team_name: str
    poly_prob: float
    book_prob: float
    edge_pct: float
    is_blast_event: bool
    is_significant: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_blast(event_name: str) -> bool:
    """Return True if the event name matches a known BLAST/major tournament."""
    lower = event_name.lower()
    return any(kw in lower for kw in _BLAST_KEYWORDS)


def _badge(event_name: str) -> str:
    """Return a display badge string for the event."""
    lower = event_name.lower()
    if "blast" in lower:
        return _BLAST_BADGE
    if any(kw in lower for kw in ("iem", "esl", "pgl", "faceit")):
        return "⚡ Major Series"
    if "major" in lower:
        return _MAJOR_BADGE
    return ""


def _opps_to_df(opportunities: list[Any]) -> pd.DataFrame:
    """Convert a list of tournament opportunity objects to a display DataFrame."""
    rows = []
    for opp in opportunities:
        rows.append(
            {
                "Event": opp.event_name,
                "Team": opp.team_name,
                "Poly Prob": opp.poly_prob,
                "Book Prob": opp.book_prob,
                "Edge %": opp.edge_pct,
                "BLAST": _is_blast(opp.event_name),
                "Significant": getattr(opp, "is_significant", False),
                "_badge": _badge(opp.event_name),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "Event",
                "Team",
                "Poly Prob",
                "Book Prob",
                "Edge %",
                "BLAST",
                "Significant",
                "_badge",
            ]
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------


def render_tournament_view(opportunities: list[Any]) -> None:
    """Render the tournament winner arbitrage view.

    Groups opportunities by tournament event name. Each event section
    shows a table of team-level implied probability comparisons sorted
    by edge% descending. BLAST/major events get a prominent badge header.

    Args:
        opportunities: List of TournamentArbitrageOpportunity (or
            protocol-compatible) objects.
    """
    if not opportunities:
        st.info(
            "🔍 No tournament winner opportunities found above the current "
            "edge threshold. Try lowering the Min Edge % slider."
        )
        return

    df = _opps_to_df(opportunities)

    # Sort BLAST events first, then by edge% desc within each event
    df = df.sort_values(
        ["BLAST", "Edge %"],
        ascending=[False, False],
    ).reset_index(drop=True)

    # Group by event
    for event_name in df["Event"].unique():
        event_df = df[df["Event"] == event_name].copy()
        badge = event_df.iloc[0]["_badge"]
        is_blast = bool(event_df.iloc[0]["BLAST"])

        # Section header
        if is_blast and badge:
            st.subheader(f"{badge} — {event_name}")
        else:
            st.subheader(f"🎮 {event_name}")

        # Display table — hide internal columns
        display_df = event_df.drop(columns=["Event", "BLAST", "Significant", "_badge"])
        display_df = display_df.sort_values("Edge %", ascending=False).reset_index(drop=True)

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
            },
            hide_index=True,
        )

        # Summary caption
        sig_count = int(event_df["Significant"].sum())
        total = len(event_df)
        st.caption(
            f"{total} team{'s' if total != 1 else ''} in this event"
            + (f" — {sig_count} significant opportunit{'ies' if sig_count != 1 else 'y'}" if sig_count else "")
        )
        st.divider()
