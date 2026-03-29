"""The Odds API client for fetching CS2/esports bookmaker odds."""
from __future__ import annotations

from typing import Any

import requests
import structlog
from cachetools import TTLCache
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings

logger = structlog.get_logger(__name__)

_QUOTA_THRESHOLD = 10


class QuotaExhaustedError(Exception):
    """Raised when the Odds API quota drops below the safety threshold."""

    def __init__(self, remaining: int) -> None:
        super().__init__(f"Odds API quota critically low: {remaining} requests remaining")
        self.remaining = remaining


def _is_retryable(exc: BaseException) -> bool:
    """Return True for 429 / 5xx HTTP errors — these warrant a retry."""
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return status == 429 or status >= 500
    return False


class OddsAPIClient:
    """Client for The Odds API v4.

    Args:
        api_key: The Odds API key. Defaults to ``settings.odds_api_key``.
        base_url: API base URL. Defaults to ``"https://api.the-odds-api.com/v4"``.
        sport_key: Sport key to query. Defaults to ``"esports_cs2"``.
        session: Optional pre-configured ``requests.Session`` (useful for testing).
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.the-odds-api.com/v4",
        sport_key: str = "esports_cs2",
        session: requests.Session | None = None,
    ) -> None:
        self._api_key = api_key or settings.odds_api_key
        self._base_url = base_url.rstrip("/")
        self._sport_key = sport_key
        self._session = session or requests.Session()
        # Per-instance TTLCache so tests get isolated caches.
        self._odds_cache: TTLCache[tuple[str, str, str], list[dict[str, Any]]] = TTLCache(
            maxsize=16, ttl=300
        )

    # ---- Internal helpers --------------------------------------------------

    def _fetch_cs2_odds(
        self,
        regions: str,
        markets: str,
        odds_format: str,
    ) -> list[dict[str, Any]]:
        """Perform the actual HTTP request for CS2 odds (no cache)."""
        url = f"{self._base_url}/sports/{self._sport_key}/odds/"
        params: dict[str, str] = {
            "apiKey": self._api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
        }
        logger.debug("GET odds", url=url, regions=regions, markets=markets)
        resp = self._session.get(url, params=params, timeout=10)
        resp.raise_for_status()

        remaining_str = resp.headers.get("X-Requests-Remaining", "")
        used_str = resp.headers.get("X-Requests-Used", "")
        remaining: int = int(remaining_str) if remaining_str.isdigit() else 999

        logger.info(
            "odds_api_quota",
            requests_remaining=remaining,
            requests_used=used_str,
        )

        if remaining < _QUOTA_THRESHOLD:
            raise QuotaExhaustedError(remaining)

        data: Any = resp.json()
        return data  # type: ignore[return-value]

    # ---- Public API --------------------------------------------------------

    @retry(  # type: ignore[misc]
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def get_cs2_odds(
        self,
        regions: str = "us,eu",
        markets: str = "h2h",
        odds_format: str = "decimal",
    ) -> list[dict[str, Any]]:
        """Fetch current CS2 odds from The Odds API.

        Results are cached for 5 minutes per (regions, markets, odds_format) key
        to preserve the monthly quota.

        Args:
            regions: Comma-separated region codes (e.g. ``"us,eu"``).
            markets: Market type (e.g. ``"h2h"``).
            odds_format: Odds format (``"decimal"`` or ``"american"``).

        Returns:
            List of raw event dicts with bookmaker odds.

        Raises:
            QuotaExhaustedError: When remaining quota drops below threshold.
            requests.HTTPError: On non-2xx responses (4xx not retried).
        """
        cache_key = (regions, markets, odds_format)
        if cache_key in self._odds_cache:
            logger.debug("odds_api_cache_hit", key=cache_key)
            return self._odds_cache[cache_key]

        result = self._fetch_cs2_odds(regions, markets, odds_format)
        self._odds_cache[cache_key] = result
        return result

    @retry(  # type: ignore[misc]
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def get_available_sports(self) -> list[str]:
        """Return list of available sport keys from The Odds API.

        Returns:
            List of sport key strings (e.g. ``["esports_cs2", ...]``).

        Raises:
            requests.HTTPError: On non-2xx responses.
        """
        url = f"{self._base_url}/sports/"
        params: dict[str, str] = {"apiKey": self._api_key}
        logger.debug("GET sports", url=url)
        resp = self._session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data: Any = resp.json()
        return [item["key"] for item in data]
