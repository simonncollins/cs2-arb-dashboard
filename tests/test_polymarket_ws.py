"""Unit tests for PolymarketWSClient.

Tests use a mock WebSocket server built with asyncio + unittest.mock — no
live network connections are made.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.polymarket_ws import PolymarketWSClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_price_msg(market_id: str, outcome: str, price: float) -> str:
    return json.dumps(
        {
            "event_type": "price_change",
            "asset_id": market_id,
            "market": outcome,
            "price": str(price),
        }
    )


def _make_other_msg(event_type: str) -> str:
    return json.dumps({"event_type": event_type, "data": "ignored"})


async def _async_iter(items: list[Any]) -> AsyncIterator[Any]:
    """Yield items from a list as an async iterator."""
    for item in items:
        yield item


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_invoked_on_price_change() -> None:
    """Callback is called once for a valid price_change message."""
    received: list[tuple[str, str, float]] = []

    async def on_price(market_id: str, outcome: str, price: float) -> None:
        received.append((market_id, outcome, price))

    client = PolymarketWSClient(on_price_update=on_price)

    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)
    mock_ws.send = AsyncMock()
    mock_ws.__aiter__ = lambda self: _async_iter(
        [_make_price_msg("0xabc", "Team A", 0.65)]
    )

    with patch("src.clients.polymarket_ws.websockets.connect", return_value=mock_ws):
        await client._connect_and_stream()

    assert received == [("0xabc", "Team A", 0.65)]


@pytest.mark.asyncio
async def test_non_price_change_events_ignored() -> None:
    """Messages with event_type other than price_change are ignored."""
    received: list[tuple[str, str, float]] = []

    async def on_price(market_id: str, outcome: str, price: float) -> None:
        received.append((market_id, outcome, price))

    client = PolymarketWSClient(on_price_update=on_price)

    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)
    mock_ws.send = AsyncMock()
    mock_ws.__aiter__ = lambda self: _async_iter(
        [_make_other_msg("tick_size_change"), _make_other_msg("book")]
    )

    with patch("src.clients.polymarket_ws.websockets.connect", return_value=mock_ws):
        await client._connect_and_stream()

    assert received == []


@pytest.mark.asyncio
async def test_multiple_price_updates_all_delivered() -> None:
    """All price_change messages in a batch are delivered to callback."""
    received: list[tuple[str, str, float]] = []

    async def on_price(market_id: str, outcome: str, price: float) -> None:
        received.append((market_id, outcome, price))

    client = PolymarketWSClient(on_price_update=on_price)

    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)
    mock_ws.send = AsyncMock()
    mock_ws.__aiter__ = lambda self: _async_iter(
        [
            _make_price_msg("0xabc", "Team A", 0.65),
            _make_price_msg("0xabc", "Team B", 0.35),
            _make_price_msg("0xdef", "Team C", 0.72),
        ]
    )

    with patch("src.clients.polymarket_ws.websockets.connect", return_value=mock_ws):
        await client._connect_and_stream()

    assert len(received) == 3
    assert received[0] == ("0xabc", "Team A", 0.65)
    assert received[1] == ("0xabc", "Team B", 0.35)
    assert received[2] == ("0xdef", "Team C", 0.72)


@pytest.mark.asyncio
async def test_non_json_message_ignored() -> None:
    """Non-JSON messages do not raise exceptions."""
    received: list[Any] = []

    async def on_price(market_id: str, outcome: str, price: float) -> None:
        received.append((market_id, outcome, price))

    client = PolymarketWSClient(on_price_update=on_price)

    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)
    mock_ws.send = AsyncMock()
    mock_ws.__aiter__ = lambda self: _async_iter(["not valid json!!!"])

    with patch("src.clients.polymarket_ws.websockets.connect", return_value=mock_ws):
        await client._connect_and_stream()  # should not raise

    assert received == []


@pytest.mark.asyncio
async def test_incomplete_price_message_ignored() -> None:
    """price_change message missing required fields is silently ignored."""
    received: list[Any] = []

    async def on_price(market_id: str, outcome: str, price: float) -> None:
        received.append((market_id, outcome, price))

    client = PolymarketWSClient(on_price_update=on_price)

    incomplete = json.dumps({"event_type": "price_change"})  # missing asset_id, market, price

    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)
    mock_ws.send = AsyncMock()
    mock_ws.__aiter__ = lambda self: _async_iter([incomplete])

    with patch("src.clients.polymarket_ws.websockets.connect", return_value=mock_ws):
        await client._connect_and_stream()

    assert received == []


@pytest.mark.asyncio
async def test_subscribe_sends_correct_payload() -> None:
    """subscribe() sends a JSON message with type 'market' and the market IDs."""
    async def on_price(market_id: str, outcome: str, price: float) -> None:
        pass

    client = PolymarketWSClient(on_price_update=on_price)

    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)
    mock_ws.send = AsyncMock()
    mock_ws.__aiter__ = lambda self: _async_iter([])  # no messages

    with patch("src.clients.polymarket_ws.websockets.connect", return_value=mock_ws):
        await client._connect_and_stream()
        # subscribe was not called yet — test _send_subscribe directly
        client._market_ids = ["0xaaa", "0xbbb"]
        await client._send_subscribe(mock_ws)

    last_call_args = mock_ws.send.call_args
    assert last_call_args is not None
    sent_payload = json.loads(last_call_args[0][0])
    assert sent_payload["type"] == "market"
    assert sent_payload["assets_ids"] == ["0xaaa", "0xbbb"]


@pytest.mark.asyncio
async def test_reconnect_on_connection_closed() -> None:
    """subscribe() reconnects when ConnectionClosed is raised, up to max attempts."""
    from websockets.exceptions import ConnectionClosed

    call_count = 0

    async def on_price(market_id: str, outcome: str, price: float) -> None:
        pass

    client = PolymarketWSClient(
        on_price_update=on_price,
        max_reconnect_attempts=2,
        base_backoff_secs=0.001,  # fast for tests
    )

    async def failing_connect() -> None:
        nonlocal call_count
        call_count += 1
        raise ConnectionClosed(None, None)  # type: ignore[arg-type]

    client._connect_and_stream = failing_connect  # type: ignore[method-assign]

    with pytest.raises(ConnectionClosed):
        await client.subscribe(["0xabc"])

    assert call_count == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_unparseable_price_field_ignored() -> None:
    """price_change with a non-numeric price string is silently ignored."""
    received: list[Any] = []

    async def on_price(market_id: str, outcome: str, price: float) -> None:
        received.append((market_id, outcome, price))

    client = PolymarketWSClient(on_price_update=on_price)

    bad_price_msg = json.dumps(
        {"event_type": "price_change", "asset_id": "0xabc", "market": "Team A", "price": "NaN_BAD"}
    )

    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)
    mock_ws.send = AsyncMock()
    mock_ws.__aiter__ = lambda self: _async_iter([bad_price_msg])

    with patch("src.clients.polymarket_ws.websockets.connect", return_value=mock_ws):
        await client._connect_and_stream()

    assert received == []
