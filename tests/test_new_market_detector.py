"""Tests for cs2_arb.alerts.new_market_detector."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from cs2_arb.alerts.new_market_detector import NewMarketAlert, NewMarketDetector


# ---------------------------------------------------------------------------
# Minimal stub for PolymarketMarket — avoids needing a live API
# ---------------------------------------------------------------------------


@dataclass
class _Market:
    market_id: str
    team_a: str
    team_b: str
    yes_price: float = 0.6
    no_price: float = 0.4
    closes_at: str = "2026-12-31T00:00:00Z"
    volume_usd: float = 10_000.0


def _m(mid: str, team_a: str = "Team A", team_b: str = "Team B") -> _Market:
    return _Market(market_id=mid, team_a=team_a, team_b=team_b)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNewMarketDetectorFirstRun:
    """First call must establish baseline without returning alerts."""

    def test_first_call_returns_empty_list(self, tmp_path: Path) -> None:
        detector = NewMarketDetector(snapshot_path=tmp_path / "snap.json")
        alerts = detector.check_new_markets([_m("id-1"), _m("id-2")])
        assert alerts == []

    def test_first_call_creates_snapshot(self, tmp_path: Path) -> None:
        snap = tmp_path / "snap.json"
        detector = NewMarketDetector(snapshot_path=snap)
        detector.check_new_markets([_m("id-1"), _m("id-2")])
        assert snap.exists()
        saved = json.loads(snap.read_text())
        assert set(saved) == {"id-1", "id-2"}


class TestNewMarketDetectorSubsequentRuns:
    """Second+ calls diff against the snapshot."""

    def test_same_markets_returns_empty(self, tmp_path: Path) -> None:
        detector = NewMarketDetector(snapshot_path=tmp_path / "snap.json")
        markets = [_m("id-1"), _m("id-2")]
        detector.check_new_markets(markets)  # baseline
        alerts = detector.check_new_markets(markets)
        assert alerts == []

    def test_one_new_market_returns_alert(self, tmp_path: Path) -> None:
        detector = NewMarketDetector(snapshot_path=tmp_path / "snap.json")
        detector.check_new_markets([_m("id-1")])  # baseline
        alerts = detector.check_new_markets([_m("id-1"), _m("id-2", "NaVi", "FaZe")])
        assert len(alerts) == 1
        alert = alerts[0]
        assert isinstance(alert, NewMarketAlert)
        assert alert.market_id == "id-2"
        assert alert.question == "NaVi vs FaZe"

    def test_multiple_new_markets(self, tmp_path: Path) -> None:
        detector = NewMarketDetector(snapshot_path=tmp_path / "snap.json")
        detector.check_new_markets([_m("id-1")])  # baseline
        alerts = detector.check_new_markets([_m("id-1"), _m("id-2"), _m("id-3")])
        new_ids = {a.market_id for a in alerts}
        assert new_ids == {"id-2", "id-3"}

    def test_snapshot_updated_after_new_markets(self, tmp_path: Path) -> None:
        snap = tmp_path / "snap.json"
        detector = NewMarketDetector(snapshot_path=snap)
        detector.check_new_markets([_m("id-1")])  # baseline
        detector.check_new_markets([_m("id-1"), _m("id-2")])
        saved = set(json.loads(snap.read_text()))
        assert saved == {"id-1", "id-2"}

    def test_no_alerts_after_snapshot_updated(self, tmp_path: Path) -> None:
        """After a new market is detected, a third call should not re-alert it."""
        detector = NewMarketDetector(snapshot_path=tmp_path / "snap.json")
        detector.check_new_markets([_m("id-1")])  # baseline
        detector.check_new_markets([_m("id-1"), _m("id-2")])  # detects id-2
        alerts = detector.check_new_markets([_m("id-1"), _m("id-2")])  # no new
        assert alerts == []


class TestNewMarketAlertContents:
    """Alert payload fields must be correct."""

    def test_polymarket_url_format(self, tmp_path: Path) -> None:
        detector = NewMarketDetector(snapshot_path=tmp_path / "snap.json")
        detector.check_new_markets([])  # baseline with empty
        alerts = detector.check_new_markets([_m("abc-123")])
        assert len(alerts) == 1
        assert alerts[0].polymarket_url == "https://polymarket.com/event/abc-123"

    def test_question_format(self, tmp_path: Path) -> None:
        detector = NewMarketDetector(snapshot_path=tmp_path / "snap.json")
        detector.check_new_markets([])
        alerts = detector.check_new_markets([_m("x1", "Vitality", "G2")])
        assert alerts[0].question == "Vitality vs G2"

    def test_volume_usd_included(self, tmp_path: Path) -> None:
        detector = NewMarketDetector(snapshot_path=tmp_path / "snap.json")
        detector.check_new_markets([])
        market = _Market(market_id="m1", team_a="A", team_b="B", volume_usd=50_000.0)
        alerts = detector.check_new_markets([market])
        assert alerts[0].volume_usd == pytest.approx(50_000.0)


class TestNewMarketDetectorFilesystemErrors:
    """Filesystem failures must be silently swallowed."""

    def test_read_only_dir_returns_empty(self, tmp_path: Path) -> None:
        # Simulate unwriteable path by using a non-existent deeply nested dir
        snap = tmp_path / "nonexistent" / "deep" / "snap.json"
        detector = NewMarketDetector(snapshot_path=snap)
        # First call: no snapshot file → baseline, save fails silently
        alerts = detector.check_new_markets([_m("id-1")])
        assert alerts == []

    def test_corrupt_snapshot_treated_as_no_snapshot(self, tmp_path: Path) -> None:
        snap = tmp_path / "snap.json"
        snap.write_text("not valid json")
        detector = NewMarketDetector(snapshot_path=snap)
        # Corrupt file → treated as first run (no alerts)
        alerts = detector.check_new_markets([_m("id-1")])
        assert alerts == []


class TestClearSnapshot:
    def test_clear_removes_snapshot(self, tmp_path: Path) -> None:
        snap = tmp_path / "snap.json"
        detector = NewMarketDetector(snapshot_path=snap)
        detector.check_new_markets([_m("id-1")])
        assert snap.exists()
        detector.clear_snapshot()
        assert not snap.exists()

    def test_clear_on_nonexistent_is_safe(self, tmp_path: Path) -> None:
        snap = tmp_path / "missing.json"
        detector = NewMarketDetector(snapshot_path=snap)
        detector.clear_snapshot()  # should not raise
