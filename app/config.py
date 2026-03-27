"""Application settings loaded from environment variables via pydantic-settings.

Usage::

    from app.config import settings

    api_key = settings.oddspapi_api_key
    min_edge = settings.min_edge_pct

All settings can be overridden by environment variables or a ``.env`` file at
the project root.  This module supersedes the legacy ``config.py`` at the repo
root — new code should import from here.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the CS2 Arbitrage Dashboard.

    Each field is populated first from an environment variable of the same name
    (upper-cased), then falls back to the default value declared here.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- API credentials ---------------------------------------------------
    # Legacy field name kept for backwards compat with existing CI env var
    odds_api_key: str = Field(default="", alias="ODDS_API_KEY")
    oddspapi_api_key: str = Field(default="", alias="ODDSPAPI_API_KEY")

    # --- Arbitrage thresholds ----------------------------------------------
    min_edge_pct: float = Field(default=0.02, alias="MIN_EDGE_PCT")

    # --- Dashboard behaviour -----------------------------------------------
    refresh_interval_secs: int = Field(default=60, alias="REFRESH_INTERVAL_SECS")

    # --- Rate limiting -----------------------------------------------------
    rate_limit_delay_secs: float = Field(default=1.0, alias="RATE_LIMIT_DELAY_SECS")

    # --- Polymarket API URLs -----------------------------------------------
    polymarket_gamma_url: str = Field(
        default="https://gamma-api.polymarket.com",
        alias="POLYMARKET_GAMMA_URL",
    )
    polymarket_clob_url: str = Field(
        default="https://clob.polymarket.com",
        alias="POLYMARKET_CLOB_URL",
    )

    # --- The-Odds-API URL --------------------------------------------------
    odds_api_base_url: str = Field(
        default="https://api.the-odds-api.com/v4",
        alias="ODDS_API_BASE_URL",
    )

    # --- OddsPapi base URL -------------------------------------------------
    oddspapi_base_url: str = Field(
        default="https://api.oddspapi.com",
        alias="ODDSPAPI_BASE_URL",
    )

    # --- Alerting ----------------------------------------------------------
    alert_webhook_url: str = Field(default="", alias="ALERT_WEBHOOK_URL")

    # --- Bookmaker filter (empty = all bookmakers) -------------------------
    enabled_bookmakers: list[str] = Field(default_factory=list)


#: Module-level singleton — import this throughout the codebase.
settings = Settings()
