"""Polymarket CLOB WebSocket client for real-time price updates.

Subscribes to the Polymarket WebSocket subscription endpoint and delivers
live order-book mid-price updates for a set of market IDs via a callback.

Usage::

    import asyncio
    from src.clients.polymarket_ws import PolymarketWSClient

    async def on_price(market_id: str, outcome: str, price: float) -> None:
        print(f"{market_id} / {outcome} -> {price:.4f}")

    async def main() -> None:
        client = PolymarketWSClient(on_price_update=on_price)
        await client.subscribe(["0xabc...", "0xdef..."])

    asyncio.run(main())

The WS endpoint used is::

    wss://ws-subscriptions-clob.polymarket.com/ws/market
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
import json
import logging
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

# Public Polymarket CLOB WebSocket endpoint
_WS_ENDPOINT = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# Callback type: async (market_id, outcome, price) -> None
PriceUpdateCallback = Callable[[str, str, float], Coroutine[Any, Any, None]]


class PolymarketWSClient:
    """Async WebSocket client for Polymarket CLOB real-time price streaming.

    Connects to the Polymarket WS subscription API, subscribes to price changes
    for the supplied market IDs, and forwards updates to an async callback.
    Reconnects automatically with exponential back-off on disconnect.

    Args:
        on_price_update: Async callback invoked for each price update, with
            signature ``async (market_id: str, outcome: str, price: float) -> None``.
        ws_endpoint: WebSocket URL to connect to (default: Polymarket CLOB WS).
        max_reconnect_attempts: Maximum reconnection attempts before giving up.
            ``0`` means unlimited (reconnect forever).
        base_backoff_secs: Initial sleep time (seconds) before the first
            reconnection attempt. Doubles on each subsequent attempt, capped at
            ``max_backoff_secs``.
        max_backoff_secs: Upper bound on reconnection wait time in seconds.
    """

    def __init__(
        self,
        on_price_update: PriceUpdateCallback,
        ws_endpoint: str = _WS_ENDPOINT,
        max_reconnect_attempts: int = 0,
        base_backoff_secs: float = 1.0,
        max_backoff_secs: float = 60.0,
    ) -> None:
        self._on_price_update = on_price_update
        self._ws_endpoint = ws_endpoint
        self._max_reconnect_attempts = max_reconnect_attempts
        self._base_backoff = base_backoff_secs
        self._max_backoff = max_backoff_secs
        self._market_ids: list[str] = []

    async def subscribe(self, market_ids: list[str]) -> None:
        """Connect and stream price updates for the given market IDs.

        Runs indefinitely (or until ``max_reconnect_attempts`` is exceeded),
        reconnecting with exponential back-off after each disconnect.

        Args:
            market_ids: List of Polymarket condition IDs / market IDs to
                subscribe to.  These are the ``conditionId`` values from the
                Gamma API.
        """
        self._market_ids = list(market_ids)
        attempt = 0
        backoff = self._base_backoff

        while True:
            try:
                await self._connect_and_stream()
                # If we return cleanly, reset back-off
                backoff = self._base_backoff
                attempt = 0
            except (ConnectionClosed, OSError) as exc:
                attempt += 1
                if self._max_reconnect_attempts and attempt > self._max_reconnect_attempts:
                    logger.error(
                        "WebSocket max reconnect attempts (%d) exceeded: %s",
                        self._max_reconnect_attempts,
                        exc,
                    )
                    raise
                logger.warning(
                    "WebSocket disconnected (attempt %d): %s — reconnecting in %.1fs",
                    attempt,
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._max_backoff)

    async def _connect_and_stream(self) -> None:
        """Open a single WebSocket connection and process messages until closed."""
        logger.info("Connecting to %s", self._ws_endpoint)
        async with websockets.connect(self._ws_endpoint) as ws:
            logger.info("WebSocket connected; subscribing to %d markets", len(self._market_ids))
            await self._send_subscribe(ws)
            async for raw_message in ws:
                await self._handle_message(raw_message)

    async def _send_subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Send the subscription request for all tracked market IDs.

        Polymarket WS accepts a JSON message of the form::

            {
                "type": "market",
                "assets_ids": ["<market_id_1>", "<market_id_2>", ...]
            }
        """
        payload = json.dumps({"type": "market", "assets_ids": self._market_ids})
        await ws.send(payload)
        logger.debug("Sent subscribe payload for %d markets", len(self._market_ids))

    async def _handle_message(self, raw: str | bytes) -> None:
        """Parse a WS message and invoke the callback for price-update events.

        Expected message shape (Polymarket CLOB WS)::

            {
                "event_type": "price_change",
                "asset_id": "<market_id>",
                "market": "<outcome_label>",
                "price": "0.6500"
            }

        Other event types (e.g. ``"tick_size_change"``) are ignored.
        """
        try:
            data: Any = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.debug("Non-JSON WS message ignored: %.120s", raw)
            return

        if not isinstance(data, dict):
            return

        event_type = data.get("event_type")
        if event_type != "price_change":
            return

        market_id: str | None = data.get("asset_id")
        outcome: str | None = data.get("market")
        raw_price = data.get("price")

        if market_id is None or outcome is None or raw_price is None:
            logger.debug("Incomplete price_change message: %s", data)
            return

        try:
            price = float(raw_price)
        except (ValueError, TypeError):
            logger.debug("Unparseable price value %r in message: %s", raw_price, data)
            return

        await self._on_price_update(market_id, outcome, price)
