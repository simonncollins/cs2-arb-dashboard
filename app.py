import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="CS2 Arb Dashboard", page_icon="🎯", layout="wide")
st_autorefresh(interval=60000, key="auto_refresh")

st.title("🎯 CS2 Esports Arbitrage Dashboard")
st.caption("Polymarket vs Bookmakers — Informational only, not financial advice")

# Sidebar
with st.sidebar:
    min_edge = st.slider("Min Edge %", 0.0, 10.0, 0.5, 0.1) / 100
    st.divider()
    st.caption("Data refreshes every 60 seconds")

tab1, tab2, tab3 = st.tabs(["🎯 Arbitrage Opportunities", "📅 Upcoming Matches", "ℹ️ About"])

with tab1:
    st.info("Data pipeline coming soon...")

with tab2:
    st.info("Match calendar coming soon...")

with tab3:
    st.markdown("""
    ## About
    This dashboard compares **Polymarket** prediction market probabilities against
    **traditional bookmaker** implied probabilities for CS2 esports events.

    An **arbitrage opportunity** exists when the combined implied probability
    across both platforms is less than 100%.

    **Data sources:** Polymarket CLOB API · The Odds API
    **Deployment:** Streamlit Community Cloud
    **Informational only — not financial advice.**
    """)
