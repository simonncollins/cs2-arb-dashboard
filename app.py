"""CS2 Esports Arbitrage Dashboard — main Streamlit entry point.

Run with: streamlit run app.py
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from cs2_arb.config import CACHE_TTL_MARKETS, CACHE_TTL_PRICES, MIN_EDGE_DEFAULT

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CS2 Arb Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "min_edge_pct" not in st.session_state:
    st.session_state.min_edge_pct = MIN_EDGE_DEFAULT * 100  # 0.5%
if "last_updated" not in st.session_state:
    st.session_state.last_updated = None
if "quota_remaining" not in st.session_state:
    st.session_state.quota_remaining = None
if "blast_only" not in st.session_state:
    st.session_state.blast_only = False

# ---------------------------------------------------------------------------
# Auto-refresh — every 60 seconds
# ---------------------------------------------------------------------------
_REFRESH_INTERVAL_MS = 60_000
_refresh_count = st_autorefresh(interval=_REFRESH_INTERVAL_MS, key="autorefresh")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    st.session_state.min_edge_pct = st.slider(
        "Min Edge %",
        min_value=0.0,
        max_value=20.0,
        value=float(st.session_state.min_edge_pct),
        step=0.5,
        help="Only show opportunities with edge above this threshold",
    )

    st.session_state.blast_only = st.checkbox(
        "⚡ BLAST events only",
        value=bool(st.session_state.blast_only),
        help="Restrict table to IEM, ESL, BLAST, and Major events",
    )

    st.divider()

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.session_state.last_updated = datetime.utcnow().strftime("%H:%M:%S UTC")
        st.rerun()

    # Last-updated timestamp
    _ts = st.session_state.last_updated
    if _ts:
        st.caption(f"Last updated: {_ts}")
    else:
        st.caption("Not yet refreshed")

    # API quota display
    st.metric(
        "API Quota Remaining",
        st.session_state.get("quota_remaining", "—"),
        help="Remaining The Odds API requests for this billing period",
    )

    st.divider()
    st.caption(f"Auto-refreshes every {_REFRESH_INTERVAL_MS // 1000}s")
    st.caption(f"Price TTL: {CACHE_TTL_PRICES}s · Market TTL: {CACHE_TTL_MARKETS}s")

# ---------------------------------------------------------------------------
# Main header
# ---------------------------------------------------------------------------
st.title("🎯 CS2 Esports Arbitrage Dashboard")
st.caption("Polymarket vs Bookmakers — Informational only, not financial advice")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(
    ["📊 Match Arbitrage", "🏆 Tournament Winners", "ℹ️ About"]
)

with tab1:
    st.info("Match arbitrage opportunities will appear here. (Coming soon)")

with tab2:
    st.info("Tournament winner mispricing will appear here. (Coming soon)")

with tab3:
    st.markdown(
        """
        ## About
        This dashboard compares **Polymarket** prediction market probabilities against
        **traditional bookmaker** implied probabilities for CS2 esports events.

        An **arbitrage opportunity** exists when the Polymarket price (after fees) implies
        a higher probability than the bookmaker's vig-removed implied probability.

        **Data sources:** Polymarket CLOB API · The Odds API

        **Deployment:** Streamlit Community Cloud

        ---
        *Informational only — not financial advice.*
        """
    )
