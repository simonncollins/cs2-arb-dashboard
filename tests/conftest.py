"""Shared pytest fixtures for cs2-arb-dashboard tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_odds() -> dict:
    """Return sample odds data for testing."""
    return {
        "home_team": "Team Vitality",
        "away_team": "Natus Vincere",
        "home_win_prob": 0.55,
        "away_win_prob": 0.45,
    }
