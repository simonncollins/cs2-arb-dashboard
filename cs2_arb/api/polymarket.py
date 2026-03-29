"""Polymarket Gamma + CLOB API client.

Fetches CS2 esports markets and current prices from Polymarket.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from cs2_arb.config import POLYMARKET_CLOB_URL, POLYMARKET_GAMMA_URL


class PolymarketError(Exception):
    """Raised when the Polymarket API returns an error or is unreachable."""


@dataclass
class PolymarketMarket:
    """Structured representation of a Polymarket CS2 binary market."""

    market_id: str
    team_a: str
    team_b: str
    yes_price: float
    no_price: float
    closes_at: str


def _parse_teams(question: str) -> tuple[str, str]:
    """Extract team names from a question string like 'Team A vs Team B'."""
    for sep in (" vs ", " VS ", " Vs "):
        if sep in question:
            parts = question.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    # Fallback: return question as team_a and empty string for team_b
    return question.strip(), ""


class PolymarketClient:
    """Client for the Polymarket Gamma and CLOB APIs."""

    def __init__(
        self,
        gamma_url: str = POLYMARKET_GAMMA_URL,
        clob_url: str = POLYMARKET_CLOB_URL,
        timeout: int = 10,
    ) -> None:
        self._gamma_url = gamma_url.rstrip("/")
        self._clob_url = clob_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()

    def _get(self, url: str, params: dict | None = None) -> dict | list:
        """Perform a GET request, raising PolymarketError on failure."""
        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise PolymarketError(f"Request to {url} failed: {exc}") from exc

    def get_market_prices(self, token_id: str) -> tuple[float, float]:
        """Fetch live YES/NO midpoint prices from the CLOB API.

        Args:
            token_id: The CLOB token ID for the YES outcome of the market.

        Returns:
            A (yes_price, no_price) tuple where both values are in [0, 1].
        """
        url = f"{self._clob_url}/midpoint"
        data = self._get(url, params={"token_id": token_id})
        if not isinstance(data, dict):
            raise PolymarketError(f"Unexpected response format from {url}")
        try:
            yes_price = float(data["mid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PolymarketError(f"Could not parse price from response: {data}") from exc
        no_price = round(1.0 - yes_price, 6)
        return yes_price, no_price

    def get_cs2_markets(self) -> list[PolymarketMarket]:
        """Fetch active CS2 esports markets from the Gamma API.

        Returns:
            A list of :class:`PolymarketMarket` objects with live prices.
        """
        url = f"{self._gamma_url}/markets"
        # Filter for active CS2 / esports binary markets
        params: dict = {
            "tag": "esports",
            "active": "true",
            "closed": "false",
        }
        raw = self._get(url, params=params)
        if not isinstance(raw, list):
            raise PolymarketError(f"Expected list from {url}, got {type(raw).__name__}")

        markets: list[PolymarketMarket] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            question: str = item.get("question", "") or item.get("title", "")
            # Only include CS2-related markets
            question_lower = question.lower()
            if not any(k in question_lower for k in ("cs2", "counter-strike", "cs:")):
                continue

            team_a, team_b = _parse_teams(question)
            market_id: str = str(item.get("id", ""))
            closes_at: str = str(item.get("endDate", "") or item.get("end_date", ""))

            # Resolve the YES token ID — CLOB needs this to fetch the price
            token_id: str = ""
            clob_token_ids = item.get("clobTokenIds")
            if clob_token_ids and isinstance(clob_token_ids, list) and len(clob_token_ids) > 0:
                token_id = str(clob_token_ids[0])
            elif market_id:
                token_id = market_id

            yes_price = 0.5
            no_price = 0.5
            if token_id:
                try:
                    yes_price, no_price = self.get_market_prices(token_id)
                except PolymarketError:
                    # Skip price fetch failures silently; keep default midpoint
                    pass

            markets.append(
                PolymarketMarket(
                    market_id=market_id,
                    team_a=team_a,
                    team_b=team_b,
                    yes_price=yes_price,
                    no_price=no_price,
                    closes_at=closes_at,
                )
            )

        return markets
