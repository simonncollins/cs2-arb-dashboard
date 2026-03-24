"""Polymarket Gamma and CLOB API client (no authentication required)."""
from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

import config

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Return True for 429 / 5xx HTTP errors - these warrant a retry."""
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return status == 429 or status >= 500
    return False


class PolymarketClient:
    """Client for Polymarket Gamma and CLOB APIs.

    Both APIs are public (no auth required for read operations).

    Args:
        gamma_url: Base URL for the Gamma REST API.
        clob_url: Base URL for the CLOB REST API.
        timeout: HTTP request timeout in seconds.
        session: Optional pre-configured ``requests.Session`` (useful for testing).
    """

    def __init__(
        self,
        gamma_url: str = config.POLYMARKET_GAMMA_URL,
        clob_url: str = config.POLYMARKET_CLOB_URL,
        timeout: int = 10,
        session: requests.Session | None = None,
    ) -> None:
        self._gamma_url = gamma_url.rstrip("/")
        self._clob_url = clob_url.rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()

    # ---- Gamma API ----------------------------------------------------------

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def get_cs2_markets(self) -> list[dict[str, Any]]:
        """Fetch active CS2 markets from the Gamma API.

        Calls ``GET /markets?tag=cs2&active=true``.

        Returns:
            List of market dicts, each containing at minimum:
            - ``conditionId`` (str): used as *market_id* in CLOB calls.
            - ``question`` (str): human-readable market title.
            - ``active`` (bool): whether the market is currently live.
            - ``outcomes`` (list[str]): possible outcome labels.

        Raises:
            requests.HTTPError: For 4xx client errors (not retried) and 5xx
                server errors after exhausting retries.
        """
        url = f"{self._gamma_url}/markets"
        params: dict[str, str] = {"tag": "cs2", "active": "true"}
        logger.debug("GET %s params=%s", url, params)
        resp = self._session.get(url, params=params, timeout=self._timeout)
        resp.raise_for_status()
        data: Any = resp.json()
        # Gamma returns either a plain list or {"markets": [...]}
        if isinstance(data, list):
            return data  # type: ignore[return-value]
        return data.get("markets", [])  # type: ignore[return-value]

    # ---- CLOB API -----------------------------------------------------------

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def get_market_prices(self, market_id: str) -> dict[str, float]:
        """Fetch mid-point prices for a market's outcome tokens from the CLOB API.

        Calls ``GET /midpoints?token_id=<market_id>``.

        Args:
            market_id: The ``conditionId`` from Gamma, used as the CLOB token ID.

        Returns:
            Dict mapping token_id -> mid-point price in [0.0, 1.0].
            - If the response contains a single ``"mid"`` key the returned dict
              has one entry: ``{market_id: <price>}``.
            - If the response contains a ``"midpoints"`` dict each entry is
              included directly.

        Raises:
            requests.HTTPError: For 4xx client errors (not retried) and 5xx /
                429 errors after exhausting retries.
        """
        url = f"{self._clob_url}/midpoints"
        params: dict[str, str] = {"token_id": market_id}
        logger.debug("GET %s params=%s", url, params)
        resp = self._session.get(url, params=params, timeout=self._timeout)
        resp.raise_for_status()
        data: Any = resp.json()
        # CLOB may return {"mid": <price>} or {"midpoints": {token_id: price}}
        if "mid" in data:
            return {market_id: float(data["mid"])}
        return {k: float(v) for k, v in data.get("midpoints", {}).items()}
