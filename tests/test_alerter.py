"""Tests for cs2_arb/alerts/alerter.py — AlertManager."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from cs2_arb.alerts.alerter import AlertManager


# ---------------------------------------------------------------------------
# Stub opportunity
# ---------------------------------------------------------------------------


@dataclass
class _StubOpp:
    event_name: str = "NaVi vs Astralis"
    outcome: str = "team_a"
    edge_pct: float = 5.0
    ev_adjusted: float = 0.04
    poly_prob: float = 0.58
    book_name: str = "bet365"


# ---------------------------------------------------------------------------
# AlertManager tests
# ---------------------------------------------------------------------------


class TestAlertManager:
    def test_fires_when_edge_exceeds_threshold(self, tmp_path: Path) -> None:
        mgr = AlertManager(min_edge_pct=2.0, log_path=tmp_path / "log.json")
        opps = [_StubOpp(edge_pct=5.0)]
        fired = mgr.check_and_alert(opps)
        assert len(fired) == 1

    def test_does_not_fire_below_threshold(self, tmp_path: Path) -> None:
        mgr = AlertManager(min_edge_pct=2.0, log_path=tmp_path / "log.json")
        opps = [_StubOpp(edge_pct=1.5)]
        fired = mgr.check_and_alert(opps)
        assert len(fired) == 0

    def test_deduplication_within_cooldown(self, tmp_path: Path) -> None:
        mgr = AlertManager(min_edge_pct=2.0, cooldown_secs=3600, log_path=tmp_path / "log.json")
        opps = [_StubOpp()]
        # First call should fire
        fired1 = mgr.check_and_alert(opps)
        assert len(fired1) == 1
        # Second call within cooldown should not fire
        fired2 = mgr.check_and_alert(opps)
        assert len(fired2) == 0

    def test_fires_again_after_cooldown(self, tmp_path: Path) -> None:
        mgr = AlertManager(min_edge_pct=2.0, cooldown_secs=1, log_path=tmp_path / "log.json")
        opps = [_StubOpp()]
        fired1 = mgr.check_and_alert(opps)
        assert len(fired1) == 1
        # Manually expire the cooldown
        key = f"{opps[0].event_name}|{opps[0].outcome}"
        mgr._log[key] = time.time() - 2  # 2 seconds ago, cooldown is 1s
        fired2 = mgr.check_and_alert(opps)
        assert len(fired2) == 1

    def test_payload_contains_required_fields(self, tmp_path: Path) -> None:
        mgr = AlertManager(min_edge_pct=2.0, log_path=tmp_path / "log.json")
        fired = mgr.check_and_alert([_StubOpp()])
        assert len(fired) == 1
        payload = fired[0]
        assert "event_name" in payload
        assert "outcome" in payload
        assert "edge_pct" in payload
        assert "ev_adjusted" in payload
        assert "poly_prob" in payload
        assert "book_name" in payload
        assert "fired_at" in payload

    def test_log_persisted_to_disk(self, tmp_path: Path) -> None:
        log_path = tmp_path / "log.json"
        mgr = AlertManager(min_edge_pct=2.0, log_path=log_path)
        mgr.check_and_alert([_StubOpp()])
        assert log_path.exists()
        data = json.loads(log_path.read_text())
        assert isinstance(data, dict)
        assert len(data) == 1

    def test_log_loaded_from_disk_on_init(self, tmp_path: Path) -> None:
        log_path = tmp_path / "log.json"
        mgr = AlertManager(min_edge_pct=2.0, log_path=log_path)
        mgr.check_and_alert([_StubOpp()])
        # Create new instance — it should load from disk and deduplicate
        mgr2 = AlertManager(min_edge_pct=2.0, log_path=log_path)
        fired = mgr2.check_and_alert([_StubOpp()])
        assert len(fired) == 0

    def test_multiple_different_opps_both_fire(self, tmp_path: Path) -> None:
        mgr = AlertManager(min_edge_pct=2.0, log_path=tmp_path / "log.json")
        opps = [
            _StubOpp(event_name="NaVi vs Astralis", outcome="team_a"),
            _StubOpp(event_name="Vitality vs FaZe", outcome="team_b"),
        ]
        fired = mgr.check_and_alert(opps)
        assert len(fired) == 2

    def test_clear_log_resets_state(self, tmp_path: Path) -> None:
        log_path = tmp_path / "log.json"
        mgr = AlertManager(min_edge_pct=2.0, log_path=log_path)
        mgr.check_and_alert([_StubOpp()])
        mgr.clear_log()
        assert not log_path.exists()
        fired = mgr.check_and_alert([_StubOpp()])
        assert len(fired) == 1

    def test_empty_opportunities_returns_empty(self, tmp_path: Path) -> None:
        mgr = AlertManager(min_edge_pct=2.0, log_path=tmp_path / "log.json")
        fired = mgr.check_and_alert([])
        assert fired == []

    def test_corrupt_log_file_handled_gracefully(self, tmp_path: Path) -> None:
        log_path = tmp_path / "log.json"
        log_path.write_text("not valid json {{{{")
        mgr = AlertManager(min_edge_pct=2.0, log_path=log_path)
        # Should not raise — just starts fresh
        assert mgr._log == {}

    def test_edge_pct_exactly_at_threshold_fires(self, tmp_path: Path) -> None:
        mgr = AlertManager(min_edge_pct=2.0, log_path=tmp_path / "log.json")
        opps = [_StubOpp(edge_pct=2.0)]
        fired = mgr.check_and_alert(opps)
        assert len(fired) == 1
