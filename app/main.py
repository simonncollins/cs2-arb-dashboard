"""CS2 Arbitrage Dashboard — Streamlit entry point.

Run with:
    streamlit run app/main.py
"""
from __future__ import annotations

import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from app.config import settings

# ---------------------------------------------------------------------------
# Page configuration (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CS2 Arb Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Auto-refresh (fires every refresh_interval_secs, returns count of refreshes)
# ---------------------------------------------------------------------------
st_autorefresh(
    interval=settings.refresh_interval_secs * 1000,
    key="autorefresh",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "min_edge_pct" not in st.session_state:
    # NOTE: slider uses 0–20 scale; config default 0.02 → show as 2.0%
    st.session_state.min_edge_pct = settings.min_edge_pct * 100
if "last_updated" not in st.session_state:
    st.session_state.last_updated = None
if "quota_remaining" not in st.session_state:
    st.session_state.quota_remaining = None

# Record timestamp whenever page renders (triggered by autorefresh or manual)
_now = datetime.datetime.now(tz=datetime.timezone.utc)
st.session_state.last_updated = _now.strftime("%Y-%m-%d %H:%M:%S UTC")

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Controls")

    st.session_state.min_edge_pct = st.slider(
        "Min Edge %",
        min_value=0.0,
        max_value=20.0,
        value=float(st.session_state.min_edge_pct),
        step=0.5,
        help="Only show opportunities with edge% above this threshold.",
    )

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"Last updated: {st.session_state.last_updated}")

    next_refresh_in = settings.refresh_interval_secs
    st.caption(f"Auto-refresh every {next_refresh_in}s")

    quota = st.session_state.get("quota_remaining")
    st.metric(
        label="API Quota Remaining",
        value=quota if quota is not None else "—",
    )

# ---------------------------------------------------------------------------
# Main content — tabbed navigation
# ---------------------------------------------------------------------------
st.title("🎯 CS2 Esports Arbitrage Dashboard")

tab1, tab2 = st.tabs(["📊 Match Arbitrage", "🏆 Tournament Winners"])

with tab1:
    st.info("Match arbitrage opportunities will appear here. (Coming soon)")

with tab2:
    st.info("Tournament winner mispricing will appear here. (Coming soon)")
