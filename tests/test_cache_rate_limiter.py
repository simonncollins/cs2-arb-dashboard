"""Unit tests for cache and rate limiter utilities."""
from __future__ import annotations

import time

from app.data.cache import ODDS_API_TTL_SECS, POLYMARKET_TTL_SECS, cached, make_ttl_cache
from app.data.rate_limiter import RateLimiter

# ---------------------------------------------------------------------------
# make_ttl_cache
# ---------------------------------------------------------------------------


class TestMakeTtlCache:
    def test_returns_ttl_cache(self) -> None:
        from cachetools import TTLCache

        cache = make_ttl_cache(60)
        assert isinstance(cache, TTLCache)

    def test_respects_maxsize(self) -> None:
        cache = make_ttl_cache(60, maxsize=5)
        assert cache.maxsize == 5

    def test_ttl_constants_defined(self) -> None:
        """Sanity-check the recommended TTL constants."""
        assert POLYMARKET_TTL_SECS == 60
        assert ODDS_API_TTL_SECS == 300


# ---------------------------------------------------------------------------
# cached decorator
# ---------------------------------------------------------------------------


class TestCachedDecorator:
    def test_caches_result(self) -> None:
        """Second call returns cached result without calling the function again."""
        call_count = 0

        @cached(ttl_seconds=60)
        def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(5) == 10
        assert call_count == 1

    def test_different_args_not_cached(self) -> None:
        """Different args produce separate cache entries."""
        call_count = 0

        @cached(ttl_seconds=60)
        def fn(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        fn(1)
        fn(2)
        assert call_count == 2

    def test_cache_exposed_on_wrapper(self) -> None:
        """The wrapped function exposes its cache as .cache."""

        @cached(ttl_seconds=60)
        def fn(x: int) -> int:
            return x

        fn(42)
        assert 42 in fn.cache.values()  # type: ignore[attr-defined]

    def test_expired_entry_re_fetches(self) -> None:
        """After TTL expiry the function is called again."""
        call_count = 0

        @cached(ttl_seconds=1)
        def fn() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        fn()
        time.sleep(1.1)
        fn()
        assert call_count == 2


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_first_call_not_delayed(self) -> None:
        """First call should complete without noticeable sleep."""
        limiter = RateLimiter(min_interval_secs=0.5)

        @limiter.limit
        def fast() -> int:
            return 1

        start = time.monotonic()
        fast()
        elapsed = time.monotonic() - start
        # First call should be essentially instant
        assert elapsed < 0.4

    def test_second_call_delayed(self) -> None:
        """Second call within interval is delayed."""
        limiter = RateLimiter(min_interval_secs=0.3)

        @limiter.limit
        def fn() -> int:
            return 1

        fn()
        start = time.monotonic()
        fn()
        elapsed = time.monotonic() - start
        # Should have slept ~0.3s
        assert elapsed >= 0.2

    def test_after_interval_no_delay(self) -> None:
        """Call after the interval expires is not delayed."""
        limiter = RateLimiter(min_interval_secs=0.2)

        @limiter.limit
        def fn() -> int:
            return 1

        fn()
        time.sleep(0.25)
        start = time.monotonic()
        fn()
        elapsed = time.monotonic() - start
        assert elapsed < 0.15

    def test_rate_limiter_enforces_min_interval(self) -> None:
        """Multiple rapid calls respect the minimum interval."""
        limiter = RateLimiter(min_interval_secs=0.1)
        call_times: list[float] = []

        @limiter.limit
        def fn() -> None:
            call_times.append(time.monotonic())

        for _ in range(3):
            fn()

        # Each gap should be >= 0.1s
        for i in range(1, len(call_times)):
            gap = call_times[i] - call_times[i - 1]
            assert gap >= 0.08, f"gap {gap:.3f}s between calls {i-1} and {i} too short"
