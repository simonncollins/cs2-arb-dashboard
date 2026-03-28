"""The Odds API client for fetching CS2/esports bookmaker odds."""
from __future__ import annotations

from typing import Any

from cachetools import TTLCache
import requests
import structlog
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
