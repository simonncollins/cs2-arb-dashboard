# CS2 Esports Arbitrage Dashboard

Real-time dashboard comparing Polymarket CS2 prediction market odds against traditional bookmaker odds (via The Odds API) to surface potential arbitrage opportunities.

**Informational only — no trade execution.**

## Stack
- **Frontend**: Streamlit (Python)
- **Hosting**: Streamlit Community Cloud (free)
- **Data**: Polymarket CLOB API (no auth) + The Odds API (free tier)

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in ODDS_API_KEY
streamlit run app.py
```

## Target Event
IEM Cologne Major 2026 — June 2–21
