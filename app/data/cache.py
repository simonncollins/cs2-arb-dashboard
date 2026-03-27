"""TTL-based caching utilities.

Provides a ``cached`` decorator factory backed by ``cachetools.TTLCache``.
Each call to ``cached(ttl_seconds=N)`` returns a decorator that wraps any
callable in a per-instance TTL cache keyed on positional and keyword arguments.

Per-source recommended TTLs:
- Polymarket: 60 seconds
- The Odds API: 300 seconds (quota preservation)
"""
from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from cachetools import TTLCache

#: Recommended TTL in seconds for Polymarket API responses.
POLYMARKET_TTL_SECS: int = 60
#: Recommended TTL in seconds for Odds API responses.
ODDS_API_TTL_SECS: int = 300

_F = TypeVar("_F", bound=Callable[..., Any])


def make_ttl_cache(ttl_seconds: int, maxsize: int = 256) -> TTLCache[Any, Any]:
    """Create a new ``TTLCache`` with the given TTL and max size.

    Args:
        ttl_seconds: Entry lifetime in seconds.
        maxsize: Maximum number of entries.

    Returns:
        A fresh ``TTLCache`` instance.
    """
    return TTLCache(maxsize=maxsize, ttl=ttl_seconds)


def cached(ttl_seconds: int, maxsize: int = 256) -> Callable[[_F], _F]:
    """Decorator factory: wraps a callable in a module-level TTL cache.

    The cache key is derived from all positional and keyword arguments.
    Suitable for module-level or class-level caching where a single shared
    cache per function is acceptable.

    For instance-level caching (to keep test isolation), prefer creating a
    ``TTLCache`` directly as an instance variable and using explicit cache
    checks as shown in ``OddsAPIClient``.

    Args:
        ttl_seconds: Entry lifetime in seconds.
        maxsize: Maximum number of cached entries.

    Returns:
        A decorator that wraps the target function with a TTL cache.

    Example::

        @cached(ttl_seconds=60)
        def get_data(key: str) -> dict:
            return fetch_from_api(key)
    """
    _cache: TTLCache[Any, Any] = TTLCache(maxsize=maxsize, ttl=ttl_seconds)

    def decorator(func: _F) -> _F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            key = (args, tuple(sorted(kwargs.items())))
            if key in _cache:
                return _cache[key]
            result = func(*args, **kwargs)
            _cache[key] = result
            return result

        # Expose the underlying cache for introspection / testing
        wrapper.cache = _cache  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
