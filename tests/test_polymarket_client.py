"""Tests for the Polymarket API client."""

from __future__ import annotations

import pytest
import requests

from cs2_arb.api.polymarket import PolymarketClient, PolymarketError, PolymarketMarket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GAMMA_URL = "https://gamma-fake.test"
CLOB_URL = "https://clob-fake.test"


def make_client() -> PolymarketClient:
    return PolymarketClient(gamma_url=GAMMA_URL, clob_url=CLOB_URL)


def _mock_market_list() -> list[dict]:
    return [
        {
            "id": "mkt-001",
            "question": "Team Liquid vs NAVI CS2 bo3",
            "endDate": "2026-04-01T18:00:00Z",
            "clobTokenIds": ["tok-001"],
        },
        {
            "id": "mkt-002",
            "question": "Vitality vs Astralis CS2 match",
            "endDate": "2026-04-02T12:00:00Z",
            "clobTokenIds": ["tok-002"],
        },
        # Non-CS2 market — should be filtered out
        {
            "id": "mkt-999",
            "question": "Some LOL tournament",
            "endDate": "2026-04-01T00:00:00Z",
            "clobTokenIds": ["tok-999"],
        },
    ]


# ---------------------------------------------------------------------------
# Tests: get_market_prices
# ---------------------------------------------------------------------------


class TestGetMarketPrices:
    def test_returns_yes_no_prices(self, mocker):
        client = make_client()
        mock_get = mocker.patch.object(client._session, "get")
        mock_resp = mocker.MagicMock()
        mock_resp.json.return_value = {"mid": 0.65}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        yes, no = client.get_market_prices("tok-001")

        assert yes == pytest.approx(0.65)
        assert no == pytest.approx(0.35, abs=1e-5)
        mock_get.assert_called_once_with(
            f"{CLOB_URL}/midpoint",
            params={"token_id": "tok-001"},
            timeout=10,
        )

    def test_http_error_raises_polymarket_error(self, mocker):
        client = make_client()
        mock_get = mocker.patch.object(client._session, "get")
        mock_resp = mocker.MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_resp

        with pytest.raises(PolymarketError, match="failed"):
            client.get_market_prices("tok-bad")

    def test_timeout_raises_polymarket_error(self, mocker):
        client = make_client()
        mock_get = mocker.patch.object(client._session, "get")
        mock_get.side_effect = requests.Timeout("timed out")

        with pytest.raises(PolymarketError, match="failed"):
            client.get_market_prices("tok-slow")

    def test_missing_mid_key_raises_polymarket_error(self, mocker):
        client = make_client()
        mock_get = mocker.patch.object(client._session, "get")
        mock_resp = mocker.MagicMock()
        mock_resp.json.return_value = {"unexpected_field": 0.5}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        with pytest.raises(PolymarketError, match="Could not parse price"):
            client.get_market_prices("tok-bad")


# ---------------------------------------------------------------------------
# Tests: get_cs2_markets
# ---------------------------------------------------------------------------


class TestGetCs2Markets:
    def _setup_mocks(self, mocker, client: PolymarketClient, market_list: list[dict], price: float = 0.72) -> None:
        """Patch session.get to return market list for Gamma and prices for CLOB."""

        def fake_get(url: str, params=None, timeout=None):
            resp = mocker.MagicMock()
            resp.raise_for_status.return_value = None
            if "gamma" in url or "markets" in url:
                resp.json.return_value = market_list
            else:
                resp.json.return_value = {"mid": price}
            return resp

        mocker.patch.object(client._session, "get", side_effect=fake_get)

    def test_returns_list_of_polymarket_markets(self, mocker):
        client = make_client()
        self._setup_mocks(mocker, client, _mock_market_list())

        result = client.get_cs2_markets()

        assert isinstance(result, list)
        assert len(result) == 2  # LOL market filtered out
        assert all(isinstance(m, PolymarketMarket) for m in result)

    def test_team_names_parsed_correctly(self, mocker):
        client = make_client()
        self._setup_mocks(mocker, client, _mock_market_list())

        result = client.get_cs2_markets()

        assert result[0].team_a == "Team Liquid"
        assert result[0].team_b == "NAVI CS2 bo3"
        assert result[1].team_a == "Vitality"
        assert result[1].team_b == "Astralis CS2 match"

    def test_prices_populated(self, mocker):
        client = make_client()
        self._setup_mocks(mocker, client, _mock_market_list(), price=0.72)

        result = client.get_cs2_markets()

        assert result[0].yes_price == pytest.approx(0.72)
        assert result[0].no_price == pytest.approx(0.28, abs=1e-5)

    def test_gamma_http_error_raises_polymarket_error(self, mocker):
        client = make_client()
        mock_get = mocker.patch.object(client._session, "get")
        mock_resp = mocker.MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_resp

        with pytest.raises(PolymarketError, match="failed"):
            client.get_cs2_markets()

    def test_gamma_timeout_raises_polymarket_error(self, mocker):
        client = make_client()
        mock_get = mocker.patch.object(client._session, "get")
        mock_get.side_effect = requests.Timeout("timed out")

        with pytest.raises(PolymarketError, match="failed"):
            client.get_cs2_markets()

    def test_non_cs2_markets_filtered_out(self, mocker):
        client = make_client()
        non_cs2_markets = [
            {
                "id": "mkt-lol",
                "question": "Team A vs Team B LoL",
                "endDate": "2026-04-01T00:00:00Z",
                "clobTokenIds": ["tok-lol"],
            }
        ]
        self._setup_mocks(mocker, client, non_cs2_markets)

        result = client.get_cs2_markets()

        assert result == []

    def test_price_fetch_failure_uses_default_midpoint(self, mocker):
        """If CLOB price fetch fails, market is still returned with default 0.5/0.5."""
        client = make_client()

        def fake_get(url: str, params=None, timeout=None):
            resp = mocker.MagicMock()
            resp.raise_for_status.return_value = None
            if "midpoint" in url:
                resp.raise_for_status.side_effect = requests.HTTPError("503")
            else:
                resp.json.return_value = _mock_market_list()
            return resp

        mocker.patch.object(client._session, "get", side_effect=fake_get)

        result = client.get_cs2_markets()

        # Should still return markets, just with default prices
        assert len(result) == 2
        assert result[0].yes_price == pytest.approx(0.5)
        assert result[0].no_price == pytest.approx(0.5)
