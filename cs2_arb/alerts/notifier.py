"""Webhook and Slack notification delivery for arbitrage alerts.

Sends alert payloads to a Slack incoming webhook or a generic HTTP webhook
when high-value arbitrage opportunities are detected.

Both notifiers are optional — if no URL is configured they skip silently.
Both retry up to 3 times on transient HTTP/network failures.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES: int = 3
_RETRY_DELAY_SECS: float = 1.0


def _post_with_retry(url: str, payload: dict[str, Any]) -> None:
    """POST *payload* as JSON to *url*, retrying up to ``_MAX_RETRIES`` times.

    On persistent failure a warning is logged but no exception is raised.

    Args:
        url: Destination URL.
        payload: JSON-serialisable dict to send.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Webhook POST attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECS)
    logger.error("Webhook POST permanently failed after %d attempts: %s", _MAX_RETRIES, last_exc)


class SlackNotifier:
    """Posts a formatted alert message to a Slack incoming webhook.

    Args:
        webhook_url: Slack incoming webhook URL.  If empty or None the
            notifier is disabled and ``notify()`` is a no-op.
    """

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or ""

    def notify(self, opportunity_payload: dict[str, Any]) -> None:
        """Send a Slack message for *opportunity_payload*.

        Skips silently if ``webhook_url`` is not configured.

        Args:
            opportunity_payload: Alert dict produced by ``AlertManager``, expected
                keys: ``event_name``, ``outcome``, ``edge_pct``, ``ev_adjusted``,
                ``poly_prob``, ``book_name``.  Missing keys are handled gracefully.
        """
        if not self.webhook_url:
            return

        event = opportunity_payload.get("event_name", "Unknown Event")
        outcome = opportunity_payload.get("outcome", "?")
        edge = opportunity_payload.get("edge_pct", 0.0)
        ev = opportunity_payload.get("ev_adjusted", 0.0)
        book = opportunity_payload.get("book_name", "?")
        poly_prob = opportunity_payload.get("poly_prob", 0.0)

        # Build Polymarket deep-link (best-effort slug)
        slug = event.lower().replace(" ", "-")
        poly_link = f"https://polymarket.com/event/{slug}"

        text = (
            f":zap: *CS2 Arbitrage Alert*\n"
            f"*Event:* {event} — {outcome}\n"
            f"*Edge:* {edge:.2f}%  |  *EV (adj):* ${ev:.4f}\n"
            f"*Book:* {book}  |  *Poly Prob:* {poly_prob * 100:.1f}%\n"
            f"<{poly_link}|View on Polymarket>"
        )

        message = {"text": text}
        _post_with_retry(self.webhook_url, message)


class WebhookNotifier:
    """POSTs the raw alert payload as JSON to a generic webhook URL.

    Args:
        url: Destination URL.  If empty or None the notifier is disabled
            and ``notify()`` is a no-op.
    """

    def __init__(self, url: str | None = None) -> None:
        self.url = url or ""

    def notify(self, opportunity_payload: dict[str, Any]) -> None:
        """POST *opportunity_payload* as JSON to ``url``.

        Skips silently if ``url`` is not configured.

        Args:
            opportunity_payload: Alert dict to send verbatim as JSON body.
        """
        if not self.url:
            return

        _post_with_retry(self.url, opportunity_payload)
