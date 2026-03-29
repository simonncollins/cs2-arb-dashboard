"""Unit tests for OddsAPIClient.

All HTTP calls are mocked — no live network access required.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from app.clients.odds_api_client import OddsAPIClient, QuotaExhaustedError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    json_data: Any,
    status_code: int = 200,
    remaining: int = 450,
    used: int = 50,
) -> MagicMock:
    """Build a mock requests.Response."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.headers = {
        "X-Requests-Remaining": str(remaining),
        "X-Requests-Used": str(used),
    }
    if status_code >= 400:
        http_err = requests.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_err
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


def _make_client() -> tuple[OddsAPIClient, MagicMock]:
    """Return an OddsAPIClient with a mocked session."""
    mock_session = MagicMock(spec=requests.Session)
    client = OddsAPIClient(
        api_key="test-key",
        base_url="https://api.test",
        session=mock_session,
    )
    return client, mock_session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetCs2Odds:
    def test_returns_list_of_events(self) -> None:
        """Happy path: returns list of event dicts."""
        events = [
            {"id": "abc", "home_team": "NaVi", "away_team": "FaZe"},
            {"id": "def", "home_team": "Liquid", "away_team": "ENCE"},
        ]
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response(events)

        result = client.get_cs2_odds()

        assert result == events

    def test_quota_logged(self) -> None:
        """Successful call completes without error; quota headers consumed."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response([], remaining=300)

        result = client.get_cs2_odds()

        assert isinstance(result, list)
        mock_session.get.assert_called_once()

    def test_raises_quota_exhausted_when_below_threshold(self) -> None:
        """X-Requests-Remaining below 10 raises QuotaExhaustedError."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response([], remaining=5)

        with pytest.raises(QuotaExhaustedError) as exc_info:
            client.get_cs2_odds()

        assert exc_info.value.remaining == 5

    def test_raises_http_error_on_4xx(self) -> None:
        """4xx errors raise immediately without retry."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response({}, status_code=404)

        with pytest.raises(requests.HTTPError):
            client.get_cs2_odds()

        # No retry on 4xx
        assert mock_session.get.call_count == 1

    def test_retries_on_5xx_then_raises(self) -> None:
        """5xx errors are retried 3 times then raise."""
        client, mock_session = _make_client()
        mock_session.get.return_value = _make_response({}, status_code=500)

        with pytest.raises(requests.HTTPError):
            client.get_cs2_odds()

        assert mock_session.get.call_count == 3

    def test_cache_prevents_second_http_call(self) -> None:
        """Second call within TTL returns cached result without HTTP request."""
        client, mock_session = _make_client()
        events = [{"id": "xyz"}]
        mock_session.get.return_value = _make_response(events)

        first = client.get_cs2_odds()
        second = client.get_cs2_odds()

        assert first == events
        assert second == events
        # Only one HTTP call made — second hit the cache
        assert mock_session.get.call_count == 1


class TestGetAvailableSports:
    def test_get_available_sports_returns_keys(self) -> None:
        """Returns list of sport key strings."""
        client, mock_session = _make_client()
        sports_data = [
            {"key": "esports_cs2", "title": "CS2"},
            {"key": "soccer_epl", "title": "Premier League"},
        ]
        mock_session.get.return_value = _make_response(sports_data)

        result = client.get_available_sports()

        assert result == ["esports_cs2", "soccer_epl"]
