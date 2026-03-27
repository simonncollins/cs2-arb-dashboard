"""Unit tests for app.config Settings (pydantic-settings)."""
from __future__ import annotations

import pytest

from app.config import Settings, settings


class TestSettingsDefaults:
    def test_default_min_edge_pct(self) -> None:
        s = Settings()
        assert isinstance(s.min_edge_pct, float)
        assert s.min_edge_pct == pytest.approx(0.02)

    def test_default_refresh_interval(self) -> None:
        s = Settings()
        assert s.refresh_interval_secs == 60

    def test_default_polymarket_gamma_url(self) -> None:
        s = Settings()
        assert s.polymarket_gamma_url == "https://gamma-api.polymarket.com"

    def test_default_polymarket_clob_url(self) -> None:
        s = Settings()
        assert s.polymarket_clob_url == "https://clob.polymarket.com"

    def test_default_api_keys_empty_string(self) -> None:
        s = Settings()
        assert s.oddspapi_api_key == ""
        assert s.odds_api_key == ""

    def test_default_alert_webhook_empty(self) -> None:
        s = Settings()
        assert s.alert_webhook_url == ""

    def test_default_enabled_bookmakers_is_empty_list(self) -> None:
        s = Settings()
        assert s.enabled_bookmakers == []


class TestSettingsOverrides:
    def test_oddspapi_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ODDSPAPI_API_KEY", "test-key-123")
        s = Settings()
        assert s.oddspapi_api_key == "test-key-123"

    def test_min_edge_pct_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MIN_EDGE_PCT", "0.05")
        s = Settings()
        assert s.min_edge_pct == pytest.approx(0.05)

    def test_refresh_interval_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REFRESH_INTERVAL_SECS", "120")
        s = Settings()
        assert s.refresh_interval_secs == 120

    def test_alert_webhook_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example.com/abc")
        s = Settings()
        assert s.alert_webhook_url == "https://hooks.example.com/abc"


class TestSettingsImport:
    def test_singleton_importable(self) -> None:
        """The module-level `settings` singleton must be importable."""
        assert isinstance(settings, Settings)

    def test_min_edge_pct_is_float(self) -> None:
        assert isinstance(settings.min_edge_pct, float)
