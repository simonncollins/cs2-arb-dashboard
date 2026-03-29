"""New Polymarket CS2 market launch detector.

Compares the current list of Polymarket markets to a persisted snapshot and
returns any markets that are new since the last check. On the first run it
establishes a baseline without firing any alerts.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cs2_arb.api.polymarket import PolymarketMarket

logger = logging.getLogger(__name__)

_POLYMARKET_EVENT_BASE = "https://polymarket.com/event"


@dataclass
class NewMarketAlert:
    """Alert payload for a newly discovered Polymarket CS2 market.

    Attributes:
        market_id: Polymarket market identifier.
        question: Human-readable match question (e.g. "Team A vs Team B").
        volume_usd: Current market liquidity in USD.
        polymarket_url: Direct link to the market on Polymarket.
    """

    market_id: str
    question: str
    volume_usd: float
    polymarket_url: str


class NewMarketDetector:
    """Detects newly launched Polymarket CS2 markets by diffing against a snapshot.

    On the first call (or when no snapshot exists) it writes a baseline snapshot
    and returns an empty list — no alerts. On subsequent calls it returns
    :class:`NewMarketAlert` objects for any market not seen in the previous
    snapshot, then updates the snapshot.

    Filesystem errors (read-only filesystem, permissions, etc.) are caught and
    logged silently so the detector never raises inside a Streamlit app.

    Args:
        snapshot_path: Path to the JSON snapshot file. Defaults to
            ``new_market_snapshot.json`` in the current working directory.
    """

    def __init__(
        self,
        snapshot_path: str | Path = "new_market_snapshot.json",
    ) -> None:
        self._snapshot_path = Path(snapshot_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_new_markets(
        self,
        markets: list[PolymarketMarket],
    ) -> list[NewMarketAlert]:
        """Compare *markets* to the stored snapshot and return new-market alerts.

        Args:
            markets: Current list of Polymarket CS2 markets.

        Returns:
            A list of :class:`NewMarketAlert` for each market whose
            ``market_id`` was not present in the previous snapshot.  Returns
            an empty list on the first call (baseline) or when any filesystem
            operation fails.
        """
        current_ids: set[str] = {m.market_id for m in markets}
        known_ids = self._load_snapshot()

        if known_ids is None:
            # First run — establish baseline, fire no alerts.
            self._save_snapshot(current_ids)
            return []

        new_ids = current_ids - known_ids
        alerts = [
            NewMarketAlert(
                market_id=m.market_id,
                question=f"{m.team_a} vs {m.team_b}",
                volume_usd=getattr(m, "volume_usd", 0.0),
                polymarket_url=f"{_POLYMARKET_EVENT_BASE}/{m.market_id}",
            )
            for m in markets
            if m.market_id in new_ids
        ]

        # Update snapshot to include all current markets.
        self._save_snapshot(current_ids)
        return alerts

    def clear_snapshot(self) -> None:
        """Delete the snapshot file, resetting to first-run state."""
        try:
            self._snapshot_path.unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover
            logger.warning("Could not delete snapshot file: %s", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_snapshot(self) -> set[str] | None:
        """Load snapshot from disk.

        Returns:
            A set of known market IDs, or *None* if the snapshot does not
            exist yet (first run).
        """
        if not self._snapshot_path.exists():
            return None
        try:
            data = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
            return set(data)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to read market snapshot: %s", exc)
            return None

    def _save_snapshot(self, market_ids: set[str]) -> None:
        """Persist *market_ids* to the snapshot file.

        Silently swallows filesystem errors.
        """
        try:
            self._snapshot_path.write_text(
                json.dumps(sorted(market_ids), indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Failed to write market snapshot: %s", exc)
