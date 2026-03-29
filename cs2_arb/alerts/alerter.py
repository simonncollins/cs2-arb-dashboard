"""Alert manager for CS2 Arbitrage Dashboard.

Fires alerts when arbitrage opportunities exceed the configured edge threshold.
Deduplicates alerts so the same opportunity does not fire again within the
cooldown window (default 1 hour).

Alert log is persisted to ``alert_log.json`` (local filesystem or Streamlit
session state depending on environment).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Sentinel type — compatible with both MatchArbitrageOpportunity and
# TournamentArbitrageOpportunity once those branches are merged.
# ---------------------------------------------------------------------------


class _OppProto(Protocol):
    """Structural protocol for arbitrage opportunity objects."""

    event_name: str
    outcome: str
    edge_pct: float
    ev_adjusted: float
    poly_prob: float
    book_name: str


# ---------------------------------------------------------------------------
# Default constants
# ---------------------------------------------------------------------------

DEFAULT_COOLDOWN_SECS: int = 3600  # 1 hour between repeat alerts
DEFAULT_ALERT_LOG: Path = Path("alert_log.json")


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------


class AlertManager:
    """Manages alert deduplication and threshold checking.

    Attributes:
        min_edge_pct: Minimum edge percentage required to trigger an alert.
        cooldown_secs: Seconds before the same opportunity can re-alert.
        log_path: Path to the JSON alert log file.
    """

    def __init__(
        self,
        min_edge_pct: float = 2.0,
        cooldown_secs: int = DEFAULT_COOLDOWN_SECS,
        log_path: Path = DEFAULT_ALERT_LOG,
    ) -> None:
        self.min_edge_pct = min_edge_pct
        self.cooldown_secs = cooldown_secs
        self.log_path = log_path
        self._log: dict[str, float] = self._load_log()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_alert(self, opportunities: list[Any]) -> list[dict[str, Any]]:
        """Check opportunities and return those that should fire an alert.

        Filters by ``min_edge_pct`` and deduplicates by cooldown window.
        Side-effects: updates the log file for fired alerts.

        Args:
            opportunities: List of arbitrage opportunity objects.

        Returns:
            List of alert payload dicts for fired alerts. Empty if none.
        """
        fired: list[dict[str, Any]] = []
        now = time.time()

        for opp in opportunities:
            if opp.edge_pct < self.min_edge_pct:
                continue

            key = self._dedup_key(opp)
            last_fired = self._log.get(key, 0.0)
            if now - last_fired < self.cooldown_secs:
                continue

            payload = self._build_payload(opp, now)
            fired.append(payload)
            self._log[key] = now

        if fired:
            self._save_log()

        return fired

    def clear_log(self) -> None:
        """Clear the deduplication log (useful for testing)."""
        self._log = {}
        if self.log_path.exists():
            self.log_path.unlink()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _dedup_key(self, opp: Any) -> str:
        """Build a stable deduplication key from the opportunity."""
        return f"{opp.event_name}|{opp.outcome}"

    def _build_payload(self, opp: Any, ts: float) -> dict[str, Any]:
        """Build a rich alert payload dict."""
        return {
            "event_name": opp.event_name,
            "outcome": opp.outcome,
            "edge_pct": round(opp.edge_pct, 4),
            "ev_adjusted": round(getattr(opp, "ev_adjusted", 0.0), 6),
            "poly_prob": round(opp.poly_prob, 4),
            "book_name": getattr(opp, "book_name", ""),
            "fired_at": ts,
        }

    def _load_log(self) -> dict[str, float]:
        """Load the dedup log from disk, returning an empty dict on failure."""
        if not self.log_path.exists():
            return {}
        try:
            data = json.loads(self.log_path.read_text())
            if isinstance(data, dict):
                return {str(k): float(v) for k, v in data.items()}
        except (json.JSONDecodeError, ValueError):
            pass
        return {}

    def _save_log(self) -> None:
        """Persist the dedup log to disk."""
        try:
            self.log_path.write_text(json.dumps(self._log, indent=2))
        except OSError:
            # On Streamlit Cloud the filesystem may be read-only; fail silently.
            pass
