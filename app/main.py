"""CS2 Arbitrage Dashboard — Streamlit entry point.

Run with:
    streamlit run app/main.py
"""
import streamlit as st

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
# Session state initialisation
# ---------------------------------------------------------------------------
if "min_edge_pct" not in st.session_state:
    st.session_state.min_edge_pct = 2.0
if "last_updated" not in st.session_state:
    st.session_state.last_updated = None
if "quota_remaining" not in st.session_state:
    st.session_state.quota_remaining = None

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

    last_updated = st.session_state.last_updated
    if last_updated is not None:
        st.caption(f"Last updated: {last_updated}")
    else:
        st.caption("Last updated: —")

    st.metric(
        label="API Quota Remaining",
        value=st.session_state.get("quota_remaining", "—"),
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
