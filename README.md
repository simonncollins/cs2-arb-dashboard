# CS2 Esports Arbitrage Dashboard

A Streamlit dashboard that compares **Polymarket** prediction market odds against **traditional bookmaker** implied probabilities for CS2 esports matches, surfacing potential arbitrage opportunities.

## Features

- **Live data ingestion** from Polymarket CLOB API and The Odds API
- **Fuzzy event matching** to correlate markets across platforms
- **Arbitrage detection engine** with configurable minimum-edge threshold
- **Expected-value (EV) calculator**
- **Auto-refreshing dashboard** (every 60 seconds)
- **Webhook / in-app alerts** for high-value opportunities

## Data Sources

- [Polymarket CLOB API](https://clob.polymarket.com)
- [The Odds API](https://the-odds-api.com) (CS2 BO3 markets)

## Setup

```bash
# Clone and install
git clone https://github.com/simonncollins/cs2-arb-dashboard
cd cs2-arb-dashboard
pip install -r requirements.txt

# Configure secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and add your ODDS_API_KEY

# Run locally
streamlit run app.py
```

## Deployment

Deploy to [Streamlit Community Cloud](https://streamlit.io/cloud). Set `ODDS_API_KEY` in the app's Secrets settings.

## Disclaimer

**Informational only — not financial advice.** Arbitrage opportunities may close before execution. Always verify odds independently before acting.
