"""Token-bucket rate limiter for API client calls.

Implements a simple token-bucket algorithm to enforce a minimum delay
between requests to the same endpoint. Configurable via
``settings.rate_limit_delay_secs``.

Usage::

    limiter = RateLimiter(min_interval_secs=1.0)

    @limiter.limit
    def fetch_data() -> dict:
        return requests.get(...).json()
"""
from __future__ import annotations

import functools
import time
from collections import defaultdict
from typing import Any, Callable, TypeVar

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_F = TypeVar("_F", bound=Callable[..., Any])


class RateLimiter:
    """Simple delay-based rate limiter.

    Enforces a minimum interval between successive calls to each decorated
    function. If a call arrives sooner than ``min_interval_secs`` after the
    previous one, the limiter sleeps for the remaining time.

    Args:
        min_interval_secs: Minimum seconds between calls. Defaults to
            ``settings.rate_limit_delay_secs``.
    """

    def __init__(self, min_interval_secs: float | None = None) -> None:
        self._interval = (
            min_interval_secs
            if min_interval_secs is not None
            else settings.rate_limit_delay_secs
        )
        # Track last-call time per function name.
        self._last_called: dict[str, float] = defaultdict(float)

    def limit(self, func: _F) -> _F:
        """Apply rate-limiting to a callable.

        Args:
            func: The function to wrap.

        Returns:
            Wrapped function that enforces the configured minimum interval.
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            key = func.__qualname__
            now = time.monotonic()
            elapsed = now - self._last_called[key]
            remaining = self._interval - elapsed
            if remaining > 0:
                logger.debug(
                    "rate_limit_sleep",
                    func=key,
                    sleep_secs=round(remaining, 3),
                )
                time.sleep(remaining)
            self._last_called[key] = time.monotonic()
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]


#: Module-level singleton — shared across all clients using the default interval.
default_limiter = RateLimiter()
