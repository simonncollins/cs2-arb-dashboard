"""Tests for cs2_arb.alerts.notifier — SlackNotifier and WebhookNotifier."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import requests

from cs2_arb.alerts.notifier import SlackNotifier, WebhookNotifier, _post_with_retry

# ---------------------------------------------------------------------------
# Shared sample payload
# ---------------------------------------------------------------------------

SAMPLE_PAYLOAD: dict[str, Any] = {
    "event_name": "IEM Cologne 2026",
    "outcome": "team_a",
    "edge_pct": 4.5,
    "ev_adjusted": 0.0123,
    "poly_prob": 0.62,
    "book_name": "Pinnacle",
    "fired_at": 1700000000.0,
}


# ---------------------------------------------------------------------------
# SlackNotifier tests
# ---------------------------------------------------------------------------


class TestSlackNotifier:
    def test_sends_formatted_slack_message(self) -> None:
        """SlackNotifier should POST a properly formatted Slack message."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            notifier.notify(SAMPLE_PAYLOAD)

            assert mock_post.call_count == 1
            _, kwargs = mock_post.call_args
            sent_body = kwargs["json"]
            assert "text" in sent_body
            assert "IEM Cologne 2026" in sent_body["text"]
            assert "4.50%" in sent_body["text"] or "4.5" in sent_body["text"]
            assert "polymarket.com" in sent_body["text"]

    def test_no_call_when_url_empty(self) -> None:
        """SlackNotifier with empty URL should not make any HTTP call."""
        notifier = SlackNotifier(webhook_url="")
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post:
            notifier.notify(SAMPLE_PAYLOAD)
            mock_post.assert_not_called()

    def test_no_call_when_url_none(self) -> None:
        """SlackNotifier with None URL should not make any HTTP call."""
        notifier = SlackNotifier(webhook_url=None)
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post:
            notifier.notify(SAMPLE_PAYLOAD)
            mock_post.assert_not_called()

    def test_message_contains_book_name(self) -> None:
        """Slack message should include the book name."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            notifier.notify(SAMPLE_PAYLOAD)

            sent_body = mock_post.call_args[1]["json"]
            assert "Pinnacle" in sent_body["text"]


# ---------------------------------------------------------------------------
# WebhookNotifier tests
# ---------------------------------------------------------------------------


class TestWebhookNotifier:
    def test_sends_json_payload(self) -> None:
        """WebhookNotifier should POST the opportunity payload as JSON."""
        notifier = WebhookNotifier(url="https://example.com/webhook")
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            notifier.notify(SAMPLE_PAYLOAD)

            assert mock_post.call_count == 1
            sent_body = mock_post.call_args[1]["json"]
            assert sent_body["event_name"] == "IEM Cologne 2026"
            assert sent_body["edge_pct"] == 4.5

    def test_no_call_when_url_empty(self) -> None:
        """WebhookNotifier with empty URL should not make any HTTP call."""
        notifier = WebhookNotifier(url="")
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post:
            notifier.notify(SAMPLE_PAYLOAD)
            mock_post.assert_not_called()

    def test_no_call_when_url_none(self) -> None:
        """WebhookNotifier with None URL should not make any HTTP call."""
        notifier = WebhookNotifier(url=None)
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post:
            notifier.notify(SAMPLE_PAYLOAD)
            mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# _post_with_retry tests
# ---------------------------------------------------------------------------


class TestPostWithRetry:
    def test_succeeds_on_first_attempt(self) -> None:
        """Should succeed with a single POST when response is ok."""
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            _post_with_retry("https://example.com", {"key": "value"})

            assert mock_post.call_count == 1

    def test_retries_on_failure_then_succeeds(self) -> None:
        """Should retry on failure and succeed on the third attempt."""
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post, \
             patch("cs2_arb.alerts.notifier.time.sleep"):
            ok_resp = MagicMock()
            ok_resp.raise_for_status.return_value = None

            mock_post.side_effect = [
                requests.ConnectionError("fail 1"),
                requests.ConnectionError("fail 2"),
                ok_resp,
            ]

            _post_with_retry("https://example.com", {"key": "value"})

            assert mock_post.call_count == 3

    def test_exhausts_retries_and_does_not_raise(self) -> None:
        """Should not raise even when all retries are exhausted."""
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post, \
             patch("cs2_arb.alerts.notifier.time.sleep"):
            mock_post.side_effect = requests.ConnectionError("always fails")

            # Should not raise
            _post_with_retry("https://example.com", {"key": "value"})

            assert mock_post.call_count == 3

    def test_sleeps_between_retries(self) -> None:
        """Should sleep between retry attempts."""
        with patch("cs2_arb.alerts.notifier.requests.post") as mock_post, \
             patch("cs2_arb.alerts.notifier.time.sleep") as mock_sleep:
            ok_resp = MagicMock()
            ok_resp.raise_for_status.return_value = None

            mock_post.side_effect = [
                requests.ConnectionError("fail 1"),
                ok_resp,
            ]

            _post_with_retry("https://example.com", {})

            # Should have slept once between attempts
            assert mock_sleep.call_count == 1
