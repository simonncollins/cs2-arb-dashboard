# Deployment Guide

Step-by-step guide for deploying the CS2 Esports Arbitrage Dashboard to Streamlit Community Cloud.

---

## Prerequisites

1. A GitHub account with the `cs2-arb-dashboard` repository forked or cloned.
2. A free [The Odds API](https://the-odds-api.com) account and API key.
3. A [Streamlit Community Cloud](https://streamlit.io/cloud) account (free, sign in with GitHub).

---

## 1. Prepare Your Repository

The repo is already configured for Streamlit Cloud deployment:

| File | Purpose |
|---|---|
| `app.py` | Streamlit entry point |
| `requirements.txt` | Runtime dependencies (pip-installable) |
| `runtime.txt` | Pins Python 3.11 |
| `.streamlit/config.toml` | Streamlit theme, server port, XSRF settings |

No changes are needed before deploying.

---

## 2. Deploy on Streamlit Community Cloud

### Step 1 — New app

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**

### Step 2 — Configure source

| Field | Value |
|---|---|
| **Repository** | `simonncollins/cs2-arb-dashboard` (or your fork) |
| **Branch** | `main` |
| **Main file path** | `app.py` |
| **Python version** | `3.11` |

### Step 3 — Configure secrets

Click **Advanced settings** → **Secrets**. Add the following TOML block:

```toml
# Required
ODDS_API_KEY = "paste_your_key_here"

# Optional — leave empty to disable Slack alerts
SLACK_WEBHOOK_URL = ""

# Optional — leave empty to disable generic webhook alerts
ALERT_WEBHOOK_URL = ""
```

> **Where to find your Odds API key:** [the-odds-api.com/account](https://the-odds-api.com/account)

### Step 4 — Deploy

Click **Deploy**. Streamlit Cloud will:
1. Pull the latest `main` branch
2. Install dependencies from `requirements.txt`
3. Launch the app on a public URL like `https://simonncollins-cs2-arb-dashboard-app-xxxx.streamlit.app`

---

## 3. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `ODDS_API_KEY` | ✅ | — | The Odds API key. Free tier: 500 req/month. |
| `SLACK_WEBHOOK_URL` | No | — | Slack incoming webhook for arb alerts. |
| `ALERT_WEBHOOK_URL` | No | — | Generic HTTP webhook (JSON POST) for arb alerts. |
| `REFRESH_INTERVAL_SECONDS` | No | `60` | Dashboard auto-refresh interval (seconds). |
| `MIN_ARBITRAGE_EDGE_PCT` | No | `2.0` | Minimum edge % to display and alert on. |

### Streamlit Secrets vs Environment Variables

Streamlit Cloud injects secrets defined in **Advanced settings → Secrets** as both `st.secrets` dict entries **and** environment variables. The app reads them via `os.environ` / `st.secrets`, so either format works:

```toml
# TOML format in Streamlit Cloud secrets manager
ODDS_API_KEY = "abc123"
```

```bash
# Equivalent .env format for local dev
ODDS_API_KEY=abc123
```

---

## 4. Local Development

```bash
# Clone
git clone https://github.com/simonncollins/cs2-arb-dashboard.git
cd cs2-arb-dashboard

# Install runtime + dev dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Configure secrets (local)
cp .env.example .env
# Edit .env: set ODDS_API_KEY=your_key_here

# Run
streamlit run app.py
```

App available at `http://localhost:8501`.

---

## 5. Updating the Deployment

Streamlit Community Cloud auto-deploys on every push to `main`. Simply merge a PR to `main` and the app will update within ~1 minute.

To manually trigger a reboot: **Manage app** → **Reboot app** in the Streamlit Cloud dashboard.

---

## 6. Monitoring & Logs

- **App logs:** Streamlit Cloud → **Manage app** → **Logs** tab
- **API quota:** The Odds API dashboard at [the-odds-api.com/account](https://the-odds-api.com/account) shows remaining monthly requests
- **CI status:** GitHub Actions badge in `README.md` tracks lint + test health on every push

---

## 7. Free Tier Limits

| Service | Free tier |
|---|---|
| The Odds API | 500 requests/month |
| Streamlit Community Cloud | Unlimited public apps; 1 GB RAM; sleeps after inactivity |
| Polymarket CLOB API | Unlimited (no auth) |

The dashboard caches API responses (TTL: 60s for Polymarket, 120s for The Odds API) to stay well within the free-tier quota at a 60-second refresh interval.

---

## 8. Troubleshooting

### App won't start — `ModuleNotFoundError`

Ensure `requirements.txt` is up to date:

```bash
pip install -r requirements.txt
```

If you added a new dependency, add it to both `pyproject.toml` and `requirements.txt`.

### `ODDS_API_KEY not set` error

The app requires `ODDS_API_KEY`. For local dev, add it to `.env`. For Streamlit Cloud, add it in **Advanced settings → Secrets**.

### Dashboard shows no opportunities

- Verify `ODDS_API_KEY` is valid and has quota remaining.
- Try lowering the **Min Edge %** slider in the sidebar to `0.5%`.
- CS2 markets may not have active bookmaker lines — check [The Odds API event explorer](https://the-odds-api.com/liveapi/guides/v4/#get-events).

### Alerts not firing

- Check `SLACK_WEBHOOK_URL` / `ALERT_WEBHOOK_URL` are set correctly in Streamlit secrets.
- Alerts deduplicate within a 1-hour window — each `event|outcome` pair fires at most once per hour.
- Verify the edge threshold (`MIN_ARBITRAGE_EDGE_PCT`) is not set too high.
