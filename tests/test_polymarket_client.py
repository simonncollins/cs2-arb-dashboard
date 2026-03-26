"""Unit tests for PolymarketClient.

All HTTP calls are mocked - no network access required.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from src.clients.polymarket_client import PolymarketClient, _price_cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    json_data: Any,
    status_code: int = 200,
) -> MagicMock:
    """Build a mock ``requests.Response``."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    if status_code >= 400:
        http_err = requests.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_err
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


def _make_client() -> tuple[PolymarketClient, MagicMock]:
    """Return a PolymarketClient with a mocked session."""
    mock_session = MagicMock(spec=requests.Session)
    client = PolymarketClient(
        gamma_url="https://gamma.test",
        clob_url="https://clob.test",
        session=mock_session,
    )
    return client, mock_session


# ---------------------------------------------------------------------------
# get_cs2_markets
# ---------------------------------------------------------------------------


class TestGetCs2Markets:
    def test_success_list_response(self) -> None:
        """Gamma returning a plain JSON list is returned as-is."""
        markets = [{"conditionId": "abc", "question": "Will NaVi win?"}]
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response(markets)

        result = client.get_cs2_markets()

        assert result == markets

    def test_success_dict_response(self) -> None:
        """Gamma returning {"markets": [...]} unwraps the inner list."""
        markets = [{"conditionId": "xyz", "question": "Will s1mple play?"}]
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response({"markets": markets})

        result = client.get_cs2_markets()

        assert result == markets

    def test_passes_tag_and_active_params(self) -> None:
        """GET /markets must be called with tag=cs2 and active=true."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response([])

        client.get_cs2_markets()

        assert mock_session.get.call_args is not None
        _, call_kwargs = mock_session.get.call_args
        params = call_kwargs.get("params", {})
        assert params.get("tag") == "cs2"
        assert params.get("active") == "true"

    def test_raises_http_error_on_4xx(self) -> None:
        """4xx errors must propagate immediately without retry."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response({}, status_code=404)

        with pytest.raises(requests.HTTPError):
            client.get_cs2_markets()

        # Only called once - no retry on 4xx
        assert mock_session.get.call_count == 1

    def test_raises_http_error_on_5xx_after_retries(self) -> None:
        """5xx errors must be retried up to 3 times, then raise."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response({}, status_code=500)

        with pytest.raises(requests.HTTPError):
            client.get_cs2_markets()

        # tenacity retries 3 times total (1 initial + 2 retries = 3 calls)
        assert mock_session.get.call_count == 3


# ---------------------------------------------------------------------------
# get_market_prices
# ---------------------------------------------------------------------------


class TestGetMarketPrices:
    def setup_method(self) -> None:
        """Clear module-level price cache before each test."""
        _price_cache.clear()

    def test_mid_key_response(self) -> None:
        """CLOB {"mid": "0.65"} -> {token_ids[0]: 0.65}."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response({"mid": "0.65"})

        result = client.get_market_prices(["cond123"])

        assert result == {"cond123": pytest.approx(0.65)}

    def test_midpoints_key_response(self) -> None:
        """CLOB {"midpoints": {tok: price}} -> {tok: float(price)}."""
        client, mock_session = _make_client()
        payload = {"midpoints": {"tok1": "0.4", "tok2": "0.6"}}
        mock_session.get.return_value = _make_response(payload)

        result = client.get_market_prices(["cond456"])

        assert result == {"tok1": pytest.approx(0.4), "tok2": pytest.approx(0.6)}

    def test_batches_multiple_token_ids(self) -> None:
        """Request must include multiple token_id params for batching."""
        client, mock_session = _make_client()
        payload = {"midpoints": {"abc": "0.3", "def": "0.7"}}
        mock_session.get.return_value = _make_response(payload)

        client.get_market_prices(["abc", "def"])

        assert mock_session.get.call_args is not None
        _, call_kwargs = mock_session.get.call_args
        params = call_kwargs.get("params", [])
        token_params = [v for k, v in params if k == "token_id"]
        assert "abc" in token_params
        assert "def" in token_params

    def test_cache_prevents_second_http_call(self) -> None:
        """Second call with same token_ids within TTL must not make an HTTP request."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response({"midpoints": {"unique_cache_tok": "0.5"}})

        client.get_market_prices(["unique_cache_tok"])
        client.get_market_prices(["unique_cache_tok"])

        # Cache should have intercepted the second call
        assert mock_session.get.call_count == 1

    def test_raises_http_error_on_429_after_retries(self) -> None:
        """429 Too Many Requests must be retried, then raise."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response({}, status_code=429)

        with pytest.raises(requests.HTTPError):
            client.get_market_prices(["cond789"])

        assert mock_session.get.call_count == 3
