# CS2 Esports Arbitrage Dashboard

Real-time dashboard comparing Polymarket CS2 prediction market odds against traditional bookmaker odds (via The Odds API) to surface potential arbitrage opportunities.

**Informational only — no trade execution.**

## Stack

- **Frontend**: Streamlit (Python)
- **Hosting**: Streamlit Community Cloud (free)
- **Data**: Polymarket CLOB API (no auth) + The Odds API (free tier)

## Local Development

```bash
pip install -e ".[dev]"
cp .env.example .env   # fill in ODDS_API_KEY
streamlit run app/main.py
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ODDS_API_KEY` | ✅ Yes | API key from [the-odds-api.com](https://the-odds-api.com/) |
| `MIN_EDGE_PCT` | No | Minimum edge % to show (default: `0.02`) |
| `REFRESH_INTERVAL_SECS` | No | Auto-refresh interval in seconds (default: `60`) |
| `RATE_LIMIT_DELAY_SECS` | No | Minimum seconds between API calls (default: `1.0`) |
| `ALERT_WEBHOOK_URL` | No | Slack/webhook URL for arbitrage alerts |

## Deploying to Streamlit Community Cloud

1. Fork or connect this repo at [share.streamlit.io](https://share.streamlit.io)
2. Set **Main file path**: `app/main.py`
3. Set **Python version**: `3.11` (see `runtime.txt`)
4. Add secrets in the Streamlit Cloud dashboard under **Settings → Secrets**:
   ```toml
   ODDS_API_KEY = "your_key_here"
   ```
5. Click **Deploy** — all dependencies are installed automatically from `requirements.txt`

## Project Structure

```
app/
  main.py          # Streamlit entry point
  config.py        # pydantic-settings config
  models.py        # Pydantic v2 data models
  data/            # Ingestion clients + normalizers
  engine/          # Arbitrage detection engine
  ui/              # Reusable UI components
.streamlit/
  config.toml      # Theme, server settings
runtime.txt        # Python 3.11
requirements.txt   # Pip dependencies (Streamlit Cloud)
pyproject.toml     # Full project config (dev)
```

## Target Events

- IEM Cologne Major 2026 — June 2–21
- BLAST events (highlighted in UI)
